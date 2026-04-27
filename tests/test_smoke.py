"""Phase 0 smoke tests — confirms test infra, config import, and fixture paths.

These tests are intentionally minimal. They verify that the scaffolding is
correct before any real logic is added in Phase 1+.
"""

from __future__ import annotations

from pathlib import Path

from sentinelsleep import config


def test_project_root_resolves() -> None:
    """PROJECT_ROOT points at the repo root and contains the master plan."""
    assert (config.PROJECT_ROOT / "SENTINELSLEEP_PLAN.md").exists(), (
        f"PROJECT_ROOT={config.PROJECT_ROOT} does not contain SENTINELSLEEP_PLAN.md"
    )


def test_thresholds_in_valid_range() -> None:
    """All probability / score thresholds are within (0, 1)."""
    assert 0.0 < config.DSS_FLAG_THRESHOLD < 1.0
    assert 0.0 < config.VALENCE_MAX_FOR_NIGHTMARE < 1.0
    assert 0.0 < config.AROUSAL_MIN_FOR_NIGHTMARE < 1.0
    assert 0.0 < config.DOMINANCE_MAX_FOR_NIGHTMARE < 1.0


def test_sample_rate_matches_window() -> None:
    """WINDOW_SAMPLES is consistent with SAMPLE_RATE × WINDOW_SECONDS."""
    assert config.WINDOW_SAMPLES == int(config.SAMPLE_RATE * config.WINDOW_SECONDS)


def test_fixture_files_exist() -> None:
    """All expected test fixture files are present (Phase 0 placeholders)."""
    expected = [
        "nightmare_mild.wav",
        "nightmare_severe.wav",
        "false_positive_snore.wav",
        "false_positive_traffic.wav",
        "calm_sleep.wav",
    ]
    missing = [f for f in expected if not (config.TEST_FIXTURES_DIR / f).exists()]
    assert not missing, f"Missing fixture files: {missing}"


def test_subpackage_imports() -> None:
    """All subpackages are importable (verifies __init__.py skeleton is correct)."""
    import sentinelsleep.detection  # noqa: F401
    import sentinelsleep.verification  # noqa: F401
    import sentinelsleep.generation  # noqa: F401
    import sentinelsleep.orchestrator  # noqa: F401
    import sentinelsleep.dashboard  # noqa: F401
    import sentinelsleep.demo  # noqa: F401
