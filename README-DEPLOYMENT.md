# CardioXNet 2.0 - GitHub Ready

## ✅ What's Included

This is a clean, production-ready version of CardioXNet 2.0 with:

- ✅ **Literature mining working** - Citation counts displayed in UI
- ✅ **GWAS/Clinical validation references removed** - As requested
- ✅ **Top Genes feature** - 5 gene cards with druggability
- ✅ **Semantic filtering** - Stricter cardiac relevance thresholds
- ✅ **Clean codebase** - No test files, logs, or temporary data

## 📦 Repository Structure

```
CardioXNet/
├── app/                    # Backend Python application
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Core business logic
│   ├── models/            # Data models
│   ├── services/          # Service layer
│   └── stages/            # Pipeline stages (including literature mining)
├── frontend/              # React + TypeScript frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── utils/         # Utility functions
│   ├── package.json       # Node dependencies
│   └── vite.config.ts     # Vite configuration
├── config/                # Configuration files
├── docs/                  # Documentation
├── outputs/               # Sample analysis output
├── scripts/               # Utility scripts
├── tools/                 # Development tools
├── requirements.txt       # Python dependencies
├── deploy-github-pages.sh # GitHub Pages deployment script
└── docker-compose.yml     # Docker setup

```

## 🚀 Quick Start

### 1. Install Dependencies

**Backend:**
```bash
cd CardioXNet
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 2. Run Development Servers

**Backend:**
```bash
python3 -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Visit: http://localhost:3000

### 3. Deploy to GitHub Pages

```bash
./deploy-github-pages.sh
```

Your site will be live at: `https://yourusername.github.io/CardioXNet/`

## 📋 Key Features

### Literature Mining ✅
- Queries PubMed for pathway-gene associations
- Relevance scoring (0.0 to 1.0)
- 25 citations per pathway
- Citation counts displayed in Results table

### Top Genes ✅
- AI-identified therapeutic targets
- Druggability annotations (FDA Approved, Clinical Trial, Research)
- Importance scoring based on pathway frequency and centrality

### Semantic Filtering ✅
- 700+ cardiac-specific terms
- Stricter relevance thresholds (0.30, 0.50)
- Disease-context aware pathway ranking

## 🔧 Configuration

### Environment Variables

Create `.env` file in root directory:

```bash
# API Keys (optional)
PUBMED_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Database (optional)
DATABASE_URL=sqlite:///./cardioxnet.db

# CORS (for production)
ALLOWED_ORIGINS=https://yourdomain.com
```

### Frontend API URL

Update `frontend/.env.production`:

```bash
VITE_API_BASE_URL=https://your-backend-url.com
```

## 📊 Sample Data

The `outputs/` directory contains a sample analysis result:
- **Analysis ID:** fast_analysis_20251027_231611
- **Seed Genes:** SCN5A, KCNH2
- **Pathways Found:** 106
- **With Literature:** 20 pathways (25 citations each)

## 🐛 Troubleshooting

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend errors
```bash
pip install --upgrade -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

### Port already in use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## 📚 Documentation

- **API Documentation:** Visit http://localhost:8000/docs when backend is running
- **User Guide:** See `docs/` directory
- **Architecture:** See `docs/ARCHITECTURE.md`

## 🎯 Recent Changes

### Latest Updates (Oct 28, 2024)
1. ✅ Removed all GWAS and clinical validation references
2. ✅ Fixed literature mining display on Results page
3. ✅ Updated validation text to focus on network/semantic analysis
4. ✅ Cleaned up codebase for GitHub deployment

### Known Issues
- Citation cards on detail pages need production build to display (code is ready)
- Frontend hot reload may not work in some environments (restart server)

## 📞 Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review the troubleshooting section above
3. Check GitHub issues
4. Contact the development team

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

CardioXNet 2.0 - AI-Powered Cardiovascular Pathway Discovery

---

**Ready to deploy?** Run `./deploy-github-pages.sh` to get started! 🚀
