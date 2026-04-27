# SentinelSleep — Evidence Log

ADR-style decision record. One entry per material decision. Append only —
never overwrite or delete entries. Superseded decisions get a status update
and a "superseded by ADR-NNN" note.

## Entry format

```
## ADR-NNN — <short title>
- **Date:** YYYY-MM-DD
- **Phase:** N (<phase name>)
- **Status:** accepted | superseded by ADR-MMM
- **Context:** Why this decision is being made.
- **Decision:** What we are doing.
- **Consequences:** What this enables, costs, or makes harder.
- **Alternatives considered:** What we ruled out and why.
```

---

## ADR-006 — DSS normalization requires multi-class co-occurrence to flag

- **Date:** 2026-04-27
- **Phase:** 1 (Detection Layer)
- **Status:** accepted
- **Context:** During Phase 1 test development, discovered that the DSS formula
  `weighted_sum / sum(all_weights)` produces a single-class ceiling of ≈0.16
  (1.0 / 6.2 for the top-weight class at probability 1.0). This means a single
  distress class firing at full strength does NOT breach the 0.4 flag threshold.
  Three moderate classes (0.7/0.6/0.5) give DSS ≈ 0.28. Three top-weight classes
  at 0.9 each give DSS ≈ 0.42, just above threshold.
- **Decision:** Keep the normalized formula as designed. The multi-class co-occurrence
  requirement is a feature: acoustic nightmares produce several simultaneous distress
  signals (crying + heavy breathing + whimpering), while false positives are typically
  single-class activations (someone coughing, a door creak). The threshold of 0.4
  is calibrated to require a genuine multi-signal profile.
- **Consequences:** Real nightmare audio (multiple co-occurring distress sounds)
  should breach 0.4. Single-class false positives (snoring, TV speech) should stay
  below 0.3. Phase 1 acceptance integration tests will validate this empirically.
  The DSS_FLAG_THRESHOLD (0.4) may need tuning after Phase 1 integration testing.
- **Alternatives considered:** Normalizing by sum of active distress weights only
  (not all weights) — rejected: this would inflate DSS for any single strong signal
  and cause more false positives.

---

## ADR-001 — Use uv with Python 3.11 for environment management

- **Date:** 2026-04-27
- **Phase:** 0 (Setup & Scaffolding)
- **Status:** accepted
- **Context:** Master plan §4 specifies Python 3.11 + uv. User's
  tool-preferences.md confirms uv as the default env manager. Existing
  projects (TruPharma, SIGNAL, PAIR) all use the same stack.
- **Decision:** Initialize a uv project (`pyproject.toml` + `uv.lock`)
  pinned to `>=3.11,<3.12`. Use `uv run` for all commands.
- **Consequences:** Fast installs, reproducible lockfile, alignment with
  rest of user's portfolio. Anyone cloning only needs `uv` to bootstrap.
- **Alternatives considered:** poetry (slower, less aligned with stack);
  pip + venv (less reproducible, no lockfile).

---

## ADR-002 — Use stdlib sqlite3, not an ORM

- **Date:** 2026-04-27
- **Phase:** 0
- **Status:** accepted
- **Context:** Phase 4 schema is 3 tables (sessions, events, interventions).
  All queries are simple INSERTs and time-bounded SELECTs. Dashboard is
  strictly read-only. No schema migrations planned (prototype scope).
- **Decision:** Use stdlib `sqlite3` module only. Explicit SQL strings,
  parameterized queries, no ORM.
- **Consequences:** Zero extra dependencies. Queries are transparent and
  easy to audit for injection safety. No impedance mismatch when reading
  rows for dashboard views.
- **Alternatives considered:** sqlmodel (Pydantic v2 churn, overkill for
  3 tables); sqlalchemy core (heavier, migration tooling we don't need).

---

## ADR-003 — Pre-generate intervention audio; never load generation models in live loop

- **Date:** 2026-04-27
- **Phase:** 0 (architectural constraint adopted before code exists)
- **Status:** accepted
- **Context:** M2 8GB RAM. AST (~350MB) + wav2vec2 (~660MB) = ~1GB resident.
  MusicGen (~1.2GB) + AudioLDM2 (~4GB) would blow the budget and add 10–20s
  latency per intervention. Master plan §4.1 + §14 enforce this.
- **Decision:** `scripts/pregenerate_cache.py` is the *only* code path that
  loads MusicGen/AudioLDM2. It runs once, writes WAVs to
  `data/audio_cache/`, and exits. The live loop reads cached WAVs from disk.
- **Consequences:** Live loop stays within memory budget. Intervention
  latency drops to disk read (~ms). Cache must be regenerated when prompts
  or models change (Phase 3 addresses this).
- **Alternatives considered:** On-demand generation (rejected: latency +
  memory); cloud generation per event (rejected: offline demo requirement).

---

## ADR-004 — All thresholds and paths centralized in config.py

- **Date:** 2026-04-27
- **Phase:** 0
- **Status:** accepted
- **Context:** User constraint: "All thresholds live in config.py — no
  magic numbers scattered through code. All paths computed from a single
  PROJECT_ROOT, never hardcoded."
- **Decision:** `src/sentinelsleep/config.py` is the single authority for:
  `PROJECT_ROOT`, all `_DIR` paths, all `DSS_*`, `VALENCE_*`, `AROUSAL_*`,
  `DOMINANCE_*`, `NIGHTMARE_*`, `INTERVENTION_*`, model IDs, and
  `select_device()`. Every other module imports from `config`.
- **Consequences:** One place to tune the system. Ablation studies are
  easy — change one constant, re-run. Path bugs caught early.
- **Alternatives considered:** Per-module constants (rejected: scatters
  tunable values, makes ablation studies painful).

---

## ADR-005 — Phase 0 test fixtures are synthetic placeholders

- **Date:** 2026-04-27
- **Phase:** 0
- **Status:** accepted
- **Context:** Phase 0 acceptance requires fixtures to exist in
  `data/test_fixtures/`. Real Freesound downloads require a user API token
  and Phase 1 curation. Fixture *content* is only exercised in Phase 1+
  acceptance tests.
- **Decision:** Phase 0 generates deterministic synthetic WAVs (pink noise,
  white noise, silence) with names matching SENTINELSLEEP_PLAN.md §6.1.
  `data/test_fixtures/SOURCES.md` documents the real sources to swap in
  during Phase 1.
- **Consequences:** Phase 0 test infra runs cleanly. Phase 1 must curate
  real audio as its first task (placeholder WAVs will intentionally fail
  Phase 1 acceptance criteria because synthetic noise won't produce DSS > 0.4).
- **Alternatives considered:** Skip fixtures (would make Phase 1 file-not-found
  errors harder to distinguish from logic errors); Freesound API in Phase 0
  (out of scope, requires token setup).
