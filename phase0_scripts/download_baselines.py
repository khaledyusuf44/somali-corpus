"""Phase 0.4: download and characterize three pre-filtered Somali corpora.

These are our PRIMARY CC-derived sources — OSCAR, MADLAD, and CC100 each
scanned hundreds of Common Crawl snapshots and ran their own language ID, so
we inherit their work instead of re-scanning 20 GB of raw WET for ~5 MB of
Somali.

Per corpus we write `data/baselines/<name>_so.jsonl` with one JSON record per
document: {id, source, text}. We also report doc count, character total,
approximate tokens, and a length distribution.

Cross-corpus byte-level overlap is computed in a second pass once all three
are on disk.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data/baselines"
REPORT_OUT = ROOT / "reports/baseline_comparison.md"


def bucket_words(n: int) -> str:
    if n < 50: return "<50w"
    if n < 200: return "50-199w"
    if n < 1000: return "200-999w"
    if n < 5000: return "1k-5kw"
    return ">=5kw"


def write_jsonl_from_stream(stream, out_path: Path, source_name: str,
                            text_field: str = "text",
                            id_field: str | None = None,
                            limit: int | None = None) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_docs = 0
    n_chars = 0
    n_words = 0
    buckets: Counter = Counter()
    t0 = time.time()
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(stream):
            if limit is not None and i >= limit:
                break
            text = r.get(text_field) or ""
            if not text.strip():
                continue
            rec_id = str(r.get(id_field) or f"{source_name}_{i}") if id_field else f"{source_name}_{i}"
            rec = {"id": rec_id, "source": source_name, "text": text}
            # keep a subset of source-specific fields when available
            for passthrough in ("url", "warc_date", "timestamp"):
                if passthrough in r and r[passthrough]:
                    rec[passthrough] = r[passthrough]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_docs += 1
            n_chars += len(text)
            w = len(text.split())
            n_words += w
            buckets[bucket_words(w)] += 1
            if n_docs % 10_000 == 0:
                print(f"    [{source_name}] {n_docs:,} docs written "
                      f"({time.time()-t0:.1f}s elapsed)", flush=True)
    elapsed = time.time() - t0
    return {
        "source": source_name,
        "docs": n_docs,
        "chars": n_chars,
        "words": n_words,
        "approx_tokens": int(n_words * 1.3),
        "length_buckets": dict(buckets),
        "file_mb": round(out_path.stat().st_size / 1024 / 1024, 2),
        "elapsed_s": round(elapsed, 2),
    }


# ---------- per-corpus loaders ----------
# Each returns (stream_iterable, source_name, text_field, id_field) or raises.

def load_oscar_so():
    """OSCAR 23.01 / 22.01 / 21.09 in order of preference."""
    from datasets import load_dataset
    attempts = [
        ("oscar-corpus/OSCAR-2301", {"language": "so", "split": "train", "trust_remote_code": True}),
        ("oscar-corpus/OSCAR-2201", {"language": "so", "split": "train", "trust_remote_code": True}),
        ("oscar-corpus/OSCAR-2109", {"language": "so", "split": "train", "trust_remote_code": True}),
        ("oscar",                   {"name": "unshuffled_deduplicated_so", "split": "train",
                                     "trust_remote_code": True}),
    ]
    last_err = None
    for repo, kwargs in attempts:
        try:
            print(f"  [oscar] trying {repo} {kwargs}")
            ds = load_dataset(repo, **kwargs, streaming=True)
            # record a 'content' field for OSCAR-2301 / 'text' for others
            def stream():
                for r in ds:
                    text = r.get("text") or r.get("content") or ""
                    yield {"text": text, "id": r.get("id")}
            return stream(), f"oscar-{repo.rsplit('-', 1)[-1].split('/')[-1]}", "text", "id"
        except Exception as e:
            print(f"  [oscar] {repo} failed: {e}")
            last_err = e
    raise RuntimeError(f"all OSCAR loaders failed; last error: {last_err}")


def load_madlad_so():
    from datasets import load_dataset
    # MADLAD-400 config is language code; "clean" split vs "noisy" split
    attempts = [
        ("allenai/MADLAD-400", "so", "clean"),
        ("allenai/MADLAD-400", "so", "noisy"),
    ]
    last_err = None
    for repo, config, split in attempts:
        try:
            print(f"  [madlad] trying {repo} config={config} split={split}")
            ds = load_dataset(repo, config, split=split, streaming=True, trust_remote_code=True)
            def stream():
                for r in ds:
                    yield {"text": r.get("text") or "", "id": r.get("id")}
            return stream(), f"madlad-so-{split}", "text", "id"
        except Exception as e:
            print(f"  [madlad] {repo} {split} failed: {e}")
            last_err = e
    raise RuntimeError(f"MADLAD loader failed; last error: {last_err}")


def load_cc100_so():
    from datasets import load_dataset
    attempts = [
        ("statmt/cc100", "so"),
        ("cc100",        "so"),
    ]
    last_err = None
    for repo, lang in attempts:
        try:
            print(f"  [cc100] trying {repo} lang={lang}")
            ds = load_dataset(repo, lang=lang, split="train", streaming=True, trust_remote_code=True)
            def stream():
                for r in ds:
                    yield {"text": r.get("text") or ""}
            return stream(), "cc100-so", "text", None
        except Exception as e:
            print(f"  [cc100] {repo} failed: {e}")
            last_err = e
    raise RuntimeError(f"CC100 loader failed; last error: {last_err}")


# ---------- cross-corpus overlap ----------

def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def cross_overlap(paths: dict[str, Path]) -> dict:
    """Report byte-level exact doc overlap between the three corpora after
    whitespace-collapse + lowercase. Answers: how much do they share?"""
    import re
    ws = re.compile(r"\s+")

    def norm(t: str) -> str:
        return ws.sub(" ", t.lower()).strip()

    hash_to_sources: dict[str, set[str]] = {}
    per_source_hashes: dict[str, set[str]] = {}
    for source, path in paths.items():
        seen: set[str] = set()
        with path.open() as f:
            for line in f:
                r = json.loads(line)
                h = sha_text(norm(r["text"]))
                seen.add(h)
                hash_to_sources.setdefault(h, set()).add(source)
        per_source_hashes[source] = seen

    # Pair overlap
    sources = list(paths.keys())
    pair_overlap = {}
    for i, a in enumerate(sources):
        for b in sources[i+1:]:
            shared = len(per_source_hashes[a] & per_source_hashes[b])
            pair_overlap[f"{a} ∩ {b}"] = {
                "shared_docs": shared,
                f"{a}_total": len(per_source_hashes[a]),
                f"{b}_total": len(per_source_hashes[b]),
            }
    all3 = len(set.intersection(*per_source_hashes.values())) if len(per_source_hashes) >= 3 else 0
    union = len(set.union(*per_source_hashes.values())) if per_source_hashes else 0
    return {
        "per_source_distinct_docs": {k: len(v) for k, v in per_source_hashes.items()},
        "pair_overlap": pair_overlap,
        "in_all_three": all3,
        "total_unique_across_corpora": union,
    }


# ---------- main ----------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    paths: dict[str, Path] = {}

    loaders = [
        ("oscar",  load_oscar_so),
        ("madlad", load_madlad_so),
        ("cc100",  load_cc100_so),
    ]

    for nick, loader in loaders:
        print(f"\n=== downloading {nick} ===")
        try:
            stream, source_name, text_field, id_field = loader()
            out_path = OUT_DIR / f"{nick}_so.jsonl"
            summary = write_jsonl_from_stream(stream, out_path, source_name,
                                              text_field=text_field, id_field=id_field)
            summaries.append(summary)
            paths[nick] = out_path
            print(f"  done: {summary['docs']:,} docs, {summary['file_mb']} MB, "
                  f"~{summary['approx_tokens']:,} tokens")
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            summaries.append({"source": nick, "error": str(e)})

    # Cross-corpus overlap (only if at least 2 succeeded)
    overlap = None
    alive = {k: v for k, v in paths.items() if v.exists() and v.stat().st_size > 0}
    if len(alive) >= 2:
        print("\n=== cross-corpus exact-dedup overlap ===")
        overlap = cross_overlap(alive)
        print(json.dumps(overlap, indent=2))

    # Markdown report
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Baseline corpora — Somali (Phase 0.4)\n"]
    lines.append("Downloaded and characterized on " + time.strftime("%Y-%m-%d") + ".\n")
    lines.append("| Source | Docs | MB | Words | Approx tokens | Length distribution |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for s in summaries:
        if "error" in s:
            lines.append(f"| {s['source']} | — | — | — | — | FAILED: {s['error']} |")
        else:
            lines.append(f"| {s['source']} | {s['docs']:,} | {s['file_mb']} | "
                         f"{s['words']:,} | {s['approx_tokens']:,} | {s['length_buckets']} |")

    if overlap:
        lines.append("\n## Cross-corpus exact-dedup overlap\n")
        lines.append("After normalize (lowercase + whitespace collapse), SHA-256 dedup:\n")
        lines.append(f"- Total unique docs across corpora: **{overlap['total_unique_across_corpora']:,}**")
        lines.append(f"- In all three corpora: {overlap['in_all_three']:,}")
        for pair, info in overlap['pair_overlap'].items():
            lines.append(f"- `{pair}`: {info['shared_docs']:,} shared docs")

    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[baselines] summary -> {REPORT_OUT}")


if __name__ == "__main__":
    main()
