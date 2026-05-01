# SentinelSleep Architecture

This document describes the 4-layer pipeline architecture for the SentinelSleep audio AI system.

```mermaid
flowchart TD
    %% Audio Sources
    subgraph Input ["Input Layer"]
        mic["Live Microphone (sounddevice)"]
        file["WAV File (Demo/Simulation)"]
        mic --> stream
        file --> stream
        stream["AudioStream (2s rolling buffer)"]
    end

    %% Layer 1
    subgraph L1 ["Phase 1: Detection"]
        stream --> ast["MIT AST Classifier\n(AudioSet 527 classes)"]
        ast --> dss["Distress Signal Score (DSS)\n[0.0 - 1.0]"]
    end

    %% Layer 2
    subgraph L2 ["Phase 2: Verification"]
        dss -- "DSS > 0.4" --> w2v2["audeering wav2vec2\n(Dimensional Emotion)"]
        w2v2 --> sig{"Nightmare Signature?\n(Val < 0.4, Aro > 0.6,\nDom < 0.4, >= 15s)"}
    end

    %% Orchestrator / State Machine
    subgraph SM ["Phase 4: Orchestration"]
        sig -- "Confirmed" --> state_intervening["INTERVENING State"]
        dss -- "DSS <= 0.4" --> state_listening["LISTENING State"]
        sig -- "Unconfirmed" --> state_flagged["FLAGGED State"]
        
        state_intervening -- "Persists > 60s" --> state_escalating["ESCALATING State"]
        state_intervening -- "Clears" --> state_resolved["RESOLVED State"]
    end

    %% Layer 3
    subgraph L3 ["Phase 3: Generation (Pre-cached)"]
        musicgen["MusicGen (ambient)"] --> mix["pydub Mixer"]
        audiogen["AudioGen (soundscape)"] --> mix
        mix --> cache[("audio_cache/\n(manifest.json + WAVs)")]
    end

    %% Intervention
    state_intervening --> select["Clip Selector"]
    cache -.-> select
    select --> playback["Audio Playback\n(-20 dBFS)"]

    %% Data Layer
    subgraph DB ["Data Layer"]
        state_listening --> logger["Event Logger"]
        state_flagged --> logger
        state_intervening --> logger
        state_escalating --> logger
        logger --> sqlite[("events.db\n(SQLite)")]
    end

    %% Dashboard
    subgraph Dash ["Phase 5: Morning Dashboard"]
        sqlite -. "Read-only" .-> queries["queries.py"]
        queries --> view1["Timeline View"]
        queries --> view2["Waveform View"]
        queries --> view3["Interventions View"]
        queries --> view4["Trends View"]
    end
```

## Data Flow Constraints

1. **Memory Budget**: Only the L1 (AST) and L2 (wav2vec2) models are loaded in the live inference loop. The L3 models (MusicGen, AudioGen) are too large for the 8GB M2 budget and run strictly offline via `scripts/pregenerate_cache.py`.
2. **State Changes**: The State Machine is pure. State transitions are computed from observations and then immediately committed to SQLite by the `EventLogger` *before* any audio side effects occur.
3. **Dashboard Access**: The Streamlit dashboard (`Phase 5`) is completely decoupled from the live orchestrator and enforces a strict read-only constraint against `events.db`.
