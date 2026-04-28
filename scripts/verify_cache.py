#!/usr/bin/env python3
"""Verify the integrity of the pre-generated therapeutic audio cache.

Reads ``data/audio_cache/manifest.json`` and checks every listed clip:

* File exists at the expected path.
* SHA-256 matches the value recorded in the manifest.
* Audio format is valid per Phase 3 acceptance criteria (duration, sample
  rate, bit depth, channels) using the existing
  :func:`sentinelsleep.generation.mixer.validate_cache_clip` helper.

Exit codes::

    0 — all checks pass
    1 — one or more checks failed

Examples::

    uv run python scripts/verify_cache.py
    uv run python scripts/verify_cache.py --no-sha256   # skip slow hash check
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("verify_cache")

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-sha256",
        action="store_true",
        help="Skip SHA-256 verification (faster, but does not detect byte-level corruption).",
    )
    args = parser.parse_args()

    from sentinelsleep import config
    from sentinelsleep.generation.manifest import read_manifest
    from sentinelsleep.generation.mixer import validate_cache_clip

    try:
        manifest = read_manifest()
    except FileNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except ValueError as exc:
        log.error("Manifest schema error: %s", exc)
        sys.exit(1)

    log.info("Manifest generated_at : %s", manifest["generated_at"])
    log.info("Manifest git_commit   : %s", manifest["git_commit"])
    log.info("Generated on device   : %s", manifest["generated_on_device"])
    log.info("Fallback used         : %s", manifest["fallback_used"])
    log.info("")

    failures: list[str] = []

    def _check_entry(entry: dict) -> None:  # type: ignore[type-arg]
        rel = entry["path"]
        full = config.AUDIO_CACHE_DIR / rel

        if not full.exists():
            failures.append(f"MISSING  {rel}")
            return

        result = validate_cache_clip(full)
        if not result["valid"]:
            for err in result["errors"]:  # type: ignore[union-attr]
                failures.append(f"FORMAT   {rel} — {err}")

        if not args.no_sha256:
            actual = _sha256(full)
            if actual != entry["sha256"]:
                failures.append(
                    f"SHA256   {rel}\n"
                    f"         expected: {entry['sha256']}\n"
                    f"         actual:   {actual}"
                )

    categories = [
        ("Music", manifest["music"]),
        ("Soundscape", manifest["soundscape"]),
        ("Mixed", manifest["mixed"]),
    ]

    for label, entries in categories:
        log.info("Checking %s clips (%d)…", label.lower(), len(entries))
        for entry in entries:
            _check_entry(entry)
            status = "✓" if not failures or not any(entry["path"] in f for f in failures) else "✗"
            log.info("  %s %s", status, entry["path"])

    log.info("")
    if failures:
        log.error("Cache verification FAILED — %d issue(s):", len(failures))
        for msg in failures:
            log.error("  %s", msg)
        sys.exit(1)

    sha_note = " (SHA-256 skipped)" if args.no_sha256 else ""
    log.info("✓ All %d clips verified%s.", sum(len(e) for _, e in categories), sha_note)
    log.info("  Cache is ready for Phase 4 orchestration.")


if __name__ == "__main__":
    main()
