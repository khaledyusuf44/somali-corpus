"""Phase 3 — LID verification.

Run langdetect on each doc from Phase 2 output. Keep only documents where the
top-1 prediction is `so` with probability ≥ min_confidence. Adds `lang_top1`
and `lang_conf` fields. Optionally tags `som_Latn` vs `ymm_Latn` via a second
GlotLID pass on survivors.

Input:   data/pipeline/02_cleaned.jsonl
Output:  data/pipeline/03_lid_verified.jsonl
Report:  reports/03_lid_drops.md
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# langdetect pool worker initialization
def _init_langdetect():
    from langdetect import DetectorFactory
    DetectorFactory.seed = 0


def _langdetect_one(text: str) -> tuple[str, float]:
    from langdetect import detect_langs, LangDetectException
    try:
        t = text.strip()
        if not t:
            return "none", 0.0
        # langdetect uses full text; clip to 2 kB for speed on long docs
        top = detect_langs(t[:2000])[0]
        return top.lang, float(top.prob)
    except LangDetectException:
        return "none", 0.0


def _worker_detect(records: list[dict]) -> list[tuple[dict, str, float]]:
    out = []
    for r in records:
        lang, conf = _langdetect_one(r["text"])
        out.append((r, lang, conf))
    return out


def chunks(it, n: int):
    buf: list = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(ROOT / "data/pipeline/02_cleaned.jsonl"))
    p.add_argument("--out", default=str(ROOT / "data/pipeline/03_lid_verified.jsonl"))
    p.add_argument("--report", default=str(ROOT / "reports/03_lid_drops.md"))
    p.add_argument("--min-conf", type=float, default=0.50)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--chunk-size", type=int, default=512)
    p.add_argument("--dialect-tag-with-glotlid", action="store_true", default=True)
    args = p.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    report_path = Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    def iter_input():
        with in_path.open() as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    n_in = 0
    n_kept = 0
    per_source_in: Counter = Counter()
    per_source_kept: Counter = Counter()
    drop_by_predicted_lang: Counter = Counter()
    drop_by_conf_bucket: Counter = Counter()
    conf_survivors: list[float] = []

    t0 = time.time()
    print(f"[phase3] langdetect verify  workers={args.workers}  chunk={args.chunk_size}")
    # Process in parallel
    with mp.Pool(processes=args.workers, initializer=_init_langdetect) as pool, \
         out_path.open("w", encoding="utf-8") as out_f:
        for batch_out in pool.imap_unordered(_worker_detect, chunks(iter_input(), args.chunk_size)):
            for rec, lang, conf in batch_out:
                n_in += 1
                per_source_in[rec["source"]] += 1
                if lang == "so" and conf >= args.min_conf:
                    rec["lang_top1"] = lang
                    rec["lang_conf"] = round(conf, 4)
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_kept += 1
                    per_source_kept[rec["source"]] += 1
                    conf_survivors.append(conf)
                else:
                    drop_by_predicted_lang[lang] += 1
                    # confidence buckets for kept-language-but-low-conf debugging
                    if lang == "so":
                        drop_by_conf_bucket[f"so_low_conf(<{args.min_conf})"] += 1
                if n_in % 50_000 == 0:
                    print(f"  [phase3] processed {n_in:,}  kept {n_kept:,}  ({time.time()-t0:.1f}s)", flush=True)

    # Optional GlotLID second pass: tag survivors as som_Latn vs ymm_Latn.
    n_som = n_ymm = n_other_dialect = 0
    if args.dialect_tag_with_glotlid:
        print(f"[phase3] tagging dialects with GlotLID on {n_kept:,} survivors...")
        try:
            import fasttext
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model_v3.bin")
            model = fasttext.load_model(model_path)

            # Re-write output with dialect_tag added
            tmp_path = out_path.with_suffix(".tagging.tmp")
            t1 = time.time()
            with out_path.open() as in_f, tmp_path.open("w", encoding="utf-8") as out_f:
                for i, line in enumerate(in_f, 1):
                    rec = json.loads(line)
                    t = rec["text"].replace("\n", " ")[:2000]
                    labels, probs = model.predict(t, k=1)
                    tag = labels[0].replace("__label__", "")
                    rec["dialect_tag"] = tag
                    rec["dialect_conf"] = float(round(probs[0], 4))
                    if tag.startswith("som_"):
                        n_som += 1
                    elif tag.startswith("ymm_"):
                        n_ymm += 1
                    else:
                        n_other_dialect += 1
                    out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    if i % 50_000 == 0:
                        print(f"  [dialect] {i:,}/{n_kept:,}  ({time.time()-t1:.1f}s)", flush=True)
            tmp_path.replace(out_path)
            print(f"[phase3] dialect tagging done in {time.time()-t1:.1f}s: "
                  f"som={n_som:,}  ymm={n_ymm:,}  other={n_other_dialect:,}")
        except Exception as e:
            print(f"[phase3] GlotLID dialect pass FAILED (non-fatal): {e}", file=sys.stderr)

    elapsed = time.time() - t0
    top_drop_langs = drop_by_predicted_lang.most_common(15)

    report_lines = [f"# Phase 3 — LID verification (langdetect, min_conf={args.min_conf})\n"]
    report_lines.append(f"Elapsed: {elapsed:.1f}s with {args.workers} workers\n")
    report_lines.append(f"- Input docs: **{n_in:,}**")
    report_lines.append(f"- Kept docs (top-1=so, conf≥{args.min_conf}): **{n_kept:,}**")
    report_lines.append(f"- Dropped: {n_in - n_kept:,} ({(n_in-n_kept)/n_in*100:.2f}%)\n")
    report_lines.append("## Per-source kept")
    report_lines.append("| Source | Input | Kept | Drop rate |")
    report_lines.append("|---|---:|---:|---:|")
    for src in per_source_in:
        pin = per_source_in[src]
        pk = per_source_kept.get(src, 0)
        rate = (1 - pk / pin) * 100 if pin else 0.0
        report_lines.append(f"| {src} | {pin:,} | {pk:,} | {rate:.2f}% |")
    report_lines.append("\n## Top 15 languages among dropped docs")
    report_lines.append("| predicted lang | count |")
    report_lines.append("|---|---:|")
    for lang, n in top_drop_langs:
        report_lines.append(f"| `{lang}` | {n:,} |")
    if drop_by_conf_bucket:
        report_lines.append("\n## Low-confidence Somali drops")
        for bucket, n in drop_by_conf_bucket.items():
            report_lines.append(f"- {bucket}: {n:,}")
    if args.dialect_tag_with_glotlid and (n_som + n_ymm + n_other_dialect):
        total_tagged = n_som + n_ymm + n_other_dialect
        report_lines.append("\n## Dialect tagging (GlotLID second pass on survivors)")
        report_lines.append(f"- `som_Latn`: {n_som:,} ({n_som/total_tagged*100:.2f}%)")
        report_lines.append(f"- `ymm_Latn`: {n_ymm:,} ({n_ymm/total_tagged*100:.2f}%)")
        report_lines.append(f"- other tag: {n_other_dialect:,} (langdetect said 'so' but GlotLID disagreed)")

    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print()
    print("=== Phase 3 summary ===")
    print(f"  input:  {n_in:,}   kept: {n_kept:,}   drop: {(n_in-n_kept)/n_in*100:.2f}%")
    print(f"  per source kept: {dict(per_source_kept)}")
    print(f"  top drop languages: {top_drop_langs[:5]}")
    print(f"  file: {out_path}  ({out_path.stat().st_size/1024/1024:.1f} MB)")
    print(f"  report: {report_path}")
    print(f"  elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
