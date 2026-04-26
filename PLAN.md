# Project plan — Somali Web Corpus (SomaliWeb-v1)

Design doc for the corpus pipeline. For *why* we made each choice, see `notes/decisions.md`. For *what state we're in at any moment*, see `notes/progress.md`. For *numbers on the raw sources*, see `reports/baseline_comparison.md`.

## Project intent

Ship a clean, deduplicated, quality-filtered Somali pretraining corpus of ~250M tokens — published on Hugging Face with a full dataset card, reproducible via one command, and accompanied by a short workshop-style paper. The primary contribution is the **aggregation + dedup + quality-filter pipeline** applied to existing Somali resources; the secondary contribution is the **first public benchmark of language identifiers on Somali**, the **first measurement of byte-level duplication inside HPLT v2's published distribution**, and the **first perplexity-based quality filter methodology tailored to low-resource languages without in-language labeled data**.

## Current state (after Phase 0)

All source material is on disk. **No further downloads needed.**

| Source | Docs | Raw tokens | Within-source byte-dup |
|---|---:|---:|---:|
| HPLT v2 `som_Latn` | 966,507 | ~505M | 17.3% |
| CC100-so | 396,524 | ~81M | 5.5% |
| Wikipedia-so | 9,021 | ~2.5M | 0.2% |
| **Union raw** | **1,372,052** | **~588M** | cross-source overlap 0.12% |

LID benchmark (our Somali test set): langdetect F1 **0.884** / GlotLID F1 0.829 / lid.176 F1 0.140.

## The remaining 7 phases

Each phase takes in the previous phase's output JSONL and produces the next one. One module per phase in `pipeline/`. All knobs live in `configs/pipeline.yaml`.

### Phase 1 — Merge + exact dedup
**Input:** `data/extracted/wikipedia_so.jsonl`, `data/baselines/{cc100,hplt2}_so.jsonl`.
**What it does:** Streams all three, writes one unified JSONL with schema `{id, source, text[, url]}`, dropping any document whose `sha256(lowercase(whitespace-collapsed(text)))` is already seen. First-seen wins.
**Output:** `data/pipeline/01_merged_dedup.jsonl`.
**Expected drops:** ~190K docs from byte-level duplication (17% of HPLT + 5.5% of CC100 + natural cross-overlap).
**Deliverable:** `reports/01_merge_stats.json` — before/after counts by source.

### Phase 2 — Clean + normalize
**Input:** Phase 1 output.
**What it does:**
  - Apply **mojibake fix** for CC100 (UTF-8 double-encoded-as-CP1252 patterns like `â€™ → '`, `Ã© → é`). Use `ftfy`.
  - Collapse whitespace; strip boilerplate URL-hugging lines, nav tokens, repeated-char rows.
  - Drop documents shorter than **50 words** post-clean (matches HPLT's own floor).
**Output:** `data/pipeline/02_cleaned.jsonl`.
**Deliverable:** `reports/02_clean_stats.json` — fraction mojibake-fixed per source, drops by reason.

### Phase 3 — LID verification
**Input:** Phase 2 output.
**What it does:** Run `langdetect` (seeded) on each doc; keep only where top-1 = `so` with prob ≥ 0.50. Second pass: GlotLID tags surviving docs with `som_Latn` vs `ymm_Latn` for corpus metadata.
**Output:** `data/pipeline/03_lid_verified.jsonl` (adds `lang_top1`, `lang_conf`, `dialect_tag`).
**Deliverable:** `reports/03_lid_drops.md` — docs dropped per source, confusion breakdown of drops, ymm fraction.

### Phase 4 — MinHash near-dedup
**Input:** Phase 3 output.
**What it does:** Import `minhash-dedup-practice/src/` directly. Word-3-gram shingles, k=64 MinHash, b=16 r=4 LSH, τ=0.80 Jaccard verification, union-find clusters, `longest` keep-rule.
**Output:** `data/pipeline/04_near_deduped.jsonl`.
**Deliverable:** `reports/04_near_dedup_stats.md` — cluster size distribution, fraction removed per source.

### Phase 5 — Perplexity quality filter
**Input:** Phase 4 output.
**What it does:**
  - Train a **KN-smoothed 5-gram character-level LM** on `Wikipedia-so` medium+long articles + BBC Somali sitemap sample (~2M tokens clean seed).
  - Score every Phase-4 doc by normalized per-char log-likelihood.
  - Drop the bottom ~15% (threshold calibrated against manual samples at decile boundaries).
**Output:** `data/pipeline/05_quality_filtered.jsonl` (adds `quality_score`).
**Deliverable:** `reports/05_quality_filter.md` — threshold curve, examples at each decile, ablation.
**Why this over a trained classifier:** No in-language labeled quality data exists for Somali. Perplexity against a clean seed is the cheapest "this looks like fluent Somali" signal that needs zero labeled negatives. A trained classifier is v2.

### Phase 6 — Final structuring + evaluation
**Input:** Phase 5 output.
**What it does:**
  - Shuffle (seed 0), 95/5 train/val split.
  - Add final metadata: `{id, text, source, length_words, quality_score, lang_conf, dialect_tag}`.
  - Write `data/release/{train,validation}.jsonl`.
  - Manual inspection of 100 random docs (quality rubric 1-4).
  - Train a tiny BPE tokenizer (vocab 4K/16K) on the released train split; measure fertility on a held-out Somali test set (pulled from Wikipedia-so recent articles).
  - Compare fertility vs. HPLT-raw on the same test set.
**Output:** `data/release/{train,validation}.jsonl`.
**Deliverable:** `reports/06_evaluation.md` — full comparison table, sample inspection findings, tokenizer fertility numbers (the paper's results section).

### Phase 7 — Release + paper
**What it does:**
  - Write `README.md` (HF dataset card) covering: summary · motivation · collection · pipeline · stats · evaluation · limitations · ethical considerations · usage.
  - `huggingface-cli repo create`, push `data/release/*.jsonl` + dataset card.
  - Mirror repo on GitHub with pipeline code, tagged `v1.0`.
  - Draft long paper at `paper/somali-web-corpus-v2.md` (markdown source) + `paper/skeleton.tex` (ACL 2024 LaTeX skeleton): goal · corpus · method · LID benchmark · dedup findings · quality filter · downstream fertility · limitations.
**Deliverable:** Public HuggingFace dataset + GitHub repo + arXiv preprint.

## Repository layout

```
somali-corpus/
├── PLAN.md                       # this file
├── README.md                     # landing (rewritten post-Phase-6)
├── notes/
│   ├── decisions.md              # why we made each choice
│   └── progress.md               # what we've done, per sub-phase
├── configs/
│   └── pipeline.yaml             # all knobs (τ, min-length, quality threshold, seeds)
├── pipeline/
│   ├── 01_merge_and_dedup.py
│   ├── 02_clean.py
│   ├── 03_lid_verify.py
│   ├── 04_near_dedup.py
│   ├── 05_quality_filter.py
│   └── 06_structure_release.py
├── src/                          # shared utilities (normalize, io helpers)
├── phase0_scripts/               # one-off context-phase scripts (kept for reproducibility)
├── data/
│   ├── extracted/                # Phase 0.1 (Wikipedia-so)
│   ├── baselines/                # Phase 0.4 (CC100, HPLT v2)
│   ├── downloads/                # raw compressed (.xz, .zst) — gitignored
│   ├── pipeline/                 # 01..05 intermediate JSONL
│   └── release/                  # train.jsonl + validation.jsonl (final)
├── reports/
│   └── *.md / *.json             # per-phase metrics and findings
└── paper/
    ├── somali-web-corpus-v2.md      # markdown source of truth
    ├── skeleton.tex                 # ACL 2024 LaTeX skeleton
    ├── refs.bib
    ├── tikz/figure1_pipeline.tex    # TikZ flow diagram
    ├── scripts/figure{2..6}_*.py    # matplotlib figure scripts
    └── figures/                     # rendered PDF + PNG
```

## Target corpus size (expected ranges)

| After phase | Expected docs | Expected tokens |
|---|---:|---:|
| 0 — raw union | 1,372,052 | ~588M |
| 1 — exact dedup | ~1,180,000 | ~490M |
| 2 — cleaned, length-filter ≥50w | ~1,000,000 | ~470M |
| 3 — LID-verified | ~950,000 | ~450M |
| 4 — near-dedup at τ=0.80 | ~700,000 | ~350M |
| 5 — quality filter (bottom-15% drop) | ~600,000 | ~**300M** |
| 6 — final release | ~600,000 | **~300M train / ~15M val** |

Numbers will adjust per phase based on actual measurements — these are pre-execution estimates.

## Success criteria

This project is done when:
1. `hf.co/datasets/khaledyusuf44/somaliweb-v1` is live with ≥ 50M tokens, a full dataset card, and reproducible load via `datasets.load_dataset(...)`.
2. A trained Somali BPE tokenizer on our corpus has measurably lower fertility on a held-out Somali test set than a GPT-4-class general tokenizer. (Target: ≥ 20% reduction; stretch: ≥ 40%.)
3. Manual inspection of 100 random docs scores ≥ 80% as "coherent Somali text usable for pretraining."
4. A 6-page workshop-style paper exists at `paper/` documenting the pipeline, the LID benchmark, and the three measured findings from Phase 0.
5. Pipeline runs end-to-end from `configs/pipeline.yaml` with a single `python run_pipeline.py` command.

## Working rhythm

Each phase is **one focused session**. Updates land in `notes/progress.md` as we complete each step.

Phase 1-4 are mechanical (merge, clean, LID, dedup) and should each run in minutes to tens of minutes on the full corpus.

Phase 5 is the research phase — threshold calibration takes thought. Longest single phase.

Phase 6 combines evaluation and release prep. Phase 7 is paperwork + writing.

## Anti-patterns (lessons from Phase 0)

- **Don't re-crawl what's already crawled.** Phase 0's original "download 20 WET files" was 4,000× wasteful; HPLT covers the same ground for 40× less bandwidth.
- **Don't trust literature predictions without empirical checks.** We predicted GlotLID > langdetect; the opposite held on our test set.
- **Don't trust "cleaned" to mean "byte-exact deduped."** HPLT v2 retains 17% byte-dups despite its cleaning pass.
- **Don't chase OSCAR/MADLAD through gated datasets-library loader scripts when the source is available direct.** CC100 via `statmt.org`, HPLT via `data.hplt-project.org`.
- **Don't scope creep on curated sources before measuring what HPLT alone gives.** News scraping is deferred to v2 precisely because HPLT already exceeded our target.
