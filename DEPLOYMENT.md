# CardioXNet Deployment Guide

## Overview

CardioXNet is a cardiovascular pathway discovery platform with AI-powered analysis pipeline.

**Version:** Enhanced with Secondary Pathway Lineage Tracking and Cardiac Disease Scoring  
**Date:** November 14, 2025

---

## System Requirements

### Backend
- Python 3.11+
- 4GB+ RAM
- 10GB+ disk space

### Frontend
- Node.js 22+
- pnpm package manager

---

## Installation

### 1. Backend Setup

```bash
cd CardioXNet

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables (optional)
cp .env.example .env
# Edit .env with your configuration
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Build for production (optional)
pnpm build
```

---

## Running the Application

### Development Mode

**Terminal 1 - Backend:**
```bash
cd CardioXNet
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd CardioXNet/frontend
pnpm dev
```

Access the application at: `http://localhost:3000`

### Production Mode

**Backend:**
```bash
cd CardioXNet
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend:**
```bash
cd CardioXNet/frontend
pnpm build
pnpm preview
```

Or serve the `dist` folder with nginx/apache.

---

## Configuration

### Backend Configuration

Edit `app/core/config.py` or set environment variables:

```bash
# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=CardioXNet

# CORS Settings
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Database Settings (if using)
DATABASE_URL=sqlite:///./cardioxnet.db

# External API Keys (optional)
PUBMED_API_KEY=your_key_here
```

### Frontend Configuration

Edit `frontend/vite.config.ts` for build settings.

Edit `frontend/src/config.ts` for API endpoint:

```typescript
export const API_BASE_URL = 'http://localhost:8000';
```

---

## Features

### New Features (Nov 2025)

1. **Secondary Pathway Lineage Tracking**
   - 4-step visualization: Seed → Primary → Secondary → Final
   - Source primary pathway tracking
   - Detailed lineage on pathway details page

2. **Cardiac Disease Score Column**
   - 0-1 continuous score based on curated gene database
   - Weighted algorithm using top cardiac genes
   - Color-coded display in results table

### Existing Features

- 14-stage AI-powered pathway discovery pipeline
- Multi-database integration (Reactome, KEGG, GO, WikiPathways)
- Network topology analysis with Graph ML
- Literature mining with PubMed integration
- GTEx tissue expression validation
- Druggability classification
- Interactive visualizations
- Comprehensive reporting (CSV, PDF)

---

## Data Requirements

### Input
- Gene list (gene symbols, e.g., GATA4, NKX2-5)
- Minimum 3 genes recommended
- Maximum 100 genes

### Databases (Auto-downloaded on first run)
- STRING PPI database
- GO annotations
- Reactome pathways
- KEGG pathways
- WikiPathways

---

## API Documentation

Once running, access interactive API docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Database errors:**
```bash
# Reset database
rm cardioxnet.db
# Restart backend
```

### Frontend Issues

**Build errors:**
```bash
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

**API connection errors:**
- Check backend is running on port 8000
- Verify CORS settings in backend config
- Check API_BASE_URL in frontend config

---

## Performance Optimization

### Backend
- Use `--workers 4` for production
- Enable caching for pathway databases
- Use PostgreSQL instead of SQLite for large datasets

### Frontend
- Run `pnpm build` for optimized production bundle
- Enable gzip compression on web server
- Use CDN for static assets

---

## Security Considerations

### Production Deployment

1. **Change default secrets:**
   ```bash
   # Generate new secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Enable HTTPS:**
   - Use nginx/apache as reverse proxy
   - Configure SSL certificates

3. **Restrict CORS:**
   ```python
   BACKEND_CORS_ORIGINS = ["https://yourdomain.com"]
   ```

4. **Rate limiting:**
   - Configure rate limits in `app/core/config.py`
   - Use nginx rate limiting

---

## Monitoring

### Logs

**Backend logs:**
```bash
# View logs
tail -f backend.log

# Or with uvicorn
python -m uvicorn app.main:app --log-level info
```

**Frontend logs:**
- Browser console (F12)
- Build logs: `pnpm build --verbose`

### Health Check

```bash
curl http://localhost:8000/health
```

---

## Backup

### Important Data

- Analysis results: `data/analyses/`
- Database: `cardioxnet.db`
- Configuration: `.env`, `app/core/config.py`

### Backup Command

```bash
tar -czf cardioxnet_backup_$(date +%Y%m%d).tar.gz \
  data/ \
  cardioxnet.db \
  .env
```

---

## Updating

### Pull Latest Changes

```bash
cd CardioXNet
git pull origin main

# Update backend dependencies
pip install -r requirements.txt --upgrade

# Update frontend dependencies
cd frontend
pnpm install
pnpm build
```

---

## Support

For issues or questions:
- Check documentation: `IMPLEMENTATION_SUMMARY.md`, `FINAL_IMPLEMENTATION_REPORT.md`
- Review API docs: `http://localhost:8000/docs`
- Check logs for error messages

---

## License

See LICENSE file for details.

---

## Credits

**Developer:** Manus AI Agent  
**Date:** November 14, 2025  
**Platform:** CardioXNet - Cardiovascular Network Analysis

**Key Technologies:**
- Backend: Python, FastAPI, NetworkX, Pandas
- Frontend: React, TypeScript, Material-UI, Vite
- Analysis: Graph ML, PubMed API, STRING DB, GTEx

