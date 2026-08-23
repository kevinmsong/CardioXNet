# CardioXNet Deployment Guide

## Overview

CardioXNet is a cardiovascular pathway-discovery platform. The UI is **server-rendered by FastAPI**
(Jinja2 + htmx + Alpine.js, with vendored JS), so there is **no Node/build step** and **no separate
frontend service** - one Python process serves the UI and the JSON API on a single port.

---

## System requirements

- Python 3.10+ (3.12 recommended)
- ~4 GB RAM, ~10 GB disk
- Outbound HTTPS to STRING, g:Profiler, Reactome, GTEx, and NCBI/PubMed
- No Node.js required to run the app (Node is only needed to run the Playwright tests under `e2e/`)

---

## Installation

```bash
cd CardioXNet
pip install -r requirements.txt

# Optional: AI-assisted report narratives
cp .env.example .env          # then set GROQ_API_KEY=...
```

---

## Running

### Development

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000**.

### Production

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Put a reverse proxy (nginx/Caddy) in front for TLS and gzip. Static assets are served by FastAPI
from `app/static/` (vendored JS + CSS - no external CDN required).

### Docker

```bash
docker compose up --build      # serves UI + API on :8000
```

### macOS desktop app (.app)

CardioXNet can be packaged as a self-contained, double-clickable `CardioXNet.app`
that bundles Python, the FastAPI server, and the UI, and opens it in a native
WKWebView window via [pywebview](https://pywebview.flowlib.org/). No Python
install is required on the end-user's machine.

> **Build on a Mac.** PyInstaller does not cross-compile - the `.app` must be
> built on macOS. Build on an Apple-silicon Mac for an arm64 app, or an Intel
> Mac (or Rosetta x86_64 Python) for an Intel app.

```bash
# on macOS, from the repo root
./build_macos.sh          # → dist/CardioXNet.app
./build_macos.sh --dmg    # also produces dist/CardioXNet.dmg
```

What this does (see `build_macos.sh` + `cardioxnet-macos.spec`):

1. installs `requirements.txt` + `requirements-desktop.txt` (adds `pywebview`,
   `pyobjc`, `pyinstaller`),
2. runs PyInstaller with `cardioxnet-macos.spec`, bundling the `app/` package
   (templates + static included), `config/`, and the scientific stack,
3. emits `dist/CardioXNet.app`.

At runtime the launcher picks a free localhost port, starts uvicorn in a
background thread, shows a splash, then loads the UI once the server answers.
A `CardioXNet.log` and the `outputs/` folder are written next to the `.app`.

**Gatekeeper:** the app is unsigned, so the first launch needs a right-click →
**Open**, or clear the quarantine attribute:

```bash
xattr -dr com.apple.quarantine dist/CardioXNet.app
```

To sign/notarize for distribution, set `codesign_identity` in
`cardioxnet-macos.spec` and run `codesign` / `xcrun notarytool` on the result.

> The same `launcher.py` is cross-platform; a Windows `.exe` can be produced by
> writing an analogous spec that uses `webview.platforms.winforms` and `EXE(...)`
> instead of the macOS `BUNDLE(...)`.

---

## Configuration

Backend configuration lives in `app/core/config.py` (Pydantic settings) and can be overridden via
environment variables or `.env`:

```bash
NETS_ENVIRONMENT=production
NETS_DEBUG=false
NETS_LOG_LEVEL=INFO
GROQ_API_KEY=your_key_here     # optional, AI narratives
```

Per-run pipeline parameters (STRING neighbors, FDR threshold, PubMed depth, permutations, etc.) are
sent as `config_overrides` from the UI presets or the API. Defaults: `GET /api/v1/config/defaults`.

Since the UI is same-origin with the API, no CORS configuration is needed for normal use.

---

## Data sources (used live)

- STRING - protein–protein interactions
- g:Profiler - GO:BP, KEGG, Reactome, WikiPathways enrichment
- Reactome - known-pathway filtering (novelty)
- GTEx - cardiac tissue expression
- PubMed / NCBI E-utilities - literature evidence
- ChEMBL / curated lists - druggability

Results are written to `outputs/{analysis_id}/results.json` and re-loadable by the API and UI.

---

## API documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- In-app summary: `http://localhost:8000/api-reference`

---

## Testing

```bash
cd e2e
npm install
npx playwright install chromium

npx playwright test ui                 # fast, deterministic (no external APIs)
npx playwright test discovery --headed # live known→unknown pipeline (slow)
```

Backend unit tests: `python -m pytest -q`.

---

## Troubleshooting

**Port already in use**
```bash
# Linux/macOS
lsof -ti:8000 | xargs kill -9
# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Missing dependencies**
```bash
pip install -r requirements.txt --upgrade
```

**PubMed returns few citations / HTTP 429** - NCBI is rate-limiting. Configure an NCBI API key (see
`docs/METHODS.md` §8) and reduce `pubmed_max_results`, or use a shallower preset.

**Static assets 404** - ensure `app/static/` is present (it ships with the repo) and that you launch
from the repository root so relative paths resolve.

### Health check
```bash
curl http://localhost:8000/health
```

---

## Backup

```bash
tar -czf cardioxnet_backup_$(date +%Y%m%d).tar.gz outputs/ .env
```

---

## Updating

```bash
git pull origin main
pip install -r requirements.txt --upgrade
# Restart uvicorn
```

---

## Credits

- Backend & pipeline: Python, FastAPI, NetworkX, pandas, scikit-learn
- UI: server-rendered Jinja2 + htmx + Alpine.js + cytoscape.js (no build step)
- Analysis: STRING, g:Profiler, Reactome, GTEx, PubMed, ChEMBL
