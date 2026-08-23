# CardioXNet benchmark report

Run date: 2026-08-22 (regenerated after the API-correctness fixes). All figures and tables in `paper/` were generated from these
runs; regenerate with the commands in `paper/README.md`.

External resources at run time: STRING v12.0, g:Profiler (`e104_eg51_p15`),
GTEx v8, ChEMBL, DrugBank v5.1.10, PubMed via NCBI E-utilities. The permutation
background is a pinned HGNC protein-coding snapshot (19,410 symbols, retrieved
2026-08-21); the permutation RNG seed is 20260821.

---

## 1. Analyses

Four cardiovascular seed panels chosen for distinct biology, plus three negative
controls. Each analysis is five seed genes under the `balanced` preset.

| Run | Kind | Seed genes | Disease context | Runtime | Hypotheses |
|-----|------|-----------|-----------------|---------|-----------|
| `hf_inflammatory` | real | VEGFA, MMP9, IL6, TNF, ACE | heart failure | 257 s | 21 |
| `dcm_structural` | real | MYH7, TTN, LMNA, MYBPC3, TNNT2 | cardiomyopathy | 181 s | 34 |
| `arrhythmia_channels` | real | SCN5A, KCNQ1, KCNH2, RYR2, CACNA1C | arrhythmia | 355 s | 41 |
| `mi_ischemic` | real | LDLR, APOB, PCSK9, NOS3, EDN1 | myocardial infarction | 323 s | 37 |
| `olfactory` | negative | OR51E2, OR2W1, OR1A1, OR5K1, OR10A4 | heart failure | 96 s | 12 |
| `random_1` | negative | RPF2, CLRN3, PRKAG1, OR8U9, CACNA1D | heart failure | 202 s | 19 |
| `random_2` | negative | C2CD4A, GORASP1, CHIC1, VCY, PLCD4 | heart failure | 144 s | 9 |

---

## 2. Ranking behaviour (Figure 2)

The corrected Pathway Prioritization Score no longer ranks by gene-set size. On
`hf_inflammatory` the largest annotated term in the top 15 has 107 genes and the
top-ranked term has 10. Under the previous formula the same seed panel returned
"cell surface receptor signaling pathway" (187 genes), "multicellular organism
development" (152) and "developmental process" (202) in the top ranks — terms
true of almost any gene list.

---

## 3. Literature saturation is discriminative (Figure 3)

PubMed corpus sizes at the (pathway × seed genes × disease) intersection on
`hf_inflammatory` range from **31 to 10,866 records** — three orders of
magnitude. The number of abstracts actually retrieved is flat at ~28–30 across
every pathway, because retrieval is capped.

This is the measurement that was previously broken. Deriving saturation from
retrieved citations rather than the corpus size made it constant, and the
citation sets themselves were near-duplicates (mean pairwise Jaccard 0.55, 120
unique PMIDs across 32 pathways) because the pathway clause was OR-ed with a
broad cardiac fallback instead of AND-ed.

---

## 4. Negative controls (Figure 5)

**Every one of the 40 hypotheses returned by the three negative controls is
flagged `Ungrounded`; none of the 133 hypotheses from the four real panels is.**
The separation is complete, in both directions.

The discriminating quantity is the seed genes' own literature footprint in the
chosen disease — one PubMed query per run:

| Panel | Seed–disease corpus |
|-------|--------------------:|
| hf_inflammatory | 10,868 |
| dcm_structural | 2,487 |
| arrhythmia_channels | 1,538 |
| mi_ischemic | 2,373 |
| olfactory (negative) | 0 |
| random_1 (negative) | 6 |
| random_2 (negative) | 1 |

Real panels exceed the grounding threshold of 100 records by 15× to 109×;
negative controls fall below it by one to two orders of magnitude.

This control was worth running because it initially **failed**. Before the
grounding check, olfactory-receptor and random gene panels produced *more*
"Highly Novel" calls (13/13 and 21/23) than any real cardiovascular panel: with
seeds nobody has written about in heart failure, every pathway intersection
returns zero records and every pathway looks maximally novel. Absence of
literature about the seeds was being read as discovery. Novelty is now only
reported when the seeds have a literature footprint to be novel against.

---

## 5. Temporal holdout — a null result (Figure 4)

**The Discovery Score does not anticipate where the literature subsequently
went.** This is the headline validation result and it is negative.

Literature was frozen at the end of 2020, novelty recomputed from pre-2020
records only, and each pathway's 2021–2026 publication record measured
(n = 132 pathways across the four real panels).

| Comparison | Spearman ρ |
|------------|-----------:|
| Discovery Score (2020) vs post-cutoff growth rate | −0.03 |
| Novelty (2020) vs post-cutoff growth rate | −0.01 |
| Novelty (2020) vs absolute post-cutoff records | **−0.98** |
| PPS (2020) vs post-cutoff growth rate | −0.15 |
| Discovery vs growth, measurable pathways only (n = 121) | +0.06 |

Mean post-cutoff growth by the tier assigned at the cutoff:

| Tier at 2020 | n | Mean growth | Median growth |
|--------------|--:|------------:|--------------:|
| Highly Novel | 17 | **0.33** | 0.00 |
| Novel | 24 | 0.89 | 0.83 |
| Emerging | 41 | 0.75 | 0.70 |
| Established | 50 | 0.61 | 0.55 |

Pathways called **Highly Novel grew the least**, and half of them gained no
publications at all in five years. The ρ = −0.98 against absolute record counts
is partly structural — novelty is a monotone transform of the pre-cutoff count,
and large fields keep publishing — but the direction is unambiguous: pathways
this metric calls novel are not where the field moved.

**Interpretation.** Literature saturation measures how much has been written
about a pathway–gene–disease intersection. It is a usable *prioritization*
signal for surfacing under-examined candidates, and it is validated as such: it
separates real panels from negative controls completely, and it spans three
orders of magnitude within a single run. It is **not** a validated predictor of
scientific importance, and a low count is as consistent with an unproductive
question, or with vocabulary mismatch, as with an opportunity. The Discovery
Score should be read as a triage heuristic, not as a forecast.

---

## 6. Statistical validation

- **Permutation null.** 1,000 size-matched permutations per pathway drawn from
  the 19,410-gene protein-coding background. On `hf_inflammatory`, observed
  overlaps of 30 against a null mean of 0.45 ± 0.65 (z ≈ 46).
- **External evidence is now actually retrieved.** The Open Targets query had
  been returning HTTP 400 on every request since the API changed
  `knownDrugs` to `drugAndClinicalCandidates`; `except Exception: pass` in the
  caller hid it, so external druggability read 0 for every gene of every earlier
  run. With the query repaired, MYH7 returns mavacamten, omecamtiv mecarbil and
  danicamtiv against dilated cardiomyopathy and heart failure.
- **Multiple testing.** Benjamini–Hochberg across every reported hypothesis,
  verified against `statsmodels.multipletests` in the test suite. Pathways whose
  null cannot be built carry `q = null` and are excluded from the correction
  family rather than assigned p = 1.
- **Resolution floor.** The smallest attainable empirical p is 1/(n+1) = 1.0e-3
  at 1,000 permutations, reported alongside every p-value.
- **Power.** Because the null samples the whole protein-coding genome, genuinely
  enriched pathways clear it by a wide margin and most reported pathways reach
  the floor. The test establishes that an overlap is not chance; it does not
  rank among strong hypotheses and must not be read as doing so.
- **Reproducibility.** Seeded RNG and a pinned background make the permutation
  step identical across reruns, and a regression test asserts it. The *pipeline*
  is not bit-reproducible, because the databases it queries are not.

  Measured directly: two back-to-back runs of the same seed panel on identical
  code produced identical functional neighbourhoods (219 genes, 2,261 STRING
  interactions) and identical primary enrichment (1,787 pathways), then diverged
  by a single pathway at secondary expansion (3,045 vs 3,046). The redundancy
  filter amplified that to a 34- vs 37-pathway final set, which in turn shifts
  Benjamini-Hochberg q-values (m changes) and the seed-proximity term of the
  centrality weight.

  The resulting noise floor, over the 33 pathways common to both runs:

  | Comparison | Pathways changed | Max relative PPS change | Novelty tier changes |
  |---|---:|---:|---:|
  | Same code, run A vs run B | 6 / 33 | 6.0% | 0 |
  | Across the Nov refactor | 0 / 37 | 0.0% | 0 |

  **No novelty tier moved in any comparison.** Report any single number with its
  run date, and treat differences below roughly 6% in PPS as run-to-run variation
  rather than signal.

---

## 7. Regression suite

87 tests (`tests/test_scientific_rigor.py` plus the pre-existing suite) pin each
defect found in the audit: the degenerate permutation universe, BH correctness
against a reference implementation, generic-term dominance, pathway-specific
query construction, saturation from corpus size, novelty-confidence gating, seed
grounding, semantic-filter discrimination, the effect-size floor, CSV
header/row alignment, the freshness of the results snapshot the UI reads, and a
sentinel per external API so that a failed call can never be read as a
measurement of zero.

A further 20 Playwright assertions cover what only the rendered page can prove:
Discovery-Score ordering, `n/t` for an untested permutation, valid novelty tiers,
the PPS component breakdown, and CSV header/row width equality. A live
end-to-end spec drives a real analysis through the browser against STRING,
g:Profiler and PubMed.

The degree-preserving permutation variants were **removed** rather than left
unused, and a test asserts they stay removed: they drew replacements from
per-degree bins over the supplied universe, which here means from the
neighbourhood itself, and reported `degree_preserved: True` while doing it. The
two tests that previously covered them asserted that behaviour was correct, and
one supplied a 5-gene universe for a 3-gene neighbourhood -- the exact degenerate
case the assertions were meant to catch.

---

## 8. Known limitations

- **Novelty is lexical.** A pathway named in identifiers rather than prose
  ("GAB1 signalosome") has little PubMed footprint regardless of how well studied
  the biology is. The concept-corpus check catches the worst cases and flags them
  `unverified`, but the metric remains vocabulary-dependent.
- **Corpus coverage.** Pathways outside the literature-mining window are
  backfilled with a single count query, and NCBI throttling is retried, so across
  all seven runs every one of the 161 reported hypotheses carries a measured
  corpus (125 `pubmed_corpus`, 36 `ungrounded_seeds`, zero `not_measured`).
  A pathway whose count cannot be obtained at all is still damped and flagged
  rather than scored as novel.
- **Not pinned.** STRING, g:Profiler, GTEx, Open Targets and PubMed all drift,
  and their schemas change: the Open Targets query silently broke and returned
  nothing for an unknown period. Every external client now carries a failure
  sentinel and logs at WARNING, and an opt-in `pytest -m live` test asserts the
  Open Targets query still matches the published schema. Record the run date with
  any reported figure.
- **Single-species, single-domain.** Human only; cardiac semantic scoring uses
  curated term lists that will miss lexically dissimilar evidence.
- **Hypotheses, not findings.** Every output is a candidate for experimental
  follow-up.
