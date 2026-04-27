# SentinelSleep — Claude Code Project Instructions

> Source of truth for architecture, phases, and acceptance criteria:
> [SENTINELSLEEP_PLAN.md](SENTINELSLEEP_PLAN.md) — read it first.
> Source of truth for decisions made during build:
> [EVIDENCE_LOG.md](EVIDENCE_LOG.md) — append every material decision.

## What this project is

A research prototype audio AI system that detects PTSD nightmares from
bedroom mic audio in real time and injects pre-generated therapeutic audio
to interrupt them without waking the patient. Four-layer pipeline:

1. **Detection** — MIT AST classifies 2s chunks across 527 AudioSet classes;
   composite Distress Signal Score (DSS) > 0.4 escalates.
2. **Verification** — audeering wav2vec2 returns valence/arousal/dominance;
   nightmare = low V + high A + low D, sustained ≥ 15s.
3. **Intervention** — MusicGen + AudioLDM2 audio pre-cached to disk; pydub
   mix played at -20dBFS for 60s.
4. **Escalation** — progressive wake protocol if distress persists.

Streamlit morning dashboard reads from a SQLite event log.

> **Not a medical device.** Frame all language as "research prototype."
> Detection and generation pipelines are real. Clinical effectiveness
> requires controlled study.

## How I work in this repo

- **Phases are gates.** Build in phase order (SENTINELSLEEP_PLAN.md §7,
  Phases 0–7). Do not start Phase N+1 until Phase N's acceptance test
  passes and the user has confirmed.
- **Evidence log is non-negotiable.** Every material decision gets an
  ADR-style entry in EVIDENCE_LOG.md (context → decision → consequences).
  Append, never overwrite.
- **Tests are non-negotiable.** Each phase has acceptance criteria. Do not
  mark a phase complete until tests pass.
- **Plan mode for new phases.** Present the next phase plan for approval
  before implementing.

## Hard architectural constraints — do not violate

1. **Live-loop memory budget:** Only AST (detection) and wav2vec2
   (verification) models may be loaded in the live detection loop.
   MusicGen and AudioLDM2 run inside `scripts/pregenerate_cache.py` only —
   that script generates the full cache and exits.

2. **No on-demand generation in live loop.** Intervention always reads
   pre-cached WAVs from `data/audio_cache/`. Cache hit rate must be 100%.

3. **State transitions are logged first.** Every state machine transition
   writes to SQLite `events` before any audio side effect.

4. **Dashboard is read-only.** Streamlit views call functions in
   `dashboard/queries.py`. They never write to SQLite.

5. **Thresholds live in `config.py`.** No magic numbers anywhere else.
   If you are about to type `0.4` outside `config.py`, stop and add a
   named constant.

6. **Paths derive from `PROJECT_ROOT`.** Never hardcode `/Users/...` or
   assume a CWD. `PROJECT_ROOT` is computed in `config.py` and re-exported.

7. **Apple MPS is the target device.** Use `config.select_device()`.
   No CUDA assumptions.

8. **License attribution stays current.** Any new model → update
   `NOTICES.md` in the same commit.

## Coding style

- Python 3.11. Type hints on every function signature. Docstrings on every
  public function and class.
- Specific exception types — never bare `except:`. Log before re-raising.
- Functions do one thing. Files focused (< 400 lines preferred).
- No silent failures. No magic numbers outside `config.py`.
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`,
  `chore:`.

## Toolchain

```bash
uv sync                                        # install/update deps
uv run pytest tests/                           # run tests
uv run pytest tests/ --cov=sentinelsleep       # with coverage
uv run ruff check src/                         # lint
uv run python scripts/pregenerate_cache.py     # build audio cache (Phase 3+)
uv run python scripts/run_simulation.py        # demo mode (Phase 6+)
uv run python scripts/run_live.py              # live mic mode (Phase 4+)
uv run streamlit run scripts/run_dashboard.py  # dashboard (Phase 5+)
```

## Where things live

| Location | Purpose |
|----------|---------|
| `src/sentinelsleep/` | All importable source code |
| `scripts/` | Runnable entry points (no src logic here) |
| `tests/` | Test suite |
| `data/audio_cache/` | Pre-generated therapeutic audio (gitignored) |
| `data/test_fixtures/` | Test audio clips (gitignored except SOURCES.md) |
| `data/events.db` | SQLite event log (gitignored) |
| `EVIDENCE_LOG.md` | Decision records (ADR-style) |
| `SENTINELSLEEP_PLAN.md` | Master build plan (source of truth) |

## What "done" means for a phase

A phase is done when **all** of:
1. All deliverables in SENTINELSLEEP_PLAN.md §7 for that phase exist.
2. The phase's acceptance test passes.
3. EVIDENCE_LOG.md has an entry for the phase's material decisions.
4. The user has confirmed.

## Things to never do

- Load MusicGen or AudioLDM2 inside the live loop.
- Hardcode an absolute path anywhere outside `config.py`.
- Write to SQLite from the dashboard.
- Skip a phase or its acceptance test.
- Use bare `except:`.
- Commit `.env`, `data/audio_cache/`, or `data/events.db`.
- Mark work complete without running the acceptance test.
