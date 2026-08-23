# Abstract

**CardioXNet: Validity-Gated Literature-Gap Detection for Cardiovascular Pathway Hypotheses**

Pathway enrichment ranks overrepresentation but does not indicate whether a
pathway-gene-disease connection has been reported. CardioXNet is an auditable
workflow that expands cardiovascular gene panels through protein associations,
performs multi-resource enrichment, and combines a specificity-aware Pathway
Prioritization Score with uncapped PubMed counts for prespecified pathway,
contributing-gene, and disease title/abstract queries; cardiac expression and
druggability remain separate annotations. A grounding gate withholds novelty
labels when the seed-disease corpus holds fewer than 100 records, and a
pathway-concept check separates searchable zero-count gaps from vocabulary
failures. In a regenerated development benchmark of four cardiovascular panels
and three controls, CardioXNet returned 124 real-panel hypotheses (0/124
Ungrounded) and 40 control hypotheses (40/40 Ungrounded). Among heart-failure
hypotheses with a positive count, query counts spanned 593.2-fold, from 8 to
4,746 records, while the capped abstract display set spanned only 8 to 30. Eight
real-panel hypotheses met the prespecified verified-gap rule, including GAB1
signalosome and NTRK2 signaling in structural cardiomyopathy, cGMP-PKG signaling
in arrhythmia, and P2Y12, GPER1, HIF-1, cAMP, and oxytocin signaling in
myocardial infarction. These combined 7.6- to 17.5-fold enrichment with
empirical q-values of 0.00128 to 0.00170, yet returned zero records for the
prespecified queries: unreported query intersections, not globally unreported
biology. In an all-hypothesis temporal holdout, the Discovery Score showed
negligible association with post-cutoff publication growth (Spearman rho =
-0.1189; n = 124). CardioXNet converts broad enrichment output into an
inspectable shortlist of statistically supported, literature-sparse
cardiovascular connections for expert review, without claiming biological
validation or forecasting impact.

---

*Word count: 242 (title excluded). This file mirrors the `abstract` environment
in `CardioXNet_IEEE_Access.tex`; update both together.*

## Evidence boundaries for the manuscript

| Claim | Evidence and boundary |
|-------|-----------------------|
| PPS deemphasizes large annotations | On the heart-failure panel, the highest final-PPS term contained 6 genes and the top 15 ranged from 5 to 72 genes. Term size and final PPS had rho = -0.81 within the top 15. Because specificity is an explicit PPS component, this is a consistency check rather than independent validation. |
| Uncapped counts preserve literature discrimination | Across the 17 of 19 heart-failure hypotheses with a positive count, exact-query counts ranged from 8 to 4,746, a 593.2-fold span, while their capped display sets ranged from 8 to 30 abstracts, a 3.75-fold span. |
| Eight current verified gaps were detected | Eight of 124 real-panel hypotheses met the prespecified zero-count rule in the regenerated benchmark. A zero means no PubMed title/abstract record matched that exact query in the benchmark snapshot, not that the biology is globally unreported. |
| Grounding invariants held | All 40 control hypotheses were Ungrounded and none of the 124 real-panel hypotheses was Ungrounded. Because the controls motivated the gate, this is a development regression invariant, not an unbiased estimate of specificity. |
| The temporal holdout was negative overall | Across all 124 real-panel hypotheses, Discovery Score versus post-cutoff growth had rho = -0.1189. The sensitivity analysis among 109 hypotheses with nonzero pre-cutoff counts had rho = +0.0132. Pathways overlap within panels, so these correlations are descriptive. |

The manuscript deliberately does not claim global biological novelty,
experimental validation, out-of-sample specificity, predictive validity, or a
degree-aware network null. The Discovery Score is an auditable triage heuristic
for literature-sparse query intersections, not a forecast of scientific impact.
