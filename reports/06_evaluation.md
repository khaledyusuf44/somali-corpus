# Phase 6 — Final evaluation

## SomaliWeb-v1 corpus — final composition

| | |
|---|---:|
| Total docs (train + val) | **819,322** |
| Train split (95%) | 778,355 |
| Validation split (5%) | 40,967 |
| Total whitespace words | 233,080,460 |
| **Approx tokens (words × 1.3)** | **~303M** |
| Train file size | 1,583 MB |
| Validation file size | 83 MB |

### Source composition

| Source | Docs | Fraction |
|---|---:|---:|
| hplt2-so | 582,257 | 71.07% |
| cc100-so | 233,394 | 28.49% |
| wikipedia-so | 3,671 | 0.45% |

## Tokenizer fertility on FLORES-200 Somali devtest (1,012 held-out sentences)

| Tokenizer | Training corpus | Vocab | Tokens | Words | **Fertility ↓** |
|---|---|---:|---:|---:|---:|
| **SomaliWeb-v1** (ours) | 350M tokens (cleaned + dedup + quality-filtered) | 16K | 35,867 | 23,322 | **1.538** |
| HPLT-raw | 505M tokens (raw HPLT v2 `som_Latn`) | 16K | 35,854 | 23,322 | 1.537 |
| GPT-4 `cl100k_base` | proprietary, mostly English | 100K | 60,010 | 23,322 | 2.573 |

### Key findings

1. **SomaliWeb-v1 matches HPLT-raw fertility at 30% smaller training set.** The tokenizer trained on our cleaned + filtered corpus achieves 1.538 tokens/word, vs HPLT-raw's 1.537 on a 40% larger training corpus. Data-efficiency gain: our cleaning doesn't hurt tokenizer quality, and arguably preserves more information density per training token.

2. **SomaliWeb-v1 is 40.2% more token-efficient than GPT-4's `cl100k_base`** on Somali text. Same 1,012 sentences → GPT-4 tokenizer emits 60,010 tokens, ours emits 35,867. For an LLM inference pricing context, GPT-4 on Somali is paying ~1.67× token overhead vs what a Somali-trained tokenizer would use.

3. **The "tokenization tax" for Somali on general-purpose tokenizers is measurable** — GPT-4 cl100k_base fertility 2.573 is 67% higher than both native Somali tokenizers. This is the quantitative motivation for Somali-specific tokenization work.

## Manual inspection sample

20 random docs sampled from the release corpus written to `data/release/manual_inspection_sample.jsonl`. Each contains `{id, source, n_words, quality_score, text_head[:400]}` for rubric-based scoring.

Informal inspection of the 20 samples: all 20 are recognizable Somali text, all 20 would be usable in a pretraining corpus. Full rubric scoring deferred until the paper writeup phase, but the positive rate on this sample is 20/20 = 100% (preliminary; n=20).

## Pipeline retention summary

From raw aggregated sources → SomaliWeb-v1:

| Stage | Docs | Retention vs raw |
|---|---:|---:|
| Raw union (HPLT + CC100 + Wiki-so) | 1,372,052 | 100% |
| Phase 1 — byte-exact dedup | 1,182,360 | 86.2% |
| Phase 2 — clean + mojibake + ≥50w | 1,080,040 | 78.7% |
| Phase 3 — LID verify | 1,077,804 | 78.6% |
| Phase 4 — MinHash near-dedup | 963,908 | 70.3% |
| Phase 5 — quality filter (15% drop) | 819,322 | **59.7%** |

**40.3% of raw aggregated input removed** by our pipeline across the five filters.
Of the 552K docs removed: 13.8% byte-dup (190K), 7.5% too-short (102K), 0.2% non-Somali (2K), 8.3% near-dup (114K), 10.5% low-quality (145K).

## Artifacts

- `data/release/train.jsonl` — 778,355 docs · 1,583 MB
- `data/release/validation.jsonl` — 40,967 docs · 83 MB
- `data/release/tokenizer_somaliweb.json` — our BPE-16K tokenizer
- `data/release/tokenizer_hplt_raw.json` — HPLT-raw BPE-16K (for reproducibility of the comparison)
- `data/release/manual_inspection_sample.jsonl` — 20 random docs for manual review
