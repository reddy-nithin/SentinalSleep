# SentinelSleep

Audio AI system that detects PTSD nightmares from bedroom mic audio in
real time and surgically injects therapeutic audio to interrupt them
without waking the patient. A Streamlit morning dashboard tracks
nightmare frequency, intervention effectiveness, and longitudinal trends.

> **Research prototype.** Detection and generation pipelines are real
> and verifiable. Clinical effectiveness requires a controlled study —
> this is not a medical device.

---

## Architecture

Four-layer pipeline, all running locally on Apple M2 (MPS):

```
Bedroom mic → [Layer 1: Detection] → DSS > 0.4?
                     ↓ yes
            [Layer 2: Verification] → nightmare confirmed?
                     ↓ yes
            [Layer 3: Intervention] ← pre-cached audio (MusicGen + AudioLDM2)
                     ↓ persists > 60s
            [Layer 4: Escalation] → progressive wake protocol
                     ↓ throughout
            SQLite event log → Streamlit dashboard
```

| Layer | Model | Purpose |
|-------|-------|---------|
| Detection | `MIT/ast-finetuned-audioset-10-10-0.4593` | 527-class AudioSet sound classifier |
| Verification | `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` | Valence / arousal / dominance |
| Music gen | `facebook/musicgen-small` | 60 BPM ambient sleep music (pre-cached) |
| Soundscape gen | `cvssp/audioldm2` | Nature soundscapes (pre-cached) |

**Memory budget (M2 8GB):** Only detection + verification models are
resident during the live loop (~1GB combined). Generation models run
once in `pregenerate_cache.py`, then unload. Cached WAVs play from disk.

---

## Setup

**Requirements:** Python 3.11, [uv](https://docs.astral.sh/uv/), ffmpeg.

```bash
# 1. Install system deps
brew install ffmpeg

# 2. Clone and install Python deps
git clone https://github.com/reddy-nithin31/sentinelsleep
cd sentinelsleep
uv sync

# 3. Verify setup
uv run pytest tests/
```

---

## Usage

```bash
# Build the therapeutic audio cache (run once before live use)
uv run python scripts/pregenerate_cache.py

# Live microphone mode
uv run python scripts/run_live.py

# Demo / simulation mode (plays a scripted audio file through the pipeline)
uv run python scripts/run_simulation.py

# Morning dashboard
uv run streamlit run scripts/run_dashboard.py
```

---

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Setup & Scaffolding | ✅ Complete |
| 1 | Detection Layer (AST + DSS) | ⬜ Pending |
| 2 | Verification Layer (wav2vec2) | ⬜ Pending |
| 3 | Generation Layer (cache builder) | ⬜ Pending |
| 4 | Orchestration (state machine + event log) | ⬜ Pending |
| 5 | Dashboard (Streamlit) | ⬜ Pending |
| 6 | Demo Mode (simulator) | ⬜ Pending |
| 7 | Polish & Presentation | ⬜ Pending |

---

## License

Source code: **MIT** — see [LICENSE](LICENSE).
Pre-trained model weights: see [NOTICES.md](NOTICES.md).
The most restrictive model license is CC-BY-NC-SA-4.0 — **non-commercial use only.**

---

## Clinical framing

SentinelSleep operationalizes Targeted Memory Reactivation (TMR) research:
low-volume auditory cues delivered during sleep can influence sleep stage
transitions without causing full arousal. The detection and generation
pipelines are implemented and verifiable. Whether audio injection reduces
nightmare severity at therapeutic levels is a question for controlled
clinical study — outside the scope of this prototype.
