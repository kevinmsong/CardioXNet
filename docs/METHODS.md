# CardioXNet — Methods & Scientific Rigor

This document describes the discovery methodology, scoring, statistical treatment, limitations,
and a roadmap of design/algorithmic improvements. It is intended to make runs interpretable and
reproducible.

---

## 1. Goal: known → unknown

CardioXNet starts from a small set of **seed genes** (what is *known*) and reasons outward to
**unreported cardiac pathways** (the *unknown*). The core idea is a two-level expansion:

1. **Network expansion** around the seeds (protein–protein interactions), then
2. **Literature-driven expansion** of each primary pathway, which introduces genes the seeds are
   not directly connected to and therefore reveals pathways unreachable from the seeds alone.

Pathways already annotated to the seeds (per Reactome) are explicitly filtered out so the output
concentrates on new biology.

---

## 2. Pipeline stages

| Stage | Method | Key parameters / sources |
|-------|--------|--------------------------|
| Seed validation | Symbol → NCBI Entrez mapping | NCBI E-utilities |
| Functional neighborhood | Union of high-confidence STRING partners of seeds | `string_neighbor_count` (default 75), `string_score_threshold` (0.60) |
| Primary enrichment | Over-representation analysis across GO:BP, KEGG, Reactome, WikiPathways | g:Profiler; `fdr_threshold` (0.05) |
| Known-pathway filter | Remove pathways where seeds are ≥50% of pathway genes / already Reactome-annotated | Reactome |
| Secondary expansion | For top primary pathways, mine PubMed for co-mentioned genes; re-enrich the expanded set | `pubmed_max_results`, `semantic_max_hypotheses_for_literature` |
| Aggregation | Deduplicate pathway instances; combine p-values (Fisher's method); weight by replication support | `min_support_threshold`, `aggregation_strategy` |
| Pathway prioritization | Weighted composite of significance, effect size, specificity, replication (below) | `db_weights` |
| Cardiac semantic filtering | Curated cardiovascular term scoring + disease-context focus | `semantic_relevance_threshold`, `disease_context`, `enforce_final_name_filter` (default off) |
| Enhanced validation | Size-matched permutation null vs the protein-coding genome + Benjamini-Hochberg FDR, GTEx v8 cardiac expression, ChEMBL/DrugBank druggability | `n_permutations` (default 1000) |
| Literature mining | Per-hypothesis PubMed query (pathway + contributing seed genes + disease context); relevance scoring | `pubmed_max_results` |
| Seed-gene tracing | Record full seed → primary → secondary → final lineage per hypothesis | — |
| Topology | Centrality (degree, betweenness, closeness, eigenvector, PageRank), modules, crosstalk, druggable targets | NetworkX |
| Novelty & discovery | PubMed corpus size at (pathway x seeds x disease) -> literature saturation -> Discovery Score | NCBI E-utilities `esearch` |

---

## 3. Novelty and the Discovery Score

Two different properties are computed. They are reported separately and must not be conflated.

**Literature novelty** is the quantity the Discovery Score weights. For each hypothesis a PubMed
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
are never emitted alone for the same reason. A pathway whose name is entirely generic yields an empty
pathway clause and is correctly recorded as saturated rather than novel.

Saturation uses the **total number of matching records** (the `esearch` `Count` field), not the
number of abstracts downloaded. Retrieval is capped at a few dozen records, so counting retrieved
citations pins saturation at its ceiling for every pathway:

```
saturation = log10(hits + 1) / log10(1001)          # 0 at no records, 1.0 at >= 1000 records
novelty    = (2 x (1 - saturation) + gene_novelty) / 3
tier       = Highly Novel >= 0.80 | Novel >= 0.55 | Emerging >= 0.30 | Established
```

**Discovery Score = PPS x novelty** is the final ranking. It surfaces pathways that are both well
supported by the enrichment evidence and under-reported for these seeds in this disease context.

**Seed-independent** is a separate *structural* flag: seed genes account for fewer than 50% of the
pathway evidence genes, so the pathway was reached by expansion rather than being one the seeds are
already annotated to. It carries no literature information.

Novelty is relative to the seeds, the disease context and PubMed at run time; absence of records is
not proof of biological novelty.

---

## 4. Pathway Prioritization Score (PPS)

```
PPS = db_weight x centrality_weight x ( 0.30 x significance
                                      + 0.30 x effect_size
                                      + 0.25 x specificity
                                      + 0.15 x replication )
```

Each term is normalised to [0, 1] before weighting:

- **significance** = `min(-log10(p_adj) / 10, 1)` - saturates at p_adj = 1e-10, beyond which
  differences reflect annotation bias and the numerical floor of the test rather than biology.
- **effect_size** = `min(log2(fold_enrichment) / log2(10), 1)`, where
  `fold_enrichment = observed / (term_size x query_size / effective_domain_size)`. Falls back to the
  recovered fraction of the term when the enrichment test does not report the sizes.
- **specificity** = `1 - min(log10(term_size) / log10(500), 1)` - 1.0 for a tightly scoped term,
  0.0 for a term of 500+ genes.
- **replication** = `min(support_count / 5, 1)` - agreement across independent primary enrichments.
- **db_weight** - source reliability (Reactome/KEGG 1.5, WikiPathways 1.2, GO:BP 1.0).
- **centrality_weight** = `1 + 0.5 x seed_proximity + 0.3 x pagerank_percentile` (range 1.0-1.8).

> **PPS is not a GSEA normalized enrichment score.** There is no running-sum statistic and no
> permutation-derived normalisation behind it. The value is stored under the field name `nes_score`
> for backwards compatibility with persisted reports and the JSON API only.

**Why this replaced the previous formula.** The earlier score was
`log10(-log10(p_adj) x evidence_count x db_weight x agg_weight x centrality_weight + 1)`. Because
`-log10(p_adj)` was capped at 50 and essentially every top term reached that cap, the ranking reduced
to sorting by gene count, and maximally generic terms won every run. On the reference
VEGFA/MMP9/IL6/TNF/ACE panel the top hits were "cell surface receptor signaling pathway" (187 genes),
"multicellular organism development" (152) and "developmental process" (202) - terms true of almost
any gene list. Weighting effect size and specificity against significance removes that bias.

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
  z-score for the overlap between each pathway and the functional neighbourhood. Null sets are drawn
  uniformly from the HGNC protein-coding genome (19,410 symbols, snapshotted in
  `app/data/protein_coding_genes.txt`), *not* from the neighbourhood: sampling from the neighbourhood
  makes every permuted set the neighbourhood again and returns p close to 1 for every pathway.
  Degree matching is deliberately **not** applied - STRING degrees are known only for genes inside
  the neighbourhood, so degree bins would draw replacements almost exclusively from it and
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

- Pin external database versions where possible (STRING release, g:Profiler/Reactome version) —
  configured in `app/core/config.py`.
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
- **g:Profiler has no request timeout.** The official `gprofiler` library calls `requests.post`
  internally and exposes no timeout parameter, so a hung connection can stall a run indefinitely.
  There is no clean fix at the library boundary; if this bites, run with a watchdog.
- **Schemas drift silently.** The Open Targets query returned HTTP 400 for an extended period after
  the API renamed `knownDrugs`, and the caller swallowed it, so external druggability read zero
  throughout. An opt-in `pytest -m live` test now asserts the query still matches the schema; run it
  before trusting a druggability number.
- **Permutation budget:** the empirical p cannot fall below `1/(n_permutations + 1)`. The default of
  1000 gives a floor of 1.0e-3; raise `n_permutations` if finer resolution is required.
- **Permutation power:** because the null samples the whole protein-coding genome, a genuinely
  enriched pathway usually clears it by a wide margin. The test confirms that an overlap is not
  chance; it does not discriminate among strong hypotheses and should not be read as a ranking.
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
  heat diffusion** from seeds — a principled, hub-bias-aware neighborhood.
- **Empirical null as a core output.** Promote degree-preserving permutation testing (and random
  gene-set nulls) from optional to standard, reported alongside FDR q-values.
- **Graded novelty score.** Replace the binary known/unknown filter with a continuous metric:
  seed↔pathway PubMed co-occurrence baseline, publication recency, and network distance.
- **Embedding-based relevance.** Swap curated keyword scoring (semantic filter, literature
  relevance) for PubMedBERT / sentence-transformer cosine similarity — fewer false negatives and
  defensible, data-driven thresholds.
- **Consensus tiers.** Require ≥2 supporting databases and `min_support ≥ 2` for a "high-confidence"
  tier, surfaced in the UI.
- **Validation harness.** Positive control (hide a known cardiac gene; confirm rediscovery) and
  negative control (random seed sets) to estimate an empirical false-discovery rate.
