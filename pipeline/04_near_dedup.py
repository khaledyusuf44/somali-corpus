"""Phase 4 — MinHash near-dedup on the LID-verified corpus (memory-efficient v2).

Design:
  - Each word-3-gram is hashed to a 31-bit int (blake2b) **inline at shingling time**.
  - We store per-doc a numpy array of unique shingle-ints (uint64), not a Python
    set of strings. For 1M docs × avg 400 shingles × 8 bytes = ~3 GB (vs. ~37 GB
    for a Python string-set layout).
  - Signatures and Jaccard both operate on the int arrays directly.

Config:
  word-3-gram shingles · k=64 MinHash · (b=16, r=4) LSH · τ=0.80 · longest-keep

Input:   data/pipeline/03_lid_verified.jsonl
Output:  data/pipeline/04_near_deduped.jsonl
Report:  reports/04_near_dedup_stats.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.lsh import generate_candidates  # noqa: E402
from src.union_find import UnionFind  # noqa: E402

# Same universal-hash setup as minhash-dedup-practice — see its CLAUDE.md for why.
P_PRIME = np.uint64((1 << 31) - 1)
UINT64_MAX = np.iinfo(np.uint64).max


def shingle_ints(text: str, k: int = 3) -> np.ndarray:
    """Word-k-gram shingle hashes as a deduplicated uint64 array.
    Normalization: lowercase + whitespace split (mirrors shingling.py's default)."""
    toks = text.lower().split()
    if len(toks) < k:
        return np.empty(0, dtype=np.uint64)
    ids = np.fromiter(
        (
            int.from_bytes(
                hashlib.blake2b(" ".join(toks[i : i + k]).encode("utf-8"), digest_size=4).digest(),
                "big",
            ) & 0x7FFFFFFF
            for i in range(len(toks) - k + 1)
        ),
        dtype=np.uint64,
        count=len(toks) - k + 1,
    )
    return np.unique(ids)  # set-of-ints semantics


def compute_signature(ids: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """MinHash signature from pre-hashed shingle-ids."""
    k = a.shape[0]
    if ids.size == 0:
        return np.full(k, UINT64_MAX, dtype=np.uint64)
    # (k, 1) * (1, n) + (k, 1), all factors < 2^31 so a*id stays < 2^62.
    hashed = (a[:, None] * ids[None, :] + b[:, None]) % P_PRIME
    return hashed.min(axis=1).astype(np.uint64)


def make_hashes(k: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    a = rng.integers(1, int(P_PRIME), size=k, dtype=np.int64).astype(np.uint64)
    b = rng.integers(0, int(P_PRIME), size=k, dtype=np.int64).astype(np.uint64)
    return a, b


def jaccard_sorted(a: np.ndarray, b: np.ndarray) -> float:
    """Jaccard on sorted unique uint64 arrays — faster than set() for >100 items."""
    if a.size == 0 and b.size == 0:
        return 1.0
    inter = np.intersect1d(a, b, assume_unique=True).size
    union = a.size + b.size - inter
    return inter / union if union else 0.0


def iter_jsonl(path: Path):
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(ROOT / "data/pipeline/03_lid_verified.jsonl"))
    p.add_argument("--out",   default=str(ROOT / "data/pipeline/04_near_deduped.jsonl"))
    p.add_argument("--report", default=str(ROOT / "reports/04_near_dedup_stats.md"))
    p.add_argument("--shingle-k", type=int, default=3)
    p.add_argument("--k-hashes", type=int, default=64)
    p.add_argument("--b", type=int, default=16)
    p.add_argument("--r", type=int, default=4)
    p.add_argument("--tau", type=float, default=0.80)
    p.add_argument("--keep-rule", choices=["longest", "first-seen", "shortest"], default="longest")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    assert args.b * args.r == args.k_hashes

    in_path = Path(args.input)
    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- 1. single pass: read, shingle-ints, sign ----
    print(f"[phase4] pass 1 — shingle + sign (k={args.k_hashes}, shingle-k={args.shingle_k})")
    a_hashes, b_hashes = make_hashes(args.k_hashes, seed=args.seed)

    # Keep only what we need from each record: id, source, n_words, plus the
    # file offset so we can stream the text back on demand in pass 3.
    doc_meta: list[dict] = []         # {id, source, n_words}
    doc_shingles: list[np.ndarray] = []  # int arrays, kept in memory (~3 GB)
    sigs_list: list[np.ndarray] = []

    t0 = time.time()
    with in_path.open() as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            ids = shingle_ints(rec["text"], k=args.shingle_k)
            sig = compute_signature(ids, a_hashes, b_hashes)
            doc_meta.append({
                "id": rec.get("id"),
                "source": rec.get("source"),
                "n_words": rec.get("n_words", len(rec["text"].split())),
            })
            doc_shingles.append(ids)
            sigs_list.append(sig)
            if (i + 1) % 100_000 == 0:
                mb = sum(x.nbytes for x in doc_shingles) / 1024 / 1024
                print(f"  shingled {i+1:,}  sig+shingle mem ~{mb:.0f} MB  ({time.time()-t0:.1f}s)", flush=True)

    n_docs = len(doc_meta)
    sigs = np.asarray(sigs_list, dtype=np.uint64)
    sigs_list.clear()  # free the Python list overhead
    shingle_mb = sum(x.nbytes for x in doc_shingles) / 1024 / 1024
    print(f"[phase4] pass 1 done: {n_docs:,} docs, sigs {sigs.shape}, "
          f"shingles {shingle_mb:.0f} MB, elapsed {time.time()-t0:.1f}s")

    # ---- 2. LSH candidate pairs ----
    print(f"[phase4] pass 2 — LSH banding (b={args.b}, r={args.r}, "
          f"s*≈{(1/args.b)**(1/args.r):.3f})")
    t1 = time.time()
    shared = generate_candidates(sigs, args.b, args.r)
    print(f"[phase4] {len(shared):,} candidate pairs in {time.time()-t1:.1f}s")

    # ---- 3. verify Jaccard + union-find ----
    print(f"[phase4] pass 3 — verify Jaccard at τ={args.tau}")
    t2 = time.time()
    uf = UnionFind()
    above = 0
    n_verified = 0
    for (ra, rc), _ in shared.items():
        j = jaccard_sorted(doc_shingles[ra], doc_shingles[rc])
        n_verified += 1
        if j >= args.tau:
            uf.union(str(ra), str(rc))
            above += 1
        if n_verified % 50_000 == 0:
            print(f"  verified {n_verified:,}/{len(shared):,}  above τ: {above:,}  "
                  f"({time.time()-t2:.1f}s)", flush=True)
    clusters = uf.components()
    print(f"[phase4] {above:,} pairs above τ → {len(clusters):,} clusters "
          f"covering {sum(len(c) for c in clusters):,} docs ({time.time()-t2:.1f}s)")

    # free shingles before pass 4
    doc_shingles.clear()

    # ---- 4. pick keepers + write output ----
    print(f"[phase4] pass 4 — apply keep-rule={args.keep_rule} + write output")
    to_remove: set[int] = set()
    for cluster in clusters:
        members = [int(x) for x in cluster]
        if args.keep_rule == "longest":
            survivor = max(members, key=lambda i: (doc_meta[i]["n_words"], -i))
        elif args.keep_rule == "shortest":
            survivor = min(members, key=lambda i: (doc_meta[i]["n_words"], i))
        else:  # first-seen
            survivor = min(members)
        for i in members:
            if i != survivor:
                to_remove.add(i)

    # Re-stream the input; write only survivors.
    kept = 0
    per_source_in: Counter = Counter()
    per_source_kept: Counter = Counter()
    with in_path.open() as f_in, out_path.open("w", encoding="utf-8") as f_out:
        for i, line in enumerate(f_in):
            rec = json.loads(line)
            per_source_in[rec["source"]] += 1
            if i in to_remove:
                continue
            f_out.write(line if line.endswith("\n") else line + "\n")
            kept += 1
            per_source_kept[rec["source"]] += 1

    cluster_sizes = Counter(len(c) for c in clusters)
    top_sizes = sorted(cluster_sizes.keys(), reverse=True)[:10]

    report = [
        f"# Phase 4 — MinHash near-dedup  (word-{args.shingle_k}, k={args.k_hashes}, ({args.b},{args.r}), τ={args.tau})\n",
        f"- Input docs: {n_docs:,}",
        f"- Candidate pairs (LSH): {len(shared):,}",
        f"- Above-τ pairs: {above:,}",
        f"- Clusters: {len(clusters):,}  covering {sum(len(c) for c in clusters):,} docs",
        f"- Docs removed (keep-rule={args.keep_rule}): {len(to_remove):,}",
        f"- Output docs: {kept:,}",
        f"- Drop rate: {len(to_remove)/n_docs*100:.2f}%",
        "",
        "## Cluster size distribution (top 10 sizes by count-of-that-size)",
        "| cluster size | clusters | total docs |",
        "|---:|---:|---:|",
    ]
    for s in top_sizes:
        c = cluster_sizes[s]
        report.append(f"| {s} | {c:,} | {s*c:,} |")
    report += [
        "",
        "## Per-source kept",
        "| Source | Input | Kept | Drop rate |",
        "|---|---:|---:|---:|",
    ]
    for src, pin in per_source_in.items():
        pk = per_source_kept.get(src, 0)
        rate = (1 - pk / pin) * 100 if pin else 0.0
        report.append(f"| {src} | {pin:,} | {pk:,} | {rate:.2f}% |")

    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print()
    print("=== Phase 4 summary ===")
    print(f"  input:       {n_docs:,}")
    print(f"  candidates:  {len(shared):,}")
    print(f"  above τ:     {above:,}")
    print(f"  clusters:    {len(clusters):,}")
    print(f"  removed:     {len(to_remove):,}  ({len(to_remove)/n_docs*100:.2f}%)")
    print(f"  output:      {kept:,}")
    print(f"  file: {out_path}  ({out_path.stat().st_size/1024/1024:.1f} MB)")
    print(f"  report: {report_path}")


if __name__ == "__main__":
    main()
