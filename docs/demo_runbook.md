# SentinelSleep — 3-Minute Demo Runbook

## Pre-flight (5 min before)

```bash
# 1. Verify audio cache is present
ls data/audio_cache/manifest.json data/audio_cache/mixed/ | wc -l   # expect ≥ 11

# 2. Build the 2-min demo track from fixtures (idempotent)
uv run python -m sentinelsleep.demo.simulator --build

# 3. Reset DB and seed 6 nights of synthetic history for dashboard context
rm -f data/events.db
uv run python scripts/seed_synthetic_events.py --nights 6 --profile mixed

# 4. Smoke-test (no audio playback, no real-time pace)
uv run python scripts/run_simulation.py --demo --fast --dry-run

# 5. Start the dashboard (keep running in background tab)
uv run streamlit run scripts/run_dashboard.py
# → opens http://localhost:8501
```

---

## Live Narrative Arc (3 min, two terminals + browser)

| t (s)   | Terminal / Browser | Script |
|---------|-------------------|--------|
| 0–20    | Browser — Overview page, 6-night history visible | "This is the morning report a clinician opens. Six nights of data — one severe, three mild, two clean. The recovery score ring on the left tells you the night at a glance." |
| 20–40   | Terminal 1: `uv run python scripts/run_simulation.py --demo` | "Now we replay last night in real-time. The system is processing the bedroom mic stream, classifying every two-second window." |
| 40–90   | Watch console output: LISTENING → FLAGGED → INTERVENING | "DSS just crossed 0.4 — that's the AST distress score, 527 AudioSet classes in real time. Wav2vec2 confirms low valence, high arousal — nightmare signature sustained for 15 seconds. The system pulled a pre-cached MusicGen + AudioGen mix and is playing it at -20dBFS. The patient doesn't wake up." |
| 90–120  | Console: RESOLVED state, intervention closes | "Pre-DSS was 0.7, post-DSS dropped to 0.2 — flagged effective. And this was logged to SQLite *before* the audio fired — hard architectural constraint." |
| 120–180 | Browser — refresh dashboard; walk Night Detail page | "The clinician opens this in the morning. Night Detail shows the full waveform — you can see the DSS spike at 01:23 and the intervention annotation. Scrub the timeline, the state ribbon stays in sync. Interventions page has the audio player — they can hear exactly what the system played." |

**Total: ~3 min.**

---

## Backup Plans

| Failure | Mitigation |
|---------|-----------|
| Audio playback fails | Add `--dry-run` flag — events still log, dashboard story holds |
| Model loading too slow | Pre-load by running `--dry-run` before the demo starts |
| Dashboard not starting | `uv run streamlit run src/sentinelsleep/dashboard/app.py` directly |
| No audio cache | Run `scripts/build_stub_cache.py` for silent stub clips, then re-seed DB |

---

## Key Technical Talking Points

- **Four foundation models**: MIT AST (527 AudioSet classes) → audeering wav2vec2 (valence/arousal/dominance) → MusicGen + AudioGen (pre-cached, never run in live loop)
- **Architectural constraint**: MusicGen and AudioGen run only in `pregenerate_cache.py`. The live loop is memory-safe.
- **Events before audio**: SQLite write happens before `sd.play()` — provable from the code.
- **No wearables**: microphone only. No EEG, no actigraphy, no contact sensors.
- **Research prototype framing**: The detection pipeline is real and verifiable; clinical efficacy claims require a controlled study.
