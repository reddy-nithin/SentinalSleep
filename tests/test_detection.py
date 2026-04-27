"""Tests for the detection layer: ASTClassifier + DSS pipeline.

Unit tests (no ``@pytest.mark.integration``):
- Mock the ASTClassifier to return controlled probabilities.
- Test DSS is computed and flag threshold is applied correctly.
- No model download required.

Integration tests (``@pytest.mark.integration``):
- Requires MIT AST model downloaded to HuggingFace cache.
- Requires REAL audio fixtures (not synthetic placeholders).
- Run with: ``uv run pytest tests/ --integration``

Phase 1 acceptance criteria (integration tests):
  - nightmare_mild.wav  → DSS > 0.4
  - calm_sleep.wav      → DSS < 0.1
  - false_positive_snore.wav  → DSS < 0.3
  - Inference < 300 ms per 2-second chunk on M2 MPS
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from sentinelsleep import config
from sentinelsleep.detection.ast_classifier import ASTClassifier, _ensure_mono_float32
from sentinelsleep.detection.distress_score import compute_dss, is_flagged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURE_DIR = config.TEST_FIXTURES_DIR

# Synthetic fixture marker: present when fixtures are placeholder WAVs.
_SYNTHETIC_MARKER = _FIXTURE_DIR / ".synthetic"


def _is_real_fixture(path: Path) -> bool:
    """Return True if the fixture file is NOT the synthetic placeholder.

    A fixture is considered real if the .synthetic marker is absent from
    the fixtures directory.  Replace the synthetic marker file with a
    note file (SOURCES.md) after installing real audio.
    """
    return not _SYNTHETIC_MARKER.exists()


# ---------------------------------------------------------------------------
# Unit tests — no model, no real audio
# ---------------------------------------------------------------------------


class TestEnsureMonoFloat32:
    """Unit tests for the _ensure_mono_float32 helper."""

    def test_mono_float32_passthrough(self) -> None:
        audio = np.ones(100, dtype=np.float32) * 0.5
        result = _ensure_mono_float32(audio)
        assert result.dtype == np.float32
        np.testing.assert_array_equal(result, audio)

    def test_stereo_converted_to_mono(self) -> None:
        audio = np.ones((100, 2), dtype=np.float32)
        audio[:, 0] = 0.0
        audio[:, 1] = 1.0
        result = _ensure_mono_float32(audio)
        assert result.ndim == 1
        assert result.shape == (100,)
        np.testing.assert_allclose(result, 0.5)

    def test_int16_normalised_to_float(self) -> None:
        audio = np.array([32767, -32767, 0], dtype=np.int16)
        result = _ensure_mono_float32(audio)
        assert result.dtype == np.float32
        assert result.max() <= 1.0
        assert result.min() >= -1.0


class TestASTClassifierMocked:
    """Unit tests for the detection pipeline using a mocked ASTClassifier."""

    @pytest.fixture()
    def mock_classifier(self) -> MagicMock:
        """Return a mock ASTClassifier with controllable classify() output."""
        clf = MagicMock(spec=ASTClassifier)
        clf.device = "cpu"
        clf.id2label = {i: f"Label_{i}" for i in range(527)}
        return clf

    def test_dss_computed_from_classifier_output(self, mock_classifier: MagicMock) -> None:
        """DSS is correctly derived from classifier probabilities."""
        mock_classifier.classify.return_value = {
            "Crying, sobbing": 0.85,
            "Whimper": 0.60,
        }
        probs = mock_classifier.classify(np.zeros(32_000, dtype=np.float32))
        dss = compute_dss(probs)
        assert dss > 0.0

    def test_high_distress_probs_trigger_flag(self, mock_classifier: MagicMock) -> None:
        """Classifier output with high distress probs should trigger flag."""
        mock_classifier.classify.return_value = {
            label: 0.8
            for label in ["Crying, sobbing", "Whimper", "Screaming", "Wail, moan"]
        }
        probs = mock_classifier.classify(np.zeros(32_000, dtype=np.float32))
        dss = compute_dss(probs)
        assert is_flagged(dss)

    def test_non_distress_probs_do_not_trigger_flag(
        self, mock_classifier: MagicMock
    ) -> None:
        """Classifier output with only non-distress labels should NOT flag."""
        mock_classifier.classify.return_value = {
            "Dog": 0.9,
            "Music": 0.85,
            "Speech": 0.7,
        }
        probs = mock_classifier.classify(np.zeros(32_000, dtype=np.float32))
        dss = compute_dss(probs)
        assert not is_flagged(dss)

    def test_classify_called_with_audio_array(self, mock_classifier: MagicMock) -> None:
        """Verify the classifier receives the audio ndarray."""
        audio = np.random.default_rng(0).standard_normal(32_000).astype(np.float32)
        mock_classifier.classify(audio)
        call_args = mock_classifier.classify.call_args[0][0]
        assert isinstance(call_args, np.ndarray)


# ---------------------------------------------------------------------------
# Integration tests — require MIT AST model + real audio fixtures
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestASTIntegration:
    """Integration tests against the real MIT AST model and real fixture audio.

    These tests are skipped unless ``--integration`` is passed to pytest AND
    real audio fixtures are present (no ``.synthetic`` marker in fixtures dir).

    To install real fixtures:
      1. Source audio per data/test_fixtures/SOURCES.md
      2. Delete data/test_fixtures/.synthetic  (if present)
      3. Replace placeholder WAVs with real audio

    Then run: ``uv run pytest tests/ --integration -v``
    """

    @pytest.fixture(scope="class")
    def classifier(self) -> ASTClassifier:
        """Load the real MIT AST model (downloads ~86 MB on first run)."""
        return ASTClassifier()

    @pytest.fixture(scope="class")
    def real_fixtures_present(self) -> None:
        """Skip the test class if synthetic marker is present."""
        if _SYNTHETIC_MARKER.exists():
            pytest.skip(
                "Synthetic fixture marker found. "
                "Replace placeholder WAVs with real audio before running integration tests. "
                "See data/test_fixtures/SOURCES.md"
            )

    def _load_fixture(self, name: str) -> tuple[np.ndarray, int]:
        """Load a fixture WAV file as float32 array."""
        path = _FIXTURE_DIR / name
        assert path.exists(), f"Fixture missing: {path}"
        audio, sr = sf.read(str(path), dtype="float32")
        return audio, sr

    # --- Phase 1 acceptance tests (per SENTINELSLEEP_PLAN.md §7 Phase 1) ---

    def test_nightmare_mild_dss_above_flag_threshold(
        self, classifier: ASTClassifier, real_fixtures_present: None
    ) -> None:
        """nightmare_mild.wav must produce DSS > config.DSS_FLAG_THRESHOLD (0.4)."""
        audio, sr = self._load_fixture("nightmare_mild.wav")
        chunk = audio[: config.WINDOW_SAMPLES]
        probs = classifier.classify(chunk, sample_rate=sr)
        dss = compute_dss(probs)
        assert dss > config.DSS_FLAG_THRESHOLD, (
            f"nightmare_mild.wav DSS={dss:.3f} did not exceed "
            f"threshold={config.DSS_FLAG_THRESHOLD}"
        )

    def test_calm_sleep_dss_below_0_1(
        self, classifier: ASTClassifier, real_fixtures_present: None
    ) -> None:
        """calm_sleep.wav must produce DSS < 0.1 (very low noise floor)."""
        audio, sr = self._load_fixture("calm_sleep.wav")
        chunk = audio[: config.WINDOW_SAMPLES]
        probs = classifier.classify(chunk, sample_rate=sr)
        dss = compute_dss(probs)
        assert dss < 0.1, f"calm_sleep.wav DSS={dss:.3f} exceeded 0.1"

    def test_false_positive_snore_dss_below_ceiling(
        self, classifier: ASTClassifier, real_fixtures_present: None
    ) -> None:
        """false_positive_snore.wav must produce DSS < config.DSS_FALSE_POSITIVE_CEILING (0.3)."""
        audio, sr = self._load_fixture("false_positive_snore.wav")
        chunk = audio[: config.WINDOW_SAMPLES]
        probs = classifier.classify(chunk, sample_rate=sr)
        dss = compute_dss(probs)
        assert dss < config.DSS_FALSE_POSITIVE_CEILING, (
            f"false_positive_snore.wav DSS={dss:.3f} exceeded "
            f"ceiling={config.DSS_FALSE_POSITIVE_CEILING}"
        )

    def test_inference_under_300ms_per_chunk(
        self, classifier: ASTClassifier, real_fixtures_present: None
    ) -> None:
        """Inference on a 2s chunk must complete in < 300ms (Phase 1 acceptance)."""
        audio, sr = self._load_fixture("calm_sleep.wav")
        chunk = audio[: config.WINDOW_SAMPLES]
        _, elapsed = classifier.classify_timed(chunk, sample_rate=sr)
        assert elapsed < 0.3, (
            f"Inference took {elapsed*1000:.0f}ms, exceeding 300ms budget."
        )

    def test_label_vocab_covers_all_distress_classes(
        self, classifier: ASTClassifier, real_fixtures_present: None
    ) -> None:
        """All distress class names in config must be present in the model's label vocabulary."""
        from sentinelsleep.detection.audioset_labels import find_unmatched_distress_labels

        unmatched = find_unmatched_distress_labels(
            classifier.id2label, config.DISTRESS_CLASS_WEIGHTS
        )
        assert not unmatched, (
            f"These distress class names are not in the model's vocabulary: {unmatched}\n"
            "Update config.DISTRESS_CLASS_WEIGHTS key strings to match exact AudioSet label names."
        )
