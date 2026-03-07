# CardioXNet

CardioXNet is a cardiovascular pathway discovery application that starts from seed genes, expands through network and pathway evidence, and returns prioritized pathway hypotheses for manual review.

The current pipeline is designed as a funnel-and-filter workflow:

1. Validate seed genes and optional disease context.
2. Expand a broad functional neighborhood through STRING.
3. Enrich primary pathways across multiple pathway databases.
4. Re-expand through secondary pathways to capture related mechanisms.
5. Aggregate, score, semantically filter, and literature-screen final pathways.

The result is a ranked shortlist for follow-up, not proof that a pathway is absent from prior literature.

## What Changed

- Frontend configuration is now preset-based instead of exposing many raw knobs.
- API wiring is consistent across REST, WebSocket progress updates, and report downloads.
- The compute funnel is broader at the primary and secondary stages before the final cardiac prioritization filters are applied.
- UI copy has been tightened so the app reports candidate pathways instead of overstating novelty.

## Stack

- Backend: FastAPI, Python
- Frontend: React, TypeScript, Material UI, Vite
- External data/services: STRING, g:Profiler-backed enrichment, PubMed, GTEx, curated cardiac annotations

## Local Setup

### Backend

```bash
pip install -r requirements.txt
python -m app.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will connect to `http://<current-host>:8000` by default. You can override this with `VITE_API_URL` and `VITE_WS_URL`.

## Running Checks

### Backend tests

```bash
pytest -q
```

### Frontend build

```bash
cd frontend
npm run build
```

### Live UI smoke test

```bash
cd frontend
npm run test:ui:smoke
```

The smoke test launches the live demo in Playwright, submits a real analysis, waits for completion, checks the results page, and downloads the report.

## API Summary

- `GET /api/v1/health`
- `POST /api/v1/genes/validate`
- `POST /api/v1/analysis/run`
- `GET /api/v1/analysis/{analysis_id}/status`
- `GET /api/v1/analysis/{analysis_id}/results`
- `GET /api/v1/analysis/{analysis_id}/detailed-results`
- `GET /api/v1/analysis/{analysis_id}/report/{format}`

The in-app API Reference page documents the same surface the frontend uses.

## Scientific Use

CardioXNet is best used as a prioritization and review tool:

- Start with a biologically coherent seed set.
- Use the balanced preset first.
- Use exploratory mode when you want a wider hypothesis funnel.
- Treat PubMed query hits and novelty cues as screening signals.
- Manually review pathway synonyms, disease relevance, and prior literature before making claims about novelty.

## Documentation

- Main docs index: `docs/index.md`
- Configuration guide: `docs/CONFIGURATION.md`
- In-app docs page: `/documentation`
- In-app API reference: `/api-reference`
