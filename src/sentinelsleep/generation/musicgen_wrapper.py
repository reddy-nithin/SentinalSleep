"""MusicGen wrapper for generating therapeutic ambient music clips.

This module wraps ``facebook/musicgen-small`` to produce 60-second ambient music
clips from text prompts.  Generated audio is written to ``data/audio_cache/music/``
by the pre-generation script.

**Memory discipline (ADR-003):**
This wrapper is ONLY used by ``pregenerate.py``.  It is NEVER imported or loaded
during the live detection/verification loop.  After generation is complete, call
``unload()`` before loading AudioLDM2 to stay within the M2 8 GB budget.

Usage::

    gen = MusicGenWrapper()
    gen.generate_to_file(
        prompt=\"slow calming ambient music, 60 BPM\",
        output_path=Path(\"data/audio_cache/music/ambient_v1.wav\"),
        duration_s=60,
    )
    gen.unload()   # ← always call before loading the next heavy model
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from sentinelsleep import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level prompt constants (mirrors config.MUSIC_PROMPTS, kept here for
# direct import by callers that only touch the generation layer).
# ---------------------------------------------------------------------------

DEFAULT_PROMPT = config.MUSIC_PROMPTS[0]


class MusicGenWrapper:
    """Wraps facebook/musicgen-small for text-to-music generation.

    Downloads the model on first use and caches it in the HuggingFace cache
    directory (``~/.cache/huggingface/``).

    Memory footprint: ~1.2 GB.  **Always call** :meth:`unload` after generation
    is complete so subsequent models (e.g., AudioLDM2) can load without OOM.

    Attributes:
        device: Torch device string (``\"mps\"`` or ``\"cpu\"``).
    """

    def __init__(
        self,
        model_id: str = config.MUSICGEN_MODEL_ID,
        device: str | None = None,
    ) -> None:
        """Load the MusicGen model and processor.

        Args:
            model_id: HuggingFace model identifier.
            device: Torch device.  Defaults to ``config.select_device()``.

        Raises:
            RuntimeError: If the model fails to load.
        """
        import torch
        from transformers import AutoProcessor, MusicgenForConditionalGeneration

        self.device = device or config.select_device()
        logger.info("Loading MusicGen model %s on device=%s", model_id, self.device)

        self._processor = AutoProcessor.from_pretrained(model_id)
        self._model = MusicgenForConditionalGeneration.from_pretrained(model_id)

        try:
            self._model = self._model.to(self.device)
        except (RuntimeError, Exception) as exc:
            logger.warning(
                "Failed to move MusicGen to %s (%s); falling back to cpu.",
                self.device,
                exc,
            )
            self.device = "cpu"
            self._model = self._model.to("cpu")

        self._model.eval()

        # MusicGen's native output sample rate (32 kHz).
        self._native_sr: int = self._model.config.audio_encoder.sampling_rate
        logger.info(
            "MusicGen loaded on device=%s, native_sr=%d Hz",
            self.device,
            self._native_sr,
        )

        self._torch = torch

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str = DEFAULT_PROMPT,
        duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
    ) -> tuple[np.ndarray, int]:
        """Generate a therapeutic ambient music clip from a text prompt.

        Args:
            prompt:    Text prompt describing the desired music style.
            duration_s: Target duration in seconds.  The model generates
                        ``int(duration_s * native_sr / 50)`` tokens; actual
                        output length may differ by up to ±1s.

        Returns:
            ``(audio_array, sample_rate)`` where ``audio_array`` is a 1-D
            float32 array and ``sample_rate`` is the model's native rate
            (32 000 Hz).
        """
        logger.info("Generating %.0fs music clip — prompt: %.80s…", duration_s, prompt)

        inputs = self._processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # max_new_tokens ≈ duration_s * native_sr / frame_rate
        # MusicGen-small uses a frame rate of 50 tokens/s.
        max_new_tokens = int(duration_s * 50)

        with self._torch.inference_mode():
            audio_values = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
            )

        # audio_values shape: (batch, channels, samples) — take batch 0, ch 0
        audio: np.ndarray = audio_values[0, 0].cpu().numpy().astype(np.float32)
        logger.info(
            "Generated %.2f s of music at %d Hz (%d samples)",
            len(audio) / self._native_sr,
            self._native_sr,
            len(audio),
        )
        return audio, self._native_sr

    def generate_to_file(
        self,
        output_path: Path,
        prompt: str = DEFAULT_PROMPT,
        duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
        target_sr: int = config.INTERVENTION_SAMPLE_RATE,
    ) -> Path:
        """Generate audio and write to a WAV file at ``target_sr``.

        The native 32 kHz output is resampled to ``target_sr`` (44.1 kHz by
        default) so all cached files share a consistent sample rate.

        Args:
            output_path: Destination WAV file path.  Parent directories are
                created if they don't exist.
            prompt:      Text prompt for generation.
            duration_s:  Target clip duration in seconds.
            target_sr:   Output sample rate in Hz.

        Returns:
            Resolved path to the written WAV file.
        """
        import librosa  # noqa: PLC0415 — lazy import; keep startup cost minimal

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio, native_sr = self.generate(prompt=prompt, duration_s=duration_s)

        if native_sr != target_sr:
            logger.info(
                "Resampling music %d Hz → %d Hz", native_sr, target_sr
            )
            audio = librosa.resample(audio, orig_sr=native_sr, target_sr=target_sr)

        # Trim or pad to exact target length.
        target_samples = int(duration_s * target_sr)
        if len(audio) >= target_samples:
            audio = audio[:target_samples]
        else:
            # Tile to fill — unlikely but safe.
            repeats = (target_samples // len(audio)) + 1
            audio = np.tile(audio, repeats)[:target_samples]

        sf.write(str(output_path), audio, target_sr, subtype="PCM_16")
        logger.info(
            "Wrote music clip → %s  (%.1f s, %d Hz, PCM_16)",
            output_path.name,
            len(audio) / target_sr,
            target_sr,
        )
        return output_path.resolve()

    def unload(self) -> None:
        """Unload the model from memory.

        Call this immediately after all generation tasks are complete to free
        ~1.2 GB before loading the next model.  After calling this method the
        instance must not be used again.
        """
        import torch  # noqa: PLC0415

        logger.info("Unloading MusicGen model from memory")
        del self._model
        del self._processor
        self._model = None  # type: ignore[assignment]
        self._processor = None  # type: ignore[assignment]
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        logger.info("MusicGen unloaded — memory freed")
