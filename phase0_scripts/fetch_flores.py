"""Download FLORES-200 Somali dev + devtest splits as held-out evaluation set.

FLORES-200 (Meta/NLLB) provides professionally-translated parallel sentences
across 200 languages. For Somali (som_Latn): 997 dev + 1012 devtest = 2009
sentences. External source — no contamination risk with our CC-derived corpus.

Used in Phase 6 for tokenizer fertility comparison.
"""

import json
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/eval/flores_so.jsonl"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    all_sentences = []
    for split in ("dev", "devtest"):
        try:
            ds = load_dataset("facebook/flores", "som_Latn", split=split)
        except Exception as e:
            print(f"facebook/flores som_Latn {split} failed: {e}")
            ds = load_dataset("facebook/flores", "som_Latn", split=split, trust_remote_code=True)
        for r in ds:
            all_sentences.append({"split": split, "text": r["sentence"]})

    with OUT.open("w", encoding="utf-8") as f:
        for r in all_sentences:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_chars = sum(len(r["text"]) for r in all_sentences)
    n_words = sum(len(r["text"].split()) for r in all_sentences)
    print(f"[flores] {len(all_sentences):,} sentences  {n_words:,} words  {n_chars:,} chars")
    print(f"[flores] -> {OUT}")


if __name__ == "__main__":
    main()
