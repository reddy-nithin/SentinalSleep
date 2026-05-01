"""Main orchestration loop for SentinelSleep Phase 4.

Wires together the four pipeline layers:

    AudioSource → ASTClassifier → distress_score → EmotionAnalyzer
        → NightmareVerifier → StateMachine → clip_selector → playback
        → EventLogger

The runner supports two modes selected by the caller:

``run_from_file(wav_path, ...)``
    Simulation / demo mode.  Uses :class:`~sentinelsleep.orchestrator.audio_stream.FileSource`
    and plays back at real-time pace (or as fast as possible in tests).

``run_live(...)``
    Production mode.  Uses :class:`~sentinelsleep.orchestrator.audio_stream.MicSource`
    and runs until the process is interrupted (Ctrl-C).

Hard constraints enforced here (from CLAUDE.md):

1.  **No MusicGen / AudioLDM2 imports** — only AST + wav2vec2 in this module.
2.  **Events logged before audio side effects** — :meth:`_log_state` is always
    called before :meth:`_play_clip`.
3.  **All paths from ``config.py``** — no hardcoded paths.
"""

from __future__ import annotations

import logging
import random
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from sentinelsleep import config
from sentinelsleep.db.schema import States
from sentinelsleep.detection.ast_classifier import ASTClassifier
from sentinelsleep.detection.distress_score import compute_dss
from sentinelsleep.generation.clip_selector import select_clip
from sentinelsleep.generation.manifest import read_manifest
from sentinelsleep.orchestrator.audio_stream import FileSource, MicSource
from sentinelsleep.orchestrator.event_logger import EventLogger
from sentinelsleep.orchestrator.state_machine import Observation, StateMachine
from sentinelsleep.verification.emotion_dim import EmotionAnalyzer
from sentinelsleep.verification.nightmare_signature import NightmareVerifier

logger = logging.getLogger(__name__)


class Runner:
    """Orchestrates the full SentinelSleep detection-to-intervention loop.

    Args:
        db_path:      Path to the SQLite event log (defaults to
                      ``config.EVENTS_DB_PATH``).
        cache_dir:    Directory containing ``manifest.json`` and WAV clips
                      (defaults to ``config.AUDIO_CACHE_DIR``).
        device:       Torch device for ML models (defaults to
                      ``config.select_device()``).
        dry_run:      If True, skip actual audio playback (useful in tests).
    """

    def __init__(
        self,
        db_path: Path | None = None,
        cache_dir: Path | None = None,
        device: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self._db_path = Path(db_path) if db_path else config.EVENTS_DB_PATH
        self._cache_dir = Path(cache_dir) if cache_dir else config.AUDIO_CACHE_DIR
        self._device = device or config.select_device()
        self._dry_run = dry_run

        logger.info(
            "Runner init — device=%s  db=%s  dry_run=%s",
            self._device,
            self._db_path,
            dry_run,
        )

        # Load models (live loop constraint: AST + wav2vec2 only)
        logger.info("Loading AST classifier …")
        self._ast = ASTClassifier(device=self._device)

        logger.info("Loading emotion analyzer …")
        self._emotion = EmotionAnalyzer(device=self._device)

        # Stateful pipeline components
        self._verifier = NightmareVerifier()
        self._sm = StateMachine()
        self._event_logger = EventLogger(self._db_path)

        # Read manifest once at startup
        self._manifest = read_manifest(self._cache_dir)

        # Track the current open session and intervention
        self._session_id: Optional[int] = None
        self._intervention_id: Optional[int] = None
        self._playback_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def run_from_file(self, wav_path: Path, *, realtime: bool = True) -> None:
        """Run the pipeline on a WAV file (simulation / demo mode).

        Args:
            wav_path: Path to the WAV file to stream through the pipeline.
            realtime: If True (default), sleep between chunks to mimic
                live streaming.  Set False in unit tests.
        """
        logger.info("=== Simulation mode: %s ===", Path(wav_path).name)
        source = FileSource(Path(wav_path), realtime=realtime)
        self._run_loop(source)

    def run_live(self, device: int | str | None = None) -> None:
        """Run the pipeline on live mic input indefinitely.

        Blocks until interrupted (Ctrl-C / KeyboardInterrupt).

        Args:
            device: sounddevice device index or name.  None = system default.
        """
        logger.info("=== Live mode ===")
        source = MicSource(device=device)
        self._run_loop(source)

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def _run_loop(self, source: FileSource | MicSource) -> None:
        """Iterate over audio chunks from *source* and drive the pipeline.

        Args:
            source: Any object implementing the :class:`AudioSource` protocol.
        """
        self._session_id = self._event_logger.start_session()
        try:
            for chunk in source.chunks():
                self._process_chunk(chunk)
        except KeyboardInterrupt:
            logger.info("Loop interrupted by user.")
        finally:
            if self._intervention_id is not None:
                self._event_logger.close_intervention(self._intervention_id)
                self._intervention_id = None
            if self._session_id is not None:
                self._event_logger.end_session(self._session_id)
                self._session_id = None
            source.close()

    def _process_chunk(self, chunk: np.ndarray) -> None:
        """Process a single audio chunk through all pipeline layers.

        Pipeline order (matches plan §3.2):
        1. AST classify → compute DSS
        2. If flagged: emotion predict → nightmare verifier update
        3. Build Observation → StateMachine.update
        4. Log event BEFORE any audio side effect
        5. Execute action (play clip, escalate, etc.)

        Args:
            chunk: float32 mono array of shape ``(config.WINDOW_SAMPLES,)``.
        """
        assert self._session_id is not None, "Session not started"

        # Layer 1 — Detection
        probs = self._ast.classify(chunk, config.SAMPLE_RATE)
        dss = compute_dss(probs)

        # Layer 2 — Verification (only when flagged to save memory bandwidth)
        valence: float | None = None
        arousal: float | None = None
        dominance: float | None = None
        nightmare_confirmed = False

        if dss > config.DSS_FLAG_THRESHOLD or self._sm.state == States.FLAGGED:
            try:
                emotion = self._emotion.predict(chunk, config.SAMPLE_RATE)
                valence, arousal, dominance = (
                    emotion.valence,
                    emotion.arousal,
                    emotion.dominance,
                )
                sig = self._verifier.update(dss, valence, arousal, dominance)
                nightmare_confirmed = sig.confirmed
            except Exception as exc:
                logger.warning("Emotion prediction failed: %s", exc)
        else:
            # Not flagged — reset verifier sliding window
            self._verifier.reset()

        # Layer 3 — State machine (pure, no I/O)
        obs = Observation(
            dss=dss,
            nightmare_confirmed=nightmare_confirmed,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
        )
        new_state, action = self._sm.update(obs)

        # Log state transition BEFORE executing action (CLAUDE.md #3)
        self._log_state(new_state, dss, valence, arousal, dominance)

        # Execute action
        if action == "intervene":
            self._do_intervene(dss)
        elif action == "escalate":
            self._do_escalate()
        elif action == "reset":
            self._do_reset()

    # ------------------------------------------------------------------
    # Action executors
    # ------------------------------------------------------------------

    def _do_intervene(self, current_dss: float) -> None:
        """Select and play an intervention clip, recording the intervention row."""
        seed = random.randint(0, 2**31 - 1)
        profile = "severe" if current_dss > config.DSS_FLAG_THRESHOLD * 1.5 else "mild"

        try:
            clip_path = select_clip(self._manifest, profile=profile, rng_seed=seed)
        except (RuntimeError, KeyError) as exc:
            logger.error("Could not select clip: %s", exc)
            return

        # Log intervention row BEFORE starting playback
        assert self._session_id is not None
        # Find the latest event_id for this session
        event_id = self._get_latest_event_id()
        if event_id is not None:
            self._intervention_id = self._event_logger.record_intervention(
                event_id=event_id,
                clip_path=clip_path,
                pre_dss=current_dss,
            )

        self._play_clip(clip_path)

    def _do_escalate(self) -> None:
        """Log escalation (progressive wake protocol hook)."""
        logger.warning("ESCALATING — distress persists. Initiating wake protocol.")
        # TODO Phase 6: trigger wake protocol (e.g., lights, louder audio)

    def _do_reset(self) -> None:
        """Handle a manual reset / patient woke up."""
        logger.info("Reset — returning to LISTENING state.")
        self._verifier.reset()
        if self._intervention_id is not None:
            self._event_logger.close_intervention(self._intervention_id, effective=None)
            self._intervention_id = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_state(
        self,
        state: str,
        dss: float,
        valence: float | None,
        arousal: float | None,
        dominance: float | None,
    ) -> None:
        """Write a state event row to SQLite."""
        assert self._session_id is not None
        self._event_logger.log_event(
            session_id=self._session_id,
            state=state,
            dss=dss,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
        )

    def _get_latest_event_id(self) -> Optional[int]:
        """Return the most-recent events.id for the current session."""
        from sentinelsleep.db.schema import get_connection

        try:
            with get_connection(self._db_path) as conn:
                row = conn.execute(
                    "SELECT id FROM events WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (self._session_id,),
                ).fetchone()
                return int(row["id"]) if row else None
        except Exception as exc:
            logger.warning("Could not fetch latest event_id: %s", exc)
            return None

    def _play_clip(self, clip_path: Path) -> None:
        """Play the intervention WAV asynchronously via sounddevice.

        In dry-run mode the playback is skipped entirely so tests can run
        without audio hardware.

        Args:
            clip_path: Absolute path to the WAV file to play.
        """
        if self._dry_run:
            logger.info("DRY RUN — skipping playback of %s", clip_path.name)
            return

        if not clip_path.exists():
            logger.error("Clip not found, skipping playback: %s", clip_path)
            return

        def _play() -> None:
            try:
                import sounddevice as sd  # noqa: PLC0415
                import soundfile as sf  # noqa: PLC0415

                data, sr = sf.read(str(clip_path), dtype="float32", always_2d=False)
                # Apply playback level (convert dBFS → linear amplitude)
                amplitude = 10 ** (config.INTERVENTION_PLAYBACK_DBFS / 20.0)
                data = data * amplitude
                logger.info("Playing: %s  %.1fs  %.0f dBFS", clip_path.name, len(data) / sr, config.INTERVENTION_PLAYBACK_DBFS)
                sd.play(data, sr)
                sd.wait()
            except Exception as exc:
                logger.error("Playback error: %s", exc)

        self._playback_thread = threading.Thread(target=_play, daemon=True, name="playback")
        self._playback_thread.start()
