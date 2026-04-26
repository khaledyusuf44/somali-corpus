"""Phase 2 — clean + normalize.

Input:
  data/pipeline/01_merged_dedup.jsonl    (Phase 1 output, 1.18M docs)

What it does:
  1. Mojibake fix via ftfy (esp. for CC100's â€™ / Ã© artifacts).
  2. Whitespace collapse.
  3. Strip repeated-char runs longer than 3 (e.g. "hellooooo" -> "hellooo").
  4. Drop docs shorter than `min_words_after_clean` (default 50).

Output:
  data/pipeline/02_cleaned.jsonl
  reports/02_clean_stats.json

The cleaning is deliberately conservative — aggressive HTML stripping or
punctuation removal lives in Phase 5's quality filter, not here. Phase 2
should preserve the text a human reader would recognize.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import ftfy

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "data/pipeline/01_merged_dedup.jsonl"
DEFAULT_OUT = ROOT / "data/pipeline/02_cleaned.jsonl"
DEFAULT_REPORT = ROOT / "reports/02_clean_stats.json"

_WS = re.compile(r"\s+")
_REPEATED_CHAR = re.compile(r"(.)\1{3,}")  # 4+ identical chars -> keep 3


def clean_text(text: str) -> tuple[str, dict[str, bool]]:
    """Clean a single text. Returns (cleaned, flags dict showing what fired)."""
    flags = {"mojibake_fixed": False, "repeated_char_collapsed": False}

    fixed = ftfy.fix_text(text)
    if fixed != text:
        flags["mojibake_fixed"] = True

    # Collapse any run of 4+ same char (punct or letter) down to 3
    before = fixed
    fixed = _REPEATED_CHAR.sub(lambda m: m.group(1) * 3, fixed)
    if fixed != before:
        flags["repeated_char_collapsed"] = True

    # Whitespace — collapse internal runs but preserve paragraph breaks.
    lines = [_WS.sub(" ", line).strip() for line in fixed.splitlines()]
    fixed = "\n".join(line for line in lines if line)

    return fixed, flags


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(DEFAULT_IN))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--min-words", type=int, default=50,
                   help="drop docs with fewer than this many whitespace-separated words")
    args = p.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    n_in = 0
    n_kept = 0
    n_mojibake_fixed = 0
    n_repeated_char = 0
    drops: defaultdict[str, int] = defaultdict(int)
    per_source_in: defaultdict[str, int] = defaultdict(int)
    per_source_kept: defaultdict[str, int] = defaultdict(int)
    per_source_mojibake: defaultdict[str, int] = defaultdict(int)

    t0 = time.time()
    with in_path.open("r", encoding="utf-8") as in_f, \
         out_path.open("w", encoding="utf-8") as out_f:
        for line in in_f:
            rec = json.loads(line)
            n_in += 1
            source = rec["source"]
            per_source_in[source] += 1

            cleaned, flags = clean_text(rec["text"])
            if flags["mojibake_fixed"]:
                n_mojibake_fixed += 1
                per_source_mojibake[source] += 1
            if flags["repeated_char_collapsed"]:
                n_repeated_char += 1

            n_words = len(cleaned.split())
            if n_words < args.min_words:
                drops["too_short"] += 1
                continue
            if not cleaned:
                drops["empty_after_clean"] += 1
                continue

            rec["text"] = cleaned
            rec["n_words"] = n_words
            rec["n_chars"] = len(cleaned)
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_kept += 1
            per_source_kept[source] += 1

            if n_in % 100_000 == 0:
                print(f"  processed {n_in:,}  kept {n_kept:,}  "
                      f"mojibake-fixed {n_mojibake_fixed:,}  "
                      f"({time.time()-t0:.1f}s)", flush=True)

    elapsed = time.time() - t0
    out_mb = out_path.stat().st_size / 1024 / 1024
    report = {
        "phase": "02_clean",
        "elapsed_s": round(elapsed, 1),
        "min_words_threshold": args.min_words,
        "input_docs": n_in,
        "output_docs": n_kept,
        "drop_total": n_in - n_kept,
        "drop_rate": round((n_in - n_kept) / n_in, 4) if n_in else 0.0,
        "drops_by_reason": dict(drops),
        "mojibake_fixed_docs": n_mojibake_fixed,
        "mojibake_fixed_fraction": round(n_mojibake_fixed / n_in, 4) if n_in else 0.0,
        "mojibake_fixed_by_source": dict(per_source_mojibake),
        "repeated_char_runs_collapsed_docs": n_repeated_char,
        "per_source_input": dict(per_source_in),
        "per_source_kept": dict(per_source_kept),
        "output_file": str(out_path),
        "output_file_mb": round(out_mb, 2),
    }
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)

    print()
    print("=== Phase 2 summary ===")
    print(f"  input  docs:  {n_in:,}")
    print(f"  output docs:  {n_kept:,}")
    print(f"  dropped:      {n_in - n_kept:,}  ({report['drop_rate']*100:.2f}%)")
    for reason, n in drops.items():
        print(f"    {reason}: {n:,}")
    print(f"  mojibake-fixed docs: {n_mojibake_fixed:,}  ({report['mojibake_fixed_fraction']*100:.2f}%)")
    print(f"    by source: {dict(per_source_mojibake)}")
    print(f"  file: {out_path}  ({out_mb:.1f} MB)")
    print(f"  elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
