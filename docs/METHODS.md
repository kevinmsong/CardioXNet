# CardioXNet - Methods & Scientific Rigor

This document describes the discovery methodology, scoring, statistical treatment, limitations,
and a roadmap of design/algorithmic improvements. It is intended to make runs interpretable and
reproducible.

---

## 1. Goal: known → unknown

CardioXNet starts from a small set of **seed genes** and reasons outward to pathway hypotheses that
can be screened for prespecified, literature-sparse pathway-gene-disease intersections. The core
idea is a two-level expansion:

1. **Network expansion** around the seeds (protein–protein interactions), then
2. **Secondary expansion** from primary-pathway member genes, optionally augmented with
   literature-derived genes for the highest-priority primaries.

Pathways already annotated to the seeds (per Reactome) are explicitly filtered out so the output
concentrates on expansion-derived connections. This structural filter does not establish that a
connection is unreported; that question is evaluated separately with the grounded PubMed query.

---

## 2. Pipeline stages

| Stage | Method | Key parameters / sources |
|-------|--------|--------------------------|
| Seed validation | Symbol → NCBI Entrez mapping | NCBI E-utilities |
| Functional neighborhood | Union of high-confidence STRING partners of seeds | `string_neighbor_count` (default 75), `string_score_threshold` (0.60) |
| Primary enrichment | Over-representation analysis across GO:BP, KEGG, Reactome, WikiPathways | g:Profiler; `fdr_threshold` (0.05) |
| Known-pathway filter | Remove pathways where seeds are ≥50% of pathway genes / already Reactome-annotated | Reactome |
| Secondary expansion | Re-enrich primary member genes; optionally augment the top primaries with PubMed-derived genes | `pubmed_max_results`, `semantic_max_hypotheses_for_literature` |
| Aggregation | Deduplicate pathway instances; combine per-query adjusted enrichment values with Fisher's method; record recurrence across upstream branches | `min_support_threshold`, `aggregation_strategy` |
| Pathway prioritization | Base weighted composite of significance, effect size, specificity, and upstream support, followed by the bounded semantic multiplier below | `db_weights` |
| Cardiac semantic filtering | Deterministic lexical cardiovascular relevance plus disease-context focus and progressive retention | `semantic_relevance_threshold`, `semantic_max_results`, `disease_context`, `enforce_final_name_filter` (default off) |
| Enhanced validation | Size-matched permutation null vs the protein-coding genome + Benjamini-Hochberg FDR, GTEx v8 cardiac expression, an embedded curated drug-target snapshot, and optional live Open Targets evidence | `n_permutations` (default 1000) |
| Literature mining | Per-hypothesis PubMed query (pathway + contributing seed genes + disease context); relevance scoring | `pubmed_max_results` |
| Seed-gene tracing | Record full seed → primary → secondary → final lineage per hypothesis | - |
| Topology | Centrality (degree, betweenness, closeness, eigenvector, PageRank), modules, crosstalk, druggable targets | NetworkX |
| Novelty & discovery | PubMed corpus size at (pathway x seeds x disease) -> literature saturation -> composite novelty -> Discovery Score | NCBI E-utilities `esearch` |

---

## 3. Novelty and the Discovery Score

Two different properties are computed. They are reported separately and must not be conflated.

**Literature novelty** is the primary component of the composite novelty term. For each hypothesis a PubMed
query is built for the *intersection* of the pathway concept, the contributing seed genes and the
disease context:

```
(gene1[TIAB] OR ... OR gene8[TIAB])
  AND (pathway phrases / distinctive unigrams [TIAB])
  AND (disease-context terms [TIAB])
```

The three clauses are combined with `AND`. This matters: an earlier revision OR-ed the pathway terms
into the same clause as a broad cardiac fallback, which made the pathway clause inert. Every pathway
then resolved to the same query and returned the same ~30 papers (mean pairwise Jaccard 0.55 across
citation sets), leaving novelty with no signal to read. Generic unigrams ("heart", "muscle", "rate")
are never emitted alone for the same reason. When informative-token expansion is empty, the complete
pathway name is retained as a quoted title/abstract phrase. A nominal strict query therefore never
silently degrades to the broader gene-by-disease corpus.

Saturation uses the **total number of matching records** (the `esearch` `Count` field), not the
number of abstracts downloaded. Retrieval is capped at a few dozen records, so counting retrieved
citations pins saturation at its ceiling for every pathway:

```
saturation = log10(hits + 1) / log10(1001)          # 0 at no records, 1.0 at >= 1000 records
literature_novelty = 1 - saturation
composite_novelty  = (2 x literature_novelty + gene_novelty) / 3
tier               = Highly Novel >= 0.80 | Novel >= 0.55 | Emerging >= 0.30 | Established
```

**Discovery Score = PPS x composite novelty** is the final ranking. It surfaces pathways that are both well
supported by enrichment evidence and literature-sparse under the prespecified title/abstract query
for these seeds and this disease context.

**Seed-independent** is a separate *structural* flag: seed genes account for fewer than 50% of the
pathway evidence genes, so the pathway was reached by expansion rather than being one the seeds are
already annotated to. It carries no literature information.

Novelty is relative to the seeds, the disease context and PubMed at run time; absence of records is
not proof of biological novelty.

---

## 4. Pathway Prioritization Score (PPS)

```
base_PPS = db_weight x ( 0.30 x significance
                       + 0.30 x effect_size
                       + 0.25 x specificity
                       + 0.15 x upstream_support )

PPS = base_PPS x (1 + semantic_cardiovascular_relevance)
```

Each term is normalized to [0, 1] before weighting:

- **significance** = `min(-log10(p_adj) / 10, 1)` - saturates at p_adj = 1e-10, beyond which
  differences reflect annotation bias and the numerical floor of the test rather than biology.
- **effect_size** = `min(log2(fold_enrichment) / log2(10), 1)`, where
  `fold_enrichment = observed / (term_size x query_size / effective_domain_size)`. Falls back to the
  recovered fraction of the term when the enrichment test does not report the sizes.
- **specificity** = `1 - min(log10(term_size) / log10(500), 1)` - 1.0 for a tightly scoped term,
  0.0 for a term of 500+ genes.
- **upstream support** = `min(support_count / 5, 1)` - recurrence across primary expansion
  branches. Those branches can overlap and this term is not independent replication.
- **db_weight** - source reliability (Reactome/KEGG 1.5, WikiPathways 1.2, GO:BP 1.0).
- **network topology** is reported separately and does not enter PPS. One-hop proximity is not used
  as a multiplier because the enriched evidence genes were selected from that same functional
  neighborhood; rewarding the overlap again would reuse rather than independently corroborate the
  enrichment evidence. PageRank is calculated later for topology interpretation.
- **semantic_cardiovascular_relevance** is a bounded lexical heuristic in [0, 1], derived from
  pathway terminology, optional disease-context terms, and explicit noncardiac penalties. The
  multiplier is therefore bounded in [1, 2]. Both the base PPS and multiplier are retained in the
  score breakdown. This term is not a trained or externally validated classifier.

The balanced benchmark uses an initial semantic threshold of 0.001. After semantic adjustment and
reranking, the first 30 candidates are retained without a further pathway-name condition. Positions
31-100 require either semantic relevance of at least 0.30 or an explicit cardiovascular or disease
term. Lower positions require relevance of at least 0.50 until the configured result cap is filled.
The final strict cardiac-name gate is separate and disabled by default.

> **PPS is not a GSEA normalized enrichment score.** There is no running-sum statistic and no
> permutation-derived normalization behind it. The value is stored under the field name `nes_score`
> for backwards compatibility with persisted reports and the JSON API only.

**Why this replaced the previous formula.** The earlier score was
`log10(-log10(p_adj) x evidence_count x db_weight x agg_weight x centrality_weight + 1)`. Because
`-log10(p_adj)` was capped at 50, the ranking could reduce to sorting largely by gene count and favor
generic terms. Weighting effect size and specificity against significance directly counters that
structural bias. In the regenerated heart-failure benchmark, term size was inversely rank-associated
with final PPS among the top 15. Because term-size specificity enters PPS, that observation is an
internal consistency check rather than independent validation.

The **expansion screen** that chooses which primary pathways are re-expanded is deliberately a
different, recall-oriented score, `min(-log10(p_adj), 20) x sqrt(evidence_count) x db_weight`.
Expansion supplies candidate material, so breadth helps there; applying the specificity penalty at
that stage starved the candidate pool and cut the reference run from 22 hypotheses to 3.

---

## 5. Statistical treatment

- **Multiple testing:** g:Profiler applies FDR correction per enrichment query (`fdr_threshold`).
- **Evidence combination:** when a pathway is supported by multiple primaries, p-values are combined
  with **Fisher's method**; a consistency score captures agreement across sources.
- **Empirical significance:** a **size-matched permutation null** estimates an empirical p-value and
  z-score for the overlap between each pathway and the functional neighborhood. Null sets are drawn
  uniformly from the HGNC protein-coding genome (19,410 symbols, snapshotted in
  `app/data/protein_coding_genes.txt`), *not* from the neighborhood: sampling from the neighborhood
  makes every permuted set the neighborhood again and returns p close to 1 for every pathway.
  Degree matching is deliberately **not** applied - STRING degrees are known only for genes inside
  the neighborhood, so degree bins would draw replacements almost exclusively from it and
  reintroduce the same degeneracy. The statistics record `degree_preserved: false`, so no control is
  claimed that was not applied.
- **Multiple testing on the empirical p-values:** Benjamini-Hochberg FDR across every reported
  hypothesis. Pathways whose null could not be built carry `q = null` and are excluded from the
  correction family rather than being assigned p = 1.
- **Resolution floor:** the smallest attainable empirical p is `1/(n_permutations + 1)`; at the
  default 1000 permutations this is 1.0e-3. The floor is reported alongside each p-value.
- **Tissue context:** GTEx cardiac expression ratio and specificity contextualize relevance.

---

## 6. Reproducibility

- Pin external database versions where possible. Each result stores the configured STRING release,
  declared g:Profiler and Reactome identifiers, endpoints, retrieval timestamps, and whether an
  identifier was verified from a live response.
- Results are persisted under `outputs/{analysis_id}/results.json` and are re-loadable by the API
  and UI, so any run can be re-opened and re-exported deterministically.
- The committed fixture (`outputs/analysis_fixture/`) provides a deterministic dataset for UI tests.

---

## 7. Limitations

- **Database & literature currency:** novelty and enrichment reflect the databases/PubMed at run
  time; absence of a pathway from the "known" set is not proof of true novelty.
- **Keyword-based relevance:** cardiac semantic and literature relevance use curated term lists,
  which can miss semantically related but lexically different evidence.
- **External API variability:** STRING/g:Profiler/PubMed availability and rate limits affect recall
  and runtime. Every client now carries an explicit failure sentinel, so a failed call is reported
  as unmeasured rather than as a measurement of zero, and PubMed count lookups retry on HTTP 429.
- **g:Profiler requires process isolation for a hard deadline.** The official `gprofiler` library
  calls `requests.post` internally and exposes no request-timeout parameter. CardioXNet runs every
  profile call in a fresh spawned process with a configurable wall-clock deadline (120 seconds by
  default). The parent terminates, reaps, and, if necessary, kills an overdue worker. By default,
  at most two transient retries are attempted; both the deadline and retry count are configurable.
  Exhaustion fails the enrichment stage explicitly. An unreadable, malformed, partial, or interrupted
  response is never treated as enrichment data; a complete empty result remains a valid enrichment
  outcome. This controls the hang but adds process-start overhead, and frozen Windows and macOS
  builds still require smoke testing.
- **Schemas drift silently.** The Open Targets query returned HTTP 400 for an extended period after
  the API renamed `knownDrugs`, and the caller swallowed it, so external druggability read zero
  throughout. An opt-in `pytest -m live` test now asserts the query still matches the schema; run it
  before trusting a druggability number.
- **Permutation budget:** the empirical p cannot fall below `1/(n_permutations + 1)`. The default of
  1000 gives a floor of 1.0e-3; raise `n_permutations` if finer resolution is required.
- **Permutation power:** because the null samples the whole protein-coding genome, a strongly
  enriched pathway usually clears it by a wide margin. The test provides evidence that an overlap
  exceeds the uniform random gene-set expectation; it does not discriminate among strong hypotheses
  and should not be read as a ranking.
- **Cardiac name filtering is off by default:** `enforce_final_name_filter` requires a cardiac or
  disease term in the pathway name. It is disabled because it is circular for a discovery tool - on
  the reference panel it cut 66 hypotheses to 23 and removed all 6 Highly Novel pathways. Enabling it
  raises precision for confirmatory work at a direct cost to novelty recall.
- **Correlation, not causation:** outputs are hypotheses for experimental follow-up.

---

## 8. Design & algorithmic roadmap

Recommendations to raise performance and scientific rigor. ⚡ marks low-risk quick wins.

### Performance
- ⚡ **NCBI API key + request batching.** Configure an E-utilities key (10 req/s) and batch
  ESearch/ESummary/EFetch instead of per-gene calls in `app/services/pubmed_client.py` to remove the
  observed HTTP 429 throttling and cut literature-mining time substantially.
- ⚡ **Persistent response cache.** The project already depends on `diskcache`; cache STRING /
  g:Profiler / Reactome / PubMed responses keyed by query. Repeat runs drop from minutes to seconds
  and become reproducible.
- **Bounded-concurrency async** for all external calls, and **approximate (sampled) betweenness**
  plus a network-size cap in `comprehensive_topology.py` to avoid O(n³) blow-ups on large graphs.

### Scientific rigor
- ⚡ **Provenance capture.** Seed the RNG and record external DB versions + timestamps in every
  report for full reproducibility.
- **Network propagation.** Replace the raw STRING neighbor union with **Random Walk with Restart /
  heat diffusion** from seeds - a principled, hub-bias-aware neighborhood.
- **Empirical null as a core output.** Promote degree-preserving permutation testing (and random
  gene-set nulls) from optional to standard, reported alongside FDR q-values.
- **Graded novelty score.** Replace the binary known/unknown filter with a continuous metric:
  seed↔pathway PubMed co-occurrence baseline, publication recency, and network distance.
- **Embedding-based relevance.** Swap curated keyword scoring (semantic filter, literature
  relevance) for PubMedBERT / sentence-transformer cosine similarity - fewer false negatives and
  defensible, data-driven thresholds.
- **Consensus tiers.** Require ≥2 supporting databases and `min_support ≥ 2` for a "high-confidence"
  tier, surfaced in the UI.
- **Validation harness.** Positive control (hide a known cardiac gene; confirm rediscovery) and
  negative control (random seed sets) to estimate an empirical false-discovery rate.
