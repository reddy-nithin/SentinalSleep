# Third-Party Notices

SentinelSleep depends on several pre-trained models. Each model retains
its own license. Users must comply with the most restrictive license in
use — currently **CC-BY-NC-SA-4.0**, which prohibits commercial use.

## Pre-trained models

| Model | Source | License | Layer |
|-------|--------|---------|-------|
| `MIT/ast-finetuned-audioset-10-10-0.4593` | Hugging Face | BSD-3-Clause | Detection (Layer 1) |
| `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` | Hugging Face | CC-BY-NC-SA-4.0 | Verification (Layer 2) |
| `facebook/musicgen-small` | Hugging Face | CC-BY-NC-4.0 | Music generation (Layer 3) |
| `cvssp/audioldm2` | Hugging Face | CC-BY-NC-SA-4.0 | Soundscape generation (Layer 3) |

## Datasets cited (no weights distributed in this repo)

- **AudioSet** (Gemmeke et al., 2017) — training data for AST.
  License: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)

## Project source code license

SentinelSleep source code (all files outside `data/audio_cache/`) is
**MIT licensed**. See [LICENSE](LICENSE).

## Practical implication

Because the verification and soundscape generation models are
CC-BY-NC-SA, this project is **non-commercial**. It is suitable for
research, academic demonstration, and personal use. Productizing it
requires replacing those models with permissively licensed alternatives.

## Test fixtures (added in Phase 1)

When real audio fixtures are added to `data/test_fixtures/`, update this
section with source URLs, Freesound IDs, and license per clip.
