"""Convert downloaded CC100-so (text.xz) to our JSONL format.

CC100 format: one paragraph per line, documents separated by blank lines.
We treat each blank-line-separated block as one document.
"""

from __future__ import annotations

import json
import lzma
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/downloads/cc100_so.txt.xz"
OUT = ROOT / "data/baselines/cc100_so.jsonl"


def bucket_words(n: int) -> str:
    if n < 50: return "<50w"
    if n < 200: return "50-199w"
    if n < 1000: return "200-999w"
    if n < 5000: return "1k-5kw"
    return ">=5kw"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_docs = 0
    n_chars = 0
    n_words = 0
    buckets: Counter = Counter()
    t0 = time.time()

    current_doc: list[str] = []
    with lzma.open(SRC, "rt", encoding="utf-8") as f, OUT.open("w", encoding="utf-8") as out:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() == "":
                if current_doc:
                    text = "\n".join(current_doc)
                    rec = {"id": f"cc100-so_{n_docs}", "source": "cc100-so", "text": text}
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_docs += 1
                    n_chars += len(text)
                    w = len(text.split())
                    n_words += w
                    buckets[bucket_words(w)] += 1
                    if n_docs % 20_000 == 0:
                        print(f"  {n_docs:,} docs  ({time.time()-t0:.1f}s)", flush=True)
                    current_doc = []
            else:
                current_doc.append(line)
        # trailing doc
        if current_doc:
            text = "\n".join(current_doc)
            rec = {"id": f"cc100-so_{n_docs}", "source": "cc100-so", "text": text}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_docs += 1
            n_chars += len(text)
            n_words += len(text.split())
            buckets[bucket_words(len(text.split()))] += 1

    elapsed = time.time() - t0
    print(f"\n[cc100] docs written:   {n_docs:,}")
    print(f"[cc100] chars:           {n_chars:,}")
    print(f"[cc100] whitespace words: {n_words:,}")
    print(f"[cc100] approx tokens:   {int(n_words * 1.3):,}")
    print(f"[cc100] length buckets:  {dict(buckets)}")
    print(f"[cc100] output file size: {OUT.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"[cc100] elapsed:         {elapsed:.1f}s")
    print(f"[cc100] -> {OUT}")


if __name__ == "__main__":
    main()
