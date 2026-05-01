# SentinelSleep: Presentation Outline

**Target Audience:** Competition Judges / Research Reviewers
**Duration:** 8-10 minutes

## Slide 1: Title & Problem Statement
*   **Project Name:** SentinelSleep
*   **Mission:** Non-pharmacological intervention for PTSD nightmares using real-time audio AI.
*   **The Problem:** Existing treatments are chemical or require disruptive awakenings. Patients need an intervention that soothes them *without* breaking the sleep cycle.

## Slide 2: The Solution
*   **Concept:** Listen for distress, verify emotional signature, and inject procedurally generated therapeutic audio (music + soundscapes) at a low volume.
*   **Core Principle:** Ambient intervention, not an alarm. 

## Slide 3: Architecture & 4-Layer Pipeline
*   *Visual: architecture.md Mermaid diagram*
*   **Layer 1 (Detection):** MIT AST model monitoring 2s chunks. Computes a Distress Signal Score (DSS).
*   **Layer 2 (Verification):** audeering wav2vec2 checks valence, arousal, and dominance to eliminate false positives (like traffic noise or snoring).
*   **Layer 3 (Intervention):** Pre-generated offline cache using MusicGen and AudioGen to stay within our local M2 8GB hardware constraints.
*   **Layer 4 (Escalation):** Progressive wake protocol if distress persists over 60s.

## Slide 4: Real-Time State Machine
*   *Visual: State transition diagram (Listening -> Flagged -> Intervening -> Resolved).*
*   Discuss the strict 15-second confirmation window before firing an intervention.
*   Emphasize safety and logging (SQLite events logged prior to any playback).

## Slide 5: Generative Audio Strategy
*   Why procedural? Avoiding habituation.
*   Why offline? Edge hardware limits (Apple Silicon).
*   **The Cache:** We build a matrix of Mild vs. Severe interventions by mixing specific BPM/frequency bands.

## Slide 6: Demo Video (2 Minutes)
*   *Play the recorded simulation video.*
*   Show the dashboard running live as the audio transitions from calm to severe nightmare, and then the intervention triggers.

## Slide 7: Morning Dashboard Review
*   *Visual: Screenshots of the 4 Streamlit views.*
*   **Clinical Intelligence:** Providing patients and clinicians with objective data.
*   Show timeline view, waveform trace, and intervention effectiveness metrics.

## Slide 8: Technical Constraints & Innovations
*   Strict memory management (load/unload cycles for generation).
*   Read-only dashboard architecture.
*   Pure state machine design for high testability.

## Slide 9: Future Work & Clinical Translation
*   Integrating wearable biometric data (HRV).
*   Moving from research prototype to IRB-approved sleep study.
*   Refining the escalation protocol (Layer 4).

## Slide 10: Q&A
*   Code repository: TruPharma-Clinical-Intelligence
*   Acknowledgments and contact info.
