"""LSH banding + candidate-pair generation over a MinHash signature matrix.

Inlined from `minhash-dedup-practice/src/lsh.py` so SomaliWeb v1's pipeline is
self-contained — no sibling-repo dependency.

Math
----
Two documents with true Jaccard `s` collide in a single band of width `r` with
probability `s^r`. Across `b` independent bands, the probability of being a
candidate (≥ 1 band collision) is the S-curve:

    P(candidate | J = s) = 1 - (1 - s^r)^b

The informal threshold where the S-curve crosses ~50% is

    s* ≈ (1/b)^(1/r)

For our pipeline we use (b, r) = (16, 4) ⇒ s* ≈ 0.50, with k = b·r = 64.
At τ = 0.80 (verification threshold):  P(cand) ≈ 0.984.

Public API
----------
- `generate_candidates(sigs, b, r) -> dict[(low_row, high_row), shared_bands]`
- `s_curve_threshold(b, r) -> float`     (informal s*)
- `p_candidate(s, b, r)   -> float`      (S-curve evaluation)
"""

from __future__ import annotations

import time
from collections import defaultdict

import numpy as np


def s_curve_threshold(b: int, r: int) -> float:
    """Informal s* where P(candidate) ≈ 0.5; useful for tuning (b, r)."""
    return float((1.0 / b) ** (1.0 / r))


def p_candidate(s: float, b: int, r: int) -> float:
    """P(candidate | true Jaccard = s) under banding (b, r)."""
    return float(1 - (1 - s ** r) ** b)


def generate_candidates(
    sigs: np.ndarray, b: int, r: int
) -> dict[tuple[int, int], int]:
    """Return ``{(low_row, high_row): shared_bands_count}`` across all *b* bands.

    Two rows of the signature matrix share a band when their `r`-tuple slice is
    byte-identical. The returned counter therefore says, for every candidate
    pair, how many bands collided — a secondary signal correlated with true
    Jaccard, useful for sanity-checking before exact verification.

    Parameters
    ----------
    sigs : (N, k) uint64
        MinHash signature matrix; one row per document.
    b, r : int
        Banding configuration with `b * r == k`.
    """
    k = sigs.shape[1]
    if b * r != k:
        raise ValueError(f"b * r must equal signature length k; got {b*r} != {k}")
    n = sigs.shape[0]

    shared: dict[tuple[int, int], int] = defaultdict(int)
    t0 = time.time()
    for band_idx in range(b):
        start = band_idx * r
        band = np.ascontiguousarray(sigs[:, start : start + r])
        buckets: dict[bytes, list[int]] = defaultdict(list)
        for row_idx in range(n):
            buckets[band[row_idx].tobytes()].append(row_idx)

        multi_buckets = [v for v in buckets.values() if len(v) >= 2]
        new_pairs_this_band = 0
        for docs in multi_buckets:
            docs.sort()  # so pair tuples are always (low, high)
            m = len(docs)
            for i in range(m):
                a = docs[i]
                for j in range(i + 1, m):
                    c = docs[j]
                    shared[(a, c)] += 1
                    new_pairs_this_band += 1

        elapsed = time.time() - t0
        print(
            f"  band {band_idx+1:2d}/{b}  "
            f"buckets={len(buckets):7d}  "
            f"multi={len(multi_buckets):5d}  "
            f"pair_events={new_pairs_this_band:7d}  "
            f"unique_pairs={len(shared):7d}  "
            f"elapsed={elapsed:.2f}s"
        )
    return dict(shared)
