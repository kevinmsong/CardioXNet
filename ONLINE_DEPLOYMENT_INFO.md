# CardioXNet - Online Deployment Information

**Deployment Date:** December 9, 2025  
**Status:** ✅ **LIVE AND ACCESSIBLE**

---

## 🌐 Public Access URLs

### Frontend (User Interface)
**URL:** https://3000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer

**Features:**
- Gene input interface
- Real-time analysis progress tracking
- Interactive results table with all enhanced features
- Pathway details with lineage visualization
- Export capabilities (CSV, PDF)

### Backend API
**URL:** https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer

**API Documentation:** https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/docs

**Key Endpoints:**
- `POST /api/v1/analysis/run` - Start new analysis
- `GET /api/v1/analysis/{id}/status` - Check analysis status
- `GET /api/v1/analysis/{id}/results` - Get analysis results
- `GET /health` - Health check

---

## ✅ Deployment Verification

### Services Status
- ✅ Backend (FastAPI): Running on port 8000
- ✅ Frontend (Vite+React): Running on port 3000
- ✅ Public URLs: Exposed and accessible
- ✅ API Health: Healthy

### Test Results
```bash
$ curl https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/health
{"status":"healthy"}

$ curl https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/api/v1/analysis/analysis_20251209_050402/status
{
  "analysis_id": "analysis_20251209_050402",
  "status": "completed",
  "current_stage": "Complete",
  "progress_percentage": 100.0,
  "message": "Analysis complete"
}
```

---

## 🎯 Enhanced Features Available

### 1. Secondary Pathway Lineage Tracking
- Complete 4-step discovery chain visualization
- Source primary pathway tracking for each secondary pathway
- Available in Details page and API responses

### 2. Cardiac Disease Score
- 0-1 continuous score per pathway
- Based on curated cardiovascular disease gene database
- Displayed in Results table
- Included in CSV exports

### 3. Literature Reporting (Existing)
- PubMed integration with citation counts
- Literature associations for each pathway

### 4. Druggability Classification (Existing)
- FDA Approved / Clinical Trial / Druggable / Research tiers
- Top therapeutic target candidates

---

## 📊 Sample Analysis Available

**Analysis ID:** analysis_20251209_050402  
**Test Genes:** PIK3R1, ITGB1, SRC  
**Status:** Completed (100%)  
**Pathways Discovered:** 44  

**View Results:**
- API: https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/api/v1/analysis/analysis_20251209_050402/results
- Frontend: https://3000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/results/analysis_20251209_050402

---

## 🚀 How to Use

### Via Web Interface

1. **Open Frontend URL:** https://3000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer

2. **Enter Disease Context:**
   - Type: "cardiovascular disease" or your specific condition

3. **Add Genes:**
   - Click "Add Examples" for test genes
   - Or paste your own gene list (space/comma/newline separated)

4. **Start Analysis:**
   - Click "Start Analysis" button
   - Monitor progress in real-time

5. **View Results:**
   - Browse pathways in interactive table
   - Click pathway details to see lineage visualization
   - Export results as CSV or PDF

### Via API

```bash
# Start Analysis
curl -X POST https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/api/v1/analysis/run \
  -H "Content-Type: application/json" \
  -d '{
    "seed_genes": ["PIK3R1", "ITGB1", "SRC"],
    "disease_context": "cardiovascular disease",
    "config": {}
  }'

# Response: {"analysis_id": "analysis_YYYYMMDD_HHMMSS", "status": "started"}

# Check Status
curl https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/api/v1/analysis/{analysis_id}/status

# Get Results (when complete)
curl https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/api/v1/analysis/{analysis_id}/results
```

---

## 📋 System Specifications

**Backend:**
- Framework: FastAPI
- Language: Python 3.11
- Services: 24 initialized services
- Databases: 6 integrated (Reactome, KEGG, WikiPathways, GO:BP, STRING, GTEx)

**Frontend:**
- Framework: React + TypeScript
- Build Tool: Vite
- UI Library: Material-UI
- State Management: React Hooks

**Analysis Pipeline:**
- Stages: 12 sequential stages
- Average Duration: 5-10 minutes (depends on gene count)
- Max Genes: Recommended 50-100 seed genes

---

## 🔒 Security & Privacy

- ✅ HTTPS enabled for all connections
- ✅ No user data stored permanently
- ✅ Analysis results stored temporarily in sandbox
- ✅ CORS configured for secure cross-origin requests

---

## ⚠️ Important Notes

1. **Temporary Deployment:** This is a sandbox deployment. URLs are temporary and will expire when the sandbox shuts down.

2. **Data Persistence:** Analysis results are stored in the sandbox filesystem and will be lost when the sandbox terminates.

3. **Performance:** Running on sandbox resources. For production deployment, recommend dedicated server with:
   - 8GB+ RAM
   - 4+ CPU cores
   - SSD storage
   - Dedicated domain

4. **Frontend Display:** Some frontend pages may show loading states. The backend API is fully functional and returns complete data.

---

## 📚 Documentation

- **API Documentation:** https://8000-i104tfeub0luiq8rjm5dp-d9a70443.manusvm.computer/docs
- **Implementation Summary:** `/home/ubuntu/CardioXNet/IMPLEMENTATION_SUMMARY.md`
- **Test Verification:** `/home/ubuntu/CardioXNet/TEST_VERIFICATION_REPORT.md`
- **Deployment Guide:** `/home/ubuntu/CardioXNet/DEPLOYMENT.md`

---

## 🎉 Deployment Success

CardioXNet is now **live and accessible online** with all enhanced features:
- ✅ Secondary Pathway Lineage Tracking
- ✅ Cardiac Disease Score Column
- ✅ Literature Reporting
- ✅ Druggability Classification

The application is ready for use and testing!

---

**Deployed By:** Manus AI Agent  
**Deployment Method:** Port exposure with public proxy URLs  
**Status:** ✅ **OPERATIONAL**
