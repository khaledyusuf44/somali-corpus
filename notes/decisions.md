# Somali Web Corpus — project decisions

Context-phase output, before full scaffolding. Locks the four decisions that shape everything downstream: language identification, source mix, comparison baselines, and the one-sentence paper contribution. Also lists open items that require empirical verification before Phase 1 proper begins.

---

## Decision 1 — Language identification

**Primary: `langdetect` (seeded for reproducibility). Secondary: GlotLID v3, used only for `som_Latn` vs `ymm_Latn` dialect tagging on docs already accepted as Somali. Drop fastText lid.176 entirely.**

> **Note — updated after Phase 0.2 empirical benchmark.** The original position below (GlotLID primary) was the prediction from the research-phase literature scan. When we actually benchmarked the three models on our 200-row test set, langdetect beat GlotLID on Somali recall by 22.5 pp (0.950 vs 0.725). GlotLID's 11 Somali misses went to unrelated Latin-script African languages, not to the defensible `ymm` sister language — making GlotLID's "not Somali" verdict unreliable as a pre-filter. Full numbers: `reports/lid_comparison.md`. Progress log: `notes/progress.md` §0.2.

### Why not the "default" the plan doc suggested

The generic plan says "use fastText." Our own `language-id-practice/REPORT.md` measured `fastText lid.176` at **7.5% recall on Somali** (3 / 40 rows) on a 200-row mixed-language eval set. `langdetect` on the same set got **95%**. The community knows about this — OpenLID-v3 (2025) explicitly flags Somali as "high confusion" and had to augment training data with MasakhaNews / Leipzig Wiki / Tatoeba Somali specifically to fix it.

### What GlotLID v3 buys us

- fastText-architecture speed (~50k–100k docs/sec on a MacBook) — essential for scanning Common Crawl WET files at millions-of-docs scale.
- Explicit `som_Latn` label, plus separate `ymm_Latn` (Maay Maay) — important because standard LIDs conflate Maay with Somali silently.
- 2100+ total language labels, so the "it's not Somali" class is richer → fewer false positives from script-adjacent languages like Oromo, Afar, Swahili.
- Trivial Python integration: `pip install fasttext huggingface_hub`, then load `cis-lmu/glotlid/model.bin`.

### Why langdetect stays in the loop

Our 95% in-house number for langdetect on Somali is the best Somali-specific benchmark that exists — **no published paper publishes per-language Somali F1 for GlotLID, OpenLID, or CLD3** (confirmed via CommonLID 2025 paper and the GlotLID/OpenLID papers themselves). Until we verify GlotLID empirically on our own eval set, langdetect is the fallback ground-truth signal.

Workflow: GlotLID tags everything; if GlotLID's top-1 probability is < 0.5 OR if it tags a language adjacent to Somali (`ymm`, Swahili, Oromo, Afar, Italian), pass the doc through langdetect as a tiebreaker.

### Known failure modes to document in the dataset card

- **Maay Maay** bleed-in when a crawler lacks the `ymm_Latn` label.
- **Italian** false positives (Somali has ~300 Italian loanwords; lid.176's miscalls likely came from this).
- **Swahili / Oromo / Afar** cross-Latin-script confusion.
- **Short documents** (< 10 words) — any LID is noisy here; we'll filter these out in Phase 4 for length anyway.

---

## Decision 2 — Source mix

**Aggregate-and-filter, not re-crawl.** Three source tracks, prioritized by yield and cost:

> **Note — revised after Phase 0.3 cost reality check.** The original plan was "20 WET files from `tiny_llm/crawl/`" as the primary CC-derived source. That was wrong — 20 GB download for ~5 MB of Somali is a 4,000× waste, and OSCAR/MADLAD/CC100 already did the scan-all-of-CC-for-Somali job for us across hundreds of snapshots. Our contribution is the **aggregation, deduplication, and quality-filtering pipeline**, not the crawl.

### Track A — Pre-filtered Somali corpora (primary CC-derived source)

> **Revised after Phase 0.4 download.** Original plan was OSCAR + MADLAD + CC100. Reality: OSCAR is gated behind HF auth + license, MADLAD and CC100 use deprecated loader scripts. **HPLT v2** (Helsinki NLP's Parallel Texts) turns out to be the highest-value source — accessible via direct HTTP, 505M tokens of cleaned Somali, larger and cleaner than OSCAR/MADLAD combined.

Final Track A composition:
- **HPLT v2 cleaned `som_Latn`** — primary. ~505M tokens across 966K docs. Their own MinHash-near-dedup left 17% byte-identical duplicates we catch trivially.
- **CC100-so** — secondary. ~81M tokens, 396K docs. Overlaps with HPLT on only 993 docs (0.12%) — worth keeping for diversity.
- **OSCAR 23.01** — skipped in v1 (gated). Re-evaluate if user provides HF auth.
- **MADLAD-400** — skipped in v1. HPLT effectively supersedes it at document level; adds little.

Combined raw Track A: ~**585M tokens across 1.36M unique docs** before dedup/quality filter.

### Track B — Curated news sources (quality-dominant)

Scrape directly under our own user-agent, honoring robots.txt (all 7 targets allowed per Phase 0.5 audit), rate-limited to 1 req/sec per host:
- **With sitemaps** (easier): BBC Somali, VOA Somali, Horseed Media, Radio Dalsan.
- **Without sitemaps** (per-site archive pages): Goobjoog News, Hiiraan Online, Garowe Online.
- **Skip for v1**: SomaliNet forums (UGC, quality and licensing unclear).

### Track C — Clean anchor (done)

- **Wikipedia-so** (Phase 0.1 ✓) — 9,021 articles / ~2.5M tokens. Too small to contribute meaningfully to the corpus, but cleanest available Somali text → use as positive-class seed for the Phase 6 perplexity quality filter.

### Optional stretch: targeted CC index probe

- Use `cdx-toolkit` to query CC's columnar index for `content_languages=som` in one recent snapshot (CC-MAIN-2024-30). Range-fetch only the matching WARC records, not full WET files. Estimated cost: ~100 MB download, not 20 GB. Only worth it if we want fresh 2024-2025 content beyond OSCAR/MADLAD's coverage.

### Target corpus size

> **Revised after Phase 0.4 numbers.** HPLT v2 alone gives 505M raw tokens. Target is now **~250M final tokens** after byte-exact dedup, MinHash near-dedup at τ=0.80, and quality filter. Track B (curated news) is **deferred to v2** — HPLT's size makes the marginal value of per-site scrapers much lower than it was when we expected 5 MB from CC.

### Legal/ethical stance

- Honor robots.txt; self-impose 1 req/sec per host (none of the targets set crawl-delay).
- Strip obvious PII (phone numbers, emails, street addresses) in Phase 4 via regex + a Somali-name dictionary (Presidio doesn't cover Somali — v1 gap we document).
- Cite sources in the dataset card with per-source token counts.
- License the corpus CC-BY-SA or similar; flag web-sourced content to downstream users.

---

## Decision 3 — Comparison baselines

**Compare against OSCAR 23.01 and MADLAD-400 at a minimum. Include CC100 and Wikipedia-so as secondary anchors.**

Comparison is what makes this a dataset paper instead of a dataset release. Pick at least two baselines and measure four things consistently:

| Metric | Why it matters |
|---|---|
| Token count | Raw size signal. |
| Duplicate rate (MinHash at τ=0.80) | Did our dedup actually beat theirs? |
| Tokenizer fertility (tokens/word) on a held-out Somali test set, using a tokenizer trained on our corpus | Downstream utility signal — the most compelling "why does this dataset matter" number. |
| Manual quality (100-doc inspection, scored on a 4-level rubric) | Keeps the numbers honest. |

Baselines to download during Phase 0:
- **OSCAR 23.01, subset `so`** via HuggingFace `oscar-corpus/OSCAR-2301` — the obvious apples-to-apples.
- **MADLAD-400 clean split, language `so`** via HF — newer, cleaner than mC4, so a harder bar.
- **CC100-so** via HF `cc100` — older, dirty reference point.
- **Wikipedia-so** via `wikimedia/wikipedia` — not a fair comparison (curated encyclopedic text), but a clean-reference anchor for token counts.

Numbers will be tentative until download; OSCAR-so anchors around ~40–60 MB / tens of M tokens, MADLAD-400-so somewhere similar or larger, Wikipedia-so ~10 MB. **All approximate — verify in Phase 0.**

---

## Decision 4 — Paper contribution (one sentence)

> **Revised after Phase 0.4:**
> "We release **SomaliWeb-v1** (~250M tokens), an aggregated and filtered Somali web corpus built from HPLT v2, CC100, and Wikipedia-so via a reproducible pipeline combining `langdetect`-based verification, MinHash near-dedup at τ=0.80, and a perplexity-based quality filter, and show that (i) HPLT v2's published distribution retains 17% byte-level exact duplicates despite its documented cleaning pass; (ii) HPLT and CC100 overlap in only 0.12% of documents, making cross-source aggregation net-positive; and (iii) our quality filter improves downstream tokenizer fertility by [X]% vs HPLT-raw on a held-out Somali test set."

The primary contribution is the **corpus**. The secondary contribution is the **quality-filter methodology for a low-resource language without in-language labeled data** — a real methodological gap. Target venue: a workshop (AfricaNLP, WiNLP, LoResMT, ACL Student Workshop). Not a main conference track — low-resource corpus papers rarely make the main track, but workshops are both the right audience and the right bar.

---

## Open items — resolve empirically in Phase 0 before Phase 1

These are known-unknowns that block final pipeline decisions. **Don't start Phase 1 until each has an answer.**

1. **Empirical LID comparison.** Run GlotLID v3, langdetect, and (as a baseline) fastText lid.176 on our existing `language-id-practice` test set + 200 new Somali samples from BBC Somali. Confirm GlotLID beats langdetect on speed with comparable recall, or fall back to langdetect-primary. *Estimated effort: 1 session.*

2. **Actual CC yield.** Decompress and scan the 20 WET files queued in `tiny_llm/crawl/`. Report: total docs, docs tagged `som_Latn` by GlotLID, total Somali MB after LID + length filter. If yield < 5 MB, expand WET list by an order of magnitude before Phase 1. *Estimated effort: 1 session (download is the slow part).*

3. **OSCAR-so / MADLAD-so baseline stats.** Download both, report token count, MinHash-dedup-rate-at-0.80, and manually inspect 50 random samples from each. Locks in the "what does better than this mean" target. *Estimated effort: 0.5 sessions.*

4. **Robots.txt + terms audit** for the five curated news targets (BBC Somali, VOA Somali, Goobjoog, Hiiraan, Horseed). One-line per source: allowed / blocked / rate-limit. *Estimated effort: 0.5 sessions.*

5. **Wikipedia-so dump acquisition.** Download, parse, strip markup, count tokens. This is probably 30 minutes — do it first, since it's the easiest win and doubles as a clean positive-class seed for the Phase 6 quality filter. *Estimated effort: 0.5 sessions.*

---

## Design implications locked in (to drive scaffolding)

Once Phase 0 is done and the above opens are answered, the scaffold will be:

- `pipeline/lang_filter.py` — GlotLID primary, langdetect secondary, no fastText lid.176.
- `pipeline/dedup.py` — `from minhash_pipeline import ...`, importing our `minhash-dedup-practice/src/` code rather than re-implementing.
- `pipeline/quality_filter.py` — Kneser-Ney perplexity scorer using a model trained on Wikipedia-so + BBC Somali as clean reference. No trained classifier in v1 (that's v2).
- `pipeline/sources/` — one module per curated source (each: a fetcher, an RSS parser, and a per-site extraction rule).
- `configs/pipeline.yaml` — all knobs (τ, min length, quality threshold) live here, config-driven, for reproducibility.
- `reports/baseline_comparison.md` — OSCAR-so / MADLAD-so / CC100-so / Wikipedia-so token counts, dedup rates, fertility numbers. Populated during Phase 0 so the paper's results table has a shape from day one.

---

## Success criteria (from the Tiny LLM roadmap, re-scoped)

This project succeeds when:
1. `SomaliWeb-v1` is published on Hugging Face with a complete dataset card, ≥ 50M tokens after all filters.
2. Tokenizer fertility on a Somali held-out test set is demonstrably lower than OSCAR-so's.
3. Manual 100-doc inspection gives ≥ 80% judged as "coherent Somali text, useful for pretraining."
4. The dedup pipeline is importable as a standalone module (or re-exported from `minhash-dedup-practice`).
5. A ≤ 6-page workshop-style writeup exists covering corpus · method · baseline comparison · limitations.

Stretch (v2, not v1): retrained quality classifier, multilingual East African extension, a Somali-optimized tokenizer as a separate release.

---

## What's NOT in this decision doc (and why)

- The actual pipeline YAML and folder structure — scaffold after Phase 0.
- PII detection specifics — Presidio doesn't cover Somali; we'll use regex + name dictionaries in v1 and document the gap. Deferred.
- Paper writing process — too early; comes after we have numbers.
- HF release logistics — mechanical, covered in the plan doc, deferred to Phase 9.
