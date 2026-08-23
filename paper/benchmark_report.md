# CardioXNet benchmark report

The main benchmark and temporal holdout were regenerated from fresh retrievals.
The holdout included all 133 real-panel hypotheses.

External resources recorded for the main run were STRING v12.0, the configured
g:Profiler identifier `e104_eg51_p15`, GTEx v8, optional live Open Targets, and
PubMed via NCBI E-utilities. Baseline druggability used an embedded curated
snapshot derived from DrugBank v5.1.10, TTD 2023, ChEMBL v31, and related
references. The g:Profiler identifier is declared configuration metadata rather
than a build value verified from the response. The permutation baseline is a pinned snapshot of 19,410 human
protein-coding symbols. Analysis genes absent from the
snapshot are added before sampling, yielding effective run-specific pools of
19,410 to 19,415 symbols. The private permutation random-number generator uses
seed 20260821.

This report distinguishes an exact-query literature gap from global biological
novelty. A zero means that no PubMed title/abstract record matched the
prespecified pathway, contributing-gene, and disease query on the retrieval
date. It does not show that the underlying pathway or biology is unreported
under other terminology or in full text.

## 1. Benchmark analyses

Four cardiovascular seed panels represented distinct disease biology. Three
control panels tested whether the grounding safeguard continued to reject
novelty estimates when the seeds had insufficient disease literature. Every
analysis used five seeds and the `balanced` preset.

| Run | Kind | Seed genes | Disease context | Runtime | Hypotheses |
|-----|------|------------|-----------------|--------:|-----------:|
| `hf_inflammatory` | Real | VEGFA, MMP9, IL6, TNF, ACE | Heart failure | 257 s | 21 |
| `dcm_structural` | Real | MYH7, TTN, LMNA, MYBPC3, TNNT2 | Cardiomyopathy | 181 s | 34 |
| `arrhythmia_channels` | Real | SCN5A, KCNQ1, KCNH2, RYR2, CACNA1C | Arrhythmia | 355 s | 41 |
| `mi_ischemic` | Real | LDLR, APOB, PCSK9, NOS3, EDN1 | Myocardial infarction | 323 s | 37 |
| `olfactory` | Control | OR51E2, OR2W1, OR1A1, OR5K1, OR10A4 | Heart failure | 96 s | 12 |
| `random_1` | Control | RPF2, CLRN3, PRKAG1, OR8U9, CACNA1D | Heart failure | 202 s | 19 |
| `random_2` | Control | C2CD4A, GORASP1, CHIC1, VCY, PLCD4 | Heart failure | 144 s | 9 |

The four real panels produced 133 hypotheses and the controls produced 40.
These outputs were regenerated in full after the semantic-filter change because
that filter changes the pathways eligible for secondary expansion.

## 2. Ranking behavior

The corrected Pathway Prioritization Score (PPS) first combines adjusted
significance, fold enrichment, annotated-set specificity, and support from
multiple upstream primary pathways, then applies the bounded semantic
cardiovascular-relevance multiplier used by the implementation. Cardiac
expression and druggability are separate annotations. They do not enter PPS or
the Discovery Score.

On `hf_inflammatory`, the final-PPS-ranked top term contained 6 annotated genes,
and the top 15 ranged from 5 to 103 genes. Within those 15, term size and final
PPS were inversely rank-associated (Spearman rho = -0.9293; n = 15). Because
gene-set specificity is an explicit PPS component, this is a descriptive
consistency check rather than independent validation.

## 3. Uncapped literature counts

For `hf_inflammatory`, the uncapped PubMed title/abstract counts at the exact
pathway, contributing-gene, and disease intersections ranged from 31 to 10,868,
a 350.6-fold span. The abstract sets retained for display ranged only from 26 to
30 records because retrieval was capped, a 1.15-fold span. The uncapped count
therefore preserves discrimination that the displayed evidence set cannot.

This distinction repairs two earlier measurement errors. Literature saturation
had been derived from the number of retrieved abstracts rather than the total
query count, and a broad fallback had been joined with `OR` rather than being
constrained by the pathway clause. The current score uses the uncapped count
from the prespecified conjunctive query. Retrieved abstracts are evidence for
inspection, not the saturation denominator.

## 4. Verified exact-query gaps

Seven of 133 real-panel hypotheses met the prespecified verified-gap rule in
the regenerated benchmark. The rule requires a grounded seed-disease corpus, a searchable
pathway concept with at least 20 PubMed records, and zero records at the exact
pathway, contributing-gene, and disease intersection.

| Panel | Candidate | Discovery Score | Fold enrichment | Empirical q | Exact-query records | Pathway-concept records |
|-------|-----------|----------------:|----------------:|------------:|--------------------:|------------------------:|
| DCM structural | GAB1 signalosome | 2.0087 | 15.824 | 0.001617 | 0 | 1,785 |
| DCM structural | NTRK2 (TRKB) signaling | 1.9840 | 17.549 | 0.001617 | 0 | 817 |
| Arrhythmia channels | cGMP-PKG signaling | 1.9070 | 7.908 | 0.001241 | 0 | 1,361 |
| Arrhythmia channels | GPER1 signaling | 1.8645 | 8.376 | 0.001241 | 0 | 563 |
| MI ischemic | P2Y12 signaling | 1.8077 | 8.062 | 0.001275 | 0 | 1,854 |
| MI ischemic | GPER1 signaling | 1.7996 | 6.719 | 0.001275 | 0 | 563 |
| MI ischemic | Oxytocin signaling | 1.7488 | 6.995 | 0.001275 | 0 | 29,242 |

These candidates combine 6.7- to 17.5-fold enrichment with empirical q-values
of 0.00124 to 0.00162 under the uniform genome-scale null. They are rank-leading
literature-sparse intersections for review, not experimentally validated
mechanisms. For P2Y12, the contribution is not the pathway name in isolation.
Its zero applies only to the exact query connecting the pathway to the
contributing genes from this panel and the myocardial-infarction context.

## 5. Grounding regression invariant

The seed-disease count is measured once per run before pathway-level novelty is
interpreted.

| Panel | Seed-disease records | Grounding result |
|-------|---------------------:|------------------|
| `hf_inflammatory` | 10,868 | Grounded |
| `dcm_structural` | 2,487 | Grounded |
| `arrhythmia_channels` | 1,538 | Grounded |
| `mi_ischemic` | 2,373 | Grounded |
| `olfactory` | 0 | Ungrounded |
| `random_1` | 6 | Ungrounded |
| `random_2` | 1 | Ungrounded |

All 40 control hypotheses were Ungrounded and none of the 133 real-panel
hypotheses was Ungrounded. Both invariants held exactly after regeneration.
This test catches the prior failure in which literature-naive controls appeared
maximally novel. Because these controls helped motivate the grounding gate and
were retained during development, the 40/40 versus 0/133 separation is a
development regression invariant. It is not an unbiased estimate of
out-of-sample specificity.

## 6. Temporal holdout

The temporal holdout included all 133 real-panel hypotheses. Pre-cutoff PubMed
records were censored at 2020-12-31. Post-cutoff records began on 2021-01-01
and extended through the follow-up retrieval snapshot. Relative growth was defined as
`post_count / (pre_count + 1)`. Eleven intersections met the verified-gap rule
at the cutoff, and none was Ungrounded.

| Comparison with post-cutoff growth | Spearman rho | n |
|------------------------------------|-------------:|--:|
| Discovery Score, all hypotheses | -0.0635 | 133 |
| Composite novelty, all hypotheses | -0.0283 | 133 |
| PPS, all hypotheses | -0.1462 | 133 |
| Discovery Score, nonzero pre-cutoff count only | +0.0225 | 122 |

Panel-specific Discovery Score associations were heterogeneous.

| Panel | Spearman rho |
|-------|-------------:|
| Arrhythmia channels | +0.0485 |
| DCM structural | -0.2235 |
| Heart failure | +0.7165 |
| Myocardial infarction | -0.3826 |

Operational-tier sizes and median growth were:

| Tier at the cutoff | n | Median growth |
|--------------------|--:|--------------:|
| Established | 12 | 0.5413 |
| Emerging | 48 | 0.6061 |
| Novel | 55 | 0.6970 |
| Highly Novel | 18 | 0.0000 |

The overall association was negligible, and panel-specific associations varied
in direction. The holdout therefore does not validate the Discovery Score as a
forecast of publication growth or scientific importance. It supports the more
limited interpretation of the score as a transparent triage measure. Pathways
overlap within panels, so all correlations are descriptive and the reported
sample sizes count pathway hypotheses rather than independent biological
replicates.

## 7. Statistical and operational safeguards

- Each pathway overlap is evaluated against 1,000 size-matched random
  neighborhoods drawn uniformly from the effective protein-coding pool. The
  finite-sampling correction gives a minimum attainable empirical p-value of
  `1/1001`.
- Benjamini-Hochberg correction is applied across all testable reported
  pathways. Untestable pathways retain missing values and are excluded from the
  correction family.
- The uniform null does not preserve STRING degree. It tests whether overlap
  exceeds a random gene-set expectation, not whether one already strong
  candidate outranks another.
- In one paired rerun, 6 of 33 shared PPS values changed, the maximum relative
  change was 6.0%, and no operational tier changed. This single comparison
  demonstrates live-resource variation but does not estimate a general noise
  floor.
- The official g:Profiler client performs its internal HTTP call without an
  exposed timeout. CardioXNet now runs each profile attempt in a fresh spawned
  process with a configurable hard wall-clock deadline, 120 seconds by default. A worker writes to a
  private temporary file and sends a completion sentinel only after the full
  response is stored. A timed-out worker is terminated and reaped, with kill
  escalation if required. Transient failures receive a configurable number of
  bounded retries, two by default, with exponential backoff. Exhaustion raises
  an explicit pipeline failure; unreadable, malformed, interrupted, or partial
  enrichment is never accepted. A complete empty result validly indicates that
  no terms met the enrichment criteria.
- Open Targets schema failures, missing GTEx symbols, malformed STRING records,
  and failed PubMed counts are represented explicitly rather than silently
  converted to zero evidence.

## 8. Verification scope

The automated regression suite covers score components, multiple testing,
background construction, grounding, semantic filtering, query construction,
literature-count semantics, g:Profiler deadline enforcement, external-client
failure states, persistence, and exports. Browser-level checks cover ranking,
missing-value display, component explanations, table integrity, navigation, and
downloads against a committed deterministic fixture. This report intentionally
does not hardcode the number of tests because the suite evolves independently
of the benchmark claims.

## 9. Interpretation limits

- Literature novelty is lexical and restricted to PubMed titles and abstracts.
  Exact-query zeros require synonym-expanded review and do not cover full text.
- The pathway-concept check reduces, but cannot eliminate, vocabulary mismatch.
- Control separation is a development invariant, not unbiased specificity.
- The temporal analysis is descriptive because pathways overlap within panels.
- Live resources drift, so retrieval timestamps, endpoints, and configured or
  response-verified resource identifiers must accompany reported values.
- The benchmark is human and cardiovascular. Generalization to other species or
  disease domains has not been established.
- GTEx bulk-tissue expression is not cell-type or disease-state evidence, and
  druggability does not imply therapeutic benefit.
- Every output is a computational hypothesis for expert and experimental
  assessment.
