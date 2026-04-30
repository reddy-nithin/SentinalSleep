# SentinelSleep — Cache Generation on Google Colab

**Phase 3** pre-generates the therapeutic audio cache that the live pipeline
plays during nightmare interventions.  Generation uses two GPU-heavy models
that exceed the M2 8 GB local budget, so we run them on a Colab T4 once and
download the result.

## Why Colab?

| Model | Size | Local M2 | Colab T4 |
| ----- | ---- | -------- | -------- |
| `facebook/musicgen-small` | ~1.2 GB | MPS, ~10 s/clip | CUDA, ~6 s/clip |
| `facebook/audiogen-medium` | ~1.5 GB | Fits but slow | CUDA, ~5 s/clip |
| Both sequential | ~2.7 GB peak | OK in theory | Easily fits in 15 GB VRAM |

The critical path during live operation reads pre-generated WAVs from disk
(ADR-003) — generation never happens at runtime.  Colab is a one-time build.

> **ADR-014:** `facebook/audiogen-medium` (Meta AudioCraft) replaced
> `cvssp/audioldm2` as the soundscape model.  AudioGen is purpose-built for
> environmental sounds, lighter (1.5 GB vs 4 GB), and lives in the same
> AudioCraft library as MusicGen — one codebase, two models.

---

## Step-by-step

### 0. Prerequisites

- Google account with Colab access
- Repo pushed to GitHub (`git push origin main`)

### 1. Open the notebook on Colab

Go to [colab.research.google.com](https://colab.research.google.com), click
**File → Open notebook → GitHub**, paste:

```text
https://github.com/reddy-nithin/SentinalSleep
```

Select `notebooks/pregenerate_on_colab.ipynb`.

### 2. Switch to GPU runtime

**Runtime → Change runtime type → T4 GPU → Save**

Verify with:

```python
import torch; print(torch.cuda.get_device_name(0))
```

### 3. Run all cells in order

| Cell | What it does | Expected time |
| ---- | ------------ | ------------- |
| 1 — Clone repo | `git clone`, `git checkout main` | < 30 s |
| 2 — Install deps | pip: transformers, audiocraft, librosa, soundfile, pydub | 2–4 min |
| 3 — HF auth | Optional; reads `HF_TOKEN` Colab secret | < 10 s |
| 4 — Build cache | `python scripts/pregenerate_cache.py` | 8–12 min |
| 5 — Verify | `verify_cache.py --no-sha256` | < 30 s |
| 6 — Zip + download | Creates `audio_cache.zip`, triggers browser download | 1–2 min |

**Total: ~12–18 min**

### 4. Expected Cell 4 output

```text
SentinelSleep — Pre-generation Cache Builder
=============================================================
STEP 1 — Generating 3 music variants with MusicGen
  [1/3] Prompt: slow calming ambient music, 60 BPM…
  [2/3] Prompt: meditative ambient music…
  [3/3] Prompt: peaceful ambient soundscape with soft piano…
MusicGen unloaded — memory freed
=============================================================
STEP 2 — Generating 3 soundscape variants (AudioGen)
  [1/3] Prompt: gentle ocean waves at night…
  [2/3] Prompt: soft steady rain on leaves…
  [3/3] Prompt: quiet forest at night…
AudioGen unloaded — memory freed
=============================================================
STEP 3 — Mixing intervention clips
  Mild variants (5): ✓
  Severe variants (5): ✓
=============================================================
STEP 4 — Validating cache
  ✓ intervention_mild_v1.wav    60.0 s  44100 Hz  16-bit
  … (10 clips total)
✓ Cache build complete — all clips valid.
Manifest written → data/audio_cache/manifest.json
```

### 5. After download — local verification

```bash
# 1. Unpack (replace with your actual repo path)
cd ~/SentinalSleep
unzip -o ~/Downloads/audio_cache.zip -d data/

# 2. Full integrity check with SHA-256
uv run python scripts/verify_cache.py

# 3. Confirm all tests pass
uv run pytest tests/ -q
```

`verify_cache.py` exits 0 → Phase 3 complete → start Phase 4 (Orchestration).

---

## Troubleshooting

### `audiocraft` import error in Cell 4

Cell 2 probably did not finish cleanly.  Re-run Cell 2.  Check that
`--no-deps` was used for the audiocraft install so pip doesn't downgrade torch.

### HF rate limit (HTTP 429 or 401)

1. Create a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. In Colab: click the **key icon** (left sidebar) → Secrets → add `HF_TOKEN`
3. Re-run Cell 3

### AudioGen OOM

Unlikely on T4 (AudioGen is only 1.5 GB).  If it happens:

- Switch to L4 or A100 runtime (Runtime → Change runtime type)
- Or re-run with `--use-synthetic-soundscape` to skip AudioGen and use pink-noise
  placeholders (weaker demo, but Phase 3 acceptance still passes)

### `verify_cache.py` reports missing files

Re-run Cell 4 with skip flags to regenerate only the missing step:

```bash
# Only re-run the mixer (music + soundscapes already generated)
!python scripts/pregenerate_cache.py --skip-music --skip-soundscapes

# Only regenerate soundscapes (music already generated)
!python scripts/pregenerate_cache.py --skip-music
```

### Download fails in Cell 6

Use the Files panel (folder icon in left sidebar).  Navigate to
`SentinalSleep/audio_cache.zip` and click the ⋮ menu → Download.

---

## What gets downloaded

```text
audio_cache.zip (~65 MB)
└── data/audio_cache/
    ├── music/
    │   ├── ambient_60bpm_low_v1.wav      (60 s, 44.1 kHz, 16-bit)
    │   ├── meditative_ambient_v2.wav
    │   └── piano_ambient_v3.wav
    ├── soundscape/
    │   ├── ocean_gentle_v1.wav
    │   ├── rain_soft_v1.wav
    │   └── forest_night_v1.wav
    ├── mixed/
    │   ├── intervention_mild_v1.wav … v5.wav
    │   └── intervention_severe_v1.wav … v5.wav
    └── manifest.json                     (provenance + SHA-256 hashes)
```

16 WAV files total.  The manifest records the git commit, device, model ids,
and per-clip SHA-256 digests for `verify_cache.py` to check.
