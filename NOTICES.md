# Third-Party Notices

SentinelSleep depends on several pre-trained models. Each model retains
its own license. Users must comply with the most restrictive license in
use — currently **CC-BY-NC-SA-4.0**, which prohibits commercial use.

> **ADR-014 (2026-04-30):** `cvssp/audioldm2` replaced by
> `facebook/audiogen-medium` as the soundscape generation model.
> The `diffusers` library entry is kept for the deprecated `audioldm2_wrapper.py`.

## Inference libraries (no weights in-repo)

| Library | Source | License | Use |
| ------- | ------ | ------- | --- |
| [audiocraft](https://github.com/facebookresearch/audiocraft) | Meta Research | MIT (code) | MusicGen + AudioGen in Layer 3 pre-generation (Colab only) |
| [diffusers](https://github.com/huggingface/diffusers) | Hugging Face | Apache-2.0 | **Deprecated** — `audioldm2_wrapper.py` back-compat only (ADR-014) |

## Pre-trained models

| Model | Source | License | Layer |
| ----- | ------ | ------- | ----- |
| `MIT/ast-finetuned-audioset-10-10-0.4593` | Hugging Face | BSD-3-Clause | Detection (Layer 1) |
| `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` | Hugging Face | CC-BY-NC-SA-4.0 | Verification (Layer 2) |
| `facebook/musicgen-small` | Hugging Face / Meta | CC-BY-NC-4.0 | Music generation (Layer 3) |
| `facebook/audiogen-medium` | Hugging Face / Meta | CC-BY-NC-4.0 | Soundscape generation (Layer 3, ADR-014) |
| `cvssp/audioldm2` | Hugging Face | CC-BY-NC-SA-4.0 | **Deprecated** — replaced by audiogen-medium (ADR-014) |

## Datasets cited (no weights distributed in this repo)

- **AudioSet** (Gemmeke et al., 2017) — training data for AST.
  License: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)

## Project source code license

SentinelSleep source code (all files outside `data/audio_cache/`) is
**MIT licensed**. See [LICENSE](LICENSE).

## Practical implication

The verification model (`audeering/wav2vec2`) is CC-BY-NC-SA-4.0, which
is the most restrictive license in use. This project is therefore
**non-commercial** — suitable for research, academic demonstration, and
personal use. Productizing it requires replacing the verification model
with a permissively licensed alternative.

## Test fixtures (added in Phase 1)

When real audio fixtures are added to `data/test_fixtures/`, update this
section with source URLs, Freesound IDs, and license per clip.
