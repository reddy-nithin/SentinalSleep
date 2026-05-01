"""Demo track generator for Phase 6.

Builds the 2-minute ``demo_track_2min.wav`` by assembling existing test fixtures.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sentinelsleep import config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def build_demo_track() -> Path:
    """Assemble the demo track from calm and nightmare fixtures using pydub."""
    from pydub import AudioSegment  # noqa: PLC0415
    
    out_path = config.TEST_FIXTURES_DIR / "demo_track_2min.wav"
    
    calm_path = config.TEST_FIXTURES_DIR / "calm_sleep.wav"
    severe_path = config.TEST_FIXTURES_DIR / "nightmare_severe.wav"
    
    if not calm_path.exists() or not severe_path.exists():
        logger.error(f"Missing fixtures: {calm_path.exists()} {severe_path.exists()}")
        raise FileNotFoundError("Run prepare_fixtures.py first.")
        
    calm = AudioSegment.from_wav(str(calm_path))
    severe = AudioSegment.from_wav(str(severe_path))
    
    # Assembly logic:
    # 30s calm -> 30s severe -> 60s calm
    # This guarantees the nightmare verification will trigger around the 45s mark.
    
    part1 = calm[:30000]
    part2 = severe[:30000]
    part3 = calm[:60000]
    
    # We might need to loop calm if it's too short
    while len(part1) < 30000:
        part1 += calm
    part1 = part1[:30000]
    
    while len(part2) < 30000:
        part2 += severe
    part2 = part2[:30000]

    while len(part3) < 60000:
        part3 += calm
    part3 = part3[:60000]
    
    # Crossfade slightly for smoothness
    track = part1.append(part2, crossfade=1000).append(part3, crossfade=1000)
    
    # Ensure it's 16kHz mono 16-bit
    track = track.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    
    track.export(str(out_path), format="wav")
    logger.info(f"Demo track built: {out_path} ({len(track)/1000:.1f}s)")
    
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the demo track.")
    args = parser.parse_args()
    
    if args.build:
        build_demo_track()
