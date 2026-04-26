"""Convert downloaded HPLT 2.0 cleaned Somali (jsonl.zst) to our JSONL format.

HPLT's records carry more fields than we need (doc_scores, lang_scores,
register, etc). We keep {id, source, text, url, collection} for provenance
and drop the rest; the full record is recoverable from the original file.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import zstandard as zstd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/downloads/hplt2_so.jsonl.zst"
OUT = ROOT / "data/baselines/hplt2_so.jsonl"


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
    fields_seen: set[str] = set()
    t0 = time.time()

    dctx = zstd.ZstdDecompressor(max_window_size=2**31)
    with SRC.open("rb") as src_f, OUT.open("w", encoding="utf-8") as out_f:
        with dctx.stream_reader(src_f) as stream, \
             open(stream.fileno() if False else "/dev/null", "rb") as _:
            pass  # placeholder — switch to line iteration below
    # Re-open properly
    with SRC.open("rb") as src_f, OUT.open("w", encoding="utf-8") as out_f:
        reader = zstd.ZstdDecompressor(max_window_size=2**31).stream_reader(src_f)
        # Wrap in a text stream
        import io
        text_stream = io.TextIOWrapper(reader, encoding="utf-8")
        for line in text_stream:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = r.get("text") or r.get("content") or ""
            if not text.strip():
                continue
            fields_seen.update(r.keys())
            rec = {
                "id": f"hplt2-so_{n_docs}",
                "source": "hplt2-so",
                "text": text,
            }
            for passthrough in ("url", "collection", "warc_date", "lang"):
                if passthrough in r and r[passthrough]:
                    rec[passthrough] = r[passthrough]
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_docs += 1
            n_chars += len(text)
            w = len(text.split())
            n_words += w
            buckets[bucket_words(w)] += 1
            if n_docs % 10_000 == 0:
                print(f"  {n_docs:,} docs  ({time.time()-t0:.1f}s)", flush=True)

    elapsed = time.time() - t0
    print(f"\n[hplt2] docs written:   {n_docs:,}")
    print(f"[hplt2] chars:           {n_chars:,}")
    print(f"[hplt2] whitespace words: {n_words:,}")
    print(f"[hplt2] approx tokens:   {int(n_words * 1.3):,}")
    print(f"[hplt2] length buckets:  {dict(buckets)}")
    print(f"[hplt2] source fields seen: {sorted(fields_seen)}")
    print(f"[hplt2] output file size: {OUT.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"[hplt2] elapsed:         {elapsed:.1f}s")
    print(f"[hplt2] -> {OUT}")


if __name__ == "__main__":
    main()
