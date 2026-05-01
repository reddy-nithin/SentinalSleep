"""Audio stream sources for the SentinelSleep orchestration loop.

Provides two interchangeable audio sources that both yield fixed-size
numpy float32 chunks:

``MicSource``
    Captures live mic audio via ``sounddevice`` into a rolling 2-second
    ring buffer.  Used in production (Phase 4 live loop).

``FileSource``
    Reads a WAV file and yields 2-second chunks at real-time pace via
    ``time.sleep``.  Used in simulation / demo mode (Phase 6) and in the
    integration test ``tests/test_runner.py``.

Both sources implement the :class:`AudioSource` protocol so the runner
can swap between them without changes.

Usage::

    from sentinelsleep.orchestrator.audio_stream import FileSource

    src = FileSource(Path("data/test_fixtures/nightmare_severe.wav"))
    for chunk in src.chunks():
        process(chunk)   # chunk is np.ndarray, shape (n_samples,), float32

``sounddevice`` is **not** imported at module level so that importing
this module in non-audio environments (CI, dashboard) does not fail.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Generator, Protocol

import numpy as np

from sentinelsleep import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class AudioSource(Protocol):
    """Protocol that both mic and file sources implement."""

    def chunks(self) -> Generator[np.ndarray, None, None]:
        """Yield fixed-size float32 audio chunks (shape ``(WINDOW_SAMPLES,)``)."""
        ...

    def close(self) -> None:
        """Release any resources held by this source."""
        ...


# ---------------------------------------------------------------------------
# FileSource — reads a WAV, yields chunks at real-time pace
# ---------------------------------------------------------------------------


class FileSource:
    """Yield 2-second chunks from a WAV file at real-time pace.

    Audio is resampled to ``config.SAMPLE_RATE`` (16 kHz) if the file's
    native sample rate differs.  The final partial chunk is zero-padded
    to ``config.WINDOW_SAMPLES``.

    Args:
        path:       Path to the WAV file to stream.
        realtime:   If ``True`` (default), sleep between chunks to mimic
                    real-time streaming.  Set ``False`` in unit tests for
                    maximum speed.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """

    def __init__(self, path: Path, *, realtime: bool = True) -> None:
        import soundfile as sf  # noqa: PLC0415

        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"FileSource: file not found: {self._path}")

        self._realtime = realtime
        self._data, self._sr = sf.read(str(self._path), dtype="float32", always_2d=False)
        # Ensure mono
        if self._data.ndim > 1:
            self._data = self._data.mean(axis=1)

        # Resample to 16 kHz if needed
        if self._sr != config.SAMPLE_RATE:
            self._data = _resample(self._data, self._sr, config.SAMPLE_RATE)
            self._sr = config.SAMPLE_RATE

        logger.info(
            "FileSource: %s  %.1fs  %d Hz  %d samples",
            self._path.name,
            len(self._data) / self._sr,
            self._sr,
            len(self._data),
        )

    def chunks(self) -> Generator[np.ndarray, None, None]:
        """Yield ``config.WINDOW_SAMPLES``-length float32 chunks from the file.

        The last chunk is zero-padded if the file length is not an exact
        multiple of ``config.WINDOW_SAMPLES``.
        """
        window = config.WINDOW_SAMPLES
        sleep_s = config.WINDOW_SECONDS  # real-time pace
        pos = 0
        total = len(self._data)

        while pos < total:
            chunk = self._data[pos : pos + window]
            if len(chunk) < window:
                # Zero-pad final chunk
                padded = np.zeros(window, dtype=np.float32)
                padded[: len(chunk)] = chunk
                chunk = padded

            if self._realtime:
                time.sleep(sleep_s)

            yield chunk
            pos += window

    def close(self) -> None:
        """No-op for FileSource (data is held in memory)."""
        pass


# ---------------------------------------------------------------------------
# MicSource — live sounddevice capture
# ---------------------------------------------------------------------------


class MicSource:
    """Capture live microphone audio into a rolling ring buffer.

    Uses ``sounddevice.InputStream`` in callback mode and exposes a
    blocking ``chunks()`` generator that yields complete 2-second windows.

    Args:
        device: sounddevice device index or name (None = system default).

    Notes:
        * sounddevice is imported lazily so this module can be imported
          safely in non-audio environments.
        * Buffer size is 4× the window size to tolerate callback jitter.
    """

    _BUFFER_MULTIPLIER = 4

    def __init__(self, device: int | str | None = None) -> None:
        import queue  # stdlib — always available

        self._queue: queue.Queue[np.ndarray] = queue.Queue(
            maxsize=self._BUFFER_MULTIPLIER
        )
        self._device = device
        self._stream = None  # opened lazily in chunks()

    def _start(self) -> None:
        import sounddevice as sd  # noqa: PLC0415

        def _callback(
            indata: np.ndarray,
            frames: int,
            time_info: object,
            status: object,
        ) -> None:
            if status:
                logger.warning("sounddevice callback status: %s", status)
            # indata shape: (frames, channels) — take mono
            self._queue.put(indata[:, 0].copy(), block=False)

        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=config.WINDOW_SAMPLES,
            device=self._device,
            callback=_callback,
        )
        self._stream.start()
        logger.info("MicSource: stream started — device=%s  %d Hz", self._device, config.SAMPLE_RATE)

    def chunks(self) -> Generator[np.ndarray, None, None]:
        """Yield mic chunks indefinitely (2s each) until :meth:`close` is called."""
        import queue  # stdlib

        self._start()
        try:
            while True:
                try:
                    yield self._queue.get(timeout=config.WINDOW_SECONDS * 2)
                except queue.Empty:
                    logger.warning("MicSource: queue empty — no audio received in %.1fs", config.WINDOW_SECONDS * 2)
        finally:
            self.close()

    def close(self) -> None:
        """Stop and close the sounddevice stream."""
        if self._stream is not None and self._stream.active:
            self._stream.stop()
            self._stream.close()
            logger.info("MicSource: stream closed")
            self._stream = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resample(data: np.ndarray, src_sr: int, tgt_sr: int) -> np.ndarray:
    """Resample *data* from *src_sr* to *tgt_sr* using scipy."""
    from scipy.signal import resample_poly  # noqa: PLC0415
    import math

    gcd = math.gcd(tgt_sr, src_sr)
    up = tgt_sr // gcd
    down = src_sr // gcd
    logger.debug("Resampling %d Hz → %d Hz (up=%d, down=%d)", src_sr, tgt_sr, up, down)
    return resample_poly(data, up, down).astype(np.float32)
