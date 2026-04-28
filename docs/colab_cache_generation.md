# SentinelSleep — Generating the Audio Cache on Google Colab Pro

The `data/audio_cache/` directory is built by `scripts/pregenerate_cache.py`, which
loads MusicGen (~1.2 GB) and AudioLDM2 (~4 GB) sequentially.  On an M2 MacBook Air with
8 GB unified RAM this exhausts memory and stalls.  This runbook moves that one-time build
step to a Colab GPU while keeping the entire live pipeline (Phases 4–7) local on the M2.

**Architecture constraint preserved (CLAUDE.md #1 / ADR-003):** Generation models only
ever run inside `pregenerate_cache.py`. The live detection loop loads only AST + wav2vec2
(~1 GB combined) and reads cached WAVs from disk.  Moving cache generation to Colab does
not change this constraint.

---

## Prerequisites

| Item | What you need |
|------|--------------|
| Google account | Colab Pro (free GPU quota) |
| Repo access | Public repo, or a GitHub PAT for private clone |
| HF token (optional) | Only if AudioLDM2 download hits rate limits — store in Colab Secrets |

---

## Step-by-step

### 1. Open the notebook in Colab

Go to [colab.research.google.com](https://colab.research.google.com), then:

**File → Open notebook → GitHub tab → paste repo URL → select `notebooks/pregenerate_on_colab.ipynb`**

Or use the direct link after the repo is public:
`https://colab.research.google.com/github/reddy-nithin/SentinalSleep/blob/main/notebooks/pregenerate_on_colab.ipynb`

### 2. Set the runtime to GPU

**Runtime → Change runtime type → T4 GPU → Save**

> T4 is free on Colab Pro and has 15 GB VRAM — well within budget for both models.

### 3. (Optional) Add your HF token as a Colab Secret

If you expect rate-limit issues with `cvssp/audioldm2`:

1. Click the key icon (🔑) in the left sidebar
2. Add a secret named `HF_TOKEN` with your token value
3. Enable "Notebook access"

The notebook reads this secret in Cell 3.  **Never paste the token directly into a cell.**

### 4. Run all cells in order

**Runtime → Run all** (or Shift+Enter through each cell)

Expected runtime on T4:
- Cell 2 (uv sync + dep install): ~3–5 min
- Cell 4 (MusicGen + AudioLDM2 + mixing): ~10–15 min
- Total: ~15–20 min

Successful output ends with:
```
✓ Cache build complete — all clips valid.
Manifest written → data/audio_cache/manifest.json
```

### 5. Download the zip

Cell 6 zips `data/audio_cache/` and triggers a browser download of `audio_cache.zip`
(~65 MB).  Save it somewhere you can find it (e.g. `~/Downloads/`).

---

## After download — local setup

```bash
# In your SentinalSleep repo directory:

# 1. Unpack (overwrites existing empty cache dirs)
unzip -o ~/Downloads/audio_cache.zip -d data/

# 2. Full integrity check — exits 0 if clean
uv run python scripts/verify_cache.py

# 3. Smoke-test the whole test suite
uv run pytest tests/ -q
```

A clean `verify_cache.py` run confirms:
- All 16 files present (3 music + 3 soundscape + 10 mixed)
- SHA-256 hashes match the Colab-generated `manifest.json`
- All clips are 60 s, mono, 44.1 kHz, 16-bit PCM

Phase 3 is complete.  Start Phase 4 (Orchestration).

---

## Troubleshooting

### AudioLDM2 OOM on Colab

Unlikely on T4 (15 GB VRAM), but if it happens:

```python
# In Cell 4, replace the command with:
!uv run python scripts/pregenerate_cache.py --use-synthetic-soundscape
```

This uses pink-noise fallback for soundscapes (ADR-010).  The manifest will record
`"fallback_used": {"soundscape": true}`.  For the academic demo this is acceptable;
for production quality, re-run on an A100 runtime.

### Rate-limit on model download

Add your HF token as a Colab Secret (Step 3 above).  The token `hf_fLk...` used during
development is stored only in your local environment — never commit it to the repo.

### Colab session disconnects mid-run

The cache build is **idempotent**: already-generated WAVs are skipped (`Skipping X — already exists`).
Simply reconnect and re-run from Cell 4.  If music is done but soundscapes are not:

```python
!uv run python scripts/pregenerate_cache.py --skip-music
```

### verify_cache.py reports SHA-256 mismatch

This means the downloaded zip was corrupted in transit.  Re-download from Colab
(Cell 6) and unpack again.

---

## Re-generating after prompt changes

If you change `config.MUSIC_PROMPTS` or `config.SOUNDSCAPE_PROMPTS`:

```bash
# Delete stale clips for the categories you changed, then re-run:
rm data/audio_cache/music/*.wav   # or soundscape/*.wav
uv run python scripts/pregenerate_cache.py --skip-soundscapes  # regenerate music only
```

Or run the full Colab notebook again from scratch.

---

## What this does NOT affect

| Concern | Status |
|---------|--------|
| Live detection loop | Unchanged — AST + wav2vec2 only, no generation models |
| Phase 4–7 development | Fully local on M2 |
| Offline demo guarantee | Cache is on disk; no internet required at demo time |
| Test suite | All 99+ tests still run locally (`uv run pytest tests/`) |
