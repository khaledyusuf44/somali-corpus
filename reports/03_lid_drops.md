# Phase 3 — LID verification (langdetect, min_conf=0.5)

Elapsed: 846.9s with 10 workers

- Input docs: **1,080,040**
- Kept docs (top-1=so, conf≥0.5): **1,077,804**
- Dropped: 2,236 (0.21%)

## Per-source kept
| Source | Input | Kept | Drop rate |
|---|---:|---:|---:|
| wikipedia-so | 5,683 | 5,479 | 3.59% |
| cc100-so | 275,744 | 275,742 | 0.00% |
| hplt2-so | 798,613 | 796,583 | 0.25% |

## Top 15 languages among dropped docs
| predicted lang | count |
|---|---:|
| `en` | 1,743 |
| `tl` | 161 |
| `id` | 86 |
| `so` | 62 |
| `sv` | 24 |
| `ar` | 20 |
| `et` | 18 |
| `pl` | 12 |
| `tr` | 12 |
| `de` | 11 |
| `it` | 10 |
| `nl` | 10 |
| `fi` | 10 |
| `fr` | 9 |
| `pt` | 9 |

## Low-confidence Somali drops
- so_low_conf(<0.5): 62

## Dialect tagging (GlotLID second pass on survivors)
- `som_Latn`: 1,077,320 (99.96%)
- `ymm_Latn`: 0 (0.00%)
- other tag: 484 (langdetect said 'so' but GlotLID disagreed)
