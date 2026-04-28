#!/usr/bin/env python3
"""CLI entry point for the Phase 3 therapeutic audio cache builder.

Builds ``data/audio_cache/{music,soundscape,mixed}/`` via MusicGen, AudioLDM2
(or synthetic soundscape fallback), and pydub mixing. See
``sentinelsleep.generation.pregenerate.build_cache`` for details.

Examples::

    uv run python scripts/pregenerate_cache.py
    uv run python scripts/pregenerate_cache.py --use-synthetic-soundscape
    uv run python scripts/pregenerate_cache.py --skip-music --skip-soundscapes
"""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    """Parse CLI flags and run :func:`build_cache`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--skip-music",
        action="store_true",
        help="Skip MusicGen; require existing WAVs in data/audio_cache/music/.",
    )
    parser.add_argument(
        "--skip-soundscapes",
        action="store_true",
        help="Skip soundscape generation; require existing WAVs in data/audio_cache/soundscape/.",
    )
    parser.add_argument(
        "--skip-mixing",
        action="store_true",
        help="Skip pydub mixing; only validate existing mixed clips.",
    )
    parser.add_argument(
        "--use-synthetic-soundscape",
        action="store_true",
        help=(
            "Never load AudioLDM2; write band-limited pink-noise placeholders for "
            "any missing soundscapes (ADR-010)."
        ),
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip writing data/audio_cache/manifest.json after a successful build (ADR-013).",
    )
    args = parser.parse_args()

    from sentinelsleep.generation.pregenerate import build_cache

    ok = build_cache(
        skip_music=args.skip_music,
        skip_soundscapes=args.skip_soundscapes,
        skip_mixing=args.skip_mixing,
        use_synthetic_soundscape=args.use_synthetic_soundscape,
        write_manifest=not args.no_manifest,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
