# CardioXNet

CardioXNet is a cardiovascular pathway discovery and review application. It starts from a seed gene list, expands through network and enrichment evidence, and returns ranked pathway candidates for scientific review.

The current system is designed as a discovery funnel rather than a claim engine. It is intended to help surface plausible pathways for follow-up, including less obvious candidates, but it does not prove that a pathway is truly absent from the literature.

## What CardioXNet Does

- Validates seed genes before analysis starts.
- Expands the seed set through a STRING-derived functional neighborhood.
- Builds a broad primary pathway candidate set through enrichment across multiple pathway resources.
- Re-expands through secondary pathways to capture related mechanisms beyond the original seed list.
- Aggregates and ranks final pathways using replication across signals, pathway-level scoring, semantic cardiac relevance, literature screening, and downstream validation layers.
- Produces a results page, detailed pathway views, CSV export, and downloadable reports.

## Scientific Scope

CardioXNet is most useful as a prioritization tool for cardiovascular pathway discovery and review.

Use it to:

- compare broad versus narrow discovery settings
- identify replicated pathway signals across multiple upstream branches
- inspect lower seed-overlap pathways that may be less obvious from the original gene list
- combine pathway ranking with tissue, literature, and therapeutic target context

Do not use it to:

- claim novelty based only on low or zero PubMed query hits
- treat the ranked output as experimental validation
- replace manual review of pathway synonyms, disease context, and prior studies

## Discovery Workflow

The live implementation in [workflow_diagram.mmd](workflow_diagram.mmd) follows this order:

1. Seed genes are validated and normalized.
2. A functional neighborhood is built from STRING interactions.
3. Primary pathway enrichment creates the first broad candidate space.
4. Leading primary pathways seed secondary pathway expansion.
5. Pathways are aggregated across branches and deduplicated into a replicated candidate set.
6. Aggregated pathways are ranked with NES scoring.
7. Semantic cardiac filtering and redundancy reduction prioritize the biologically relevant set.
8. Enhanced validation adds GTEx support, degree-preserving permutation testing when enabled, and curated plus bounded live Open Targets evidence.
9. Literature mining and seed-gene tracing annotate the prioritized pathways.
10. A final strict cardiac-name filter is applied, and literature evidence is refreshed on the retained final pathways.
11. Important genes are generated from the top ranked pathways with DisGeNET and therapeutic evidence.
12. Reports and downloadable outputs are generated.

This broader early funnel is intentional. CardioXNet keeps more primary and secondary candidates in play before the later prioritization filters are applied.

## Data Sources and Evidence Layers

The pipeline combines multiple evidence types:

- STRING for functional neighborhood expansion
- g:Profiler-backed enrichment across pathway resources
- Reactome and other pathway databases for pathway-level evidence
- PubMed for rapid literature screening
- GTEx for tissue-expression context
- Open Targets for live therapeutic target and drug evidence
- curated cardiovascular annotations and bounded live Open Targets lookups for translational review

The final pathway ranking is not based on a single score alone. Important fields on the results and detail pages include:

- `NES score`: combined prioritization score
- `Support count`: number of upstream branches supporting the pathway
- `Evidence genes`: genes contributing to the pathway signal
- `PubMed query hits`: automated retrieval signal, not proof of prior reporting or non-reporting
- `GTEx support`: pathway-level tissue expression context
- `Therapeutic evidence`: targetability and related drug evidence where available

## Repository Structure

```text
app/        FastAPI backend, pipeline logic, services, models, templates
config/     YAML configuration
docs/       Short operator-facing documentation
frontend/   React + TypeScript client
outputs/    Generated analysis artifacts and reports
scripts/    Utility scripts
tests/      Backend tests
```

## Local Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm

### Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional environment setup:

```bash
copy .env.example .env
```

Run the API:

```bash
python -m app.main
```

Default backend address:

- API root: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Versioned health: `http://127.0.0.1:8000/api/v1/health`

### Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Run the frontend:

```bash
npm run dev
```

Default frontend address:

- App: `http://127.0.0.1:3000`

The frontend auto-builds API and WebSocket URLs from the current browser hostname. You can override them with:

- `VITE_API_URL`
- `VITE_WS_URL`

## Configuration

The frontend now uses a simplified preset-driven configuration model instead of exposing every internal algorithm knob.

### Discovery profiles

- `Focused`: narrower funnel and smaller final output
- `Balanced`: default operating mode
- `Exploratory`: broader expansion and a wider candidate funnel

### Evidence depth

- `Fast screening`: lighter literature and validation workload for quick runs
- `Standard review`: balanced evidence depth
- `Deep evidence pass`: broader literature and stronger empirical validation

Backend configuration can still be controlled through:

1. code defaults
2. `config/config.yaml`
3. environment variables
4. per-request `config_overrides`

High-impact backend parameters are described in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Running an Analysis

### Through the UI

1. Open the home page.
2. Enter or paste a seed gene list.
3. Optionally choose disease context.
4. Select a discovery profile and evidence depth preset.
5. Start the analysis and follow progress updates.
6. Review the final results table, pathway detail pages, and downloadable report.

### Through the API

Start with gene validation:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/genes/validate" ^
  -H "Content-Type: application/json" ^
  -d "{\"gene_ids\":[\"PIK3R1\",\"ITGB1\",\"SRC\"]}"
```

Then launch an analysis:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/analysis/run" ^
  -H "Content-Type: application/json" ^
  -d "{\"seed_genes\":[\"PIK3R1\",\"ITGB1\",\"SRC\"]}"
```

## API Surface

Core REST endpoints:

- `GET /api/v1/health`
- `GET /health`
- `POST /api/v1/genes/validate`
- `POST /api/v1/analysis/run`
- `GET /api/v1/analysis/{analysis_id}/status`
- `GET /api/v1/analysis/{analysis_id}/results`
- `GET /api/v1/analysis/{analysis_id}/detailed-results`
- `GET /api/v1/analysis/{analysis_id}/stage/{stage_id}`
- `GET /api/v1/config/defaults`
- `GET /api/v1/analysis/{analysis_id}/report/{format}`

Progress updates:

- WebSocket: `/api/v1/analysis/{analysis_id}/progress`

The frontend uses the same versioned API and WebSocket surface documented on the in-app API Reference page.

## Outputs

A completed analysis can produce:

- ranked final pathways
- pathway detail views with lineage and evidence summaries
- important-gene summaries with curated and Open Targets-derived therapeutic evidence when available
- CSV export
- downloadable reports in supported formats
- generated artifacts under `outputs/`

## Interpreting Results

A strong candidate pathway usually has a combination of:

- high support count across upstream branches
- strong pathway-level ranking metrics
- coherent evidence genes
- cardiac semantic relevance
- plausible tissue-expression context
- literature hits that support relevance or identify a review gap
- therapeutic target evidence that strengthens translational interest

A weak or uncertain candidate often has:

- only one supporting upstream branch
- generic biology with weak cardiac specificity
- unstable literature retrieval
- no convergent support from other evidence layers

Manual review is still required before making novelty claims.

## Testing and Verification

### Backend tests

```bash
pytest -q
```

### Frontend production build

```bash
cd frontend
npm run build
```

### UI smoke test with Playwright

```bash
cd frontend
npm run test:ui:smoke
```

The smoke test launches the live app, submits a real analysis, waits for completion, checks the results page, and downloads the report.

Additional frontend commands:

- `npm run test:ui`
- `npm run test:ui:live`
- `npm run test:e2e`

## Documentation

- Overview: [docs/index.md](docs/index.md)
- Configuration guide: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- In-app documentation: `/documentation`
- In-app API reference: `/api-reference`
- Deployment notes: [DEPLOYMENT.md](DEPLOYMENT.md)

## Notes for Scientific Use

- Start with a biologically coherent seed set.
- Use `Balanced` first, then compare with `Focused` or `Exploratory` as needed.
- Treat low literature retrieval as a screening signal, not as proof of novelty.
- Review pathway naming overlap and synonyms before concluding that two pathways are distinct.
- Prefer candidates supported by multiple evidence layers rather than a single favorable metric.

## License and Attribution

Copyright © 2026 Yajing Wang and Jay Zhang Labs, The University of Alabama at Birmingham. All rights reserved.
