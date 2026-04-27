# SentinelSleep — Master Build Plan v1.0

**Project:** SentinelSleep — AI-Powered PTSD Nightmare Interrupter
**Owner:** Nithin Reddy
**Type:** Academic portfolio project (multimodal foundation models challenge)
**Target environment:** MacBook Air M2, 8GB RAM (local-first), GCP credits available for heavy work
**Status:** Pre-build planning
**Last updated:** April 27, 2026

---

## 1. Executive Summary

SentinelSleep is a multimodal audio AI system that listens to a sleeping patient's bedroom ambient audio, detects the acoustic signature of PTSD nightmares in real time, and surgically injects therapeutic audio (calming music + nature soundscape) at low volume to nudge the brain toward lighter sleep stages — without fully waking the patient. A morning clinician dashboard tracks nightmare frequency, intervention effectiveness, and longitudinal sleep quality trends.

The system uses four foundation models from the Hugging Face ecosystem in a layered architecture: ambient sound classification (MIT AST), dimensional emotion verification (audeering wav2vec2), therapeutic music generation (Meta MusicGen), and nature soundscape generation (CVSSP AudioLDM2). All models run locally on M2 hardware via MPS acceleration with pre-generation caching to eliminate inference latency in the critical path.

**Why this matters:** PTSD nightmares are a documented driver of treatment dropout and suicide risk. Current interventions are pharmaceutical (side-effect heavy) or therapist-dependent (don't scale). SentinelSleep is a research prototype demonstrating that audio-only AI can detect and intervene on nightmare events without wearables, drugs, or clinician presence.

---

## 2. Clinical & Research Foundation

### 2.1 The Targeted Memory Reactivation (TMR) Premise

The brain during REM sleep is not auditorily closed off. Research on Targeted Memory Reactivation has shown that low-volume auditory cues delivered during sleep can influence memory consolidation, dream content, and sleep stage transitions without producing full arousal. SentinelSleep operationalizes this premise: detect the nightmare → deliver calibrated audio → influence sleep stage → log effectiveness.

### 2.2 Acoustic Signatures of Nightmares

Documented nightmare audio markers in the literature include:
- Vocalizations (crying, whimpering, screaming)
- Sleep talking with negative emotional valence
- Heavy or irregular breathing patterns
- Movement sounds (thrashing, sheet rustling)

These map cleanly onto AudioSet classes — which is exactly what the MIT AST model classifies.

### 2.3 Honest Framing

This is a **research prototype**, not a medical device. The detection-and-generation pipeline is real and verifiable. The clinical claim that low-volume audio injection reduces nightmare severity without waking would require a controlled clinical study to validate. Frame the project this way in writeups and presentations — reviewers respect calibrated claims.

---

## 3. System Architecture

### 3.1 Four-Layer Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    BEDROOM MICROPHONE                         │
│              (continuous 16kHz audio stream)                  │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼ 2-second windows
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1 — DETECTION                                          │
│  Model: MIT/ast-finetuned-audioset-10-10-0.4593               │
│  Output: probability across 527 AudioSet classes              │
│  Action: composite Distress Signal Score (DSS)                │
│  Threshold: DSS > 0.4 → escalate to Layer 2                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼ if flagged
┌──────────────────────────────────────────────────────────────┐
│  LAYER 2 — VERIFICATION                                       │
│  Model: audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim │
│  Output: valence, arousal, dominance (continuous)             │
│  Action: nightmare signature = low valence + high arousal     │
│          + low dominance, sustained > 15 seconds              │
│  Threshold: confirmed → escalate to Layer 3                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼ if confirmed
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3 — INTERVENTION                                       │
│  Models (pre-generated, cached):                              │
│    • facebook/musicgen-small (60 BPM ambient music)           │
│    • cvssp/audioldm2 (nature soundscape)                      │
│  Action: select cached clip matching distress profile,        │
│          mix layers, play at -20dB ambient                    │
│  Duration: 60s, then re-evaluate                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼ if distress persists
┌──────────────────────────────────────────────────────────────┐
│  LAYER 4 — ESCALATION                                         │
│  Progressive wake alarm + grounding breathing audio +         │
│  crisis resource surfacing                                    │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼ logged throughout
┌──────────────────────────────────────────────────────────────┐
│  EVENT LOG (SQLite) → MORNING DASHBOARD (Streamlit)           │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 State Machine

```
        ┌─── LISTENING ──────────────────────────┐
        │                                         │
        │  [DSS > 0.4]                           │
        ▼                                         │
    FLAGGED ──[verification fails]──────────────┘
        │
        │  [nightmare signature confirmed]
        ▼
    INTERVENING ──[distress resolves < 60s]──┐
        │                                     │
        │  [distress persists > 60s]          │
        ▼                                     ▼
    ESCALATING                            RESOLVED
        │                                     │
        │  [wake protocol complete]           │
        ▼                                     │
    AWAKE ◄──────────────────────────────────┘
```

Every state transition logs to `events` table with timestamp, trigger reason, distress scores, and intervention metadata.

---

## 4. Tech Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11 | Matches existing TruPharma/SIGNAL stack |
| Env manager | uv | Standard across user's projects |
| ML framework | PyTorch + transformers | Native HF model loading; MPS support on M2 |
| Audio I/O | sounddevice + soundfile | Real-time mic capture + WAV read/write |
| Audio mixing | pydub | Simple layer mixing, volume calibration |
| Database | SQLite | No server overhead, file-based, perfect for prototype |
| UI | Streamlit | Matches user's stack default; fast dashboards |
| Visualization | Plotly + matplotlib | Plotly for interactive timeline; matplotlib for spectrograms |
| Acceleration | Apple MPS | M2 GPU via PyTorch MPS backend |
| Packaging | uv project + pyproject.toml | Reproducible env |

### 4.1 Model Inventory

| Layer | Model | Params | License | Local? |
|-------|-------|--------|---------|--------|
| Detection | `MIT/ast-finetuned-audioset-10-10-0.4593` | 86.6M | BSD-3 | ✅ |
| Verification | `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` | 165.3M | CC-BY-NC-SA | ✅ |
| Music gen | `facebook/musicgen-small` | 300M | CC-BY-NC | ✅ |
| Sound gen | `cvssp/audioldm2` | 1.1B | CC-BY-NC-SA | ⚠️ heavy — pre-generate, then cache |

**Memory budget on M2 8GB:** Detection + verification can co-reside in memory (~250MB combined). Generation models are NOT loaded during the live detection loop — they run during a one-time pre-generation step at startup, then unload. Cached audio plays from disk.

---

## 5. Project Structure

```
sentinelsleep/
├── README.md
├── CLAUDE.md                    # Claude Code project instructions
├── EVIDENCE_LOG.md              # Decision records (ADR-style)
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── src/
│   └── sentinelsleep/
│       ├── __init__.py
│       ├── config.py            # Thresholds, paths, constants
│       │
│       ├── detection/
│       │   ├── __init__.py
│       │   ├── ast_classifier.py        # MIT AST wrapper
│       │   ├── audioset_labels.py       # 527 class names
│       │   └── distress_score.py        # Composite DSS calculator
│       │
│       ├── verification/
│       │   ├── __init__.py
│       │   ├── emotion_dim.py           # audeering wav2vec2 wrapper
│       │   └── nightmare_signature.py   # Combined logic
│       │
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── musicgen_wrapper.py      # MusicGen interface
│       │   ├── audioldm2_wrapper.py     # AudioLDM2 interface
│       │   ├── mixer.py                 # pydub layer mixing
│       │   └── pregenerate.py           # One-time cache builder
│       │
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   ├── state_machine.py         # State transitions
│       │   ├── audio_stream.py          # sounddevice mic capture
│       │   ├── event_logger.py          # SQLite event writer
│       │   └── runner.py                # Main event loop
│       │
│       ├── dashboard/
│       │   ├── __init__.py
│       │   ├── app.py                   # Streamlit entry
│       │   ├── views/
│       │   │   ├── timeline.py
│       │   │   ├── waveform.py
│       │   │   ├── interventions.py
│       │   │   └── trends.py
│       │   └── queries.py               # SQLite read layer
│       │
│       └── demo/
│           ├── __init__.py
│           ├── simulator.py             # Plays test audio through pipeline
│           └── fixtures/                # Pre-recorded test clips
│
├── data/
│   ├── audio_cache/                     # Pre-generated therapeutic audio
│   │   ├── music/
│   │   └── soundscape/
│   ├── test_fixtures/                   # Sample nightmare audio for testing
│   └── events.db                        # SQLite event log
│
├── tests/
│   ├── test_detection.py
│   ├── test_verification.py
│   ├── test_distress_score.py
│   ├── test_state_machine.py
│   └── test_event_logger.py
│
├── scripts/
│   ├── pregenerate_cache.py             # Run once to build audio cache
│   ├── run_live.py                      # Real-time pipeline
│   ├── run_simulation.py                # Demo mode with fake audio
│   └── run_dashboard.py                 # Launches Streamlit
│
└── docs/
    ├── architecture.md
    ├── demo_script.md
    └── presentation_outline.md
```

---

## 6. Data & Test Fixtures

### 6.1 Test Audio Sources

For development and demo, you do not need real patient audio. You will assemble simulated nightmare audio from royalty-free sources:

| Component | Source | Purpose |
|-----------|--------|---------|
| Crying samples | Freesound.org (CC0) | Detection layer testing |
| Heavy breathing | Freesound.org | Verification layer testing |
| Movement / sheet rustling | Freesound.org | Composite distress testing |
| Calm sleep audio | Freesound.org | Negative test (should NOT trigger) |
| Background room ambient | Self-recorded | Baseline audio |

Build `data/test_fixtures/` with at least:
- `nightmare_mild.wav` — whimpering only
- `nightmare_severe.wav` — crying + heavy breathing
- `false_positive_snore.wav` — should not trigger
- `false_positive_traffic.wav` — should not trigger
- `calm_sleep.wav` — baseline

### 6.2 The Demo Audio

For class presentation: build a 2-minute scripted audio file that goes:
1. 30s calm sleep (system shows green)
2. 20s mild distress onset (Layer 1 flags, dashboard waveform spikes)
3. 30s confirmed nightmare (Layer 2 verifies, Layer 3 fires intervention)
4. 30s recovery (intervention works, distress drops)
5. 10s back to calm

This single file is what you play in class. The dashboard reacts in real time. No need to fake a sleeping person.

---

## 7. Build Phases

Each phase is a self-contained Claude Code task with a clear deliverable and acceptance test. Build in order — do not skip ahead.

### Phase 0 — Setup & Scaffolding *(0.5 day)*

**Deliverables:**
- uv project initialized with `pyproject.toml`
- All directories from §5 created with `__init__.py` files
- `CLAUDE.md` written with project context and conventions
- `EVIDENCE_LOG.md` initialized
- `config.py` with all thresholds and paths
- `.env.example` with any future API keys
- Sample test fixtures downloaded into `data/test_fixtures/`
- README with setup instructions

**Acceptance:**
- `uv sync` runs clean
- `pytest tests/` runs (no tests yet, just confirms test infra works)
- Repo pushes to GitHub

---

### Phase 1 — Detection Layer *(1 day)*

**Deliverables:**
- `detection/ast_classifier.py` — loads MIT AST, classifies 2-second audio chunks, returns top-K predictions
- `detection/audioset_labels.py` — full 527-class label list with distress-relevant subset flagged
- `detection/distress_score.py` — composite DSS calculator combining crying, screaming, whimpering, heavy breathing, movement sound probabilities
- `tests/test_detection.py` — passing tests on fixture audio

**Distress class subset (initial):**
```python
DISTRESS_CLASSES = {
    "Crying, sobbing": 1.0,
    "Whimper": 0.9,
    "Screaming": 1.0,
    "Wail, moan": 0.8,
    "Heavy breathing": 0.6,
    "Gasp": 0.7,
    "Groan": 0.5,
    "Rustle": 0.3,
    "Thump, thud": 0.4,
}
# DSS = sum(prob_class * weight) normalized
```

**Acceptance:**
- `nightmare_mild.wav` produces DSS > 0.4
- `calm_sleep.wav` produces DSS < 0.1
- `false_positive_snore.wav` produces DSS < 0.3
- Inference < 300ms per 2s chunk on M2 MPS

---

### Phase 2 — Verification Layer *(1 day)*

**Deliverables:**
- `verification/emotion_dim.py` — wraps audeering wav2vec2, returns (valence, arousal, dominance) for any audio chunk
- `verification/nightmare_signature.py` — combines DSS history + dimensional scores into a confirmed/unconfirmed binary, with confidence
- `tests/test_verification.py` — passing tests

**Nightmare signature rule (initial):**
```python
def is_nightmare(dss_window, valence, arousal, dominance, duration_s):
    return (
        mean(dss_window) > 0.4
        and valence < 0.4       # negative emotional state
        and arousal > 0.6       # high activation
        and dominance < 0.4     # low control
        and duration_s >= 15
    )
```

**Acceptance:**
- `nightmare_severe.wav` confirms after 15s
- `false_positive_traffic.wav` never confirms
- Inference < 500ms per chunk

---

### Phase 3 — Generation Layer *(1.5 days)*

**Deliverables:**
- `generation/musicgen_wrapper.py` — MusicGen wrapper with prompt templates
- `generation/audioldm2_wrapper.py` — AudioLDM2 wrapper for soundscapes
- `generation/mixer.py` — pydub-based two-layer mixing with volume calibration
- `generation/pregenerate.py` — script that builds the entire audio cache

**Pre-generated cache structure:**
```
data/audio_cache/
├── music/
│   ├── ambient_60bpm_low_v1.wav    # 60s
│   ├── ambient_60bpm_low_v2.wav
│   ├── ambient_60bpm_low_v3.wav
│   └── ...
├── soundscape/
│   ├── ocean_gentle_v1.wav
│   ├── rain_soft_v1.wav
│   ├── forest_night_v1.wav
│   └── ...
└── mixed/
    ├── intervention_mild_v1.wav      # music + soundscape, mixed
    ├── intervention_severe_v1.wav
    └── ...
```

**Generation prompts (starting point):**
- Music: `"slow calming ambient music, 60 BPM, low frequency drone, no percussion, sleep therapy, gentle, warm"`
- Soundscape: `"gentle ocean waves at night, distant and slow"` / `"soft steady rain on leaves"` / `"quiet forest at night, wind, no birds"`

**Acceptance:**
- `pregenerate.py` runs end-to-end and populates `data/audio_cache/`
- All output WAV files are 60s, 16-bit, 44.1kHz
- Mixed clips have soundscape at -6dB relative to music
- Cache contains at least 5 mild + 5 severe variants

---

### Phase 4 — Orchestration *(1.5 days)*

**Deliverables:**
- `orchestrator/audio_stream.py` — continuous mic capture into a rolling 2s buffer
- `orchestrator/state_machine.py` — implements the state diagram from §3.2
- `orchestrator/event_logger.py` — SQLite schema + write API
- `orchestrator/runner.py` — main loop that ties detection → verification → intervention together

**SQLite schema:**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    timestamp TIMESTAMP,
    state TEXT,                 -- listening/flagged/intervening/escalating/resolved
    dss REAL,                   -- distress signal score
    valence REAL,
    arousal REAL,
    dominance REAL,
    intervention_clip TEXT,     -- path to played audio, if any
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE interventions (
    id INTEGER PRIMARY KEY,
    event_id INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    clip_path TEXT,
    pre_dss REAL,
    post_dss REAL,
    effective BOOLEAN,
    FOREIGN KEY (event_id) REFERENCES events(id)
);
```

**Acceptance:**
- Run `scripts/run_simulation.py` with `nightmare_severe.wav` as input
- Pipeline transitions: LISTENING → FLAGGED → INTERVENING → RESOLVED
- All transitions logged to SQLite
- An intervention clip plays from speakers

---

### Phase 5 — Dashboard *(1.5 days)*

**Deliverables:**
- `dashboard/app.py` — Streamlit entry point
- Four views: Timeline, Waveform, Interventions, Trends
- `dashboard/queries.py` — read-only SQLite queries for views
- `scripts/run_dashboard.py`

**View specs:**

**Timeline view:**
- Horizontal timeline of last night
- Color-coded bars for each state (green=listening, yellow=flagged, red=intervening, blue=resolved)
- Click any segment for details

**Waveform view:**
- Plotly chart, x=time, y=DSS
- Overlay: valence, arousal, dominance lines
- Vertical markers where interventions fired

**Interventions view:**
- Table of all interventions: timestamp, clip name, pre/post DSS, effective?
- Audio playback widget for each clip

**Trends view:**
- 7-day rolling: total nightmares, avg duration, intervention success rate
- Sleep quality composite score (your formula)

**Acceptance:**
- `streamlit run scripts/run_dashboard.py` launches
- All four views render correctly with data from a simulated session
- No SQL injection or unsafe queries

---

### Phase 6 — Demo Mode *(1 day)*

**Deliverables:**
- `demo/simulator.py` — plays a scripted audio file through the full pipeline as if it were live mic input
- `demo/fixtures/demo_track_2min.wav` — the 2-minute scripted demo audio (build per §6.2)
- `scripts/run_simulation.py` — single command that triggers the demo
- `docs/demo_script.md` — exact steps to run during presentation

**Acceptance:**
- One command launches: `python scripts/run_simulation.py`
- Dashboard updates live as the audio plays
- Spectrogram visualization is visible during the demo
- Total runtime: ~2 minutes, ends with a clean dashboard summary

---

### Phase 7 — Polish & Presentation *(1 day)*

**Deliverables:**
- `README.md` — full project description, setup, demo instructions, model credits
- `docs/architecture.md` — system diagram (export from draw.io or Mermaid)
- `docs/presentation_outline.md` — 8-10 slide outline for class presentation
- Demo video (1-2 min) recorded with QuickTime + dashboard screen capture
- LICENSE (MIT or similar; respect underlying model licenses in NOTICES.md)
- `NOTICES.md` — model attribution and license summary

**Acceptance:**
- Repo is clean, well-documented, public-ready on GitHub
- README has badges, screenshots, demo GIF
- Presentation outline is ready to convert into Gamma deck

---

## 8. Demo Strategy

### 8.1 The Class Demo Flow (5-7 minutes)

1. **Hook (30s):** "PTSD nightmares affect 8 million Americans. Drugs have side effects. Therapists can't be in the bedroom. What if AI could be?"
2. **Architecture overview (90s):** Show the 4-layer diagram on screen, narrate each layer's job
3. **Live demo (2-3 min):** Run `scripts/run_simulation.py`, point to:
   - Spectrogram lighting up as nightmare audio starts
   - DSS waveform climbing in real time
   - Verification scores updating
   - Intervention firing — audio audibly starts playing
   - DSS dropping as intervention takes effect
4. **Dashboard tour (60s):** Switch to Streamlit, show timeline, intervention log, trends view
5. **Honest framing (30s):** "This is a research prototype. Detection and generation are real. Clinical effectiveness needs controlled study."
6. **Q&A**

### 8.2 What Could Go Wrong During Demo

| Risk | Mitigation |
|------|-----------|
| Mic issues with live audio | Use file-based simulator, never live mic during class |
| Audio output cuts out | Pre-test exact AV setup at venue; bring backup laptop |
| Generation latency mid-demo | Pre-generated cache eliminates this |
| Dashboard slow to update | Cache SQLite reads; refresh every 1s not on every event |
| Internet flaky | Entire demo runs offline; download all models in advance |

---

## 9. Evaluation & Metrics

For your writeup, evaluate the system on:

### 9.1 Detection Metrics
- Precision/recall on a labeled test set (your fixtures + 5-10 added)
- False positive rate on negative fixtures (snoring, traffic, AC unit)
- Inference latency per chunk (must be < 500ms)

### 9.2 Verification Metrics
- Confusion matrix: confirmed nightmares vs. confirmed non-nightmares
- Time-to-confirmation (should be 15-25s)

### 9.3 System Metrics
- End-to-end pipeline latency (detection → intervention play): target < 12s
- Cache hit rate (should be 100% — no on-demand generation)
- SQLite write throughput (non-issue, but log it)

### 9.4 Subjective Quality
- Have 3-5 friends listen to generated soundscapes; rate calmness 1-5
- A/B test: which sounds more "sleep-conducive"?

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| AST detects too many false positives in noisy environments | Medium | High | Two-layer verification specifically addresses this; tune thresholds |
| MusicGen output is monotonous / doesn't sound calming | Medium | Medium | Generate 10+ variants, manually curate top 5; iterate prompts |
| AudioLDM2 too heavy for M2 8GB | Medium | Medium | Pre-generate only; never load during live loop. Fall back to royalty-free nature audio if needed. |
| Mic capture has latency on macOS | Low | Medium | Use sounddevice with explicit buffer config; test early in Phase 4 |
| Streamlit slow with frequent updates | Low | Low | Use st.empty() containers and rerun throttling |
| Demo file plays out of sync with dashboard | Medium | High | Use single audio thread; events written before audio plays each chunk |
| Class projector audio has issues | Medium | High | Bring own portable speaker; pre-test |

---

## 11. Stretch Goals (post-MVP)

If you finish core build with time remaining:

- **Personalization:** Learn each user's baseline acoustics over multiple nights; auto-adjust thresholds
- **Multi-night dashboard:** 30-day view with sleep quality trend, nightmare frequency curve
- **Clinician export:** Generate a PDF report summarizing a week of data
- **Voice journaling integration:** Morning voice check-in adds qualitative context to acoustic data (extends to ARIA territory — clean integration path)
- **Phone-based version:** Port detection layer to mobile via ONNX export
- **Comparative analysis:** Run all four detection thresholds (DSS only / dimensional only / both / either) on labeled set; quantify the value of two-layer verification

---

## 12. Submission Deliverables

For the academic challenge:

1. ✅ Working codebase on GitHub (public)
2. ✅ README with setup + demo instructions
3. ✅ Architecture diagram
4. ✅ Demo video (1-2 minutes)
5. ✅ Presentation deck (8-10 slides via Gamma)
6. ✅ Live class demo (5-7 minutes)
7. ✅ Brief written report (2-3 pages) covering: problem, architecture, models used, evaluation results, honest limitations, future work
8. ✅ Model attribution / NOTICES.md

---

## 13. Total Build Estimate

| Phase | Days | Cumulative |
|-------|------|-----------|
| 0 — Setup | 0.5 | 0.5 |
| 1 — Detection | 1.0 | 1.5 |
| 2 — Verification | 1.0 | 2.5 |
| 3 — Generation | 1.5 | 4.0 |
| 4 — Orchestration | 1.5 | 5.5 |
| 5 — Dashboard | 1.5 | 7.0 |
| 6 — Demo Mode | 1.0 | 8.0 |
| 7 — Polish | 1.0 | 9.0 |

**Total: ~9 working days.** Compressed timeline (parallel work, evenings): 5-6 calendar days.

---

## 14. Hardware Notes

**MacBook Air M2 (8GB RAM) — what runs where:**

- ✅ MIT AST: ~350MB, MPS-accelerated, real-time fine
- ✅ audeering wav2vec2: ~660MB, MPS-accelerated, real-time fine
- ⚠️ MusicGen-small: ~1.2GB, MPS-accelerated, ~10s per 60s clip — pre-generate only
- ⚠️ AudioLDM2: ~4GB, MPS-accelerated, ~20s per 60s clip — pre-generate only
- ✅ Streamlit + SQLite: negligible

**Critical rule:** During live operation, only Detection + Verification models are loaded. Generation models are loaded by `pregenerate.py`, run once, then unloaded. The live loop reads pre-generated WAVs from disk.

**If memory pressure becomes real:** Move pre-generation to GCP free tier (use those `$295` of credits expiring May 28). One-time job, ~30 minutes, downloads cache back to local.

---

## 15. References to Cite in Report

When writing up the project, cite (look up exact citations):
- AudioSet paper (Gemmeke et al., 2017) — for MIT AST training data
- AST paper (Gong et al., 2021) — for the detection architecture
- wav2vec 2.0 paper (Baevski et al., 2020) — for verification model
- MusicGen paper (Copet et al., 2023) — for music generation
- AudioLDM 2 paper (Liu et al., 2023) — for soundscape generation
- TMR research (Oudiette & Paller, 2013) — for the auditory sleep intervention premise
- PTSD nightmare literature (Davis et al., for prevalence and clinical context)

---

**End of plan v1.0** — update version on every material change. Log decisions to `EVIDENCE_LOG.md`.
