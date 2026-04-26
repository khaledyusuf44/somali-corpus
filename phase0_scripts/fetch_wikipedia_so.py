"""Phase 0.1: pull Somali Wikipedia into a JSONL file.

Uses HuggingFace's `wikimedia/wikipedia` dataset (cleanly parsed — no wiki-markup
residue, no templates, no citation footers). One JSON record per article:

    {"id": "wiki_so_<n>", "source": "wikipedia-so", "url": ..., "title": ..., "text": ...}

Prints a summary with article count, character total, and a rough token estimate.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/extracted/wikipedia_so.jsonl"

# HF `wikimedia/wikipedia` config names are `<snapshot>.<lang>`. Use the most
# recent snapshot that has a Somali build; 2023-11-01 is the current stable one.
CONFIG = "20231101.so"


def main() -> None:
    from datasets import load_dataset  # lazy, heavy import

    print(f"[wiki-so] loading {CONFIG} from HF...")
    ds = load_dataset("wikimedia/wikipedia", CONFIG, split="train")
    print(f"[wiki-so] articles: {len(ds):,}")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    n_chars = 0
    n_words = 0
    length_buckets = {"<200w": 0, "200-1k": 0, "1k-5k": 0, ">5k": 0}

    with OUT.open("w", encoding="utf-8") as f:
        for r in ds:
            text = r["text"]
            rec = {
                "id": f"wiki_so_{r['id']}",
                "source": "wikipedia-so",
                "url": r["url"],
                "title": r["title"],
                "text": text,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_chars += len(text)
            w = len(text.split())
            n_words += w
            if w < 200:
                length_buckets["<200w"] += 1
            elif w < 1000:
                length_buckets["200-1k"] += 1
            elif w < 5000:
                length_buckets["1k-5k"] += 1
            else:
                length_buckets[">5k"] += 1

    # Rough token estimate: whitespace words × 1.3 (English rule of thumb,
    # slightly off for Somali morphology but gives a useful ballpark).
    approx_tokens = int(n_words * 1.3)

    print(f"[wiki-so] wrote -> {OUT}")
    print(f"[wiki-so] file size: {OUT.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"[wiki-so] total chars: {n_chars:,}")
    print(f"[wiki-so] total whitespace words: {n_words:,}")
    print(f"[wiki-so] approx tokens (words * 1.3): {approx_tokens:,}")
    print(f"[wiki-so] length distribution: {length_buckets}")


if __name__ == "__main__":
    main()
