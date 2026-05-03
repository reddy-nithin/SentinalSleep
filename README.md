# SentinelSleep

> Real-time PTSD nightmare detection and therapeutic audio intervention — runs entirely on a MacBook.

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=next.js)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/Source-MIT-green)](LICENSE)
[![Models: Non-commercial](https://img.shields.io/badge/Models-CC--BY--NC--SA--4.0-orange)](NOTICES.md)
[![Research Prototype](https://img.shields.io/badge/Status-Research%20Prototype-blueviolet)](#research-disclaimer)

SentinelSleep is an audio AI system that monitors bedroom microphone audio for nightmare distress signatures and automatically injects pre-generated therapeutic soundscapes to interrupt them — without waking the patient. A Next.js dashboard visualizes overnight session data, DSS waveforms, and longitudinal sleep trends.

---

## How It Works

Four layers run in sequence on every 2-second audio chunk:

| Layer | Model | Role |
| ----- | ----- | ---- |
| **1 · Detection** | [MIT AST](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593) (AudioSet 527 classes) | Computes a Distress Signal Score (DSS ∈ [0, 1]) per chunk |
| **2 · Verification** | [audeering wav2vec2](https://huggingface.co/audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim) | Confirms nightmare via valence / arousal / dominance; requires ≥ 15 s sustained signature |
| **3 · Intervention** | MusicGen + AudioGen *(pre-cached offline)* | Plays ambient audio at −20 dBFS from a pre-built WAV cache |
| **4 · Escalation** | Rule-based state machine | Progressive wake protocol if distress persists beyond 60 s |

```text
Mic / WAV file
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Detection        MIT AST → DSS score           │
│                            DSS > 0.4? ──────────┐        │
│  Layer 2: Verification     wav2vec2 VAD → nightmare sig? │
│                            confirmed? ──────────┐        │
│  Layer 3: Intervention     pre-cached WAV playback       │
│                            persists > 60s? ─────┐        │
│  Layer 4: Escalation       progressive wake protocol     │
└─────────────────────────────────────────────────────────┘
      │                           │
      ▼                           ▼
  SQLite event log          Next.js dashboard
```

**Memory budget (Apple M2 8 GB):** Only detection + verification models (~1 GB combined) are resident during the live loop. Generation models run once in `scripts/pregenerate_cache.py`, then unload. Cached WAVs play from disk at inference time.

→ [Full architecture diagram](docs/architecture.md)

---

## Dashboard

The Next.js dashboard reads from JSON exports of the SQLite event log — overnight session timelines, DSS waveforms, intervention audio playback, and multi-session trend charts.

> **Demo data is included.** Clone the repo, run `npm run dev`, and the dashboard is immediately populated with four synthetic overnight sessions.

---

## Quick Start

**Requirements:** Python 3.11 · [uv](https://docs.astral.sh/uv/) · Node.js 20+ · ffmpeg

```bash
# 1. Install system dependency
brew install ffmpeg

# 2. Clone and install Python deps
git clone https://github.com/reddy-nithin/SentinalSleep.git
cd SentinalSleep
uv sync

# 3. Verify setup
uv run pytest tests/

# 4. Run demo simulation (scripted audio scenario through the full pipeline)
uv run python scripts/run_simulation.py

# 5. Web dashboard (demo data included — no setup needed)
cd web && npm install && npm run dev    # → http://localhost:3000
```

**Pre-generate the audio cache** (required for live microphone mode):

```bash
# Option A: local CPU / Apple MPS (~60 min)
uv run python scripts/pregenerate_cache.py

# Option B: Colab GPU (~15 min)
# See docs/colab_cache_generation.md
```

**Live microphone mode** (after cache is built):

```bash
uv run python scripts/run_live.py
```

---

## Tech Stack

| Component | Technology |
| --------- | ---------- |
| Sound classification | MIT AST fine-tuned on AudioSet-527 |
| Emotion verification | audeering wav2vec2 (valence / arousal / dominance) |
| Ambient music generation | `facebook/musicgen-small` *(pre-cached)* |
| Soundscape generation | `facebook/audiogen-medium` *(pre-cached)* |
| Audio mixing | pydub |
| Live audio capture | sounddevice |
| Event persistence | SQLite (custom schema) |
| Dashboard | Next.js 15 · Tailwind CSS · Recharts |
| Python toolchain | uv · pytest · ruff |
| Target hardware | Apple M2 (MPS) |

---

## Project Structure

```text
SentinalSleep/
├── src/sentinelsleep/
│   ├── detection/        # MIT AST classifier + Distress Signal Score
│   ├── verification/     # wav2vec2 dimensional emotion model
│   ├── generation/       # MusicGen / AudioGen wrappers + cache manifest
│   ├── orchestrator/     # State machine, event logger, audio stream runner
│   └── db/               # SQLite schema + query helpers
├── scripts/
│   ├── run_simulation.py          # Demo / test mode
│   ├── run_live.py                # Live microphone mode
│   ├── pregenerate_cache.py       # Build audio cache (run once)
│   └── export_snapshot.py         # Export SQLite → web/data/ JSON
├── web/                           # Next.js 15 dashboard
│   └── data/                      # Demo session snapshots (4 sessions included)
├── tests/                         # pytest suite (~12 test files)
├── docs/
│   ├── architecture.md            # Mermaid system diagram + data flow constraints
│   └── colab_cache_generation.md  # GPU cache generation guide
└── notebooks/
    └── pregenerate_on_colab.ipynb # Colab notebook for cache generation
```

---

## Research Disclaimer

SentinelSleep operationalizes [Targeted Memory Reactivation (TMR)](https://doi.org/10.1016/j.cub.2019.10.064) research: low-volume auditory cues delivered during sleep can influence sleep stage transitions without full arousal. **This is not a medical device.** The detection and generation pipelines are implemented and verifiable. Whether audio injection reduces nightmare severity at therapeutic levels is a question for controlled clinical study — outside the scope of this prototype.

---

## License

Source code: **MIT** — see [LICENSE](LICENSE).  
Pre-trained model weights: **non-commercial use only** (CC-BY-NC-SA-4.0) — see [NOTICES.md](NOTICES.md).  
The verification model (`audeering/wav2vec2`) is the most restrictive; productizing this system requires replacing it with a permissively licensed alternative.
