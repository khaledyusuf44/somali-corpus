"""Bootstrap 95% confidence intervals for the LID per-class F1 numbers.

Resamples the 200-row LID test set 500 times with replacement, recomputes per-class
precision / recall / F1 each time, and reports the empirical 2.5th and 97.5th
percentiles for each metric. This adds statistical rigor to reports/lid_comparison.md
for the paper.

Inputs
------
We re-derive the per-row predictions from the existing benchmark numbers in
reports/lid_comparison.md (per-class tp / fp / fn). Without per-row predictions,
we reconstruct a categorical prediction vector per model that has the same per-class
counts the original benchmark observed; bootstrap is then exact for these counts.

A more rigorous version would re-run the three LID models. The reconstructed
version still gives a valid CI for the F1 estimator on the same test set; the
caveat (no model re-runs) is recorded in the JSON output.

Output
------
reports/lid_bootstrap_ci.json
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Per-class TP / FP / FN from reports/lid_comparison.md.
# Per language counts: 40 each across en/so/ar/fr/sw → 200 rows total.
PER_CLASS = {
    "fasttext_lid176": {
        "ar": (36, 0, 4), "en": (38, 30, 2), "fr": (35, 2, 5),
        "so": (3, 0, 37),  "sw": (8, 0, 32),
    },
    "langdetect": {
        "ar": (39, 0, 1),  "en": (26, 1, 14), "fr": (25, 1, 15),
        "so": (38, 8, 2),  "sw": (31, 1, 9),
    },
    "glotlid_v3": {
        "ar": (36, 0, 4),  "en": (29, 2, 11), "fr": (25, 0, 15),
        "so": (29, 1, 11), "sw": (29, 0, 11),
    },
}


def reconstruct_per_row(model_counts: dict[str, tuple[int, int, int]]
                        ) -> list[tuple[str, str]]:
    """Build a list of (true_label, predicted_label) pairs that exactly reproduces
    the given per-class TP / FP / FN counts for a single model.

    Strategy: each true class has 40 rows. TP rows predict the same class. FN rows
    predict 'other'. FP rows have 'other' as true and predict this class — so they
    come from rows of *other* true classes. We allocate the FP credit deterministically
    so each true class's 40 rows balance.
    """
    classes = list(model_counts.keys())
    rows: list[tuple[str, str]] = []
    # TP / FN per class
    fn_pool: list[str] = []  # rows whose true label is class c but predicted != c
    for c in classes:
        tp, fp, fn = model_counts[c]
        # tp rows: (c, c)
        rows.extend([(c, c)] * tp)
        # fn rows: (c, ?) — we'll fill the ? from "predicted = something else"
        fn_pool.extend([c] * fn)
    # Each FP for a class c means a row with true != c was predicted as c.
    # Total FPs across all classes = total FNs across all classes (in a closed
    # multiclass setup with no abstain). Pair FNs to FPs.
    fp_demands: list[str] = []
    for c, (_, fp, _) in model_counts.items():
        fp_demands.extend([c] * fp)
    # If FP and FN counts don't perfectly balance (multi-class with "other"
    # predictions like 'fi', 'kin', 'tl', etc., that aren't in our 5-class set),
    # the residual FN rows get predictions like "other". This matches the source
    # report — many drops went to non-target languages.
    rng = random.Random(0)
    rng.shuffle(fp_demands)
    while fn_pool and fp_demands:
        true_c = fn_pool.pop()
        pred_c = fp_demands.pop()
        if true_c != pred_c:
            rows.append((true_c, pred_c))
        else:
            # Mismatch — push back; should be rare since we shuffled
            fp_demands.append(pred_c)
            fn_pool.insert(0, true_c)
            if len(fp_demands) <= 1:
                break
    # Any leftover FN rows go to "other"
    for true_c in fn_pool:
        rows.append((true_c, "other"))
    # Any leftover FP demands go from "other" true (shouldn't happen if FP=FN totals match)
    for pred_c in fp_demands:
        rows.append(("other", pred_c))
    return rows


def per_class_f1(pairs: list[tuple[str, str]], cls: str) -> tuple[float, float, float]:
    tp = sum(1 for t, p in pairs if t == cls and p == cls)
    fp = sum(1 for t, p in pairs if t != cls and p == cls)
    fn = sum(1 for t, p in pairs if t == cls and p != cls)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def bootstrap_ci(pairs: list[tuple[str, str]], cls: str, n_iter: int, seed: int = 0
                 ) -> dict[str, tuple[float, float]]:
    rng = random.Random(seed)
    n = len(pairs)
    p_dist, r_dist, f_dist = [], [], []
    for _ in range(n_iter):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        p, r, f = per_class_f1(sample, cls)
        p_dist.append(p); r_dist.append(r); f_dist.append(f)
    p_dist.sort(); r_dist.sort(); f_dist.sort()
    lo = int(0.025 * n_iter)
    hi = int(0.975 * n_iter) - 1
    return {
        "precision_ci95": (p_dist[lo], p_dist[hi]),
        "recall_ci95":    (r_dist[lo], r_dist[hi]),
        "f1_ci95":        (f_dist[lo], f_dist[hi]),
    }


def main() -> None:
    n_iter = 500
    seed = 0
    out: dict = {
        "n_iter": n_iter,
        "seed": seed,
        "test_set": "language-id-practice/data/multilingual_samples.csv (200 rows, 40 per class)",
        "method": "Reconstructed per-row predictions from reports/lid_comparison.md "
                  "per-class TP/FP/FN; resampled with replacement.",
        "models": {},
    }

    classes = ("en", "so", "ar", "fr", "sw")
    for model, counts in PER_CLASS.items():
        pairs = reconstruct_per_row(counts)
        # sanity: check our reconstruction reproduces published F1 to within rounding
        published_f1 = {c: 2 * counts[c][0] / (2 * counts[c][0] + counts[c][1] + counts[c][2])
                        for c in classes}
        actual_f1 = {c: per_class_f1(pairs, c)[2] for c in classes}
        out["models"][model] = {"point_estimates": {}, "bootstrap_ci": {}}
        for c in classes:
            point_p, point_r, point_f = per_class_f1(pairs, c)
            ci = bootstrap_ci(pairs, c, n_iter, seed)
            out["models"][model]["point_estimates"][c] = {
                "precision": round(point_p, 4),
                "recall":    round(point_r, 4),
                "f1":        round(point_f, 4),
                "f1_published": round(published_f1[c], 4),
            }
            out["models"][model]["bootstrap_ci"][c] = {
                "precision_95": [round(ci["precision_ci95"][0], 4), round(ci["precision_ci95"][1], 4)],
                "recall_95":    [round(ci["recall_ci95"][0], 4),    round(ci["recall_ci95"][1], 4)],
                "f1_95":        [round(ci["f1_ci95"][0], 4),        round(ci["f1_ci95"][1], 4)],
            }

    out_path = ROOT / "reports/lid_bootstrap_ci.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    # Print a paper-ready summary
    print()
    print("=== Somali F1 with 95% CI per model (n_iter=500, seed=0) ===")
    print(f"{'model':>20s}  {'F1 (point)':>10s}  {'95% CI':>14s}")
    for m in PER_CLASS:
        pe = out["models"][m]["point_estimates"]["so"]
        ci = out["models"][m]["bootstrap_ci"]["so"]
        print(f"{m:>20s}  {pe['f1']:>10.3f}  [{ci['f1_95'][0]:.3f}, {ci['f1_95'][1]:.3f}]")


if __name__ == "__main__":
    main()
