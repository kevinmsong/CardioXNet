# CardioXNet IEEE Access manuscript workspace

This directory contains the IEEE Access manuscript source, benchmark
documentation, figures, tables, and rendered review copy. The required front
matter affiliation is Department of Biomedical Engineering, The University of
Alabama at Birmingham.

## Contents

| Path | Contents |
|------|----------|
| `CardioXNet_IEEE_Access.tex` | IEEE Access manuscript source |
| `CardioXNet_IEEE_Access.pdf` | Rendered manuscript for visual review |
| `references.bib` | Bibliographic database |
| `abstract.md` | Standalone 248-word abstract and claim boundaries |
| `benchmark_report.md` | Regenerated benchmark values and interpretation limits |
| `figures/` | Publication PDFs and 600-dpi PNG exports |
| `tables/` | Generated CSV tables and Markdown review copies |

Figures and tables are generated from benchmark artifacts. Regenerate them
after any analysis or filtering change so that the numerical claims, captions,
and graphics remain synchronized.

The `ieeeaccess.cls`, IEEE bibliography style, font assets, and archived
template package are from the official IEEE Access LaTeX template dated May 13,
2026.

## Regenerating the analyses and figures

The commands below call live external resources and can take approximately one
hour for the complete suite.

```bash
# 1. Regenerate four real panels and three controls.
python bench/run_suite.py

# 2. Recompute the all-hypothesis temporal holdout.
python bench/temporal_holdout.py \
    --runs bench/out/hf_inflammatory.json bench/out/dcm_structural.json \
           bench/out/arrhythmia_channels.json bench/out/mi_ischemic.json \
    --cutoff 2020 --through 2026 --retrieved-on YYYY-MM-DD \
    --cache bench/out/pubmed_counts_holdout.json \
    --out bench/out/holdout.json

# 3. Regenerate figures and tables.
python bench/make_figures.py --manifest bench/out/manifest.json \
    --holdout bench/out/holdout.json --out paper
```

Main-benchmark PubMed counts are cached in `bench/out/pubmed_counts.json`; the
holdout command uses its dedicated cache. These caches reproduce counts already
retrieved. A genuinely fresh retrieval requires a new or cleared cache and a
newly recorded retrieval date.

The application views in Figure 6 are generated from the committed
deterministic fixture, rather than from a live benchmark run:

```bash
npm run screenshots:manuscript
```

Figure 7 summarizes representative cardiovascular literature-gap candidates.
Its exact-query zeros are operational results at the pathway,
contributing-gene, and disease intersection, not claims of globally unreported
biology.

## Figure quality and interpretation

- PDF is the preferred manuscript format. Matching PNG exports are written at
  600 dpi for raster-delivery requirements.
- Scientific plots use a colorblind-safe palette plus redundant marker shapes
  or hatching where category distinctions matter.
- Plot text uses regular sans serif fonts and defines abbreviations or encoded
  quantities in the caption.
- Every figure file is named for the number it compiles to, so `figN_*` is
  Figure N. Keep it that way: if a float moves, renumber the file with it.
- Figure 4 is the grounding development benchmark. Its 40/40 control and 0/124
  real-panel results are regression invariants, not unbiased specificity.
- Figure 5 is the all-hypothesis temporal holdout. Correlations are descriptive
  because pathways overlap within panels.
- Figures 6 and 7 demonstrate interface behavior and are not additional
  scientific evidence. They render a fixed demonstration fixture, so their
  values are deliberately not the benchmark values in Table 2.
- Figure 8 is the verified exact-query gap set.

## Building and checking the manuscript

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error CardioXNet_IEEE_Access.tex
bibtex CardioXNet_IEEE_Access
pdflatex -interaction=nonstopmode -halt-on-error CardioXNet_IEEE_Access.tex
pdflatex -interaction=nonstopmode -halt-on-error CardioXNet_IEEE_Access.tex
```

Render every page to an image and inspect captions, float placement, font
legibility, table overflow, and figure completeness before submission. The
current draft uses the IEEE Access two-column class and retains `XX` as the
volume placeholder until publication metadata are assigned.

## Reproducibility and failure semantics

- The permutation baseline contains 19,410 pinned human protein-coding symbols.
  Genes present in an analysis but absent from that snapshot are added before
  sampling, so the effective benchmark pools contain 19,410 to 19,415 symbols.
- The permutation procedure uses a private random-number generator with default
  seed 20260821 and 1,000 size-matched draws per testable pathway.
- g:Profiler calls run in spawned workers with a configurable hard deadline per
  attempt, 120 seconds by default, and a configurable retry count, two by default. Timed-out workers are terminated and
  reaped. Retry exhaustion fails the pipeline explicitly rather than returning
  malformed or partial enrichment. A complete empty result is valid.
- STRING, g:Profiler, GTEx endpoints, Open Targets, and PubMed are live resources
  that can drift. Record retrieval timestamps, endpoints, and configured or
  response-verified resource identifiers with reported values. ChEMBL-derived
  druggability is part of the embedded curated snapshot, not a live query.
- `bench/out/` is ignored by Git because it contains reproducible raw analysis
  JSON and query caches. The manuscript, generated figures, and generated
  tables in `paper/` are tracked.
