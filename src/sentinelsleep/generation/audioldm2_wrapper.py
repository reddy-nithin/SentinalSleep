"""AudioLDM2 wrapper for generating therapeutic nature soundscapes.

This module wraps ``cvssp/audioldm2`` to produce 60-second ambient nature
soundscapes from text prompts.  Generated audio is written to
``data/audio_cache/soundscape/`` by the pre-generation script.

**Memory discipline (ADR-003):**
This wrapper is ONLY used by ``pregenerate.py``.  It is NEVER imported or
loaded during the live detection/verification loop.  AudioLDM2 is ~4 GB and
should only be loaded *after* MusicGen has been unloaded.

**M2 8 GB fallback:**
If the model fails to load due to OOM, the class raises ``AudioLDM2LoadError``
with clear instructions.  The fallback strategy per the project risk register
is to:

  1. Pre-generate on GCP (see SENTINELSLEEP_PLAN.md §14)
  2. Or substitute royalty-free WAV files downloaded from Freesound into
     ``data/audio_cache/soundscape/`` manually.

Usage::

    gen = AudioLDM2Wrapper()
    gen.generate_to_file(
        prompt=\"gentle ocean waves at night\",
        output_path=Path(\"data/audio_cache/soundscape/ocean_gentle_v1.wav\"),
        duration_s=60,
    )
    gen.unload()
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from sentinelsleep import config

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = config.SOUNDSCAPE_PROMPTS[0]


class AudioLDM2LoadError(RuntimeError):
    """Raised when AudioLDM2 cannot be loaded (typically OOM on M2 8 GB).

    Read the message for fallback instructions.
    """


class AudioLDM2Wrapper:
    """Wraps cvssp/audioldm2 for text-to-audio soundscape generation.

    Downloads the model on first use and caches it in the HuggingFace cache
    directory (``~/.cache/huggingface/``).

    Memory footprint: ~4 GB.  **Load only after MusicGen is unloaded.**
    **Always call** :meth:`unload` when generation is complete.

    Attributes:
        device: Torch device string (``\"mps\"`` or ``\"cpu\"``).
    """

    def __init__(
        self,
        model_id: str = config.AUDIOLDM2_MODEL_ID,
        device: str | None = None,
    ) -> None:
        """Load the AudioLDM2 pipeline.

        Args:
            model_id: HuggingFace model identifier.
            device: Torch device.  Defaults to ``config.select_device()``.

        Raises:
            AudioLDM2LoadError: If the model cannot be loaded (e.g., OOM).
        """
        import torch
        from diffusers import AudioLDM2Pipeline

        self.device = device or config.select_device()
        logger.info("Loading AudioLDM2 pipeline %s on device=%s", model_id, self.device)

        try:
            self._pipe = AudioLDM2Pipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float32,  # MPS requires float32
            )
            self._pipe = self._pipe.to(self.device)
        except (RuntimeError, Exception) as exc:
            _msg = (
                f"AudioLDM2 failed to load on device={self.device!r}: {exc}\n\n"
                "This is likely an out-of-memory error on M2 8 GB RAM.\n"
                "Fallback options:\n"
                "  1. Pre-generate on GCP: see SENTINELSLEEP_PLAN.md §14.\n"
                "  2. Download royalty-free WAVs from Freesound and place them in\n"
                "     data/audio_cache/soundscape/ manually, then re-run the mixer.\n"
                "     Required filenames: ocean_gentle_v1.wav, rain_soft_v1.wav,\n"
                "     forest_night_v1.wav  (each ≥ 60 s, mono, any sample rate)."
            )
            raise AudioLDM2LoadError(_msg) from exc

        self._torch = torch
        self._native_sr: int = 16_000  # AudioLDM2 outputs at 16 kHz
        logger.info(
            "AudioLDM2 loaded on device=%s, native_sr=%d Hz",
            self.device,
            self._native_sr,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str = DEFAULT_PROMPT,
        duration_s: float = float(config.INTERVENTION_DURATION_SECONDS),
        num_inference_steps: int = 200,
        guidance_scale: float = 3.5,
    ) -> tuple[np.ndarray, int]:
        """Generate a nature soundscape from a text prompt.

        Args:
            prompt:               Text prompt describing the soundscape.
            duration_s:           Target duration in seconds.
            num_inference_steps:  Diffusion steps — fewer is faster but lower quality.
                                  200 is the recommended default for AudioLDM2.
            guidance_scale:       Classifier-free guidance scale.  3.5–4.0 works well
                                  for ambient sounds.

        Returns:
            ``(audio_array, sample_rate)`` where ``audio_array`` is a 1-D
            float32 array and ``sample_rate`` is 16 000 Hz (native).
        """
        logger.info(
            "Generating %.0fs soundscape — prompt: %.80s…", duration_s, prompt
        )

        result = self._pipe(
            prompt,
            num_inference_steps=num_inference_steps,
            audio_length_in_s=duration_s,
            guidance_scale=guidance_scale,
            num_waveforms_per_prompt=1,
        )

        # result.audios shape: (batch, samples) — take first waveform
        audio: np.ndarray = result.audios[0].astype(np.float32)
        logger.info(
            "Generated %.2f s of soundscape at %d Hz (%d samples)",
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
        num_inference_steps: int = 200,
        guidance_scale: float = 3.5,
    ) -> Path:
        """Generate a soundscape and write to a WAV file at ``target_sr``.

        Args:
            output_path: Destination WAV file path.  Parent directories are
                created if they don't exist.
            prompt:      Text prompt for generation.
            duration_s:  Target clip duration in seconds.
            target_sr:   Output sample rate in Hz.
            num_inference_steps: Diffusion steps.
            guidance_scale:      CFG scale.

        Returns:
            Resolved path to the written WAV file.
        """
        import librosa  # noqa: PLC0415

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio, native_sr = self.generate(
            prompt=prompt,
            duration_s=duration_s,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )

        if native_sr != target_sr:
            logger.info(
                "Resampling soundscape %d Hz → %d Hz", native_sr, target_sr
            )
            audio = librosa.resample(audio, orig_sr=native_sr, target_sr=target_sr)

        # Trim or pad to exact target length.
        target_samples = int(duration_s * target_sr)
        if len(audio) >= target_samples:
            audio = audio[:target_samples]
        else:
            repeats = (target_samples // len(audio)) + 1
            audio = np.tile(audio, repeats)[:target_samples]

        sf.write(str(output_path), audio, target_sr, subtype="PCM_16")
        logger.info(
            "Wrote soundscape → %s  (%.1f s, %d Hz, PCM_16)",
            output_path.name,
            len(audio) / target_sr,
            target_sr,
        )
        return output_path.resolve()

    def unload(self) -> None:
        """Unload the pipeline from memory.

        Call this immediately after generation to free ~4 GB.  After calling
        this the instance must not be used again.
        """
        import torch  # noqa: PLC0415

        logger.info("Unloading AudioLDM2 pipeline from memory")
        del self._pipe
        self._pipe = None  # type: ignore[assignment]
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        logger.info("AudioLDM2 unloaded — memory freed")
