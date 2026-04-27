# Test Fixtures — Sources

Phase 0 ships **synthetic placeholder WAVs** so the test infra runs and
all file paths resolve. Phase 1 replaces them with real curated audio.

## Fixture inventory

| Filename | Purpose | Expected behaviour (Phase 1+) | Real source (Phase 1) |
|----------|---------|-------------------------------|----------------------|
| `nightmare_mild.wav` | Whimpering only | DSS > 0.4 | Freesound.org CC0 — search "whimper soft cry" |
| `nightmare_severe.wav` | Crying + heavy breathing | DSS > 0.4, nightmare confirmed after 15s | Freesound.org CC0 — combine sobbing + heavy breathing clips |
| `false_positive_snore.wav` | Snoring | DSS < 0.3 | Freesound.org CC0 — search "snore sleep" |
| `false_positive_traffic.wav` | Distant traffic | DSS < 0.3, never confirms | Freesound.org CC0 — search "distant traffic ambient" |
| `calm_sleep.wav` | Quiet ambient room | DSS < 0.1 | Self-recorded room tone OR Freesound.org CC0 |

## Phase 1 curation checklist

- [ ] Log in to Freesound.org (free account, API token in `.env` if scripting)
- [ ] Download each clip, trim to 10–30 seconds, resample to 16kHz mono WAV
- [ ] Verify DSS behaviour on each clip against Phase 1 acceptance criteria
- [ ] Update NOTICES.md with Freesound attribution (clip ID, uploader, license)

## License requirement

Only **CC0** or **CC-BY** (with attribution in NOTICES.md) sources.
No CC-BY-NC or CC-BY-SA in test fixtures — they would restrict CI use.

## Phase 0 placeholder note

The current WAVs are synthetic (pink noise, white noise, silence) generated
by `scripts/make_placeholder_fixtures.py` with `numpy.random.default_rng(42)`.
They exist only so file paths resolve. They will NOT pass Phase 1 DSS tests.
