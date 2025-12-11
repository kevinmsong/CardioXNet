# CardioXNet Optimization Plan

## Goal
Speed up application, improve cardiac relevance filtering, fix UI/UX issues, and ensure 100% accuracy

---

## Phase 1: Remove Slow/Unimplemented Features

### Features to Remove:
1. **Stage 7: Network Topology Analysis** (Lines 356-412)
   - Slow and not critical for pathway discovery
   - Remove `TopologyAnalyzer` and `ComprehensiveTopologyAnalyzer`
   - Remove from UI display

2. **Permutation Testing** (if slow)
   - Check if this is causing delays
   - Consider making it optional or removing

3. **Redundancy Detection** (if slow)
   - Check performance impact
   - Consider simplifying or removing

### Keep These Essential Stages:
- ✅ Stage 0: Input Validation
- ✅ Stage 1: Functional Neighborhood (STRING PPI)
- ✅ Stage 2a: Primary Pathway Enrichment
- ✅ Stage 2b: Secondary Pathway Discovery
- ✅ Stage 2c: Pathway Aggregation
- ✅ Stage 5a: NES Scoring
- ✅ Stage 4a: Semantic Filtering (OPTIMIZE)
- ✅ Stage 4b: Enhanced Validation (tissue, druggability)
- ✅ Stage 6: Literature Mining (OPTIMIZE)
- ✅ Stage 6c: Final Strict Cardiac Name Filter (STRENGTHEN)

---

## Phase 2: Strengthen Cardiac Filtering

### Current Filtering:
- Stage 4a: Semantic filtering with cardiac relevance boost
- Stage 6c: Final strict name filter

### Improvements Needed:
1. **Stricter Name Filtering**
   - Require pathway names to contain cardiac-specific terms
   - Terms: cardiac, heart, cardiovascular, myocardial, coronary, vascular, etc.
   - Apply earlier in pipeline to save computation

2. **Semantic Filtering Enhancement**
   - Make faster and more accurate
   - Use disease context more effectively
   - Document how cardiac context influences results

3. **Final Pathway Selection**
   - Only show pathways with clear cardiac relevance
   - Better scoring based on cardiac gene database

---

## Phase 3: UI/UX Improvements

### Issues to Fix:
1. **Details Page Navigation**
   - Don't automatically navigate away after selecting a row
   - Fix routing to prevent blank pages

2. **Results Page Layout**
   - Move "Important Genes" to TOP (top 20 genes from top 50 pathways by NES)
   - Move "Drug Targets" to BOTTOM
   - Remove network topology section

3. **Frontend Performance**
   - Fix data loading issues
   - Improve table rendering

---

## Phase 4: Verify Pipeline Accuracy

### Critical Checks:
1. **Lineage Tracking**
   - Verify 100% accuracy for all final pathways
   - Ensure source_primary_pathway is always populated
   - Validate seed gene tracing

2. **Evidence Integration**
   - Literature validation working correctly
   - Database cross-referencing accurate
   - Fast but complete

3. **Scoring Accuracy**
   - NES scores calculated correctly
   - Cardiac disease scores accurate
   - Druggability tiers correct

---

## Phase 5: Documentation

### Document How Cardiac Context Influences Results:

1. **Input Stage**
   - Disease context used for semantic filtering

2. **Semantic Filtering Stage**
   - Pathway names must contain cardiac/disease terms
   - Pathways scored based on cardiac relevance
   - Non-cardiac pathways filtered out

3. **Final Filtering Stage**
   - Strict name filter requires cardiac terms
   - Only cardiac-relevant pathways shown

4. **Scoring Stage**
   - Cardiac gene database used for scoring
   - Higher scores for pathways with more cardiac genes

---

## Implementation Order

1. Remove topology analysis (fastest win)
2. Strengthen cardiac name filtering
3. Fix UI/UX issues
4. Optimize semantic filtering
5. Verify lineage tracking
6. Update documentation
7. Test end-to-end
