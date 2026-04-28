"""audeering wav2vec2 dimensional emotion model wrapper for the verification layer.

This module wraps ``audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim`` which
predicts three continuous emotional dimensions (valence, arousal, dominance) for any
audio clip.  The verification layer uses these to confirm that a flagged event has
the emotional profile of a nightmare (low valence, high arousal, low dominance).

**Custom architecture note:**
The audeering model uses a custom ``RegressionHead`` that is not part of the standard
HuggingFace transformers library.  The ``RegressionHead`` and ``EmotionModel`` classes
below must be defined locally so that ``from_pretrained`` can reconstruct the weights
correctly.  This is standard practice for audEERING models; see their w2v2-how-to repo.

**Output dimension order:**
The model internally predicts [arousal, dominance, valence].  ``EmotionAnalyzer``
re-orders these into the (valence, arousal, dominance) convention used throughout
SentinelSleep (matching the config threshold naming and plan §7 Phase 2).

Memory budget: This model is ~660 MB.  It co-resides with the AST model (~350 MB)
during live operation, staying within the M2 8GB budget.  Never load MusicGen or
AudioLDM2 from this context.  See CLAUDE.md and ADR-003.
"""

from __future__ import annotations

import logging
import time
from typing import NamedTuple

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoFeatureExtractor, Wav2Vec2Model, Wav2Vec2PreTrainedModel

from sentinelsleep import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom model architecture required by audeering wav2vec2 emotion model
# ---------------------------------------------------------------------------


class RegressionHead(nn.Module):
    """Prediction head for dimensional emotion regression.

    Architecture matches the audEERING checkpoint exactly:
    Dropout → Dense(hidden, hidden) → Tanh → Dropout → Linear(hidden, num_labels).

    Args:
        config: HuggingFace model config carrying ``hidden_size``,
            ``final_dropout``, and ``num_labels``.
    """

    def __init__(self, model_config: object) -> None:
        super().__init__()
        self.dense = nn.Linear(model_config.hidden_size, model_config.hidden_size)  # type: ignore[attr-defined]
        self.dropout = nn.Dropout(model_config.final_dropout)  # type: ignore[attr-defined]
        self.out_proj = nn.Linear(model_config.hidden_size, model_config.num_labels)  # type: ignore[attr-defined]

    def forward(self, features: torch.Tensor, **kwargs: object) -> torch.Tensor:  # noqa: ARG002
        x = self.dropout(features)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        return self.out_proj(x)


class EmotionModel(Wav2Vec2PreTrainedModel):
    """wav2vec2 backbone + regression head for dimensional emotion prediction.

    Pooling strategy: mean over time steps of the final hidden state, as used
    in the audEERING w2v2-how-to reference implementation.

    Outputs logits of shape ``(batch, num_labels)`` where num_labels=3
    corresponding to [arousal, dominance, valence] — note the model-internal order.
    ``EmotionAnalyzer.predict()`` re-orders to (valence, arousal, dominance).
    """

    def __init__(self, model_config: object) -> None:
        super().__init__(model_config)  # type: ignore[arg-type]
        self.wav2vec2 = Wav2Vec2Model(model_config)  # type: ignore[arg-type]
        self.classifier = RegressionHead(model_config)
        self.init_weights()

    def forward(
        self,
        input_values: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Run forward pass and return raw regression logits.

        Args:
            input_values: Float tensor of shape ``(batch, seq_len)`` at 16 kHz.
            attention_mask: Optional mask for padded sequences.

        Returns:
            Tensor of shape ``(batch, 3)`` in [arousal, dominance, valence] order.
        """
        outputs = self.wav2vec2(input_values, attention_mask=attention_mask)
        hidden_states = outputs.last_hidden_state  # (batch, time, hidden)
        # Mean-pool over time dimension
        pooled = hidden_states.mean(dim=1)  # (batch, hidden)
        return self.classifier(pooled)


# ---------------------------------------------------------------------------
# EmotionResult NamedTuple
# ---------------------------------------------------------------------------


class EmotionResult(NamedTuple):
    """Dimensional emotion prediction for a single audio chunk.

    All three values are in [0, 1] (the model is trained to output in this range).

    Attributes:
        valence:   Positive (1.0) vs. negative (0.0) emotional state.
        arousal:   Excited / activated (1.0) vs. calm (0.0).
        dominance: In-control (1.0) vs. submissive / powerless (0.0).
    """

    valence: float
    arousal: float
    dominance: float


# ---------------------------------------------------------------------------
# EmotionAnalyzer
# ---------------------------------------------------------------------------


def _ensure_mono_float32(audio: np.ndarray) -> np.ndarray:
    """Convert audio to mono float32 in [-1, 1].

    Args:
        audio: Input array, possibly stereo (2-D) or int16.

    Returns:
        1-D float32 array.
    """
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
        if audio.max() > 1.0:
            audio = audio / 32_768.0
    return audio


class EmotionAnalyzer:
    """Wraps the audeering wav2vec2 model for dimensional emotion inference.

    Downloads the model on first use and caches it in the HuggingFace cache
    directory (``~/.cache/huggingface/``).

    Usage::

        analyzer = EmotionAnalyzer()
        audio, sr = soundfile.read("clip.wav")
        result = analyzer.predict(audio, sr)
        # result.valence, result.arousal, result.dominance → floats in [0, 1]

    Attributes:
        device: The torch device being used (``"mps"`` or ``"cpu"``).
    """

    def __init__(
        self,
        model_id: str = config.EMOTION_MODEL_ID,
        device: str | None = None,
    ) -> None:
        """Load the audeering wav2vec2 emotion model.

        Args:
            model_id: HuggingFace model identifier.
            device: Torch device string.  Defaults to ``config.select_device()``.

        Raises:
            RuntimeError: If the model cannot be loaded on any available device.
        """
        self.device = device or config.select_device()
        logger.info(
            "Loading emotion model %s on device=%s", model_id, self.device
        )

        self._feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
        self._model = EmotionModel.from_pretrained(model_id)

        try:
            self._model = self._model.to(self.device)
        except (RuntimeError, Exception) as exc:
            logger.warning(
                "Failed to move emotion model to %s (%s); falling back to cpu.",
                self.device,
                exc,
            )
            self.device = "cpu"
            self._model = self._model.to("cpu")

        self._model.eval()
        logger.info("Emotion model loaded on device=%s", self.device)

    def predict(
        self,
        audio: np.ndarray,
        sample_rate: int = config.SAMPLE_RATE,
    ) -> EmotionResult:
        """Predict dimensional emotion scores for an audio chunk.

        Audio is converted to mono float32 and resampled to 16 kHz if needed.
        The model has no strict minimum length; very short clips may yield less
        reliable predictions.  For the SentinelSleep pipeline, 2-second windows
        (32 000 samples at 16 kHz) are the standard input size.

        Args:
            audio: Float32 or int16 mono/stereo audio array.
            sample_rate: Sample rate of ``audio``.  Defaults to 16 000 Hz.

        Returns:
            :class:`EmotionResult` with (valence, arousal, dominance) in [0, 1].
        """
        audio = _ensure_mono_float32(audio)

        if sample_rate != 16_000:
            import librosa  # noqa: PLC0415 — lazy import: keep startup cost low

            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=16_000)

        inputs = self._feature_extractor(
            audio,
            sampling_rate=16_000,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs["input_values"].to(self.device)

        with torch.inference_mode():
            logits = self._model(input_values)

        # Model output order: [arousal, dominance, valence]
        # Re-order to (valence, arousal, dominance) for API consistency.
        scores: np.ndarray = logits.squeeze().cpu().numpy()
        arousal = float(np.clip(scores[0], 0.0, 1.0))
        dominance = float(np.clip(scores[1], 0.0, 1.0))
        valence = float(np.clip(scores[2], 0.0, 1.0))

        return EmotionResult(valence=valence, arousal=arousal, dominance=dominance)

    def predict_timed(
        self,
        audio: np.ndarray,
        sample_rate: int = config.SAMPLE_RATE,
    ) -> tuple[EmotionResult, float]:
        """Predict emotion and return (result, elapsed_seconds).

        Convenience wrapper for latency profiling during Phase 2 acceptance.

        Args:
            audio: Audio array (see :meth:`predict`).
            sample_rate: Sample rate of ``audio``.

        Returns:
            Tuple of (:class:`EmotionResult`, wall-clock seconds for inference).
        """
        start = time.perf_counter()
        result = self.predict(audio, sample_rate)
        elapsed = time.perf_counter() - start
        return result, elapsed
