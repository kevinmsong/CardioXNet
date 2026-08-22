# Abstract

**CardioXNet: prioritising under-examined cardiovascular pathways by coupling
network expansion to literature saturation**

Pathway enrichment analysis reliably returns what is statistically significant,
but significance grows with gene-set size, so rankings are dominated by broad,
already-familiar terms and offer no guidance toward what remains unexamined. We
present CardioXNet, an open pipeline that reasons from a small seed-gene panel
and a disease context to ranked, mechanistically specific cardiovascular
hypotheses. Seed genes are expanded through STRING protein interactions,
enriched across Reactome, KEGG, WikiPathways and GO:BP, re-expanded to recover
secondary pathways, then scored by a Pathway Prioritization Score that weights
statistical significance, fold enrichment, gene-set specificity and cross-source
replication — replacing the significance-times-set-size heuristic that otherwise
promotes generic terms. Each hypothesis is validated against GTEx cardiac
expression, a size-matched permutation null over the protein-coding genome with
Benjamini–Hochberg control, and curated druggability. The pipeline's distinctive
component is literature saturation: the true PubMed corpus size at the
intersection of pathway concept, contributing seed genes and disease context,
which yields a Discovery Score favouring pathways that are well supported yet
sparsely reported. Across four cardiovascular panels, corpus sizes spanned three
orders of magnitude within single runs, and hypotheses were mechanistically
specific rather than generic. Negative controls established the metric's
boundary: random and olfactory-receptor panels produced no interpretable novelty
once scores were conditioned on the seeds' own literature footprint. A
temporal-holdout test was, however, negative — pathways flagged novel in 2020
did not accumulate publications through 2026 — establishing the Discovery Score
as a triage heuristic rather than a validated predictor of scientific
importance. A pinned permutation background and seeded sampling make every
reported result reproducible.

---

*Word count: 253 (title excluded).*

## Notes for the manuscript

**What the abstract claims, and where it is supported.**

| Claim | Evidence |
|-------|----------|
| Significance-times-size promotes generic terms | `benchmark_report.md` §2; the prior formula returned 187-, 152- and 202-gene terms at top rank |
| PPS returns specific pathways | Figure 2; largest top-15 term is 107 genes |
| Corpus sizes span three orders of magnitude | Figure 3; 31–10,866 records on `hf_inflammatory` |
| Negative controls yield no interpretable novelty | Figure 5; 0/36 grounded across three control panels |
| Temporal holdout is negative | Figure 4; ρ = −0.01 (growth), −0.98 (absolute records), n = 125 |

**Deliberately not claimed.** That the Discovery Score predicts importance; that
low PubMed counts prove biological novelty; that the permutation test ranks among
strong hypotheses; that degree-matched network nulls are applied.

**Framing.** The negative holdout result is reported in the abstract rather than
confined to the discussion. It is the honest read of the validation, it defines
what the tool is for, and a methods paper that reports the limits of its own
central metric is the stronger one.
