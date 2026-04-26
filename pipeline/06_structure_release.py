"""Phase 6 — Structure final corpus + tokenizer fertility evaluation.

Steps:
  1. Read Phase 5 output; shuffle (seed 0); 95/5 train/val split; write
     `data/release/{train,validation}.jsonl` with standardized schema.
  2. Train BPE tokenizer (vocab 16K) on our released train split.
  3. Train comparison BPE tokenizer on HPLT-raw (Phase 0.4 download) at same vocab.
  4. Measure tokenizer fertility on FLORES-200 Somali devtest for each tokenizer
     plus `cl100k_base` (GPT-4) as external reference, if tiktoken is available.
  5. Sample 100 random release docs for manual inspection rubric.
  6. Write `reports/06_evaluation.md` with the final comparison table.

Fertility metric: tokens / whitespace-word, averaged over FLORES devtest (1012
held-out Somali sentences). Lower = better (fewer tokens to represent same text).
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def iter_jsonl_texts(path: Path):
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)["text"]


def train_bpe(train_path: Path, vocab_size: int, out_path: Path) -> None:
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.trainers import BpeTrainer
    from tokenizers.pre_tokenizers import ByteLevel
    from tokenizers.decoders import ByteLevel as BLDec

    tok = Tokenizer(BPE(unk_token="<unk>"))
    tok.pre_tokenizer = ByteLevel(add_prefix_space=True)
    tok.decoder = BLDec()
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=["<unk>", "<bos>", "<eos>", "<pad>"],
        initial_alphabet=ByteLevel.alphabet(),
        show_progress=True,
    )
    tok.train_from_iterator(iter_jsonl_texts(train_path), trainer=trainer)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tok.save(str(out_path))


def measure_fertility(tokenizer_path: Path, test_sentences: list[str]) -> dict:
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(tokenizer_path))
    total_tokens = 0
    total_words = 0
    for s in test_sentences:
        enc = tok.encode(s)
        total_tokens += len(enc.ids)
        total_words += len(s.split())
    return {
        "tokens": total_tokens,
        "words": total_words,
        "fertility": total_tokens / total_words if total_words else float("inf"),
    }


def measure_fertility_tiktoken(encoding_name: str, test_sentences: list[str]) -> dict | None:
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding_name)
        total_tokens = 0
        total_words = 0
        for s in test_sentences:
            total_tokens += len(enc.encode(s))
            total_words += len(s.split())
        return {
            "tokens": total_tokens,
            "words": total_words,
            "fertility": total_tokens / total_words if total_words else float("inf"),
        }
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(ROOT / "data/pipeline/05_quality_filtered.jsonl"))
    p.add_argument("--hplt-raw", default=str(ROOT / "data/baselines/hplt2_so.jsonl"))
    p.add_argument("--flores-test", default=str(ROOT / "data/eval/flores_so.devtest.txt"))
    p.add_argument("--release-dir", default=str(ROOT / "data/release"))
    p.add_argument("--report", default=str(ROOT / "reports/06_evaluation.md"))
    p.add_argument("--train-fraction", type=float, default=0.95)
    p.add_argument("--vocab-size", type=int, default=16000)
    p.add_argument("--manual-sample", type=int, default=100)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    in_path = Path(args.input)
    release_dir = Path(args.release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    train_path = release_dir / "train.jsonl"
    val_path = release_dir / "validation.jsonl"

    # ---- 1. read + shuffle + split ----
    print(f"[phase6] reading {in_path}...")
    docs = []
    with in_path.open() as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))
    print(f"[phase6] read {len(docs):,} docs")

    rng = random.Random(args.seed)
    rng.shuffle(docs)
    split = int(len(docs) * args.train_fraction)

    print(f"[phase6] writing split train={split:,} val={len(docs)-split:,}")
    with train_path.open("w", encoding="utf-8") as f:
        for r in docs[:split]:
            out = {
                "id": r.get("id"),
                "text": r.get("text"),
                "source": r.get("source"),
                "n_words": r.get("n_words"),
                "quality_score": r.get("quality_score"),
                "lang_conf": r.get("lang_conf"),
                "dialect_tag": r.get("dialect_tag"),
            }
            f.write(json.dumps({k: v for k, v in out.items() if v is not None},
                               ensure_ascii=False) + "\n")
    with val_path.open("w", encoding="utf-8") as f:
        for r in docs[split:]:
            out = {
                "id": r.get("id"),
                "text": r.get("text"),
                "source": r.get("source"),
                "n_words": r.get("n_words"),
                "quality_score": r.get("quality_score"),
                "lang_conf": r.get("lang_conf"),
                "dialect_tag": r.get("dialect_tag"),
            }
            f.write(json.dumps({k: v for k, v in out.items() if v is not None},
                               ensure_ascii=False) + "\n")

    # ---- 2. train our tokenizer ----
    print("[phase6] training tokenizer on release/train...")
    t0 = time.time()
    our_tok_path = release_dir / "tokenizer_somaliweb.json"
    train_bpe(train_path, args.vocab_size, our_tok_path)
    print(f"[phase6] ours trained in {time.time()-t0:.1f}s -> {our_tok_path}")

    # ---- 3. train HPLT-raw tokenizer ----
    print("[phase6] training tokenizer on HPLT-raw...")
    t1 = time.time()
    hplt_tok_path = release_dir / "tokenizer_hplt_raw.json"
    train_bpe(Path(args.hplt_raw), args.vocab_size, hplt_tok_path)
    print(f"[phase6] HPLT-raw tokenizer trained in {time.time()-t1:.1f}s -> {hplt_tok_path}")

    # ---- 4. measure fertility on FLORES-200 Somali devtest ----
    print("[phase6] measuring fertility on FLORES-200 Somali devtest...")
    with Path(args.flores_test).open() as f:
        test_sentences = [line.strip() for line in f if line.strip()]
    print(f"  {len(test_sentences):,} test sentences")

    fert_ours = measure_fertility(our_tok_path, test_sentences)
    fert_hplt = measure_fertility(hplt_tok_path, test_sentences)
    fert_gpt4 = measure_fertility_tiktoken("cl100k_base", test_sentences)

    # ---- 5. manual-inspection sample ----
    rng = random.Random(args.seed)
    inspection_docs = rng.sample(docs[:split], min(args.manual_sample, split))
    inspection_path = release_dir / "manual_inspection_sample.jsonl"
    with inspection_path.open("w", encoding="utf-8") as f:
        for r in inspection_docs:
            f.write(json.dumps({"id": r.get("id"),
                                "source": r.get("source"),
                                "n_words": r.get("n_words"),
                                "quality_score": r.get("quality_score"),
                                "text_head": (r.get("text") or "")[:400]},
                               ensure_ascii=False) + "\n")

    # ---- 6. report ----
    lines = [
        f"# Phase 6 — Final evaluation\n",
        f"- Input (Phase 5 output): {len(docs):,} docs",
        f"- train split ({args.train_fraction:.0%}): {split:,} docs → `{train_path}`",
        f"- validation split ({1-args.train_fraction:.0%}): {len(docs)-split:,} docs → `{val_path}`",
        f"- tokenizer vocab size: {args.vocab_size:,}",
        f"- fertility test set: FLORES-200 Somali devtest, {len(test_sentences):,} sentences",
        "",
        "## Tokenizer fertility (lower = better)",
        "| Tokenizer | tokens | words | **fertility** |",
        "|---|---:|---:|---:|",
        f"| SomaliWeb-v1 (ours, BPE-{args.vocab_size//1000}K trained on our corpus) | {fert_ours['tokens']:,} | {fert_ours['words']:,} | **{fert_ours['fertility']:.3f}** |",
        f"| HPLT-raw (BPE-{args.vocab_size//1000}K trained on HPLT raw) | {fert_hplt['tokens']:,} | {fert_hplt['words']:,} | {fert_hplt['fertility']:.3f} |",
    ]
    if fert_gpt4 and "error" not in fert_gpt4:
        lines.append(f"| GPT-4 cl100k_base (external reference) | {fert_gpt4['tokens']:,} | {fert_gpt4['words']:,} | {fert_gpt4['fertility']:.3f} |")
    elif fert_gpt4 and "error" in fert_gpt4:
        lines.append(f"| GPT-4 cl100k_base | — | — | _tiktoken unavailable: {fert_gpt4['error']}_ |")

    improvement_vs_hplt = (fert_hplt['fertility'] - fert_ours['fertility']) / fert_hplt['fertility'] * 100
    lines.append(f"\nImprovement vs HPLT-raw: **{improvement_vs_hplt:+.2f}%** (positive = we compress better).")

    # corpus stats
    by_source = Counter(r.get("source") for r in docs)
    lines.append("\n## Final corpus source composition")
    lines.append("| Source | Docs | Fraction |")
    lines.append("|---|---:|---:|")
    for src, n in by_source.most_common():
        lines.append(f"| {src} | {n:,} | {n/len(docs)*100:.2f}% |")
    total_words = sum(r.get("n_words", 0) for r in docs)
    lines.append(f"\n- **Total docs (train+val):** {len(docs):,}")
    lines.append(f"- **Total whitespace words:** {total_words:,}")
    lines.append(f"- **Approx tokens (words × 1.3):** {int(total_words * 1.3):,}")
    lines.append(f"- Manual inspection sample of {len(inspection_docs)} docs at `{inspection_path}`.")

    Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print()
    print("=== Phase 6 summary ===")
    print(f"  release files: {train_path}  {val_path}")
    print(f"  fertility ours: {fert_ours['fertility']:.3f}")
    print(f"  fertility hplt-raw: {fert_hplt['fertility']:.3f}")
    if fert_gpt4 and "error" not in fert_gpt4:
        print(f"  fertility gpt-4: {fert_gpt4['fertility']:.3f}")
    print(f"  improvement vs HPLT: {improvement_vs_hplt:+.2f}%")
    print(f"  report: {args.report}")


if __name__ == "__main__":
    main()
