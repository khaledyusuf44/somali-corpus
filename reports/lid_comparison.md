# LID benchmark — GlotLID v3 vs langdetect vs fastText lid.176

Test set: `/Users/khalidyusufdahir/Desktop/projects/ai_projects/language-id-practice/data/multilingual_samples.csv` — 200 rows across 5 languages.
Counts per language: {'en': 40, 'so': 40, 'ar': 40, 'fr': 40, 'sw': 40}

## Headline
| Model | Overall accuracy | Docs/sec | Somali precision | Somali recall | Somali F1 |
|---|---:|---:|---:|---:|---:|
| **fasttext_lid176** | 0.600 | 178823.4 | 1.000 | 0.075 | 0.140 |
| **langdetect** | 0.795 | 416.8 | 0.826 | 0.950 | 0.884 |
| **glotlid_v3** | 0.740 | 3944.9 | 0.967 | 0.725 | 0.829 |

## Per-language precision / recall / F1

### fasttext_lid176
| lang | precision | recall | F1 | tp | fp | fn |
|---|---:|---:|---:|---:|---:|---:|
| ar | 1.000 | 0.900 | 0.947 | 36 | 0 | 4 |
| en | 0.559 | 0.950 | 0.704 | 38 | 30 | 2 |
| fr | 0.946 | 0.875 | 0.909 | 35 | 2 | 5 |
| so | 1.000 | 0.075 | 0.140 | 3 | 0 | 37 |
| sw | 1.000 | 0.200 | 0.333 | 8 | 0 | 32 |

### langdetect
| lang | precision | recall | F1 | tp | fp | fn |
|---|---:|---:|---:|---:|---:|---:|
| ar | 1.000 | 0.975 | 0.987 | 39 | 0 | 1 |
| en | 0.963 | 0.650 | 0.776 | 26 | 1 | 14 |
| fr | 0.962 | 0.625 | 0.758 | 25 | 1 | 15 |
| so | 0.826 | 0.950 | 0.884 | 38 | 8 | 2 |
| sw | 0.969 | 0.775 | 0.861 | 31 | 1 | 9 |

### glotlid_v3
| lang | precision | recall | F1 | tp | fp | fn |
|---|---:|---:|---:|---:|---:|---:|
| ar | 1.000 | 0.900 | 0.947 | 36 | 0 | 4 |
| en | 0.935 | 0.725 | 0.817 | 29 | 2 | 11 |
| fr | 1.000 | 0.625 | 0.769 | 25 | 0 | 15 |
| so | 0.967 | 0.725 | 0.829 | 29 | 1 | 11 |
| sw | 1.000 | 0.725 | 0.841 | 29 | 0 | 11 |

## Top confusions (true → predicted, off-diagonal, top 10 per model)

### fasttext_lid176
- `so` → `en`  (18 rows)
- `sw` → `en`  (10 rows)
- `so` → `fi`  (7 rows)
- `ar` → `fa`  (4 rows)
- `so` → `af`  (3 rows)
- `sw` → `id`  (3 rows)
- `sw` → `de`  (3 rows)
- `sw` → `it`  (3 rows)
- `so` → `de`  (2 rows)
- `fr` → `it`  (2 rows)

### langdetect
- `en` → `so`  (5 rows)
- `sw` → `so`  (3 rows)
- `en` → `tl`  (2 rows)
- `fr` → `fi`  (2 rows)
- `fr` → `it`  (2 rows)
- `sw` → `id`  (2 rows)
- `sw` → `tl`  (2 rows)
- `en` → `sk`  (1 rows)
- `en` → `tr`  (1 rows)
- `en` → `fr`  (1 rows)

### glotlid_v3
- `sw` → `kin`  (4 rows)
- `fr` → `zxx`  (3 rows)
- `en` → `zxx`  (2 rows)
- `en` → `ekk`  (2 rows)
- `ar` → `und`  (2 rows)
- `ar` → `fas`  (2 rows)
- `fr` → `ita`  (2 rows)
- `fr` → `und`  (2 rows)
- `sw` → `und`  (2 rows)
- `en` → `luo`  (1 rows)