"""Phase 5 — Quality filter via character-n-gram coverage.

Seed: Wikipedia-so articles with >= `min_seed_words` (default 200). Build the set
of all character 5-grams appearing in the seed.

Score: fraction of each doc's character 5-grams that appear in the seed set.
Interpretation: "how much of this doc's character-level patterns match known
clean Somali Wikipedia?" High = fluent Somali. Low = mojibake, boilerplate, or
non-Somali-looking content.

Filter: drop the bottom `drop_bottom_fraction` (default 0.15) by score.

Why n-gram coverage over trained classifier or perplexity LM
-----------------------------------------------------------
- No labeled Somali quality data exists → classifier needs bootstrapping.
- Perplexity requires a smoothed probability model — doable but more code and
  slower.
- n-gram coverage is a one-liner over two sets, interpretable to readers, and
  monotonic in "text cleanliness" for our failure modes (garbage encoding,
  random-symbol pages, non-Somali content). Good enough for v1; v2 can upgrade
  to a trained classifier.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "data/pipeline/04_near_deduped.jsonl"
DEFAULT_SEED = ROOT / "data/extracted/wikipedia_so.jsonl"
DEFAULT_OUT = ROOT / "data/pipeline/05_quality_filtered.jsonl"
DEFAULT_REPORT = ROOT / "reports/05_quality_filter.md"


def char_ngrams(text: str, n: int) -> set[str]:
    if len(text) < n:
        return set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def build_seed_vocab(seed_path: Path, n: int, min_seed_words: int) -> set[str]:
    """Collect all char-n-grams from seed docs meeting the min-word threshold."""
    vocab: set[str] = set()
    n_docs = 0
    n_tokens = 0
    with seed_path.open() as f:
        for line in f:
            r = json.loads(line)
            text = r.get("text") or ""
            if len(text.split()) < min_seed_words:
                continue
            vocab |= char_ngrams(text, n)
            n_docs += 1
            n_tokens += len(text.split())
    return vocab, n_docs, n_tokens


def score_doc(text: str, vocab: set[str], n: int) -> tuple[float, int, int]:
    doc_ngrams = char_ngrams(text, n)
    if not doc_ngrams:
        return 0.0, 0, 0
    in_vocab = sum(1 for g in doc_ngrams if g in vocab)
    return in_vocab / len(doc_ngrams), in_vocab, len(doc_ngrams)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(DEFAULT_IN))
    p.add_argument("--seed", default=str(DEFAULT_SEED))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--ngram-n", type=int, default=5)
    p.add_argument("--min-seed-words", type=int, default=200)
    p.add_argument("--drop-bottom-fraction", type=float, default=0.15)
    p.add_argument("--sample-per-decile", type=int, default=3)
    p.add_argument("--seed-rng", type=int, default=0)
    args = p.parse_args()

    in_path = Path(args.input)
    seed_path = Path(args.seed)
    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[phase5] building seed vocab: n={args.ngram_n}, min_seed_words={args.min_seed_words}")
    t0 = time.time()
    vocab, seed_docs, seed_tokens = build_seed_vocab(seed_path, args.ngram_n, args.min_seed_words)
    print(f"[phase5] seed: {seed_docs:,} docs, ~{seed_tokens:,} tokens, "
          f"{len(vocab):,} unique {args.ngram_n}-grams ({time.time()-t0:.1f}s)")

    # Score all docs in a single pass; store (row_idx, score, n_words, source).
    print("[phase5] scoring corpus...")
    t1 = time.time()
    scores: list[tuple[int, float, int, str]] = []
    with in_path.open() as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            s, _, _ = score_doc(r["text"], vocab, args.ngram_n)
            scores.append((i, s, r.get("n_words", len(r["text"].split())), r["source"]))
            if (i + 1) % 100_000 == 0:
                print(f"  scored {i+1:,}  ({time.time()-t1:.1f}s)", flush=True)
    n_total = len(scores)
    print(f"[phase5] scored {n_total:,} docs in {time.time()-t1:.1f}s")

    # Threshold = drop_bottom_fraction percentile.
    scores_sorted = sorted(scores, key=lambda x: x[1])
    drop_n = int(n_total * args.drop_bottom_fraction)
    threshold = scores_sorted[drop_n - 1][1] if drop_n > 0 else 0.0
    kept_row_idxs = {x[0] for x in scores_sorted[drop_n:]}
    print(f"[phase5] threshold @ bottom-{args.drop_bottom_fraction*100:.0f}%: {threshold:.4f}")

    # Decile samples — for `reports/05_quality_filter.md`.
    rng = random.Random(args.seed_rng)
    decile_samples: list[list[tuple[int, float, int, str]]] = []
    for d in range(10):
        lo = int(n_total * d / 10)
        hi = int(n_total * (d + 1) / 10)
        band = scores_sorted[lo:hi]
        decile_samples.append(rng.sample(band, min(args.sample_per_decile, len(band))))

    # Write filtered output.
    print("[phase5] writing filtered output...")
    t2 = time.time()
    score_by_row = {r[0]: r[1] for r in scores}
    per_source_in: Counter = Counter()
    per_source_kept: Counter = Counter()
    decile_texts: dict[int, list[dict]] = {d: [] for d in range(10)}
    decile_lookup: dict[int, tuple[int, float, int, str]] = {}
    for d, band in enumerate(decile_samples):
        for row_idx, s, n_w, src in band:
            decile_lookup[row_idx] = (d, s, n_w, src)

    with in_path.open() as f_in, out_path.open("w", encoding="utf-8") as f_out:
        for i, line in enumerate(f_in):
            rec = json.loads(line)
            per_source_in[rec["source"]] += 1
            # Attach score for metadata
            s = score_by_row.get(i, 0.0)
            if i in decile_lookup:
                d, _, _, _ = decile_lookup[i]
                decile_texts[d].append({"id": rec.get("id"), "source": rec["source"],
                                        "score": round(s, 4), "n_words": rec.get("n_words"),
                                        "snippet": rec["text"][:280]})
            if i in kept_row_idxs:
                rec["quality_score"] = round(s, 4)
                f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                per_source_kept[rec["source"]] += 1
    elapsed = time.time() - t2

    total_in = sum(per_source_in.values())
    total_kept = sum(per_source_kept.values())

    # Report
    lines = [
        f"# Phase 5 — Quality filter (char-{args.ngram_n}-gram coverage)\n",
        f"- Seed: Wikipedia-so articles ≥ {args.min_seed_words} words — {seed_docs:,} docs, ~{seed_tokens:,} tokens, {len(vocab):,} unique {args.ngram_n}-grams",
        f"- Scoring elapsed: {time.time()-t1:.1f}s for {n_total:,} docs",
        f"- Threshold (drop bottom {args.drop_bottom_fraction*100:.0f}%): score={threshold:.4f}",
        f"- Input docs: {total_in:,}",
        f"- Output docs: {total_kept:,}",
        f"- Dropped: {total_in-total_kept:,} ({(total_in-total_kept)/total_in*100:.2f}%)",
        "",
        "## Per-source kept",
        "| Source | Input | Kept | Drop rate |",
        "|---|---:|---:|---:|",
    ]
    for src, pin in per_source_in.items():
        pk = per_source_kept.get(src, 0)
        lines.append(f"| {src} | {pin:,} | {pk:,} | {(1 - pk / pin) * 100:.2f}% |")

    lines.append("\n## Samples by score decile")
    for d in range(10):
        score_lo = scores_sorted[int(n_total * d / 10)][1]
        score_hi = scores_sorted[min(int(n_total * (d + 1) / 10) - 1, n_total - 1)][1]
        kept_flag = "keep" if d >= int(args.drop_bottom_fraction * 10) else "DROP"
        lines.append(f"\n### Decile {d+1} (score range ~{score_lo:.3f}–{score_hi:.3f}) — `{kept_flag}`")
        for t in decile_texts[d]:
            snippet = t["snippet"].replace("\n", " ")
            lines.append(f"\n**{t['source']}** score={t['score']} n_words={t['n_words']}\n\n> {snippet}{'…' if len(t['snippet']) == 280 else ''}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print()
    print("=== Phase 5 summary ===")
    print(f"  input:     {total_in:,}")
    print(f"  output:    {total_kept:,}")
    print(f"  dropped:   {total_in - total_kept:,}")
    print(f"  threshold: {threshold:.4f}")
    print(f"  per source: {dict(per_source_kept)}")
    print(f"  file: {out_path}  ({out_path.stat().st_size/1024/1024:.1f} MB)")
    print(f"  report: {report_path}")


if __name__ == "__main__":
    main()
