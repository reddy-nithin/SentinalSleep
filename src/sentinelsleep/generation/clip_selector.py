"""Manifest-aware clip selector for Phase 4 orchestration.

Selects a pre-generated intervention clip from the audio cache based on
a ``profile`` (``'mild'`` or ``'severe'``) and an RNG seed, so the
same seed always yields the same clip (reproducible for testing) while
production calls can pass a random seed for variety.

Public API::

    from sentinelsleep.generation.clip_selector import select_clip
    from sentinelsleep.generation.manifest import read_manifest

    manifest = read_manifest()
    clip_path = select_clip(manifest, profile="severe", rng_seed=42)
    # → Path to the selected intervention WAV (absolute)

The function is deliberately pure (no I/O beyond reading the manifest
dict) so it is trivially unit-testable with a stub manifest fixture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from sentinelsleep import config

logger = logging.getLogger(__name__)

# Type alias for clarity
Profile = Literal["mild", "severe"]


def select_clip(
    manifest: dict[str, Any],
    profile: Profile,
    rng_seed: int,
) -> Path:
    """Select an intervention clip from *manifest* for the given *profile*.

    Uses *rng_seed* to pick deterministically from the available clips for
    the requested profile.  The returned path is absolute, resolved relative
    to ``config.AUDIO_CACHE_DIR``.

    Args:
        manifest: Parsed manifest dict as returned by
            :func:`sentinelsleep.generation.manifest.read_manifest`.
        profile:  Intervention intensity — ``'mild'`` or ``'severe'``.
        rng_seed: Integer seed for numpy default_rng so selection is
            reproducible in tests and logged for traceability.

    Returns:
        Absolute :class:`~pathlib.Path` to the selected WAV file.

    Raises:
        ValueError:  If *profile* is not ``'mild'`` or ``'severe'``.
        KeyError:    If *manifest* does not contain the expected ``'mixed'``
                     section.
        RuntimeError: If no clips are available for the requested profile.
    """
    if profile not in ("mild", "severe"):
        raise ValueError(
            f"Invalid profile {profile!r}. Must be 'mild' or 'severe'."
        )

    mixed: list[dict[str, Any]] = manifest.get("mixed", [])
    candidates = [entry for entry in mixed if entry.get("profile") == profile]

    if not candidates:
        raise RuntimeError(
            f"No '{profile}' clips found in manifest. "
            "Run scripts/build_stub_cache.py or scripts/pregenerate_cache.py first."
        )

    # Deterministic selection from candidates
    import numpy as np  # noqa: PLC0415 — lazy import to keep module lightweight

    rng = np.random.default_rng(rng_seed)
    idx = int(rng.integers(0, len(candidates)))
    entry = candidates[idx]

    rel_path = entry["path"]  # e.g. "mixed/intervention_severe_v2.wav"
    abs_path = (config.AUDIO_CACHE_DIR / rel_path).resolve()

    logger.info(
        "clip_selector: profile=%r seed=%d → %s (variant %d of %d)",
        profile,
        rng_seed,
        abs_path.name,
        idx + 1,
        len(candidates),
    )
    return abs_path
