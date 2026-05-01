# SentinelSleep — Phase 6 Demo Script

## Setup
1. Open terminal 1 and launch the dashboard:
   ```bash
   uv run python scripts/seed_synthetic_events.py --clear
   uv run streamlit run scripts/run_dashboard.py
   ```
2. Open terminal 2 and build the demo track:
   ```bash
   uv run python src/sentinelsleep/demo/simulator.py --build
   ```

## Live Demo Flow

**Speaker**: "Welcome to the SentinelSleep demo. This system detects PTSD nightmares entirely on-device and intervenes automatically. We'll run our 2-minute simulated night."

**Action**: Run the simulation.
```bash
uv run python scripts/run_simulation.py --demo
```

### Timeline
- **0:00 - 0:30 (Calm)**: "The system is LISTENING. You can see the Distress Signal Score (DSS) is near zero."
- **0:30 - 0:45 (Distress Onset)**: "A nightmare signature appears. DSS crosses the 0.4 threshold. State transitions to FLAGGED."
- **0:45 - 0:48 (Verification)**: "The verification layer confirms low valence and high arousal. The system triggers INTERVENING."
- **0:48 - 1:48 (Intervention)**: "A procedurally generated therapeutic soundscape plays. We use MusicGen and AudioGen for this. The audio is designed to soothe without causing a full wake event."
- **1:48+ (Resolved)**: "Distress drops back down. State returns to LISTENING."

### Dashboard Review
**Action**: Switch to the browser where Streamlit is running.
**Speaker**: "Now let's review the night. The timeline view shows exactly when the intervention fired. The waveform view correlates the DSS with the dimensional emotion scores. The intervention was recorded successfully."
