# Phase 4 — MinHash near-dedup  (word-3, k=64, (16,4), τ=0.8)

- Input docs: 1,077,804
- Candidate pairs (LSH): 1,017,790
- Above-τ pairs: 153,123
- Clusters: 82,679  covering 196,575 docs
- Docs removed (keep-rule=longest): 113,896
- Output docs: 963,908
- Drop rate: 10.57%

## Cluster size distribution (top 10 sizes by count-of-that-size)
| cluster size | clusters | total docs |
|---:|---:|---:|
| 75 | 1 | 75 |
| 22 | 1 | 22 |
| 17 | 1 | 17 |
| 16 | 1 | 16 |
| 15 | 3 | 45 |
| 14 | 5 | 70 |
| 13 | 9 | 117 |
| 12 | 8 | 96 |
| 11 | 27 | 297 |
| 10 | 44 | 440 |

## Per-source kept
| Source | Input | Kept | Drop rate |
|---|---:|---:|---:|
| wikipedia-so | 5,479 | 4,624 | 15.61% |
| cc100-so | 275,742 | 247,672 | 10.18% |
| hplt2-so | 796,583 | 711,612 | 10.67% |
