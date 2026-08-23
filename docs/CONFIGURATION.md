# Configuration Guide

CardioXNet exposes a small preset-based configuration in the frontend. The backend supports environment variables and per-analysis `config_overrides`. The YAML files under `config/` document the configuration schema but are not loaded automatically.

## Configuration Order

Settings are applied in this order:

1. Backend defaults from code
2. Environment variables, including values in `.env`
3. Per-request `config_overrides`

To turn a value from `config/config.example.yaml` into a runtime setting, use its `NETS_` environment-variable form or pass it in `config_overrides`.

## Frontend Presets

The home page maps UI choices to backend settings.

### Discovery profile

- `Focused`: narrower funnel, stricter FDR, smaller final result set
- `Balanced`: uses backend defaults
- `Exploratory`: larger STRING neighborhood, more primary pathways expanded, broader final result cap

### Evidence depth

- `Fast screening`: reduced literature depth, permutations off
- `Standard review`: default literature depth with permutations on
- `Deep evidence pass`: larger literature pass and more permutations

### Lower seed-overlap bias

When enabled, the frontend lowers `seed_overlap_threshold` to favor pathways that move farther away from the original seed list.

## High-Impact Backend Parameters

These are the settings that most directly shape the funnel:

| Parameter | Why it matters |
| --- | --- |
| `string_neighbor_count` | Controls how broadly the seed neighborhood expands |
| `primary_pathways_to_expand` | Controls how many leading primary pathways seed the secondary discovery stage |
| `fdr_threshold` | Sets statistical strictness during enrichment filtering |
| `min_support_threshold` | Requires recurrence across pathway branches before promotion |
| `semantic_relevance_threshold` | Controls how much cardiac semantic evidence is needed |
| `semantic_max_results` | Caps the final returned pathway set |
| `semantic_max_hypotheses_for_literature` | Limits how many final pathways receive PubMed screening |
| `pubmed_max_results` | Sets the literature retrieval depth per query |
| `permutation_test_enabled` | Enables or disables empirical validation |
| `n_permutations` | Sets the depth of permutation-based testing |
| `seed_overlap_threshold` | Controls how close final candidates can remain to the original seed list |
| `gprofiler_timeout_seconds` | Sets the hard wall-clock deadline for each process-isolated g:Profiler attempt |

## Example `config_overrides`

```json
{
  "string_neighbor_count": 110,
  "primary_pathways_to_expand": 45,
  "fdr_threshold": 0.08,
  "semantic_relevance_threshold": 0.11,
  "semantic_max_results": 100,
  "seed_overlap_threshold": 0.35
}
```

## Practical Advice

- Use balanced settings as the default baseline.
- Increase `primary_pathways_to_expand` before you start relaxing too many later filters.
- Keep `min_support_threshold` at `2` or higher if you want replicated signals rather than one-off branches.
- Do not interpret a low literature count alone as evidence that a pathway is unreported.
