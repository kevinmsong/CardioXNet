# CardioXNet

**CardioXNet** is a cardiovascular pathway discovery platform implementing the NETS (Network Expansion & Topology Scoring) pipeline. You give it a short list of seed genes, and it returns ranked candidate cardiac pathways and therapeutic targets. To get there, it expands the gene list through protein–protein interaction networks, runs enrichment across several pathway databases, filters for cardiac relevance, and validates the results statistically.

It has a FastAPI backend (`app/`) and a React/Vite web UI (`frontend/`). The data sources it calls are public APIs, so no API keys are required.

---

## Quick Start

### Prerequisites
- Python 3.10+, pip
- Node.js 18+

### Backend
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Runs at http://localhost:3000
```

Start the backend first, then open <http://localhost:3000>. For Docker and production setup, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Configuration (optional)

The app runs with the built-in defaults listed under **Default parameters** below, so no `.env` file is needed.

- **Override pipeline settings:** create a `.env` file in the repo root and use `NETS_`-prefixed variables (for example, `NETS_STRING_NEIGHBOR_COUNT=75`).
- **About `.env.example`:** it is a template, and some of its values differ from the defaults. It sets `NETS_STRING_SCORE_THRESHOLD=0.7` and `NETS_TOP_HYPOTHESES_COUNT=5`. Adjust those values if you copy it to `.env`.
- **AI narrative text in reports:** set `GROQ_API_KEY` in your shell environment. Without it, that step is skipped.

---

## Features

- **Gene Input** — Paste 5–50 cardiovascular gene symbols (HGNC format)
- **12-Stage NETS Pipeline** — Network expansion → enrichment → NES scoring → semantic filtering → statistical validation → topology analysis → report
- **Results Table** — Ranked pathways with NES scores, FDR-adjusted p-values, empirical p-values, cardiac relevance, druggability
- **Therapeutic Targets** — Hub genes ranked by centrality, cardiac association, and druggability tier
- **Configuration Presets** — Fast (~5 min), Balanced (default, ~10 min), Comprehensive (~20 min)
- **Export** — CSV table and PDF report with full provenance

---

## 12-Stage Pipeline

| Stage | Name | Progress |
|-------|------|----------|
| 01 | Input Validation — HGNC normalization | 5% |
| 02 | Functional Neighborhood — STRING v11.5 PPI (75 neighbors, score ≥ 0.60) | 15% |
| 03 | Primary Pathway Enrichment — g:Profiler (GO:BP, KEGG, Reactome, WikiPathways) | 25% |
| 04 | Secondary Pathway Discovery — per-neighbor re-enrichment | 40% |
| 05 | Pathway Aggregation — frequency-based, Jaccard ≥ 0.85 redundancy filter | 55% |
| 06 | NES Scoring — `–log₁₀(p_adj) × √gene_count × db_weight` | 65% |
| 07 | Semantic Cardiac Filtering — 700+ curated cardiovascular terms, strict name filter | 75% |
| 08 | Enhanced Validation — GTEx v8, 25 degree-preserving permutations, ChEMBL druggability | 83% |
| 09 | Literature Mining — PubMed (20 abstracts/gene) | 88% |
| 10 | Network Topology — PageRank, betweenness, closeness centrality | 93% |
| 11 | Therapeutic Targets — importance scoring with druggability tiers | 95% |
| 12 | Report Generation — JSON + PDF | 100% |

**Default parameters:**

| Parameter | Value |
|-----------|-------|
| STRING neighbors | 75 |
| Confidence threshold | ≥ 0.60 |
| FDR threshold | ≤ 0.05 |
| Permutations | 25 (degree-preserving) |
| Top hypotheses | 15 |
| PubMed per gene | 20 |

---

## API

Interactive docs: `http://localhost:8000/docs`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/genes/validate` | POST | Validate gene identifiers |
| `/api/v1/analysis/run` | POST | Start analysis |
| `/api/v1/analysis/{id}/status` | GET | Poll progress |
| `/api/v1/analysis/{id}/results` | GET | Fetch results |
| `/api/v1/analysis/{id}/report/{format}` | GET | Download PDF/JSON report |
| `/api/v1/config/defaults` | GET | Get default configuration |

---

## Data Sources

| Source | Usage |
|--------|-------|
| STRING v11.5 | Protein-protein interaction networks |
| g:Profiler | GO:BP, KEGG, Reactome, WikiPathways enrichment |
| GTEx v8 | Cardiac tissue expression (live API) |
| PubMed/NCBI | Literature evidence (live API) |
| DrugBank v5.1.10 | Curated druggability gene lists (Nov 2023) |
| ChEMBL REST API | Live drug phase & activity lookup (EBI) |

---

## Testing

### Playwright E2E Tests
```bash
cd frontend
npx playwright install chromium
npm run test:ui    # UI component tests
npm run test:e2e   # API integration tests (requires backend on :8000)
```

---

## Citation

> Yajing Wang & Jay Zhang Labs, University of Alabama at Birmingham. CardioXNet (2026).

---

## License

© 2026 University of Alabama at Birmingham. All rights reserved.
