# Comprehensive Implementation Plan for CardioXNet Enhancements

## Issues Identified from Testing

### Critical Issues
1. ❌ **Details page not loading** - "Pathway not found in analysis results"
2. ❌ **No pathway lineage visualization** - Cannot see seed gene → primary → secondary → final pathway
3. ❌ **No cardiac disease score column** - Only binary 100%/0% cardiac relevance
4. ❌ **No literature references displayed** - Only counts, no actual PubMed links
5. ❌ **Network topology empty** - Shows 0 genes, 0 interactions

### Enhancement Requests
1. 🔧 Add pathway lineage tracking and visualization
2. 🔧 Add continuous cardiac disease score (0-1)
3. 🔧 Implement "Not Reported" for zero literature
4. 🔧 List actual literature references in Details page
5. 🔧 Test and integrate DrugBank API for Top 20 genes
6. 🔧 Adjust pipeline funneling (less restrictive early, more stringent final)

## Implementation Strategy

### Phase 1: Fix Critical Backend Issues (Priority: CRITICAL)

#### 1.1 Fix Details Page API Endpoint
**File:** `/home/ubuntu/CardioXNet/app/api/endpoints.py`

**Problem:** The pathway detail endpoint returns 404 because:
- Pathway lookup by ID is failing
- Data structure mismatch between storage and retrieval

**Solution:**
```python
# Fix get_pathway_detail endpoint to correctly look up pathways
# Ensure pathway_id matches the stored format (e.g., "GO:0007507")
# Check both stage_3 and ranked_hypotheses for pathway data
```

#### 1.2 Add Pathway Lineage Tracking
**Files:** 
- `/home/ubuntu/CardioXNet/app/services/pipeline.py`
- `/home/ubuntu/CardioXNet/app/services/pathway_analyzer_primary.py`
- `/home/ubuntu/CardioXNet/app/services/pathway_analyzer_secondary.py`

**Implementation:**
```python
# Add lineage field to each hypothesis:
hypothesis = {
    "pathway_id": "GO:0007507",
    "pathway_name": "heart development",
    "lineage": {
        "seed_genes": ["GATA4", "NKX2-5"],
        "primary_pathway": "GO:0007507",
        "primary_pathway_name": "heart development",
        "secondary_pathway": None,  # or pathway ID if discovered via secondary
        "discovery_method": "primary"  # or "secondary"
    },
    ...
}
```

### Phase 2: Add Cardiac Disease Scoring (Priority: HIGH)

#### 2.1 Implement Continuous Cardiac Score
**File:** `/home/ubuntu/CardioXNet/app/services/semantic_filter.py`

**Method:**
```python
def calculate_cardiac_disease_score(pathway_name, pathway_description, disease_context):
    """
    Calculate continuous cardiac disease relevance score (0-1)
    
    Factors:
    1. Semantic similarity to disease context (40%)
    2. Cardiac term frequency in pathway description (30%)
    3. Literature co-occurrence score (20%)
    4. Gene-disease association score (10%)
    
    Returns: float between 0.0 and 1.0
    """
    # Use TF-IDF or embedding similarity for semantic matching
    # Count cardiac terms in description
    # Query PubMed for pathway + disease co-occurrence
    # Average gene cardiac scores from curated database
```

#### 2.2 Add Column to Results Page
**File:** `/home/ubuntu/CardioXNet/frontend/src/pages/ResultsPageClean.tsx`

**Add new column:**
- Header: "Cardiac Disease Score"
- Display: Progress bar with percentage (e.g., 87%)
- Tooltip: "Quantitative measure of pathway relevance to cardiac disease context"
- Sort: Enabled

### Phase 3: Literature Integration (Priority: HIGH)

#### 3.1 PubMed Query for Pathway-Disease Associations
**File:** `/home/ubuntu/CardioXNet/app/services/literature_miner.py`

**New method:**
```python
async def query_pathway_disease_literature(pathway_name, disease_context):
    """
    Query PubMed for pathway-disease associations
    
    Returns:
    {
        "count": 42,
        "references": [
            {
                "pmid": "12345678",
                "title": "...",
                "authors": "...",
                "journal": "...",
                "year": 2020,
                "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"
            },
            ...
        ]
    }
    """
```

#### 3.2 Display "Not Reported" in Results Table
**File:** `/home/ubuntu/CardioXNet/frontend/src/pages/ResultsPageClean.tsx`

**Update Literature Reported column:**
```typescript
{pathway.literature_count === 0 ? (
  <Chip label="Not Reported" size="small" color="default" />
) : (
  <Chip label={pathway.literature_count} size="small" color="primary" />
)}
```

#### 3.3 Display References in Details Page
**File:** `/home/ubuntu/CardioXNet/frontend/src/pages/UltraDetailPage.tsx`

**Add Literature References section:**
- Show all PubMed references
- Clickable links to PubMed
- Formatted citations

### Phase 4: DrugBank Integration (Priority: MEDIUM)

#### 4.1 Test DrugBank API Access
**Test script:**
```python
import requests

# Test DrugBank API
# Note: DrugBank requires API key or uses public data dumps
# Check if API key is available or use alternative (OpenTargets, ChEMBL)
```

#### 4.2 Query Top 20 Genes
**File:** `/home/ubuntu/CardioXNet/app/services/drugbank_client.py`

**Implementation:**
```python
class DrugBankClient:
    async def get_gene_druggability(self, gene_symbol):
        """
        Query DrugBank for gene druggability information
        
        Returns:
        {
            "gene": "GATA4",
            "druggability": "Research",
            "drugs": [],  # List of associated drugs if any
            "clinical_trials": [],  # List of clinical trials
            "targets": []  # Drug target information
        }
        """
```

### Phase 5: Pipeline Adjustments (Priority: MEDIUM)

#### 5.1 Adjust Early-Stage Filtering
**File:** `/home/ubuntu/CardioXNet/app/services/pipeline.py`

**Changes:**
- Reduce primary pathway p-value threshold (e.g., 0.05 → 0.10)
- Allow more secondary pathways through (e.g., top 200 → top 500)
- Lower initial NES threshold (e.g., 1.5 → 1.2)

#### 5.2 Increase Final Cardiac Filtering
**File:** `/home/ubuntu/CardioXNet/app/services/semantic_filter.py`

**Changes:**
- Increase cardiac relevance threshold (e.g., 0.3 → 0.5)
- Require minimum cardiac disease score (e.g., 0.4)
- Add literature evidence requirement (e.g., min 5 citations or "Not Reported" acceptable)

### Phase 6: Pathway Lineage Visualization (Priority: HIGH)

#### 6.1 Create Lineage Component
**File:** `/home/ubuntu/CardioXNet/frontend/src/components/PathwayLineage.tsx`

**Design:**
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│ Seed Genes  │ ──> │   Primary    │ ──> │  Secondary   │ ──> │    Final    │
│ GATA4       │     │   Pathway    │     │   Pathway    │     │   Pathway   │
│ NKX2-5      │     │              │     │  (if any)    │     │             │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
```

**Features:**
- Arrows showing discovery flow
- Clickable nodes to jump to pathway details
- Highlight discovery method (primary vs. secondary)
- Show enrichment scores at each stage

#### 6.2 Add to Details Page Header
**File:** `/home/ubuntu/CardioXNet/frontend/src/pages/UltraDetailPage.tsx`

**Placement:** Top of page, below pathway title, above statistics

## Implementation Order

### Day 1: Critical Fixes
1. ✅ Fix Details page API endpoint (1.1)
2. ✅ Add pathway lineage tracking to backend (1.2)
3. ✅ Create lineage visualization component (6.1)
4. ✅ Test Details page with lineage display

### Day 2: Cardiac Scoring
1. ✅ Implement continuous cardiac disease scoring (2.1)
2. ✅ Add cardiac disease score column to Results page (2.2)
3. ✅ Test scoring with different disease contexts

### Day 3: Literature Integration
1. ✅ Implement PubMed pathway-disease queries (3.1)
2. ✅ Add "Not Reported" display (3.2)
3. ✅ Add literature references section to Details page (3.3)

### Day 4: DrugBank & Pipeline
1. ✅ Test DrugBank API (4.1)
2. ✅ Implement gene druggability queries (4.2)
3. ✅ Adjust pipeline parameters (5.1, 5.2)
4. ✅ Run new analysis to test changes

### Day 5: Testing & Documentation
1. ✅ End-to-end testing with screenshots
2. ✅ Update documentation
3. ✅ Create demo video/slides

## Success Criteria

- [ ] Details page loads without errors
- [ ] Pathway lineage visualization shows complete discovery path
- [ ] Cardiac disease score column displays continuous values (not just 100%/0%)
- [ ] "Not Reported" appears for pathways with 0 literature
- [ ] Literature references are listed and clickable in Details page
- [ ] DrugBank data enriches Top 20 genes display
- [ ] Pipeline produces more diverse early results
- [ ] Final results have higher cardiac specificity
- [ ] All features tested with screenshot evidence

