"""MIT AST model wrapper for real-time AudioSet sound classification.

This module wraps ``MIT/ast-finetuned-audioset-10-10-0.4593`` for inference
on 2-second audio windows. The classifier is designed to remain loaded for
the entire duration of the live detection loop.

Memory constraint: This model (~350 MB) plus the verification model (~660 MB)
are the ONLY models that may be resident during live operation. Never load
MusicGen or AudioLDM2 from this context. See CLAUDE.md.
"""

from __future__ import annotations

import logging
import time

import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

from sentinelsleep import config
from sentinelsleep.detection.audioset_labels import (
    build_distress_weight_map,
    extract_label_map,
    find_unmatched_distress_labels,
)

logger = logging.getLogger(__name__)


def _ensure_mono_float32(audio: np.ndarray) -> np.ndarray:
    """Convert audio to mono float32 in [-1, 1].

    Args:
        audio: Input audio array. May be int16, float32, or stereo (2-D).

    Returns:
        1-D float32 array.
    """
    if audio.ndim == 2:
        # Stereo → mono by averaging channels
        audio = audio.mean(axis=1)
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
        if audio.max() > 1.0:
            # Assume int16 range; normalise to [-1, 1]
            audio = audio / 32768.0
    return audio


class ASTClassifier:
    """Wraps the MIT AST model for multi-label AudioSet sound classification.

    Downloads the model on first use and caches it in the Hugging Face cache
    directory (``~/.cache/huggingface/``).

    Usage::

        clf = ASTClassifier()
        audio, sr = soundfile.read("clip.wav")
        probs = clf.classify(audio, sr)
        # probs is {label_name: probability} for all 527 AudioSet classes

    Attributes:
        device: The torch device being used (``"mps"`` or ``"cpu"``).
        id2label: {label_id: label_name} mapping from the model config.
    """

    def __init__(
        self,
        model_id: str = config.AST_MODEL_ID,
        device: str | None = None,
    ) -> None:
        """Load the AST feature extractor and model.

        Args:
            model_id: HuggingFace model identifier.
            device: Torch device string. Defaults to ``config.select_device()``.

        Raises:
            RuntimeError: If the model fails to load on the requested device
                and the CPU fallback also fails.
        """
        self.device = device or config.select_device()
        logger.info("Loading AST model %s on device=%s", model_id, self.device)

        self._feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
        self._model = AutoModelForAudioClassification.from_pretrained(model_id)

        try:
            self._model = self._model.to(self.device)
        except (RuntimeError, Exception) as exc:
            # MPS can occasionally fail on first use; fall back to CPU.
            logger.warning(
                "Failed to move model to %s (%s); falling back to cpu.",
                self.device,
                exc,
            )
            self.device = "cpu"
            self._model = self._model.to("cpu")

        self._model.eval()
        self.id2label: dict[int, str] = extract_label_map(self._model.config)

        # Warn once about any distress classes that have no model label match.
        unmatched = find_unmatched_distress_labels(
            self.id2label, config.DISTRESS_CLASS_WEIGHTS
        )
        if unmatched:
            logger.warning(
                "Distress classes not found in model labels (check spelling): %s",
                unmatched,
            )

        # Pre-compute {label_id: weight} for fast DSS lookup.
        self._distress_weight_map: dict[int, float] = build_distress_weight_map(
            self.id2label, config.DISTRESS_CLASS_WEIGHTS
        )
        logger.info(
            "AST loaded. %d distress classes mapped.",
            len(self._distress_weight_map),
        )

    def classify(
        self,
        audio: np.ndarray,
        sample_rate: int = config.SAMPLE_RATE,
    ) -> dict[str, float]:
        """Classify an audio chunk and return per-class probabilities.

        Input audio is resampled to 16 kHz if needed. For 2-second windows
        the feature extractor zero-pads to the model's expected length (≈10s).

        Args:
            audio: Float32 or int16 mono (or stereo) audio array.
            sample_rate: Sample rate of ``audio``. Defaults to
                ``config.SAMPLE_RATE`` (16 000 Hz).

        Returns:
            ``{class_name: probability}`` for all 527 AudioSet classes.
            Probabilities are independent sigmoid scores, not a distribution.
        """
        audio = _ensure_mono_float32(audio)

        if sample_rate != 16_000:
            import librosa  # noqa: PLC0415 — lazy to keep import cost outside live loop

            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=16_000)

        inputs = self._feature_extractor(
            audio,
            sampling_rate=16_000,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.inference_mode():
            logits = self._model(**inputs).logits

        # AudioSet uses multi-label classification → sigmoid, not softmax.
        probs: np.ndarray = torch.sigmoid(logits).squeeze().cpu().numpy()

        return {self.id2label[i]: float(probs[i]) for i in range(len(probs))}

    def classify_timed(
        self,
        audio: np.ndarray,
        sample_rate: int = config.SAMPLE_RATE,
    ) -> tuple[dict[str, float], float]:
        """Classify audio and return (probabilities, elapsed_seconds).

        Convenience wrapper for latency profiling during Phase 1 acceptance.

        Args:
            audio: Audio array (see :meth:`classify`).
            sample_rate: Sample rate of ``audio``.

        Returns:
            Tuple of (probabilities dict, wall-clock seconds for inference).
        """
        start = time.perf_counter()
        probs = self.classify(audio, sample_rate)
        elapsed = time.perf_counter() - start
        return probs, elapsed
