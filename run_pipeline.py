#!/usr/bin/env python3
"""Run the full SomaliWeb v1 pipeline (phases 1-6) with one command.

Usage
-----
    python run_pipeline.py                  # run phases 1-6 sequentially
    python run_pipeline.py --from 4         # skip phases 1-3, start at 4
    python run_pipeline.py --to 5           # stop after phase 5
    python run_pipeline.py --from 4 --to 5  # only run phases 4 and 5
    python run_pipeline.py --dry-run        # print the commands, run nothing

The pipeline expects Phase 0 to have already populated:
    data/extracted/wikipedia_so.jsonl
    data/baselines/cc100_so.jsonl
    data/baselines/hplt2_so.jsonl
    data/eval/flores_so.devtest.txt

If any of those are missing, this runner will tell you which Phase 0 script
to invoke. Phase 0 is intentionally NOT auto-run by this script — it does
network I/O and gated downloads, and one of its scripts (``download_baselines.py``)
documents a now-historical OSCAR/MADLAD attempt rather than being a clean fetch.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (phase_num, label, script, hard prerequisites — files that MUST exist before this phase can start)
PHASES: list[tuple[int, str, str, list[str]]] = [
    (1, "merge + byte-exact dedup",
        "pipeline/01_merge_and_dedup.py",
        ["data/extracted/wikipedia_so.jsonl",
         "data/baselines/cc100_so.jsonl",
         "data/baselines/hplt2_so.jsonl"]),
    (2, "clean + normalize + length filter",
        "pipeline/02_clean.py",
        ["data/pipeline/01_merged_dedup.jsonl"]),
    (3, "LID verify + dialect tag",
        "pipeline/03_lid_verify.py",
        ["data/pipeline/02_cleaned.jsonl"]),
    (4, "MinHash + LSH near-dedup",
        "pipeline/04_near_dedup.py",
        ["data/pipeline/03_lid_verified.jsonl"]),
    (5, "char-n-gram quality filter",
        "pipeline/05_quality_filter.py",
        ["data/pipeline/04_near_deduped.jsonl",
         "data/extracted/wikipedia_so.jsonl"]),
    (6, "release structuring + tokenizer + fertility",
        "pipeline/06_structure_release.py",
        ["data/pipeline/05_quality_filtered.jsonl",
         "data/baselines/hplt2_so.jsonl",
         "data/eval/flores_so.devtest.txt"]),
]

PHASE0_HINT = """
Missing Phase 0 prerequisites. Run these first (one-time):

    python phase0_scripts/fetch_wikipedia_so.py
    python phase0_scripts/lid_benchmark.py
    curl -L -o data/downloads/cc100_so.txt.xz   https://data.statmt.org/cc-100/so.txt.xz
    curl -L -o data/downloads/hplt2_so.jsonl.zst https://data.hplt-project.org/two/cleaned/som_Latn/1.jsonl.zst
    python phase0_scripts/convert_cc100.py
    python phase0_scripts/convert_hplt.py
    python phase0_scripts/baseline_overlap_report.py
    python phase0_scripts/fetch_flores.py
"""


def fmt_secs(s: float) -> str:
    if s < 60:
        return f"{s:.1f}s"
    m, sec = divmod(s, 60)
    if m < 60:
        return f"{int(m)}m{sec:.0f}s"
    h, m = divmod(m, 60)
    return f"{int(h)}h{int(m):02d}m"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="start", type=int, default=1,
                   help="phase to start from (1-6, default 1)")
    p.add_argument("--to", dest="end", type=int, default=6,
                   help="phase to stop after (1-6, default 6)")
    p.add_argument("--dry-run", action="store_true",
                   help="print the commands without running them")
    args = p.parse_args()

    if not (1 <= args.start <= args.end <= 6):
        print(f"error: --from {args.start} --to {args.end} out of [1,6] range",
              file=sys.stderr)
        return 2

    selected = [ph for ph in PHASES if args.start <= ph[0] <= args.end]

    # Pre-flight: ensure all hard prerequisites exist for the FIRST phase we run.
    first = selected[0]
    missing = [pre for pre in first[3] if not (ROOT / pre).exists()]
    if missing and not args.dry_run:
        print(f"error: Phase {first[0]} is missing prerequisites:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        if first[0] == 1 or any(m.startswith(("data/extracted", "data/baselines", "data/eval"))
                                for m in missing):
            print(PHASE0_HINT, file=sys.stderr)
        return 1

    print("="*72)
    print(f"SomaliWeb v1 — running phases {args.start}–{args.end}")
    print("="*72)

    total_t0 = time.time()
    for n, label, script, _ in selected:
        cmd = [sys.executable, str(ROOT / script)]
        print(f"\n--- Phase {n}: {label} ---")
        print(f"$ {shlex.join(cmd)}")
        if args.dry_run:
            continue
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        elapsed = time.time() - t0
        if rc != 0:
            print(f"\n[FAIL] Phase {n} exited rc={rc} after {fmt_secs(elapsed)}",
                  file=sys.stderr)
            return rc
        print(f"[ok] Phase {n} done in {fmt_secs(elapsed)}")

    print("\n" + "="*72)
    print(f"Pipeline complete. Total wall time: {fmt_secs(time.time()-total_t0)}")
    print("="*72)
    if args.end == 6:
        print("\nDeliverables:")
        print("  data/release/train.jsonl")
        print("  data/release/validation.jsonl")
        print("  data/release/tokenizer_somaliweb.json")
        print("  reports/06_evaluation.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
