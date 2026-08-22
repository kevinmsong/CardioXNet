# CardioXNet

**CardioXNet** is a cardiovascular pathway-discovery platform that reasons from *known* seed
genes to *unreported* cardiac pathways. Given a handful of genes, it assembles their functional
neighborhood, finds primary enriched pathways, then expands through the literature into
**secondary pathways** — surfacing cardiac mechanisms not already annotated for the seeds, each
traced back to its network evidence and PubMed citations.

It implements the **NETS** pipeline (Network Expansion & Topology Scoring): protein-interaction
expansion, multi-database enrichment, literature-driven secondary discovery, pathway prioritization
scoring, cardiac semantic filtering, permutation-based validation, literature-saturation novelty
scoring, and network topology analysis.

The headline output is the **Discovery Score** = pathway prioritization score x literature novelty,
which ranks pathways that are both well supported by the enrichment evidence *and* under-reported
at the intersection of (pathway x seed genes x disease context).

> **Lightweight & no-build.** The UI is server-rendered by FastAPI (Jinja2 + htmx + Alpine.js,
> with vendored JS — no CDN required). There is **no Node/npm/bundler build step** and no separate
> frontend server: one Python process serves the UI and the JSON API on a single port.

---

## Quick start

**Prerequisites:** Python 3.10+ (3.12 recommended). No Node.js required to run the app.

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** — enter seed genes (e.g. `PIK3R1 ITGB1 SRC`), pick an optional
disease context and an analysis depth, and start discovery. You'll watch each pipeline stage live
and land on the results automatically.

Optional: create a `.env` with `GROQ_API_KEY=...` to enable AI-assisted report narratives.

---

## How discovery works (known → unknown)

| Stage | What it does |
|-------|--------------|
| **Seed validation** | Map gene symbols to NCBI Entrez IDs. |
| **Functional neighborhood** | High-confidence STRING interaction partners around the seeds. |
| **Primary pathways** | g:Profiler enrichment (GO/KEGG/Reactome/WikiPathways); pathways *already known* for the seeds (per Reactome) are filtered out. |
| **Secondary expansion** | For each primary pathway, mine PubMed for co-mentioned genes; the expanded gene set reveals **unreported** secondary pathways. |
| **Aggregation & scoring** | Deduplicate pathway instances, combine evidence (Fisher's method), and score with the **Pathway Prioritization Score (PPS)** — a weighted composite of significance (0.30), fold enrichment (0.30), gene-set specificity (0.25) and cross-source replication (0.15). PPS is *not* a GSEA normalized enrichment score. |
| **Cardiac filtering** | Semantic filter keeps cardiovascular-relevant hypotheses, focused by the chosen disease context. |
| **Validation** | Size-matched permutation tests against the HGNC protein-coding genome with Benjamini–Hochberg FDR control, GTEx v8 cardiac expression, ChEMBL/DrugBank druggability. |
| **Literature mining** | Attach ranked PubMed citations to each hypothesis. |
| **Topology** | Hub genes and prioritized druggable therapeutic targets. |
| **Novelty & discovery** | PubMed corpus size at the (pathway x seeds x disease) intersection gives literature saturation; **Discovery Score = PPS x novelty** produces the final ranking. |

Two distinct properties are reported and must not be conflated:

- **Literature novelty** (`novelty_tier`, Highly Novel → Established) is derived from the *number of
  PubMed records* at the (pathway x seed genes x disease) intersection. This is what the Discovery
  Score weights.
- **Seed-independent** is a *structural* flag: seed genes are a minority (<50%) of the pathway's
  evidence genes, so the pathway was reached by network expansion rather than being one the seeds
  are already annotated to. It says nothing about the literature.

See **[docs/METHODS.md](docs/METHODS.md)** for the full methodology, scoring formulas, validation
design and limitations.

**Analysis depth presets:** Fast screening (~5 min) · Balanced (~10 min, default) · Comprehensive
(~20 min). Advanced parameters (STRING neighbors, FDR threshold, PubMed depth, permutations) can
override any preset.

---

## Architecture

```
python -m uvicorn app.main:app   ->  http://localhost:8000
  /                  server-rendered UI (Jinja2 + htmx + Alpine)
  /static/*          CSS + vendored htmx / alpine / cytoscape (no CDN, no build)
  /api/v1/*          JSON API (used by the UI, tests, and programmatic clients)
  /docs, /redoc      OpenAPI documentation
```

- **Backend & pipeline:** `app/services/*` (unchanged scientific engine), `app/api/*` (JSON API).
- **Web UI:** `app/web/routes.py` (HTML routes), `app/web/view_models.py` (derived view data),
  `app/templates/*.html`, `app/static/`.
- The HTML routes reuse the same API handlers as the JSON endpoints, so the UI and API never diverge.

---

## API

Interactive docs at `http://localhost:8000/docs`. See the in-app **[API reference](http://localhost:8000/api-reference)**.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/genes/validate` | POST | Validate gene identifiers |
| `/api/v1/analysis/run` | POST | Start an analysis |
| `/api/v1/analysis/{id}/status` | GET | Poll progress |
| `/api/v1/analysis/{id}/results` | GET | Fetch normalized results |
| `/api/v1/analysis/{id}/report/{format}` | GET | Download report (pdf/markdown/html/json) |
| `/api/v1/config/defaults` | GET | Default configuration |

---

## Testing

Playwright is **dev tooling only** — it lives under `e2e/` and is the *only* place Node is used.

```bash
cd e2e
npm install
npx playwright install chromium
```

**Fast suite** (deterministic, no external APIs; renders the committed fixture analysis). Auto-starts
the app:

```bash
npx playwright test ui
```

**Live "known → unknown" discovery** (runs the real pipeline against STRING/g:Profiler/PubMed so you
can watch genuine discovery — slow, network-dependent). Run it **headed** to watch:

```bash
npx playwright test discovery --headed
```

The discovery test asserts the science: the run produces pathway hypotheses, at least one is **novel**
for the seeds, secondary expansion occurred, and top hypotheses carry literature citations with
full seed → primary → secondary → final lineage. Screenshots are saved to `e2e/artifacts/`.

Tune it via env vars: `DISCOVERY_SEEDS`, `DISCOVERY_DISEASE`, `DISCOVERY_TIMEOUT_MS`.

Backend unit tests: `python -m pytest -q`.

---

## Docker

```bash
docker compose up --build      # serves UI + API on :8000
```

---

## Data sources

| Source | Usage |
|--------|-------|
| STRING | Protein–protein interaction networks |
| g:Profiler | GO:BP, KEGG, Reactome, WikiPathways enrichment |
| Reactome | Known-pathway filtering (novelty) |
| GTEx | Cardiac tissue expression |
| PubMed / NCBI E-utilities | Literature evidence |
| ChEMBL / curated lists | Druggability |

---

## Citation

> Yajing Wang & Jay Zhang Labs, University of Alabama at Birmingham. CardioXNet (2026).

## License

© 2026 University of Alabama at Birmingham. All rights reserved.
