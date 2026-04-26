"""Phase 1 — merge three source corpora + exact-dedup in a single streaming pass.

Input  (from Phase 0):
  data/extracted/wikipedia_so.jsonl        9,021 docs, ~2.5M tokens
  data/baselines/cc100_so.jsonl          396,524 docs, ~81M tokens
  data/baselines/hplt2_so.jsonl          966,507 docs, ~505M tokens

Output:
  data/pipeline/01_merged_dedup.jsonl    unified schema {id, source, text[, url]}

Dedup rule:
  - Byte-identical after normalize_for_hash (lowercase + whitespace collapse).
  - First-seen wins. Sources are processed in the order:
        wikipedia-so  →  cc100-so  →  hplt2-so
    so if the same doc appears in multiple corpora, Wikipedia wins over CC100
    wins over HPLT. Rationale: Wikipedia is cleanest; CC100 predates HPLT.

Expected (from baseline stats):
  1,372,052 raw docs  →  ~1,182,000 after exact dedup (~190K drops).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.normalize import normalize_for_hash, short_hash  # noqa: E402


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            yield json.loads(line)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=str(ROOT / "configs/pipeline.yaml"))
    p.add_argument("--out", default=str(ROOT / "data/pipeline/01_merged_dedup.jsonl"))
    p.add_argument("--report", default=str(ROOT / "reports/01_merge_stats.json"))
    args = p.parse_args()

    # Processing order locks first-seen preference when hashes collide across sources.
    sources = [
        (ROOT / "data/extracted/wikipedia_so.jsonl", "wikipedia-so"),
        (ROOT / "data/baselines/cc100_so.jsonl",     "cc100-so"),
        (ROOT / "data/baselines/hplt2_so.jsonl",     "hplt2-so"),
    ]

    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # hash -> (source, doc_id) of the first-seen doc carrying that hash
    seen: dict[str, tuple[str, str]] = {}

    kept = 0
    per_source_in: defaultdict[str, int] = defaultdict(int)
    per_source_kept: defaultdict[str, int] = defaultdict(int)
    per_source_within_dup: defaultdict[str, int] = defaultdict(int)
    per_source_cross_dup: defaultdict[str, int] = defaultdict(int)

    t0 = time.time()
    with out_path.open("w", encoding="utf-8") as out_f:
        for path, source_name in sources:
            if not path.exists():
                print(f"[WARN] missing {path}, skipping {source_name}", file=sys.stderr)
                continue
            t_src_start = time.time()
            for rec in iter_jsonl(path):
                per_source_in[source_name] += 1
                text = rec.get("text") or ""
                if not text.strip():
                    continue

                h = short_hash(normalize_for_hash(text))
                if h in seen:
                    prev_source, _ = seen[h]
                    if prev_source == source_name:
                        per_source_within_dup[source_name] += 1
                    else:
                        per_source_cross_dup[source_name] += 1
                    continue

                seen[h] = (source_name, rec.get("id") or f"{source_name}_{per_source_in[source_name]}")

                out_rec = {
                    "id": rec.get("id") or f"{source_name}_{per_source_in[source_name]}",
                    "source": source_name,
                    "text": text,
                }
                for passthrough in ("url", "title", "collection"):
                    if passthrough in rec and rec[passthrough]:
                        out_rec[passthrough] = rec[passthrough]
                out_f.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                kept += 1
                per_source_kept[source_name] += 1

                if per_source_in[source_name] % 100_000 == 0:
                    print(f"  [{source_name}] read {per_source_in[source_name]:,}  "
                          f"kept {per_source_kept[source_name]:,}  "
                          f"({time.time()-t_src_start:.1f}s)", flush=True)
            print(f"  [{source_name}] done in {time.time()-t_src_start:.1f}s: "
                  f"read {per_source_in[source_name]:,}, "
                  f"kept {per_source_kept[source_name]:,}, "
                  f"within-dup {per_source_within_dup[source_name]:,}, "
                  f"cross-dup {per_source_cross_dup[source_name]:,}")

    total_in = sum(per_source_in.values())
    total_within = sum(per_source_within_dup.values())
    total_cross = sum(per_source_cross_dup.values())

    out_mb = out_path.stat().st_size / 1024 / 1024

    report = {
        "phase": "01_merge_and_dedup",
        "elapsed_s": round(time.time() - t0, 1),
        "total_input_docs": total_in,
        "total_output_docs": kept,
        "total_drops": total_in - kept,
        "drop_rate": round((total_in - kept) / total_in, 4) if total_in else 0.0,
        "within_source_dup_drops": dict(per_source_within_dup),
        "cross_source_dup_drops": dict(per_source_cross_dup),
        "per_source_input": dict(per_source_in),
        "per_source_kept": dict(per_source_kept),
        "output_file": str(out_path),
        "output_file_mb": round(out_mb, 2),
    }

    with report_path.open("w") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"=== Phase 1 summary ===")
    print(f"  input  docs:  {total_in:,}")
    print(f"  output docs:  {kept:,}")
    print(f"  dropped:      {total_in - kept:,}  ({report['drop_rate']*100:.2f}%)")
    print(f"    within-source: {total_within:,}")
    print(f"    cross-source:  {total_cross:,}")
    print(f"  per source kept: {dict(per_source_kept)}")
    print(f"  file: {out_path} ({out_mb:.1f} MB)")
    print(f"  report: {report_path}")
    print(f"  elapsed: {report['elapsed_s']}s")


if __name__ == "__main__":
    main()
