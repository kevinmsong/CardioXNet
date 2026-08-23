# Abstract

**CardioXNet: Evidence-Weighted Network Expansion for Auditable Discovery of Cardiovascular Literature Gaps**

Pathway enrichment ranks overrepresentation but does not show whether a
pathway-gene-disease connection has been reported. CardioXNet is an auditable
workflow that expands focused cardiovascular gene panels through protein
associations, performs multi-resource enrichment, and combines a
specificity-aware Pathway Prioritization Score with uncapped PubMed counts for
prespecified pathway, contributing-gene, and disease title/abstract queries.
Cardiac expression and druggability remain separate annotations. A grounding
gate withholds novelty labels when the seed-disease corpus contains fewer than
100 records, and a pathway-concept check distinguishes searchable zero-count
gaps from vocabulary failures. In a regenerated development benchmark of four
cardiovascular panels and three controls, CardioXNet returned 133 real-panel
hypotheses, with 0/133 Ungrounded, and 40 control hypotheses, with 40/40
Ungrounded. Heart-failure query counts varied 350.6-fold, from 31 to 10,868,
while capped abstract retrieval varied only from 26 to 30. Seven real-panel
hypotheses met the prespecified verified-gap rule. Rank-leading gaps included
GAB1 signalosome and NTRK2 signaling in structural cardiomyopathy, cGMP-PKG and
GPER1 signaling in arrhythmia, and P2Y12 and GPER1 signaling in myocardial
infarction. These candidates combined 6.7- to 17.5-fold enrichment with
empirical q-values of 0.00124 to 0.00162, yet the prespecified PubMed
title/abstract queries returned zero records in the regenerated benchmark. These zeros identify unreported
query intersections, not globally unreported biology. In an all-hypothesis
temporal holdout, the Discovery Score showed negligible association with
2021-2026 publication growth (Spearman rho = -0.0635; n = 133). CardioXNet
converts broad enrichment output into an inspectable shortlist of statistically
supported, literature-sparse cardiovascular connections for expert review,
without claiming biological validation or forecasting scientific impact.

---

*Word count: 248 (title excluded).*

## Evidence boundaries for the manuscript

| Claim | Evidence and boundary |
|-------|-----------------------|
| PPS deemphasizes large annotations | On the heart-failure panel, the highest final-PPS term contained 6 genes and the top 15 ranged from 5 to 103 genes. Term size and final PPS had rho = -0.9293 within the top 15. Because specificity is an explicit PPS component, this is a consistency check rather than independent validation. |
| Uncapped counts preserve literature discrimination | Heart-failure exact-query counts ranged from 31 to 10,868, a 350.6-fold span, while the capped display set ranged from 26 to 30 abstracts, a 1.15-fold span. |
| Seven current verified gaps were detected | Seven of 133 real-panel hypotheses met the prespecified zero-count rule in the regenerated benchmark. A zero means no PubMed title/abstract record matched that exact query in the benchmark snapshot, not that the biology is globally unreported. |
| Grounding invariants held | All 40 control hypotheses were Ungrounded and none of the 133 real-panel hypotheses was Ungrounded. Because the controls motivated the gate, this is a development regression invariant, not an unbiased estimate of specificity. |
| The temporal holdout was negative overall | Across all 133 real-panel hypotheses, Discovery Score versus 2021-2026 growth had rho = -0.0635. The sensitivity analysis among 122 hypotheses with nonzero pre-cutoff counts had rho = +0.0225. Pathways overlap within panels, so these correlations are descriptive. |

The manuscript deliberately does not claim global biological novelty,
experimental validation, out-of-sample specificity, predictive validity, or a
degree-aware network null. The Discovery Score is an auditable triage heuristic
for literature-sparse query intersections, not a forecast of scientific impact.
