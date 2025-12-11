# Current State Observations - CardioXNet Results Page

## Screenshot Evidence: Results Page

### Top Genes Section (Working)
✅ **5 therapeutic targets displayed:**
1. GATA4 - Importance: 22.06, Pathways: 15, Cardiac: 95%
2. SMAD4 - Importance: 21.27, Pathways: 14, Cardiac: 72%
3. NKX2-5 - Importance: 21.10, Pathways: 14, Cardiac: 95%
4. HEY2 - Importance: 19.15, Pathways: 14, Cardiac: 78%
5. TBX5 - Importance: 18.29, Pathways: 12, Cardiac: 95%

### Pathway Table Columns (Current)
✅ **Existing columns:**
1. Pathway Name
2. NES Score (with sorting)
3. Cardiac Relevance (100% for all visible)
4. Clinical Impact (star ratings: 30%, 60%)
5. Evidence Genes (counts: 30, 63, 39)
6. Literature Reported (values: 0, 50, 42)
7. GTEx Cardiac Specificity (100%, 31%, etc.)
8. Complexity (100%, 88%)
9. Database (badges: GO:BP, etc.)
10. Details (eye icon button)

### Visible Pathways (Top 3)
1. **anatomical structure morphogenesis** (GO:0009653)
   - NES: 5.532, Cardiac: 100%, Clinical: 30%, Evidence: 30, Literature: 0, GTEx: 100%

2. **heart development** (GO:0007507)
   - NES: 5.364, Cardiac: 100%, Clinical: 60%, Evidence: 63, Literature: 50, GTEx: 100%

3. **heart morphogenesis** (GO:0003007)
   - NES: 5.349, Cardiac: 100%, Clinical: 60%, Evidence: 39, Literature: 42, GTEx: 31%

## Issues Identified

### 1. Missing Features
❌ **Cardiac Disease Score column** - Not present (only Cardiac Relevance which is binary 100%/0%)
❌ **Pathway lineage visualization** - Not visible on Results page
❌ **Literature references list** - Only counts shown, no actual references
❌ **DrugBank integration** - Only shows "Research" classification

### 2. Data Issues
⚠️ **Literature Reported = 0** for "anatomical structure morphogenesis" - Should show "Not Reported"
⚠️ **Network Topology shows 0 genes, 0 interactions** - Not populated
⚠️ **All pathways show 100% Cardiac Relevance** - No gradient/continuous scoring

### 3. Details Page (Not Yet Tested)
❓ Need to test pathway lineage visualization
❓ Need to verify literature references display
❓ Need to check seed gene backtracking

## Implementation Plan

### Priority 1: Pathway Lineage Tracking
- Add lineage field to hypothesis data structure
- Track: seed_genes → primary_pathway → secondary_pathway → final_pathway
- Store in results.json

### Priority 2: Cardiac Disease Score
- Implement continuous scoring (0-1) based on:
  - Semantic match strength to disease context
  - Literature co-occurrence with cardiac terms
  - Gene-disease association scores
- Add new column to Results table

### Priority 3: Literature Integration
- Query PubMed for pathway-disease associations
- Display "Not Reported" when count = 0
- Store and display actual references in Details page

### Priority 4: DrugBank Integration
- Test DrugBank API access
- Query Top 20 genes for druggability
- Update gene cards with detailed druggability info

### Priority 5: Pipeline Adjustments
- Reduce early-stage filtering threshold
- Increase final cardiac relevance threshold
- Balance discovery vs. precision

