# CardioXNet Pipeline Stage Reorganization Plan

## Current Stage Structure (Confusing)

| Current Label | Progress % | Description | Issue |
|--------------|-----------|-------------|-------|
| Stage 0 | 0% | Input Validation | ✅ OK |
| Stage 1 | 15% | Functional Neighborhood | ✅ OK |
| Stage 2a | 30% | Primary Pathway Enrichment | ✅ OK |
| Stage 2b | 45% | Secondary Pathway Discovery | ✅ OK |
| Stage 2c | 60-65% | Pathway Aggregation | ✅ OK |
| **Stage 5a** | 72-74% | **Final NES Scoring** | ❌ Out of order! |
| **Stage 4a** | 76-77% | **Semantic Filtering** | ❌ Out of order! |
| **Stage 4b** | 78-79% | **Enhanced Validation** | ❌ Out of order! |
| Stage 6 | 80% | Literature Mining | ⚠️ Should be earlier |
| Final Filtering | 88% | Cardiac Name Filter | ⚠️ Redundant with 4a |
| Stage 7 | 85% | Network Topology & Targets | ❌ Out of order! |
| Reporting | 90% | Report Generation | ✅ OK |
| Complete | 100% | Analysis Complete | ✅ OK |

**Problems:**
1. Stage 5a runs before Stage 4a/4b (illogical)
2. Stage 7 runs at 85% but Stage 6 is at 80% (progress goes backward)
3. "Final Filtering" is redundant with Stage 4a semantic filtering
4. Stage numbers don't match execution order

---

## Proposed Sequential Structure (Logical)

| New Label | Progress % | Description | Rationale |
|-----------|-----------|-------------|-----------|
| **Stage 1** | 5% | Input Validation | Entry point |
| **Stage 2** | 15% | Functional Neighborhood | Network expansion |
| **Stage 3** | 25% | Primary Pathway Enrichment | First enrichment |
| **Stage 4** | 40% | Secondary Pathway Discovery | Expand pathways |
| **Stage 5** | 55% | Pathway Aggregation | Merge & deduplicate |
| **Stage 6** | 65% | NES Scoring | Score pathways |
| **Stage 7** | 72% | Semantic Filtering | Filter by cardiac relevance |
| **Stage 8** | 78% | Enhanced Validation | Biological validation |
| **Stage 9** | 82% | Literature Mining | PubMed citations |
| **Stage 10** | 88% | Network Topology | Hub genes & centrality |
| **Stage 11** | 93% | Therapeutic Targets | Top genes with cardiac scores |
| **Stage 12** | 97% | Report Generation | JSON, PDF, CSV |
| **Complete** | 100% | Analysis Complete | Done |

**Improvements:**
1. ✅ Sequential numbering (1-12)
2. ✅ Logical execution order
3. ✅ No backward progress
4. ✅ Clear stage separation
5. ✅ Removed redundant "Final Filtering"
6. ✅ Split Stage 7 into two stages (10 & 11)

---

## Code Changes Required

### Backend (pipeline.py)
```python
# OLD → NEW mappings
"Stage 0" → "Stage 1"
"Stage 1" → "Stage 2"
"Stage 2a" → "Stage 3"
"Stage 2b" → "Stage 4"
"Stage 2c" → "Stage 5"
"Stage 5a" → "Stage 6"
"Stage 4a" → "Stage 7"
"Stage 4b" → "Stage 8"
"Stage 6" → "Stage 9"
"Stage 7" (topology) → "Stage 10"
"Stage 7" (top genes) → "Stage 11"
"Reporting" → "Stage 12"
```

### Backend (endpoints.py)
```python
# Update stage name mappings
stage_names = {
    "stage_1": "Input Validation",
    "stage_2": "Functional Neighborhood",
    "stage_3": "Primary Pathway Enrichment",
    "stage_4": "Secondary Pathway Discovery",
    "stage_5": "Pathway Aggregation",
    "stage_6": "NES Scoring",
    "stage_7": "Semantic Filtering",
    "stage_8": "Enhanced Validation",
    "stage_9": "Literature Mining",
    "stage_10": "Network Topology",
    "stage_11": "Therapeutic Targets",
    "stage_12": "Report Generation"
}
```

### Frontend (ProgressPage.tsx)
- Update stage descriptions to match new numbering
- Update progress calculations

### Data Storage Keys
**Keep internal keys unchanged** to maintain compatibility with existing analysis results:
- `stage_0` → Keep as is (internal storage)
- `stage_1` → Keep as is
- etc.

**Only change display labels** in progress updates and UI.

---

## Migration Strategy

### Option 1: Display-Only Changes (Recommended)
- ✅ Keep internal stage keys unchanged (`stage_0`, `stage_1`, etc.)
- ✅ Only update display labels in `_update_progress()` calls
- ✅ No data migration needed
- ✅ Existing analyses still work
- ✅ Minimal code changes

### Option 2: Full Refactor
- ❌ Rename all internal keys
- ❌ Requires data migration
- ❌ Breaks existing analyses
- ❌ Extensive code changes
- ❌ High risk

**Decision: Use Option 1** - Display-only changes for safety and compatibility.

---

## Implementation Steps

1. **Update pipeline.py progress labels**
   - Change all `_update_progress()` calls to use new stage numbers
   - Keep internal method names unchanged

2. **Update endpoints.py stage mappings**
   - Update `stage_names` dictionary
   - Keep API response keys unchanged

3. **Update frontend ProgressPage**
   - Update stage descriptions
   - Keep stage ID keys unchanged

4. **Update workflow diagram**
   - Use new sequential numbering
   - Update stage descriptions

5. **Update documentation**
   - Update all references to stage numbers
   - Add migration notes

---

## Testing Checklist

- [ ] Submit new analysis
- [ ] Verify progress shows sequential stages (1-12)
- [ ] Check Results page displays correctly
- [ ] Verify API returns correct data
- [ ] Test with existing analysis (analysis_20251112_092746)
- [ ] Confirm workflow diagram matches execution

---

## Benefits

1. **Clearer for Users** - Sequential numbering is intuitive
2. **Easier to Debug** - Stages match execution order
3. **Better Documentation** - No confusing jumps (5a → 4a)
4. **Professional** - Logical flow shows careful design
5. **Maintainable** - Future stages easy to add

---

**Recommendation:** Proceed with Option 1 (display-only changes) for minimal risk and maximum compatibility.

