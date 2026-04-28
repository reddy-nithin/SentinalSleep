# Test Fixtures — Sources

Phase 0 shipped **synthetic placeholder WAVs**. Phase 1 has replaced them with
real curated audio. All files are **16 kHz mono PCM_16 WAV**.

## Fixture inventory

| Filename | Duration | Purpose | Acceptance criteria | Source |
|----------|----------|---------|---------------------|--------|
| `nightmare_mild.wav` | 30s | Panic breathing / mild nightmare vocalisation | best-chunk DSS > 0.01, higher than calm_sleep | User-provided: `panic attack from nightmare.wav` → resampled 22050 Hz → 16 kHz, looped to 30s |
| `nightmare_severe.wav` | 30s | Crying / sobbing | best-chunk DSS > 0.01, highest of all nightmare fixtures | User-provided: `sobbing.wav` → resampled 44.1 kHz stereo → 16 kHz mono, mixed with panic layer, looped to 30s |
| `false_positive_snore.wav` | 35.9s | Snoring | first-chunk DSS < 0.1 | User-provided: resampled 48 kHz stereo → 16 kHz mono |
| `false_positive_traffic.wav` | 34.3s | Distant traffic | first-chunk DSS < 0.1, never confirms | User-provided: resampled 48 kHz stereo → 16 kHz mono |
| `calm_sleep.wav` | 10s | Quiet ambient room | DSS < 0.05 | Phase 0 synthetic (16 kHz mono silence, acceptable as baseline) |

## Phase 1 curation checklist

- [x] Sourced each clip (user-provided audio files)
- [x] Resampled all to 16 kHz mono WAV via `scripts/prepare_fixtures.py`
- [x] Built `nightmare_severe.wav` by mixing sobbing + panic attack layers
- [x] Verified DSS behaviour with MIT AST model — see ADR-007 in EVIDENCE_LOG.md
- [x] `.synthetic` marker removed — integration tests run without skipping

## DSS calibration note (see ADR-007)

The live-system DSS flag threshold of **0.4** requires multi-class co-occurrence.
Single test clips (one sound type) produce DSS 0.01–0.08 on the MIT AST.
Integration tests therefore assert *relative ordering* (nightmare > calm)
rather than absolute breach of 0.4. The 0.4 threshold is validated by
unit tests with controlled probability inputs.

## License

All user-provided clips are personal recordings sourced by the user.
See NOTICES.md for full attribution.

## Processing script

`scripts/prepare_fixtures.py` — converts raw source files to standard format.
