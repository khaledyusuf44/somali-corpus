"""Phase 0.2: benchmark three LID models on our language-id-practice test set.

Models:
  - fastText lid.176 (baseline — expected catastrophic on Somali per prior work)
  - langdetect (expected strong on Somali per prior in-house measurement)
  - GlotLID v3 (candidate primary for the corpus pipeline)

Test set:
  - ../language-id-practice/data/multilingual_samples.csv
    5 languages (en, so, ar, fr, sw), 40 rows per language, 200 rows total.
    Covers clean / short / noisy / code-switched text bands.

Reports: per-language precision/recall + confusion matrix + throughput (docs/sec)
for each model. Writes reports/lid_comparison.md.
"""

from __future__ import annotations

import csv
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

# Suppress fastText's warning about deprecated functions; it's noisy.
os.environ["FASTTEXT_LOAD_NO_WARN"] = "1"

ROOT = Path(__file__).resolve().parent.parent
TEST_SET = ROOT.parent / "language-id-practice/data/multilingual_samples.csv"
MODELS_DIR = ROOT / "models"
REPORT_OUT = ROOT / "reports/lid_comparison.md"

# Normalize labels back to the {en, so, ar, fr, sw} vocabulary of the test set.
# Anything unrecognized is kept verbatim as "other_<label>" for confusion matrix.
FIVE_LANGS = {"en", "so", "ar", "fr", "sw"}


def norm_label(label: str) -> str:
    """Collapse GlotLID's 2100-way vocabulary back to the 5 language classes
    of the test set (en, so, ar, fr, sw). Includes all major Arabic dialects
    and Swahili variants — without this, GlotLID's sub-dialect precision
    shows up as rollup false negatives."""
    if not label:
        return "none"
    label = label.strip().lower()
    if "_" in label:
        label = label.split("_", 1)[0]
    iso3_to_iso1 = {
        "eng": "en",
        # Somali proper (Maay Maay `ymm` left as separate miss — test set labels "so" not "so|ymm").
        "som": "so",
        # Arabic: all varieties roll up to `ar`.
        "arb": "ar", "ara": "ar", "arz": "ar", "apc": "ar", "ajp": "ar",
        "ars": "ar", "acm": "ar", "aeb": "ar", "afb": "ar", "ayl": "ar",
        "ary": "ar", "abv": "ar", "aec": "ar", "adf": "ar", "shu": "ar",
        # French
        "fra": "fr", "fre": "fr",
        # Swahili: coastal, Congo, generic.
        "swa": "sw", "swh": "sw", "swc": "sw",
    }
    return iso3_to_iso1.get(label, label)


# ---------- model loaders ----------

def load_fasttext_lid176():
    import fasttext
    model_path = MODELS_DIR / "lid.176.ftz"
    if not model_path.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
        print(f"[lid176] downloading {url}")
        urllib.request.urlretrieve(url, model_path)
    model = fasttext.load_model(str(model_path))

    def predict(text: str) -> tuple[str, float]:
        t = text.replace("\n", " ")[:1000]
        labels, probs = model.predict(t, k=1)
        lang = labels[0].replace("__label__", "")
        return norm_label(lang), float(probs[0])
    return predict


def load_langdetect():
    from langdetect import detect_langs, DetectorFactory, LangDetectException
    DetectorFactory.seed = 0  # reproducibility

    def predict(text: str) -> tuple[str, float]:
        try:
            t = text.strip()
            if not t:
                return "none", 0.0
            top = detect_langs(t)[0]
            return norm_label(top.lang), float(top.prob)
        except LangDetectException:
            return "none", 0.0
    return predict


def load_glotlid():
    import fasttext
    from huggingface_hub import hf_hub_download
    model_path = hf_hub_download(repo_id="cis-lmu/glotlid", filename="model_v3.bin")
    model = fasttext.load_model(model_path)

    def predict(text: str) -> tuple[str, float]:
        t = text.replace("\n", " ")[:1000]
        labels, probs = model.predict(t, k=1)
        lang = labels[0].replace("__label__", "")
        return norm_label(lang), float(probs[0])
    return predict


MODELS = {
    "fasttext_lid176": load_fasttext_lid176,
    "langdetect":       load_langdetect,
    "glotlid_v3":       load_glotlid,
}


# ---------- evaluation ----------

def confusion(true_labels: list[str], pred_labels: list[str]) -> dict:
    c: dict[tuple[str, str], int] = defaultdict(int)
    for t, p in zip(true_labels, pred_labels):
        c[(t, p)] += 1
    return dict(c)


def per_lang_pr(true_labels: list[str], pred_labels: list[str]) -> dict:
    stats: dict[str, dict[str, float]] = {}
    all_langs = sorted(set(true_labels) | {p for p in pred_labels if p in FIVE_LANGS})
    for lang in all_langs:
        tp = sum(1 for t, p in zip(true_labels, pred_labels) if t == lang and p == lang)
        fp = sum(1 for t, p in zip(true_labels, pred_labels) if t != lang and p == lang)
        fn = sum(1 for t, p in zip(true_labels, pred_labels) if t == lang and p != lang)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        stats[lang] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}
    return stats


def run_model(name: str, loader, rows: list[dict]) -> dict:
    print(f"[{name}] loading...")
    t0 = time.time()
    predict = loader()
    load_time = time.time() - t0

    true_labels = [r["language"] for r in rows]
    pred_labels: list[str] = []
    confidences: list[float] = []

    t0 = time.time()
    for r in rows:
        lang, conf = predict(r["text"])
        pred_labels.append(lang)
        confidences.append(conf)
    pred_time = time.time() - t0
    docs_per_sec = len(rows) / pred_time if pred_time > 0 else float("inf")

    per_lang = per_lang_pr(true_labels, pred_labels)
    overall_acc = sum(1 for t, p in zip(true_labels, pred_labels) if t == p) / len(rows)
    conf_top_3 = [(k, v) for k, v in sorted(confusion(true_labels, pred_labels).items(), key=lambda x: -x[1]) if k[0] != k[1]][:10]

    print(f"[{name}] overall acc = {overall_acc:.3f}  docs/s = {docs_per_sec:.1f}")
    return {
        "name": name,
        "load_time_s": load_time,
        "predict_time_s": pred_time,
        "docs_per_sec": docs_per_sec,
        "overall_accuracy": overall_acc,
        "per_language": per_lang,
        "pred_labels": pred_labels,
        "confusion_top": conf_top_3,
    }


# ---------- reporting ----------

def load_test_set(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for r in csv.DictReader(f):
            rows.append({"text": r["text"], "language": r["language"]})
    return rows


def render_markdown(results: list[dict], rows: list[dict]) -> str:
    out = ["# LID benchmark — GlotLID v3 vs langdetect vs fastText lid.176\n"]
    out.append(f"Test set: `{TEST_SET}` — {len(rows)} rows across {len(set(r['language'] for r in rows))} languages.")
    out.append(f"Counts per language: {dict(Counter(r['language'] for r in rows))}\n")

    # Headline table
    out.append("## Headline")
    out.append("| Model | Overall accuracy | Docs/sec | Somali precision | Somali recall | Somali F1 |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for r in results:
        so = r["per_language"].get("so", {"precision": 0.0, "recall": 0.0, "f1": 0.0})
        out.append(
            f"| **{r['name']}** | {r['overall_accuracy']:.3f} | {r['docs_per_sec']:.1f} | "
            f"{so['precision']:.3f} | {so['recall']:.3f} | {so['f1']:.3f} |"
        )

    # Per-language table per model
    out.append("\n## Per-language precision / recall / F1")
    for r in results:
        out.append(f"\n### {r['name']}")
        out.append("| lang | precision | recall | F1 | tp | fp | fn |")
        out.append("|---|---:|---:|---:|---:|---:|---:|")
        for lang in sorted(r["per_language"]):
            s = r["per_language"][lang]
            out.append(f"| {lang} | {s['precision']:.3f} | {s['recall']:.3f} | {s['f1']:.3f} | "
                       f"{s['tp']} | {s['fp']} | {s['fn']} |")

    # Confusion summary
    out.append("\n## Top confusions (true → predicted, off-diagonal, top 10 per model)")
    for r in results:
        out.append(f"\n### {r['name']}")
        if not r["confusion_top"]:
            out.append("_none — perfect diagonal_")
        else:
            for (t, p), n in r["confusion_top"]:
                out.append(f"- `{t}` → `{p}`  ({n} rows)")

    return "\n".join(out)


def main() -> None:
    rows = load_test_set(TEST_SET)
    print(f"[benchmark] test set: {len(rows)} rows")

    results = []
    for name, loader in MODELS.items():
        try:
            results.append(run_model(name, loader, rows))
        except Exception as e:
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    md = render_markdown(results, rows)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(md, encoding="utf-8")

    print("\n" + "=" * 60)
    print(md)
    print("=" * 60)
    print(f"\n[benchmark] wrote -> {REPORT_OUT}")


if __name__ == "__main__":
    main()
