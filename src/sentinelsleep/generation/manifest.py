"""Cache manifest writer and reader for the SentinelSleep audio cache.

The manifest (``data/audio_cache/manifest.json``) is written once by
:func:`sentinelsleep.generation.pregenerate.build_cache` after all clips are
validated.  It records provenance metadata and SHA-256 hashes for every clip so
the Colab→local handoff is auditable and ``scripts/verify_cache.py`` can check
integrity without re-running the models.

Schema version history:
  1 — original; ``models.audioldm2`` key, ``cvssp/audioldm2`` as soundscape model.
  2 — ``models.audioldm2`` renamed to ``models.audiogen`` (ADR-014); reader
      accepts both 1 and 2 so old downloaded caches validate without re-gen.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sentinelsleep import config

MANIFEST_SCHEMA_VERSION: int = 2
_SUPPORTED_SCHEMA_VERSIONS: tuple[int, ...] = (1, 2)
MANIFEST_FILENAME: str = "manifest.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    """Return lowercase hex SHA-256 digest of the file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    """Return the current short git commit hash, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_manifest(
    music_paths: list[Path],
    soundscape_paths: list[Path],
    mixed_paths: list[Path],
    mild_pairs: list[tuple[int, int]],
    severe_pairs: list[tuple[int, int]],
    device: str,
    fallback_used: dict[str, bool],
) -> Path:
    """Write ``manifest.json`` to ``AUDIO_CACHE_DIR`` and return its path.

    Args:
        music_paths: Ordered list of music WAV paths (index = variant idx).
        soundscape_paths: Ordered list of soundscape WAV paths.
        mixed_paths: All mixed intervention WAV paths (in any order; profile and
            version are parsed from the filename per the naming convention
            ``intervention_{profile}_v{N}.wav``).
        mild_pairs: Fixed ``(music_idx, soundscape_idx)`` tuples for mild clips,
            indexed by variant number minus one.  Mirrors ``_MILD_PAIRS`` in
            ``pregenerate.py``.
        severe_pairs: Same for severe clips.
        device: Device used during generation (e.g., ``'cuda'``, ``'mps'``, ``'cpu'``).
        fallback_used: Dict with keys ``'music'`` and ``'soundscape'`` indicating
            whether synthetic fallback was used for each type.

    Returns:
        Path to the written ``manifest.json``.
    """
    mild_by_version = {i + 1: (m, s) for i, (m, s) in enumerate(mild_pairs)}
    severe_by_version = {i + 1: (m, s) for i, (m, s) in enumerate(severe_pairs)}

    music_entries: list[dict[str, Any]] = []
    for i, path in enumerate(music_paths):
        music_entries.append(
            {
                "index": i,
                "path": str(Path(path).relative_to(config.AUDIO_CACHE_DIR)),
                "prompt": (
                    config.MUSIC_PROMPTS[i] if i < len(config.MUSIC_PROMPTS) else ""
                ),
                "sha256": _sha256(path),
            }
        )

    soundscape_entries: list[dict[str, Any]] = []
    for i, path in enumerate(soundscape_paths):
        soundscape_entries.append(
            {
                "index": i,
                "path": str(Path(path).relative_to(config.AUDIO_CACHE_DIR)),
                "prompt": (
                    config.SOUNDSCAPE_PROMPTS[i]
                    if i < len(config.SOUNDSCAPE_PROMPTS)
                    else ""
                ),
                "sha256": _sha256(path),
            }
        )

    mixed_entries: list[dict[str, Any]] = []
    for clip_path in sorted(mixed_paths):
        stem = clip_path.stem  # e.g. intervention_mild_v1
        parts = stem.split("_")  # ['intervention', 'mild', 'v1']
        profile = parts[1] if len(parts) >= 3 else "unknown"
        version = int(parts[2][1:]) if len(parts) >= 3 and parts[2].startswith("v") else 0
        pairs_map = mild_by_version if profile == "mild" else severe_by_version
        m_idx, s_idx = pairs_map.get(version, (-1, -1))
        mixed_entries.append(
            {
                "profile": profile,
                "version": version,
                "music_index": m_idx,
                "soundscape_index": s_idx,
                "path": str(Path(clip_path).relative_to(config.AUDIO_CACHE_DIR)),
                "playback_dbfs": float(config.INTERVENTION_PLAYBACK_DBFS),
                "sha256": _sha256(clip_path),
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "generated_on_device": device,
        "git_commit": _git_commit(),
        "models": {
            "musicgen": config.MUSICGEN_MODEL_ID,
            "audiogen": config.AUDIOGEN_MODEL_ID,
        },
        "fallback_used": fallback_used,
        "audio_format": {
            "sample_rate": config.INTERVENTION_SAMPLE_RATE,
            "bit_depth": config.INTERVENTION_BIT_DEPTH,
            "channels": 1,
            "duration_s": config.INTERVENTION_DURATION_SECONDS,
        },
        "music": music_entries,
        "soundscape": soundscape_entries,
        "mixed": mixed_entries,
    }

    manifest_path = config.AUDIO_CACHE_DIR / MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def read_manifest(cache_dir: Path | None = None) -> dict[str, Any]:
    """Read and return the parsed manifest from the audio cache directory.

    Args:
        cache_dir: Directory containing ``manifest.json``.  Defaults to
            ``config.AUDIO_CACHE_DIR``.

    Returns:
        Parsed manifest dict (schema version validated).

    Raises:
        FileNotFoundError: If ``manifest.json`` does not exist.
        ValueError: If ``schema_version`` is not in ``_SUPPORTED_SCHEMA_VERSIONS``.
    """
    if cache_dir is None:
        cache_dir = config.AUDIO_CACHE_DIR
    path = Path(cache_dir) / MANIFEST_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"No manifest found at {path}. "
            "Run scripts/pregenerate_cache.py first."
        )
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported manifest schema_version {version!r}. "
            f"Supported: {_SUPPORTED_SCHEMA_VERSIONS}."
        )
    return data
