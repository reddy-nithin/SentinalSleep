"""AudioGen wrapper for generating therapeutic nature soundscapes.

This module wraps ``facebook/audiogen-medium`` (Meta AudioCraft) to produce
60-second ambient nature soundscapes from text prompts.  Generated audio is
written to ``data/audio_cache/soundscape/`` by the pre-generation script.

This replaces ``audioldm2_wrapper.py`` (deprecated in ADR-014).  AudioGen
is purpose-built for environmental sound effects, lives in the same AudioCraft
library as MusicGen (fewer moving parts), and is lighter (~1.5 GB vs 4 GB).

**Memory discipline (ADR-003):**
This wrapper is ONLY used by ``pregenerate.py``.  It is NEVER imported or
loaded during the live detection/verification loop.  Load only after MusicGen
has been unloaded.

Usage::

    gen = AudioGenWrapper()
    gen.generate_to_file(
        prompt="gentle ocean waves at night",
        output_path=Path("data/audio_cache/soundscape/ocean_gentle_v1.wav"),
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


class AudioGenLoadError(RuntimeError):
    """Raised when AudioGen cannot be loaded (e.g. OOM or missing audiocraft).

    Read the message for fallback instructions.
    """


class AudioGenWrapper:
    """Wraps facebook/audiogen-medium for text-to-audio soundscape generation.

    Downloads the model on first use and caches it in the HuggingFace cache
    directory (``~/.cache/huggingface/``).

    Memory footprint: ~1.5 GB.  **Load only after MusicGen is unloaded.**
    **Always call** :meth:`unload` when generation is complete.

    Attributes:
        device: Torch device string (``"mps"``, ``"cuda"``, or ``"cpu"``).
    """

    def __init__(
        self,
        model_id: str = config.AUDIOGEN_MODEL_ID,
        device: str | None = None,
    ) -> None:
        """Load the AudioGen model.

        Args:
            model_id: AudioCraft model identifier (e.g. ``"facebook/audiogen-medium"``).
            device: Torch device.  Defaults to ``config.select_device()``.

        Raises:
            AudioGenLoadError: If the model cannot be loaded (e.g., OOM or
                ``audiocraft`` is not installed).
        """
        self.device = device or config.select_device()
        logger.info("Loading AudioGen model %s on device=%s", model_id, self.device)

        try:
            from audiocraft.models import AudioGen  # noqa: PLC0415

            self._model = AudioGen.get_pretrained(model_id)
            # Move to target device; AudioCraft models have a ``to`` method.
            self._model.to(self.device)
        except Exception as exc:
            _msg = (
                f"AudioGen failed to load on device={self.device!r}: {exc}\n\n"
                "Possible causes:\n"
                "  • audiocraft not installed: add it to pyproject.toml and run uv sync\n"
                "  • Out of memory on M2 8 GB: run pregenerate_cache.py on Colab T4\n"
                "    (see notebooks/pregenerate_on_colab.ipynb)\n"
                "  • Model download failed: check network and HF_TOKEN if rate-limited\n\n"
                "Fallback options:\n"
                "  1. Re-run with --use-synthetic-soundscape for pink-noise placeholders\n"
                "  2. Download royalty-free WAVs from Freesound and place them in\n"
                "     data/audio_cache/soundscape/ manually, then re-run the mixer.\n"
                "     Required filenames: ocean_gentle_v1.wav, rain_soft_v1.wav,\n"
                "     forest_night_v1.wav  (each ≥ 60 s, mono, any sample rate)."
            )
            raise AudioGenLoadError(_msg) from exc

        # AudioGen outputs at 16 kHz (same as AudioLDM2; resample path unchanged).
        self._native_sr: int = 16_000
        logger.info(
            "AudioGen loaded on device=%s, native_sr=%d Hz",
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
    ) -> tuple[np.ndarray, int]:
        """Generate a nature soundscape from a text prompt.

        Args:
            prompt:     Text prompt describing the desired soundscape.
            duration_s: Target duration in seconds.

        Returns:
            ``(audio_array, sample_rate)`` where ``audio_array`` is a 1-D
            float32 array and ``sample_rate`` is 16 000 Hz (native).
        """
        logger.info(
            "Generating %.0fs soundscape — prompt: %.80s…", duration_s, prompt
        )

        self._model.set_generation_params(duration=duration_s)
        # generate() returns a tensor of shape (batch, channels, samples).
        wav = self._model.generate(descriptions=[prompt])

        # Take first item in batch, first channel → 1-D numpy float32.
        audio: np.ndarray = wav[0, 0].cpu().numpy().astype(np.float32)
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
    ) -> Path:
        """Generate a soundscape and write to a WAV file at ``target_sr``.

        Args:
            output_path: Destination WAV file path.  Parent directories are
                created if they don't exist.
            prompt:      Text prompt for generation.
            duration_s:  Target clip duration in seconds.
            target_sr:   Output sample rate in Hz (default: 44 100 Hz).

        Returns:
            Resolved path to the written WAV file.
        """
        import librosa  # noqa: PLC0415

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        audio, native_sr = self.generate(prompt=prompt, duration_s=duration_s)

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
        """Unload the model from memory.

        Call this immediately after generation to free ~1.5 GB.  After calling
        this the instance must not be used again.
        """
        import torch  # noqa: PLC0415

        logger.info("Unloading AudioGen model from memory")
        del self._model
        self._model = None  # type: ignore[assignment]
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("AudioGen unloaded — memory freed")
