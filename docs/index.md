# CardioXNet Documentation

This documentation set is intentionally short. The goal is to explain how to run the app, how to interpret the pipeline, and which configuration choices materially change the result set.

## Start Here

- [README](../README.md): project overview, single-port no-build setup, and test commands
- [Methods & Scientific Rigor](METHODS.md): methodology, novelty definition, scoring, statistics, limitations, and the improvement roadmap
- [Configuration Guide](CONFIGURATION.md): backend settings and the UI presets they influence

## Core Workflow

CardioXNet follows a staged discovery funnel:

1. Seed genes are validated.
2. STRING expands the local functional neighborhood.
3. Primary pathway enrichment creates the first candidate set.
4. Secondary pathway enrichment broadens discovery beyond the original seed list.
5. Pathway aggregation produces a replicated candidate set.
6. The Pathway Prioritization Score (PPS) scores aggregated pathways on significance, effect size,
   gene-set specificity and replication.
7. Semantic cardiac filtering and redundancy reduction narrow the shortlist.
8. Enhanced validation adds GTEx cardiac expression, a size-matched permutation null with
   Benjamini-Hochberg FDR control, and therapeutic target evidence.
9. Literature mining measures the PubMed corpus size at the (pathway x seed genes x disease)
   intersection and traces each hypothesis back to its seed genes.
10. An optional cardiac-name filter can be enabled for confirmatory work; it is **off by default**
    because it removes exactly the under-reported pathways the tool exists to surface.
11. Novelty and the **Discovery Score** (PPS x literature novelty) produce the final ranking.
12. Important genes are generated from top pathways.
13. Reports and exports are generated.

The exact current implementation workflow is captured in [workflow_diagram.mmd](../workflow_diagram.mmd).

## Interpreting Results

- Final pathways are prioritized candidates, not confirmed novel findings.
- Lower seed-overlap pathways are useful leads, but they still require literature review.
- PubMed corpus size is a screening signal, not a definitive novelty adjudication step: a low count
  can reflect vocabulary mismatch as easily as a genuine gap.
- **Literature novelty** (`novelty_tier`) and **seed-independence** measure different things. The
  first is about how much has been published at the intersection; the second is a structural property
  of where the pathway came from. A pathway can be either without being the other.
- The permutation q-value confirms an overlap is not chance. Because the null samples the whole
  protein-coding genome, most genuinely enriched pathways clear it comfortably, so it should not be
  read as a ranking among strong hypotheses.
- Important genes highlight recurrence across highly ranked pathways and may include therapeutic evidence from curated annotations and Open Targets.

## Where To Look In The App

- `/`: gene entry and preset-based configuration
- `/documentation`: concise workflow and interpretation notes
- `/api-reference`: REST and WebSocket interface summary

## Suggested Review Pattern

1. Run the balanced preset first.
2. Compare with exploratory mode if the shortlist is too narrow or too obvious.
3. Review top pathways manually for synonym overlap and domain relevance.
4. Only make novelty claims after manual literature screening.
