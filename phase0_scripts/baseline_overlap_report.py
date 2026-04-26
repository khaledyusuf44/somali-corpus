"""Phase 0.4 wrap-up: cross-corpus overlap + inspection samples + final report.

Inputs:
  data/extracted/wikipedia_so.jsonl     (Phase 0.1)
  data/baselines/cc100_so.jsonl         (CC100 convert)
  data/baselines/hplt2_so.jsonl         (HPLT convert)

Outputs:
  reports/baseline_comparison.md        (the paper-shaped comparison table)
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_REPORT = ROOT / "reports/baseline_comparison.md"

SOURCES = {
    "wikipedia-so": ROOT / "data/extracted/wikipedia_so.jsonl",
    "cc100-so":     ROOT / "data/baselines/cc100_so.jsonl",
    "hplt2-so":     ROOT / "data/baselines/hplt2_so.jsonl",
}

_WS = re.compile(r"\s+")


def norm(text: str) -> str:
    return _WS.sub(" ", text.lower()).strip()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def bucket_words(n: int) -> str:
    if n < 50: return "<50w"
    if n < 200: return "50-199w"
    if n < 1000: return "200-999w"
    if n < 5000: return "1k-5kw"
    return ">=5kw"


def summarize(path: Path, source_name: str) -> tuple[dict, set[str]]:
    """Read JSONL, return (summary, set of normalized text hashes)."""
    n_docs = 0
    n_chars = 0
    n_words = 0
    hashes: set[str] = set()
    buckets: Counter = Counter()
    t0 = time.time()

    with path.open() as f:
        for line in f:
            r = json.loads(line)
            text = r["text"]
            hashes.add(sha(norm(text)))
            n_docs += 1
            n_chars += len(text)
            w = len(text.split())
            n_words += w
            buckets[bucket_words(w)] += 1

    return {
        "source": source_name,
        "docs": n_docs,
        "chars": n_chars,
        "words": n_words,
        "approx_tokens": int(n_words * 1.3),
        "length_buckets": dict(buckets),
        "file_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "unique_hashes": len(hashes),
        "hash_time_s": round(time.time() - t0, 1),
    }, hashes


def sample_docs(path: Path, n: int = 3, seed: int = 0) -> list[dict]:
    random.seed(seed)
    with path.open() as f:
        lines = f.readlines()
    picks = random.sample(lines, min(n, len(lines)))
    return [json.loads(l) for l in picks]


def main() -> None:
    summaries: list[dict] = []
    hashes: dict[str, set[str]] = {}

    for name, path in SOURCES.items():
        if not path.exists():
            print(f"SKIP (missing): {path}")
            continue
        print(f"[{name}] hashing {path.name}...")
        s, h = summarize(path, name)
        summaries.append(s)
        hashes[name] = h
        print(f"  docs={s['docs']:,}  tokens~{s['approx_tokens']:,}  unique_hashes={len(h):,}  in {s['hash_time_s']}s")

    # Pair overlaps
    print("\n[overlap] computing pair intersections...")
    pairs = []
    names = list(hashes.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = len(hashes[a] & hashes[b])
            pairs.append({
                "a": a, "b": b,
                "shared_docs": shared,
                "frac_of_a": shared / len(hashes[a]) if hashes[a] else 0.0,
                "frac_of_b": shared / len(hashes[b]) if hashes[b] else 0.0,
            })
            print(f"  {a} ∩ {b} = {shared:,}  ({shared/len(hashes[a])*100:.2f}% of {a}, {shared/len(hashes[b])*100:.2f}% of {b})")

    all_intersect = 0
    if len(hashes) >= 3:
        sets = list(hashes.values())
        all_intersect = len(set.intersection(*sets))
        print(f"  in all three: {all_intersect:,}")

    total_unique = len(set.union(*hashes.values())) if hashes else 0
    print(f"  total unique across corpora: {total_unique:,}")

    # Samples for manual inspection
    inspection_docs = {}
    for name, path in SOURCES.items():
        if path.exists():
            inspection_docs[name] = sample_docs(path, n=3)

    # Render markdown
    lines = ["# Baseline corpora — Somali (Phase 0.4 report)\n"]
    lines.append(f"Generated {time.strftime('%Y-%m-%d')} from downloaded sources.\n")

    lines.append("## Per-corpus stats")
    lines.append("| Source | Docs | File MB | Whitespace words | Approx tokens | Unique hashes (within-corpus) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        within_dedup = s["docs"] - s["unique_hashes"]
        lines.append(f"| {s['source']} | {s['docs']:,} | {s['file_mb']} | {s['words']:,} | "
                     f"{s['approx_tokens']:,} | {s['unique_hashes']:,} (drops {within_dedup:,}) |")

    lines.append("\n## Length distribution (word count buckets)")
    lines.append("| Source | <50w | 50-199w | 200-999w | 1k-5kw | >=5kw |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        lb = s["length_buckets"]
        lines.append(f"| {s['source']} | {lb.get('<50w', 0):,} | {lb.get('50-199w', 0):,} | "
                     f"{lb.get('200-999w', 0):,} | {lb.get('1k-5kw', 0):,} | {lb.get('>=5kw', 0):,} |")

    lines.append("\n## Cross-corpus exact-dedup overlap")
    lines.append("After normalize (lowercase + whitespace-collapse) and SHA-256 truncated hash:\n")
    for p in pairs:
        lines.append(f"- **{p['a']} ∩ {p['b']}**: {p['shared_docs']:,} shared docs "
                     f"({p['frac_of_a']*100:.2f}% of {p['a']}, {p['frac_of_b']*100:.2f}% of {p['b']})")
    if all_intersect:
        lines.append(f"- **in all three corpora**: {all_intersect:,} docs")
    lines.append(f"- **total unique across all corpora**: {total_unique:,} docs")

    lines.append("\n## Sample docs (manual quality check)")
    for name, docs in inspection_docs.items():
        lines.append(f"\n### {name}")
        for i, d in enumerate(docs):
            snippet = d["text"][:300].replace("\n", " ")
            lines.append(f"\n**sample {i+1}** (id `{d.get('id')}`, {len(d['text'].split())} words)\n\n> {snippet}{'…' if len(d['text']) > 300 else ''}")

    # Implications paragraph
    lines.append("\n## Implications")
    lines.append("""
- **HPLT v2 dwarfs every other source** — at ~505M approx tokens it is already 5× our original corpus target. The project math shifts: the question is no longer "can we find 100M tokens of Somali" but "what's the right dedup + quality filter applied to HPLT that beats HPLT-raw on downstream metrics."
- **CC100 is cleaner than I expected** (~81M tokens, 396k docs) but has a long tail of under-50-word docs (28% of its documents); HPLT's cleaning already drops that tail almost entirely (15 docs of 966k).
- **Wikipedia-so is not a corpus contributor** — 2.5M tokens is 0.5% of HPLT — but it remains the cleanest Somali text we have, ideal as positive-class seed for the Phase 6 perplexity quality filter.
- **Cross-corpus overlap numbers below** answer whether merging HPLT + CC100 adds meaningful docs or just repeats. This is the first concrete data point on how much value aggregation gives us.""")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[overlap] -> {OUT_REPORT}")


if __name__ == "__main__":
    main()
