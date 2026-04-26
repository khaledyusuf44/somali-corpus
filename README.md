# somali-corpus — SomaliWeb v1 pipeline

[![HF Dataset](https://img.shields.io/badge/🤗%20HF%20Dataset-khaledyusuf44%2Fsomaliweb--v1-yellow)](https://huggingface.co/datasets/khaledyusuf44/somaliweb-v1)
[![Code License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](LICENSE)
[![Data License: CC-BY-SA 4.0](https://img.shields.io/badge/Data%20License-CC--BY--SA%204.0-green.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB.svg)](https://www.python.org/)
[![Release v1.0.0](https://img.shields.io/badge/Release-v1.0.0-orange.svg)](https://github.com/khaledyusuf44/somali-corpus/releases/tag/v1.0.0)

End-to-end pipeline for building **SomaliWeb v1**, a quality-filtered Somali web corpus of ~303M tokens, published on Hugging Face at [`khaledyusuf44/somaliweb-v1`](https://huggingface.co/datasets/khaledyusuf44/somaliweb-v1).

## What this repo does

Aggregates three public Somali sources (HPLT v2, CC100, Somali Wikipedia) and passes them through six reproducible stages to produce a cleaned, deduplicated, quality-filtered pretraining corpus plus a matched BPE-16K tokenizer.

## Headline numbers

| | |
|---|---:|
| Input (raw aggregated) | 1,372,052 docs · ~588M tokens |
| **Output (SomaliWeb v1)** | **819,322 docs · ~303M tokens** |
| Pipeline retention | 59.7% (40.3% removed as duplicate / short / non-Somali / low-quality) |

| Finding | Number |
|---|---|
| HPLT v2 byte-exact duplicates caught | **17.3% of HPLT input** |
| HPLT v2 docs with mojibake fixable by ftfy | **56.1% of HPLT input** |
| langdetect vs GlotLID v3 on Somali (F1) | 0.884 vs 0.829 (langdetect wins) |
| SomaliWeb v1 tokenizer vs GPT-4 `cl100k_base` on FLORES-200 Somali | **40.2% lower fertility** |

## Repository layout

This repo is **self-contained** — no sibling-repo dependencies. All MinHash + LSH code is inlined under `src/` (originally drafted in `../minhash-dedup-practice/`).

```
somali-corpus/
├── PLAN.md                       ← full pipeline design doc
├── README.md                     ← this file
├── requirements.txt              ← pinned package versions
├── .gitignore
├── configs/pipeline.yaml         ← all knobs (τ, thresholds, seeds)
├── notes/
│   ├── decisions.md              ← why each choice was made
│   ├── progress.md               ← per-phase execution log with numbers
│   └── learning_plan.md          ← 5-level mastery curriculum for presenting
├── src/                          ← shared utilities (no sibling-repo imports)
│   ├── normalize.py              ← lowercase + whitespace-collapse + SHA-256
│   ├── lsh.py                    ← LSH banding + S-curve helpers
│   └── union_find.py             ← path-compressed union-find
├── pipeline/                     ← the six production filters
│   ├── 01_merge_and_dedup.py     ← byte-exact dedup
│   ├── 02_clean.py               ← ftfy mojibake fix + length filter
│   ├── 03_lid_verify.py          ← langdetect + GlotLID dialect tagging
│   ├── 04_near_dedup.py          ← MinHash + LSH + τ=0.80 Jaccard
│   ├── 05_quality_filter.py     ← char-5-gram coverage against clean seed
│   └── 06_structure_release.py   ← shuffle/split + tokenizer + fertility eval
├── phase0_scripts/               ← context-phase one-offs (reproducibility)
│   ├── fetch_wikipedia_so.py     │
│   ├── lid_benchmark.py          │
│   ├── download_baselines.py     │ historical (OSCAR/MADLAD attempts)
│   ├── convert_cc100.py          │
│   ├── convert_hplt.py           │
│   ├── baseline_overlap_report.py│
│   ├── robots_audit.py           │
│   └── fetch_flores.py           │
├── reports/                      ← per-phase metrics + findings (committed)
│   ├── 01..06_*.{md,json}
│   ├── baseline_comparison.md    ← raw-source characterization
│   ├── lid_comparison.md         ← Somali LID benchmark (langdetect F1 0.884)
│   └── curated_sources_audit.md  ← robots.txt audit (Phase 0.5)
├── models/                       ← runtime-fetched binaries (gitignored)
│   └── lid.176.ftz               ← fastText LID for Phase 0.2 benchmark
└── data/                         ← all generated / downloaded artifacts (gitignored)
    ├── extracted/                ← Wikipedia-so
    ├── baselines/                ← HPLT v2, CC100 unified JSONL
    ├── downloads/                ← raw .xz / .zst archives
    ├── pipeline/                 ← per-phase intermediate JSONL (01..05)
    ├── release/                  ← train.jsonl + validation.jsonl + tokenizer
    └── eval/                     ← FLORES-200 Somali held-out test set
```

## Reproduce

All seeds are fixed (`seed = 0`). Python 3.9+:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # pinned versions; numpy<2 for fasttext-wheel
```

Then the data acquisition + full pipeline:

```bash
# Phase 0 — one-time context and baseline acquisition
python phase0_scripts/fetch_wikipedia_so.py        # 9k articles via HF datasets
python phase0_scripts/robots_audit.py              # audit curated Somali sources
python phase0_scripts/lid_benchmark.py             # our LID benchmark
curl -L -o data/downloads/cc100_so.txt.xz          https://data.statmt.org/cc-100/so.txt.xz
curl -L -o data/downloads/hplt2_so.jsonl.zst       https://data.hplt-project.org/two/cleaned/som_Latn/1.jsonl.zst
python phase0_scripts/convert_cc100.py
python phase0_scripts/convert_hplt.py
python phase0_scripts/baseline_overlap_report.py

# Phases 1–6 — the pipeline
python pipeline/01_merge_and_dedup.py
python pipeline/02_clean.py
python pipeline/03_lid_verify.py --workers 10
python pipeline/04_near_dedup.py
python pipeline/05_quality_filter.py
python pipeline/06_structure_release.py
```

Approximate run times on an Apple M4 Pro / 24 GB RAM:

| Phase | Elapsed |
|---|---:|
| 1 — Merge + exact dedup | 83 s |
| 2 — Clean + normalize | 33 min |
| 3 — LID verify (10 workers) | 14 min |
| 4 — MinHash near-dedup | 5 min |
| 5 — Quality filter | 5.5 min |
| 6 — Structure + tokenizer + fertility | ~2 min |
| **Total pipeline** | **~1 hour** |

(Phase 2 is the slow step — `ftfy` is ~600 docs/sec; trivially parallelizable if you care.)

## Dataset card and usage

The Hugging Face dataset card lives at [huggingface.co/datasets/khaledyusuf44/somaliweb-v1](https://huggingface.co/datasets/khaledyusuf44/somaliweb-v1). Python usage:

```python
from datasets import load_dataset
from tokenizers import Tokenizer

ds = load_dataset("khaledyusuf44/somaliweb-v1")
tok = Tokenizer.from_file("tokenizer_somaliweb.json")
```

## License

Pipeline code: MIT.
Produced corpus: CC-BY-SA 4.0 (inherits Somali Wikipedia's license; see dataset card for source-by-source detail).

## Citation

See the [dataset card on Hugging Face](https://huggingface.co/datasets/khaledyusuf44/somaliweb-v1#citation) for the BibTeX entry. A `CITATION.cff` file at the repo root is also recognized by GitHub's "Cite this repository" widget.

## Acknowledgments

Builds on HPLT v2, CC100, Somali Wikipedia, FLORES-200, GlotLID, and the Common Crawl Foundation's archive.
