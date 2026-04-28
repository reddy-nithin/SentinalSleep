"""Tests for the verification layer: EmotionAnalyzer + NightmareVerifier.

Unit tests (no ``@pytest.mark.integration``):
- All logic in nightmare_signature.py and the EmotionResult NamedTuple.
- No model download or audio files required.
- Always pass.

Integration tests (``@pytest.mark.integration``):
- Require audeering wav2vec2 model downloaded to HuggingFace cache.
- Require REAL audio fixtures in data/test_fixtures/.
- Run with: ``uv run pytest tests/ --integration``

Phase 2 acceptance criteria (integration tests):
  - nightmare_severe.wav confirms after 15s sustained distress
  - false_positive_traffic.wav never confirms
  - Inference < 500ms per 2-second chunk on M2 MPS
  - Relative ordering: nightmare arousal > calm arousal,
                       nightmare valence < calm valence
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from sentinelsleep import config
from sentinelsleep.verification.emotion_dim import EmotionAnalyzer, EmotionResult
from sentinelsleep.verification.nightmare_signature import (
    NightmareSignature,
    NightmareVerifier,
    is_nightmare_frame,
)

_FIXTURE_DIR = config.TEST_FIXTURES_DIR
_SYNTHETIC_MARKER = _FIXTURE_DIR / ".synthetic"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nightmare_frame_kwargs(**overrides: float) -> dict[str, float]:
    """Return kwargs that satisfy is_nightmare_frame() by default.

    Override individual keys to test threshold boundaries.
    """
    base: dict[str, float] = {
        "dss": config.DSS_FLAG_THRESHOLD + 0.1,
        "valence": config.VALENCE_MAX_FOR_NIGHTMARE - 0.1,
        "arousal": config.AROUSAL_MIN_FOR_NIGHTMARE + 0.1,
        "dominance": config.DOMINANCE_MAX_FOR_NIGHTMARE - 0.1,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Unit tests — EmotionResult
# ---------------------------------------------------------------------------


class TestEmotionResult:
    """Tests for the EmotionResult NamedTuple."""

    def test_field_access_by_name(self) -> None:
        result = EmotionResult(valence=0.3, arousal=0.7, dominance=0.2)
        assert result.valence == pytest.approx(0.3)
        assert result.arousal == pytest.approx(0.7)
        assert result.dominance == pytest.approx(0.2)

    def test_positional_access(self) -> None:
        result = EmotionResult(0.3, 0.7, 0.2)
        assert result[0] == pytest.approx(0.3)  # valence
        assert result[1] == pytest.approx(0.7)  # arousal
        assert result[2] == pytest.approx(0.2)  # dominance

    def test_is_tuple(self) -> None:
        result = EmotionResult(valence=0.5, arousal=0.5, dominance=0.5)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_extreme_values_stored(self) -> None:
        result = EmotionResult(valence=0.0, arousal=1.0, dominance=0.0)
        assert result.valence == pytest.approx(0.0)
        assert result.arousal == pytest.approx(1.0)
        assert result.dominance == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Unit tests — is_nightmare_frame
# ---------------------------------------------------------------------------


class TestIsNightmareFrame:
    """Unit tests for the per-frame nightmare predicate."""

    def test_all_thresholds_satisfied_returns_true(self) -> None:
        assert is_nightmare_frame(**_nightmare_frame_kwargs()) is True

    # --- DSS boundary ---

    def test_dss_exactly_at_threshold_returns_false(self) -> None:
        """Strict inequality: dss > threshold, so exactly at threshold is False."""
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(dss=config.DSS_FLAG_THRESHOLD)
        ) is False

    def test_dss_below_threshold_returns_false(self) -> None:
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(dss=config.DSS_FLAG_THRESHOLD - 0.01)
        ) is False

    # --- Valence boundary ---

    def test_valence_exactly_at_max_returns_false(self) -> None:
        """Strict inequality: valence < max, so exactly at max is False."""
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(valence=config.VALENCE_MAX_FOR_NIGHTMARE)
        ) is False

    def test_valence_above_max_returns_false(self) -> None:
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(valence=config.VALENCE_MAX_FOR_NIGHTMARE + 0.01)
        ) is False

    # --- Arousal boundary ---

    def test_arousal_exactly_at_min_returns_false(self) -> None:
        """Strict inequality: arousal > min, so exactly at min is False."""
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(arousal=config.AROUSAL_MIN_FOR_NIGHTMARE)
        ) is False

    def test_arousal_below_min_returns_false(self) -> None:
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(arousal=config.AROUSAL_MIN_FOR_NIGHTMARE - 0.01)
        ) is False

    # --- Dominance boundary ---

    def test_dominance_exactly_at_max_returns_false(self) -> None:
        """Strict inequality: dominance < max, so exactly at max is False."""
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(dominance=config.DOMINANCE_MAX_FOR_NIGHTMARE)
        ) is False

    def test_dominance_above_max_returns_false(self) -> None:
        assert is_nightmare_frame(
            **_nightmare_frame_kwargs(
                dominance=config.DOMINANCE_MAX_FOR_NIGHTMARE + 0.01
            )
        ) is False

    def test_custom_thresholds_respected(self) -> None:
        """Custom threshold arguments override config defaults."""
        # Using a very permissive set of thresholds
        assert is_nightmare_frame(
            dss=0.1,
            valence=0.9,
            arousal=0.1,
            dominance=0.9,
            dss_threshold=0.05,
            valence_max=0.95,
            arousal_min=0.05,
            dominance_max=0.95,
        ) is True


# ---------------------------------------------------------------------------
# Unit tests — NightmareVerifier
# ---------------------------------------------------------------------------


class TestNightmareVerifier:
    """Unit tests for the sliding-window nightmare verifier."""

    @pytest.fixture()
    def verifier(self) -> NightmareVerifier:
        """Return a fresh NightmareVerifier with a short confirmation window for testing."""
        # Use 1.0 second so tests run fast without real sleeps.
        return NightmareVerifier(confirm_duration_s=1.0)

    # --- Initial state ---

    def test_empty_window_not_confirmed(self, verifier: NightmareVerifier) -> None:
        # A non-distress frame → window stays empty → not confirmed.
        sig = verifier.update(dss=0.0, valence=0.9, arousal=0.1, dominance=0.9)
        assert sig.confirmed is False
        assert sig.frames == 0

    def test_single_distress_frame_not_confirmed(
        self, verifier: NightmareVerifier
    ) -> None:
        """A single qualifying frame cannot span 1s → not confirmed."""
        sig = verifier.update(**_nightmare_frame_kwargs())
        assert sig.confirmed is False
        assert sig.frames == 1

    # --- Sustained distress confirms ---

    def test_sustained_distress_confirms(self, verifier: NightmareVerifier) -> None:
        """Frames spanning > 1s must confirm (controlled via monotonic time mock)."""
        # We inject frames with monotonically increasing timestamps by mocking
        # time.monotonic() in nightmare_signature to space frames 0.6s apart.
        # Two frames → span = 0.6s < 1.0s (not confirmed).
        # Three frames → span = 1.2s >= 1.0s (confirmed).
        fake_times = [0.0, 0.6, 1.2]
        time_iter = iter(fake_times)

        import sentinelsleep.verification.nightmare_signature as ns_module

        with patch.object(ns_module.time, "monotonic", side_effect=fake_times):
            sig1 = verifier.update(**_nightmare_frame_kwargs())
            sig2 = verifier.update(**_nightmare_frame_kwargs())
            sig3 = verifier.update(**_nightmare_frame_kwargs())

        assert sig1.confirmed is False, "One frame cannot span 1s"
        assert sig2.confirmed is False, "Two frames span 0.6s < 1.0s"
        assert sig3.confirmed is True, "Three frames span 1.2s >= 1.0s"

    # --- Broken distress resets ---

    def test_non_distress_frame_resets_window(
        self, verifier: NightmareVerifier
    ) -> None:
        """A non-qualifying frame resets the window; counter must restart."""
        # First: accumulate a distress frame.
        verifier.update(**_nightmare_frame_kwargs())
        assert len(verifier._window) == 1

        # Next: calm frame — window must reset.
        sig = verifier.update(dss=0.0, valence=0.9, arousal=0.1, dominance=0.9)
        assert sig.confirmed is False
        assert sig.frames == 0
        assert len(verifier._window) == 0

        # After reset, new distress frames start a fresh window.
        sig2 = verifier.update(**_nightmare_frame_kwargs())
        assert sig2.frames == 1

    # --- reset() method ---

    def test_reset_clears_window(self, verifier: NightmareVerifier) -> None:
        verifier.update(**_nightmare_frame_kwargs())
        verifier.update(**_nightmare_frame_kwargs())
        assert len(verifier._window) == 2

        verifier.reset()
        assert len(verifier._window) == 0

    def test_after_reset_starts_fresh(self, verifier: NightmareVerifier) -> None:
        verifier.update(**_nightmare_frame_kwargs())
        verifier.reset()
        sig = verifier.update(**_nightmare_frame_kwargs())
        assert sig.frames == 1
        assert sig.confirmed is False

    # --- Signature fields ---

    def test_signature_dss_mean_correct(self, verifier: NightmareVerifier) -> None:
        kwargs1 = _nightmare_frame_kwargs(dss=0.5)
        kwargs2 = _nightmare_frame_kwargs(dss=0.7)
        verifier.update(**kwargs1)
        sig = verifier.update(**kwargs2)
        assert sig.dss_mean == pytest.approx((0.5 + 0.7) / 2, rel=1e-5)

    def test_signature_reflects_latest_frame_values(
        self, verifier: NightmareVerifier
    ) -> None:
        verifier.update(**_nightmare_frame_kwargs(valence=0.2, arousal=0.8))
        sig = verifier.update(**_nightmare_frame_kwargs(valence=0.15, arousal=0.85))
        # latest frame values should appear in the signature
        assert sig.valence == pytest.approx(0.15)
        assert sig.arousal == pytest.approx(0.85)

    def test_confidence_is_zero_on_empty_window(
        self, verifier: NightmareVerifier
    ) -> None:
        sig = verifier.update(dss=0.0, valence=0.9, arousal=0.1, dominance=0.9)
        assert sig.confidence == pytest.approx(0.0)

    def test_confidence_is_positive_with_distress_frames(
        self, verifier: NightmareVerifier
    ) -> None:
        verifier.update(**_nightmare_frame_kwargs())
        sig = verifier.update(**_nightmare_frame_kwargs())
        assert sig.confidence > 0.0
        assert sig.confidence <= 1.0

    def test_confidence_higher_with_stronger_signal(
        self, verifier: NightmareVerifier
    ) -> None:
        """Stronger nightmare signal should produce higher confidence."""
        # weak signal: dss=0.41, valence=0.39, arousal=0.61, dominance=0.39
        weak = NightmareVerifier(confirm_duration_s=1.0)
        weak.update(**_nightmare_frame_kwargs(
            dss=config.DSS_FLAG_THRESHOLD + 0.01,
            valence=config.VALENCE_MAX_FOR_NIGHTMARE - 0.01,
            arousal=config.AROUSAL_MIN_FOR_NIGHTMARE + 0.01,
            dominance=config.DOMINANCE_MAX_FOR_NIGHTMARE - 0.01,
        ))
        sig_weak = weak.update(**_nightmare_frame_kwargs(
            dss=config.DSS_FLAG_THRESHOLD + 0.01,
            valence=config.VALENCE_MAX_FOR_NIGHTMARE - 0.01,
            arousal=config.AROUSAL_MIN_FOR_NIGHTMARE + 0.01,
            dominance=config.DOMINANCE_MAX_FOR_NIGHTMARE - 0.01,
        ))

        # strong signal: dss=0.8, valence=0.1, arousal=0.9, dominance=0.1
        strong = NightmareVerifier(confirm_duration_s=1.0)
        strong.update(**_nightmare_frame_kwargs(dss=0.8, valence=0.1, arousal=0.9, dominance=0.1))
        sig_strong = strong.update(**_nightmare_frame_kwargs(dss=0.8, valence=0.1, arousal=0.9, dominance=0.1))

        assert sig_strong.confidence > sig_weak.confidence

    def test_duration_tracked_correctly(self, verifier: NightmareVerifier) -> None:
        """Duration spans from oldest to newest frame timestamp."""
        fake_times = [10.0, 12.0, 14.0]

        import sentinelsleep.verification.nightmare_signature as ns_module

        with patch.object(ns_module.time, "monotonic", side_effect=fake_times):
            verifier.update(**_nightmare_frame_kwargs())
            verifier.update(**_nightmare_frame_kwargs())
            sig = verifier.update(**_nightmare_frame_kwargs())

        assert sig.duration_s == pytest.approx(4.0)  # 14.0 - 10.0
        assert sig.frames == 3

    def test_nightmare_signature_is_dataclass(self) -> None:
        sig = NightmareSignature(
            confirmed=True,
            confidence=0.5,
            dss_mean=0.6,
            valence=0.2,
            arousal=0.8,
            dominance=0.2,
            duration_s=16.0,
            frames=8,
        )
        assert sig.confirmed is True
        assert sig.confidence == pytest.approx(0.5)

    def test_default_confirm_duration_matches_config(self) -> None:
        """Default verifier uses the config duration constant."""
        v = NightmareVerifier()
        assert v.confirm_duration_s == float(config.NIGHTMARE_CONFIRM_DURATION_SECONDS)


# ---------------------------------------------------------------------------
# Integration tests — require real audeering model + real audio fixtures
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestEmotionIntegration:
    """Integration tests against the real audeering wav2vec2 model.

    Skipped unless ``--integration`` is passed AND real audio fixtures are present.
    Run with: ``uv run pytest tests/ --integration -v``
    """

    @pytest.fixture(scope="class")
    def analyzer(self) -> EmotionAnalyzer:
        """Load the real audeering model (downloads ~660 MB on first run)."""
        return EmotionAnalyzer()

    @pytest.fixture(scope="class")
    def real_fixtures_present(self) -> None:
        """Skip class if synthetic fixtures marker is present."""
        if _SYNTHETIC_MARKER.exists():
            pytest.skip(
                "Synthetic fixture marker found. "
                "Replace placeholder WAVs with real audio before running integration tests. "
                "See data/test_fixtures/SOURCES.md"
            )

    def _load_chunk(self, name: str) -> tuple[np.ndarray, int]:
        """Load the first 2 seconds of a fixture WAV."""
        path = _FIXTURE_DIR / name
        assert path.exists(), f"Fixture missing: {path}"
        audio, sr = sf.read(str(path), dtype="float32")
        # Take first 2-second window only (consistent with detection layer)
        chunk = audio[: config.WINDOW_SAMPLES]
        return chunk, sr

    def _load_full(self, name: str) -> tuple[np.ndarray, int]:
        """Load the full fixture WAV."""
        path = _FIXTURE_DIR / name
        assert path.exists(), f"Fixture missing: {path}"
        audio, sr = sf.read(str(path), dtype="float32")
        return audio, sr

    # --- Single-chunk emotion predictions ---

    def test_nightmare_has_low_valence(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """nightmare_severe.wav first chunk should have valence < 0.5."""
        chunk, sr = self._load_chunk("nightmare_severe.wav")
        result = analyzer.predict(chunk, sr)
        assert result.valence < 0.5, (
            f"Expected nightmare valence < 0.5, got {result.valence:.3f}"
        )

    def test_nightmare_has_high_arousal(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """nightmare_severe.wav first chunk should have arousal > 0.5."""
        chunk, sr = self._load_chunk("nightmare_severe.wav")
        result = analyzer.predict(chunk, sr)
        assert result.arousal > 0.5, (
            f"Expected nightmare arousal > 0.5, got {result.arousal:.3f}"
        )

    def test_nightmare_arousal_exceeds_calm_arousal(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """Nightmare audio should produce higher arousal than calm sleep."""
        chunk_nm, sr_nm = self._load_chunk("nightmare_severe.wav")
        chunk_calm, sr_calm = self._load_chunk("calm_sleep.wav")
        result_nm = analyzer.predict(chunk_nm, sr_nm)
        result_calm = analyzer.predict(chunk_calm, sr_calm)
        assert result_nm.arousal > result_calm.arousal, (
            f"nightmare arousal={result_nm.arousal:.3f} not > "
            f"calm arousal={result_calm.arousal:.3f}"
        )

    def test_nightmare_valence_below_calm_valence(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """Nightmare audio should produce lower valence than calm sleep."""
        chunk_nm, sr_nm = self._load_chunk("nightmare_severe.wav")
        chunk_calm, sr_calm = self._load_chunk("calm_sleep.wav")
        result_nm = analyzer.predict(chunk_nm, sr_nm)
        result_calm = analyzer.predict(chunk_calm, sr_calm)
        assert result_nm.valence < result_calm.valence, (
            f"nightmare valence={result_nm.valence:.3f} not < "
            f"calm valence={result_calm.valence:.3f}"
        )

    # --- NightmareVerifier on real clips ---

    def test_nightmare_severe_verifier_confirms(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """nightmare_severe.wav should confirm after 15s of sustained distress.

        We feed the full clip chunk-by-chunk through the verifier with a DSS
        stub set above the flag threshold (as would happen in the live pipeline
        after Layer 1 has already flagged). The emotion model must sustain a
        nightmare-compatible profile long enough to confirm.

        Note: This test uses a stubbed DSS value above the threshold because
        the verification layer receives pre-filtered events from Layer 1.
        """
        from sentinelsleep.detection.distress_score import compute_dss
        from sentinelsleep.detection.ast_classifier import ASTClassifier

        ast_clf = ASTClassifier()
        verifier = NightmareVerifier()

        audio, sr = self._load_full("nightmare_severe.wav")
        window = config.WINDOW_SAMPLES
        confirmed_any = False

        for i in range(0, len(audio) - window, window):
            chunk = audio[i : i + window]
            # Layer 1: compute real DSS
            probs = ast_clf.classify(chunk, sample_rate=sr)
            dss = compute_dss(probs)
            # Layer 2: compute real emotion scores
            result = analyzer.predict(chunk, sr)
            sig = verifier.update(
                dss=dss,
                valence=result.valence,
                arousal=result.arousal,
                dominance=result.dominance,
            )
            if sig.confirmed:
                confirmed_any = True
                break

        # nightmare_severe.wav should trigger at least one confirmation attempt.
        # If the audio is only ~30s and the model produces nightmare-consistent dims,
        # we expect this to confirm.  If not, we surface a diagnostic message.
        assert confirmed_any, (
            "nightmare_severe.wav never confirmed after scanning the full clip. "
            "Check fixture audio quality or review dimensional thresholds in config.py."
        )

    def test_traffic_false_positive_never_confirms(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """false_positive_traffic.wav must never confirm a nightmare signature."""
        from sentinelsleep.detection.distress_score import compute_dss
        from sentinelsleep.detection.ast_classifier import ASTClassifier

        ast_clf = ASTClassifier()
        verifier = NightmareVerifier()

        audio, sr = self._load_full("false_positive_traffic.wav")
        window = config.WINDOW_SAMPLES

        for i in range(0, len(audio) - window, window):
            chunk = audio[i : i + window]
            probs = ast_clf.classify(chunk, sample_rate=sr)
            dss = compute_dss(probs)
            result = analyzer.predict(chunk, sr)
            sig = verifier.update(
                dss=dss,
                valence=result.valence,
                arousal=result.arousal,
                dominance=result.dominance,
            )
            assert not sig.confirmed, (
                f"false_positive_traffic.wav confirmed at chunk {i // window} "
                f"(dss={dss:.3f}, valence={result.valence:.3f}, "
                f"arousal={result.arousal:.3f}, dominance={result.dominance:.3f})"
            )

    def test_inference_under_500ms_per_chunk(
        self, analyzer: EmotionAnalyzer, real_fixtures_present: None
    ) -> None:
        """Emotion model inference on a 2s chunk must complete in < 500ms on M2 MPS.

        Plan §7 Phase 2 specifies < 500ms per chunk for the verification layer.
        We measure steady-state latency (after one warm-up call to absorb kernel
        compilation overhead on MPS).
        """
        chunk, sr = self._load_chunk("calm_sleep.wav")
        # Warm-up: absorb MPS kernel compilation cost
        analyzer.predict(chunk, sr)
        # Timed measurement
        _, elapsed = analyzer.predict_timed(chunk, sr)
        assert elapsed < config.VERIFICATION_LATENCY_BUDGET_MS / 1000, (
            f"Emotion inference took {elapsed * 1000:.0f}ms, "
            f"exceeding {config.VERIFICATION_LATENCY_BUDGET_MS}ms budget."
        )
