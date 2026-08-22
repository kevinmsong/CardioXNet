# CardioXNet manuscript workspace

Drafts, figures and tables for the CardioXNet methods paper.

## Contents

| Path | What it holds |
|------|---------------|
| `abstract.md` | The 250-word abstract. |
| `figures/` | Generated figures (`.pdf` vector + `.png` at 300 dpi). |
| `tables/` | Generated tables (`.csv` for import, `.md` for review). |
| `benchmark_report.md` | Full benchmark results with the numbers the abstract cites. |

Figures and tables are **generated, never hand-edited** — regenerate them rather
than patching a value, so what the manuscript claims always matches what the code
produced.

## Regenerating everything

```bash
# 1. Run the analyses (real seed panels + negative controls). ~1 h, hits live APIs.
python bench/run_suite.py

# 2. Temporal-holdout validation. Cached, so reruns are free.
python bench/temporal_holdout.py \
    --runs bench/out/hf_inflammatory.json bench/out/dcm_structural.json \
           bench/out/arrhythmia_channels.json bench/out/mi_ischemic.json \
    --cutoff 2020 --through 2026 --out bench/out/holdout.json

# 3. Figures and tables.
python bench/make_figures.py --manifest bench/out/manifest.json \
    --holdout bench/out/holdout.json --out paper
```

`bench/out/` is git-ignored: it holds raw analysis JSON and the PubMed count
cache, which are large and reproducible. Only the drafts and the generated
figures/tables in this directory are tracked.

## Reproducibility notes

- The permutation background is a pinned snapshot
  (`app/data/protein_coding_genes.txt`, HGNC protein-coding symbols retrieved
  2026-08-21), so empirical p-values are comparable across runs.
- `PermutationTester` uses a seeded private RNG (default seed 20260821).
- PubMed counts are cached in `bench/out/pubmed_counts.json`. Delete it to
  re-query live; keep it to reproduce the exact numbers in the manuscript.
- External resources that are *not* pinned and will drift: STRING v11.5,
  g:Profiler, GTEx v8, ChEMBL and PubMed itself. Record the run date with any
  reported figure.
