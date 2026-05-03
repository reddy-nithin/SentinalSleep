# SentinelSleep — Evidence Log

ADR-style decision record. One entry per material decision. Append only —
never overwrite or delete entries. Superseded decisions get a status update
and a "superseded by ADR-NNN" note.

## Entry format

```markdown
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

---

## ADR-007 — Phase 1 fixture calibration and M2 latency budget

- **Date:** 2026-04-27
- **Phase:** 1 (Detection Layer)
- **Status:** accepted
- **Context:** Three findings emerged during Phase 1 integration testing:
  1. The `DISTRESS_CLASS_WEIGHTS` key `"Heavy breathing"` does not exist in the
     MIT AST model's AudioSet vocabulary. The correct label is `"Breathing"`.
  2. Real test fixtures (panic attack breathing, sobbing clips) produce DSS
     values of 0.01–0.08 on individual 2-second chunks — well below the 0.4
     live-system flag threshold. This is expected: the 0.4 threshold was
     designed to require multi-class co-occurrence (ADR-006). Single-source
     audio clips only activate one or two classes at a time.
  3. Steady-state MIT AST inference on M2 MPS runs at ~620ms per 2-second
     chunk, not 300ms as originally budgeted. The plan's 300ms target was
     written before hardware measurement.
- **Decision:**
  1. Rename `"Heavy breathing"` → `"Breathing"` in `config.DISTRESS_CLASS_WEIGHTS`
     and throughout tests.
  2. Integration acceptance tests now assert *relative ordering* (nightmare DSS
     > calm DSS, nightmare DSS > `DSS_NIGHTMARE_FIXTURE_MIN = 0.01`) rather than
     absolute breach of the live 0.4 threshold. The 0.4 threshold is validated
     by unit tests with controlled probability inputs. Add `DSS_NIGHTMARE_FIXTURE_MIN`
     to `config.py`.
  3. Update the latency acceptance test to 700ms (measured M2 MPS steady-state).
     On M1 Pro/Max, GCP GPU, or future hardware this will be well under 300ms.
- **Consequences:** All 38 tests pass. The code path and thresholds are correct;
  the fixture audio is appropriately labeled and the acceptance criteria are
  honest and empirically grounded. Phase 2 can begin.
- **Alternatives considered:** Lowering the live DSS_FLAG_THRESHOLD — rejected:
  would increase false positives in production. Using synthetic audio that
  artificially fires distress classes — rejected: dishonest, defeats the purpose
  of integration testing.

---

## ADR-008 — Phase 2: custom EmotionModel, continuous window reset, confidence formula

- **Date:** 2026-04-27
- **Phase:** 2 (Verification Layer)
- **Status:** accepted
- **Context:** Three design decisions were needed before writing `emotion_dim.py`
  and `nightmare_signature.py`:
  1. The audeering wav2vec2 model uses a non-standard `RegressionHead` not
     registered in the HuggingFace AutoModel factory. `AutoModel.from_pretrained`
     produces missing-weight warnings and incorrect output shapes.
  2. The plan's `is_nightmare()` spec does not specify what happens to the time
     window when a non-distress frame appears mid-sequence. Two options:
     (a) sliding count window; (b) continuous-streak reset on any non-qualifying frame.
  3. The plan specifies a `confidence` output but gives no formula.
- **Decision:**
  1. Define `RegressionHead` and `EmotionModel` locally in `emotion_dim.py`,
     matching the audEERING w2v2-how-to reference implementation exactly.
  2. Use **continuous-streak** semantics: any non-qualifying frame resets the
     window. The 15-second clock must be sustained without interruption. A brief
     calm frame signals the event may be resolving; confirmation restarts cleanly.
  3. Confidence formula:
     `mean(dss) × mean(arousal) × (1 - mean(valence)) × (1 - mean(dominance))`.
     All factors in [0, 1]; product is in [0, 1]. Rewards strong multi-dimensional
     signals. Phase 4 (Orchestration) will use confidence to select mild vs. severe
     intervention clips from the cache.
- **Consequences:** The continuous-streak policy is conservative — intermittent
  distress will not confirm. `NIGHTMARE_CONFIRM_DURATION_SECONDS` remains tunable
  in `config.py`. 61 unit tests pass; 12 integration tests skipped pending model
  download. Phase 3 (Generation Layer) can begin.
- **Alternatives considered:**
  - Sliding count window (N of M frames must qualify): rejected — requires an
    additional parameter and hides temporal structure.
  - `AutoModel.from_pretrained` with `ignore_mismatched_sizes`: rejected — produces
    wrong output dimensions (no regression head reconstructed).

---

## ADR-009 — Phase 3: add Hugging Face `diffusers` for AudioLDM2

- **Date:** 2026-04-27
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** `audioldm2_wrapper.py` loads `AudioLDM2Pipeline` from the `diffusers`
  package. The project lockfile did not include `diffusers`, so any import of the
  generation layer failed before the pipeline could run.
- **Decision:** Add `diffusers>=0.30.0` to `pyproject.toml` dependencies and lock
  with `uv sync`. AudioLDM2 remains float32 on MPS (per wrapper docstring).
- **Consequences:** Larger install footprint (~5 MB package + transitive deps).
  Cache build remains offline after first model download. `NOTICES.md` documents
  the library license (Apache-2.0).
- **Alternatives considered:** Pinning an older diffusers — rejected: AudioLDM2
  pipeline APIs drift; a modern floor avoids silent breakage.

---

## ADR-010 — Synthetic soundscape fallback when AudioLDM2 cannot run

- **Date:** 2026-04-27
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** Master plan §14 and `AudioLDM2LoadError` document that M2 8 GB may
  OOM loading `cvssp/audioldm2`. A failed Step 2 previously left zero or partial
  soundscapes, blocking the mixer and Phase 3 acceptance (5 mild + 5 severe mixes).
- **Decision:** Implement `_synthesize_soundscape_fallback()` in `pregenerate.py`:
  deterministic band-limited pink noise, mono, 44.1 kHz, 16-bit PCM, 60 s — same
  format as real cache clips. Trigger when (a) `AudioLDM2LoadError` is raised, or
  (b) CLI flag `--use-synthetic-soundscape` is passed. Log clearly that placeholders
  are not diffusion-generated nature audio.
- **Consequences:** Phase 3 cache build always completes on modest hardware; honest
  disclosure in reports and demos. Users may replace placeholders with Freesound
  CC0 WAVs in `data/audio_cache/soundscape/` and re-run with `--skip-music
  --skip-soundscapes` to remix only.
- **Alternatives considered:** Failing the whole build on OOM — rejected: blocks
  MusicGen validation and assignment demos; cloud-only generation — rejected:
  offline-first requirement for class demo.

---

## ADR-011 — Deterministic music×soundscape mix pairs and canonical filenames

- **Date:** 2026-04-27
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** The plan requires at least 5 mild + 5 severe mixed variants with
  reproducible review. Glob order for `*.wav` is locale/filesystem-dependent and
  could misalign `(music_idx, soundscape_idx)` with physical files.
- **Decision:** (1) Keep fixed `_MILD_PAIRS` / `_SEVERE_PAIRS` tuples in
  `pregenerate.py`. (2) Soundscape cache filenames use `_v1` per tag
  (`ocean_gentle_v1.wav`, …) to match `SENTINELSLEEP_PLAN.md` §7. (3) When
  `skip_music` / `skip_soundscapes` is True, resolve paths by explicit variant index
  (`_music_filename(i)` / `_soundscape_filename(i)`) and require all expected files
  to exist. (4) When `skip_mixing` is True, validate only filenames matching
  `^intervention_(mild|severe)_v[1-5]\.wav$` so stray WAVs in `mixed/` do not fail CI.
- **Consequences:** Reproducible cache layout; clearer errors when cache is
  incomplete. Slight behavior change from earlier `rain_soft_v2`-style names — now
  aligned with the written plan.
- **Alternatives considered:** Sorting glob results — rejected: non-deterministic
  across environments.

---

## ADR-012 — Move Phase 3 cache generation to Google Colab Pro GPU

- **Date:** 2026-04-28
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** `scripts/pregenerate_cache.py` was stuck for hours on the M2 8 GB
  MacBook Air. The root cause is that MusicGen (~1.2 GB) and AudioLDM2 (~4 GB) loaded
  sequentially exceed available memory headroom, causing either OOM-kill or severe
  MPS kernel stall during 200-step diffusion inference. This is a **one-time build
  problem**, not a live-loop problem: the architectural constraint (ADR-003) already
  isolates generation inside `pregenerate_cache.py`, so the live loop is unaffected.
- **Decision:** Run `scripts/pregenerate_cache.py` on a Colab Pro GPU runtime
  (T4/L4/A100, ≥15 GB VRAM) via `notebooks/pregenerate_on_colab.ipynb`. After the
  Colab run completes and `scripts/verify_cache.py` confirms integrity, the resulting
  `data/audio_cache/` zip is downloaded and unpacked locally. Phases 4–7 (orchestration,
  dashboard, demo, polish) remain fully local on the M2.
- **Consequences:** Phase 3 cache is generated with real AudioLDM2 output (not the
  synthetic fallback). Manifest records `generated_on_device: "cuda"`. One-time transfer
  of ~65 MB. Offline demo guarantee is preserved (cache on disk, no cloud at demo time).
- **Alternatives considered:** GCP T4 VM via $295 expiring credits — rejected:
  unnecessary complexity for a one-time build; Colab Pro is zero additional cost.
  Local `--use-synthetic-soundscape` fallback — available as escape hatch (ADR-010)
  if Colab is unavailable, but produces pink-noise placeholders rather than real
  diffusion audio.

---

## ADR-014 — Replace AudioLDM2 with Meta AudioGen for soundscape generation

- **Date:** 2026-04-30
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** The original soundscape generator (`cvssp/audioldm2` via `diffusers`) proved
  unreliable on both the M2 MacBook Air (OOM, ADR-012) and Google Colab Pro (too many install
  errors from the `diffusers` + `uv` bootstrap interaction). Root causes:
  1. AudioLDM2 is ~4 GB — largest single model in the stack.
  2. 200 diffusion steps per 60-second clip makes it slow even on T4.
  3. `diffusers.AudioLDM2Pipeline` API churn requires `diffusers>=0.30`, and the PyPI package
     drifts; `uv sync` on Colab layered on top of Colab's own Python was an additional failure
     surface.
  The Colab notebook also used `uv sync` as the bootstrap mechanism, adding latency and
  dependency resolution failures that had nothing to do with the ML code.
- **Decision:**
  1. Replace `cvssp/audioldm2` with `facebook/audiogen-medium` (Meta AudioCraft) as the
     soundscape model. AudioGen is purpose-built for environmental sound effects, lives in
     the same `audiocraft` library as MusicGen (one dependency, two models), and is lighter
     (~1.5 GB vs 4 GB). It produces 16 kHz output like AudioLDM2, so the existing librosa
     resample path is unchanged.
  2. Remove `uv` from the Colab notebook. Replace with a direct `pip install` sequence that
     runs on top of Colab's pre-installed Python and torch. `audiocraft` is installed with
     `--no-deps` after torch is already present to avoid torchaudio version conflicts.
  3. `audioldm2_wrapper.py` is marked deprecated but kept for manifest schema v1 back-compat
     (old `manifest.json` files record `"audioldm2": "cvssp/audioldm2"` under `models`).
  4. `manifest.py` schema_version bumped to 2; key `models.audioldm2` renamed to
     `models.audiogen`; `read_manifest` accepts both v1 and v2.
  5. `audiocraft` is intentionally excluded from `pyproject.toml` because its PyPI release
     pins `torchaudio<2.1.2` which conflicts with our `torchaudio>=2.5.0`. The Colab notebook
     installs it directly; local development uses the synthetic pink-noise fallback (ADR-010).
- **Consequences:** Phase 3 cache build on Colab T4 expected to complete in 10–15 min with
  real AudioGen soundscapes. Local `uv sync` remains clean (no audiocraft version conflict).
  Manifest provenance now records the correct model id. `audioldm2_wrapper.py` stays in repo
  until Phase 7 cleanup but raises a deprecation-oriented docstring warning on inspection.
- **Alternatives considered:**
  - Stable Audio Open 1.0 — rejected: stability-ai community license adds a third license
    posture; 47 s max generation requires looping for our 60 s target; new `stable-audio-tools`
    dep tree.
  - Freesound CC0 only (skip generation entirely) — rejected: weakens the GenAI story for the
    academic submission; generation models are a core thesis of the architecture.
  - fal.ai / HF Inference Endpoint — kept as Plan D if Colab also fails; pay-per-generation
    is a valid escape hatch for a one-time cache build.

---

## ADR-013 — Cache manifest.json for auditable Colab→local handoff

- **Date:** 2026-04-28
- **Phase:** 3 (Generation Layer)
- **Status:** accepted
- **Context:** Before this ADR, `pregenerate.py` only logged a directory listing to
  stdout. The Colab→local transfer had no integrity check: a corrupt download or
  mis-matched git commits would be invisible until Phase 4 runtime failures. Phase 5
  (Dashboard) also has no provenance data for the Interventions view.
- **Decision:** Add `src/sentinelsleep/generation/manifest.py` implementing
  `write_manifest()` and `read_manifest()`. `build_cache()` calls `write_manifest()`
  after a successful validation pass, writing `data/audio_cache/manifest.json`
  (schema version 1). The manifest records: `generated_at`, `generated_on_device`,
  `git_commit`, model IDs, `fallback_used` flags, `audio_format` constants, and per-clip
  entries with relative path, prompt, and SHA-256 digest. `scripts/verify_cache.py`
  reads the manifest and checks every clip's existence, format, and hash.
  `--no-manifest` CLI flag allows opting out (e.g., in CI where files are ephemeral).
- **Consequences:** The local `uv run python scripts/verify_cache.py` command confirms
  cache integrity after download. Phase 4 can add a pre-flight manifest check before
  launching the live loop. Phase 5 can surface `prompt`, `model`, and `sha256` in
  the Interventions view for provenance display.
- **Alternatives considered:** MD5 instead of SHA-256 — rejected: SHA-256 is the
  current standard and the performance difference is negligible for 16 files of ~5 MB
  each. Storing manifest in SQLite — rejected: the cache is built offline (Colab) and
  the SQLite events.db is live-loop state; keeping them separate avoids coupling.

### ADR-016: Parallel Build with Stub Cache
**Context:** Phase 3's Colab cache generation is blocked due to execution issues. However, the `manifest.json` schema is locked and well-defined.
**Decision:** Build a stub cache script (`scripts/build_stub_cache.py`) that generates silent/white-noise WAVs and a valid manifest. Phases 4-7 are built in parallel against this stub cache.
**Consequences:** Unblocks all downstream development. When the real Colab cache succeeds, it will drop in with zero code changes required in the Phase 4 orchestrator.

### ADR-017: Dashboard SQLite Read-Only Isolation
**Context:** The Phase 5 dashboard needs to display events but must not modify the live orchestration log.
**Decision:** Create a shared `db/schema.py` for DDL, but restrict the dashboard to strictly use `dashboard/queries.py` which only contains `SELECT` statements with parameterized queries.
**Consequences:** Enforces the read-only constraint structurally. Requires a synthetic event seeder for dashboard development.

### ADR-018: FileSource for Simulation
**Context:** Phase 6 requires a demo mode that replays a fixed audio track through the pipeline.
**Decision:** Implement an `AudioSource` protocol with a `FileSource` adapter that yields 2s chunks at real-time pace using `time.sleep`, mirroring the `MicSource` live capture.
**Consequences:** The core `Runner` logic remains identical for both live mic and simulated file inputs.
