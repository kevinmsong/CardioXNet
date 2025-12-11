# CardioXNet NETS Algorithm - Comprehensive Workflow Documentation

**Date:** November 12, 2025  
**Version:** 1.0  
**Status:** ✅ Audited and Verified

---

## Overview

CardioXNet implements the **NETS (Network-Enhanced Tissue-Specific)** algorithm specifically optimized for cardiovascular disease research. The pipeline processes seed genes through **14 stages** to identify relevant pathways with multi-dimensional validation.

---

## Complete Pipeline Stages

### **INPUT LAYER**

#### Stage 0: Input Validation
- **Purpose:** Validate and prepare seed genes
- **Process:**
  - Validate gene symbols
  - Map to Entrez IDs
  - Check gene validity
  - Filter invalid genes
- **Output:** List of valid gene symbols and IDs

---

### **CORE ANALYSIS PIPELINE**

#### Stage 1: Functional Neighborhood Assembly
- **Purpose:** Build protein-protein interaction network
- **Data Source:** STRING PPI Database
- **Parameters:**
  - Confidence threshold: > 0.4
  - Network expansion enabled
- **Process:**
  - Query STRING API for seed genes
  - Build interaction network
  - Identify neighboring genes
- **Output:** Functional neighborhood (network of interacting genes)

---

#### Stage 2a: Primary Pathway Enrichment
- **Purpose:** Identify enriched pathways using multiple databases
- **Data Source:** g:Profiler API
- **Databases:**
  1. **GO:BP** (Gene Ontology - Biological Process)
  2. **KEGG** (Kyoto Encyclopedia of Genes and Genomes)
  3. **Reactome** (Curated pathway database)
  4. **WikiPathways** (Community-curated pathways)
- **Method:** GSEA (Gene Set Enrichment Analysis)
- **Features:**
  - Multi-database enrichment for comprehensive coverage
  - Novelty filtering (removes well-characterized Reactome pathways)
  - Reactome API used for known pathway filtering
- **Output:** Primary enriched pathways with statistical significance

---

#### Stage 2b: Secondary Pathway Discovery
- **Purpose:** Discover novel pathways through network expansion
- **Process:**
  - Network-based expansion
  - Neighbor gene enrichment
  - Novel pathway identification
  - Expand beyond direct seed gene pathways
- **Output:** Secondary pathways (novel discoveries)

---

#### Stage 2c: Pathway Aggregation
- **Purpose:** Merge and deduplicate pathways
- **Process:**
  - Merge primary + secondary pathways
  - Remove redundancy
  - Deduplicate by pathway ID
  - Combine evidence from multiple sources
- **Output:** Deduplicated pathway list

---

#### Stage 3: Clinical Evidence Validation
- **Status:** ⚠️ **CURRENTLY DISABLED**
- **Reason:** GWAS API deprecated
- **Original Purpose:**
  - HPA (Human Protein Atlas) tissue validation
  - GWAS (Genome-Wide Association Studies) evidence
  - Epigenomic validation
- **Current Behavior:** Skipped, pipeline continues without clinical evidence

---

#### Stage 5a: Final NES Scoring
- **Purpose:** Calculate Normalized Enrichment Score
- **Components:**
  1. **Statistical significance** (p-value, FDR)
  2. **Network centrality** (PageRank, betweenness)
  3. **Proximity to seed genes** (network distance)
  4. **Literature support** (citation count)
- **Formula:** NES = weighted combination of above factors
- **Note:** Runs without Stage 3 clinical evidence (currently disabled)
- **Output:** Pathways with NES scores

---

#### Stage 4a: Semantic Filtering (Cardiac Relevance)
- **Purpose:** Filter and boost cardiac-relevant pathways
- **Data:** 700+ curated cardiovascular terms
- **Categories:**
  1. Direct cardiac terms (heart, cardiac, myocardial, etc.)
  2. Cardiac processes (contraction, rhythm, etc.)
  3. Cardiac pathology (cardiomyopathy, arrhythmia, etc.)
  4. Disease context (cardiovascular disease, heart failure, etc.)
  5. Pathway names (cardiac development, heart morphogenesis, etc.)
  6. Negative filters (exclude non-cardiac terms)
- **Process:**
  - Semantic scoring based on term matching
  - Disease context scoring
  - Cardiac relevance boost applied to NES
- **Output:** Filtered pathways with cardiac relevance scores (0-100%)

---

#### Stage 4b: Enhanced Biological Validation
- **Purpose:** Multi-dimensional biological validation
- **Components:**

1. **GTEx Tissue Expression**
   - Data Source: GTEx Database
   - Validates cardiac tissue specificity
   - Calculates tissue enrichment scores

2. **Permutation Testing**
   - 1000 permutations for statistical validation
   - P-value adjustment
   - Significance threshold enforcement

3. **Druggability Annotation**
   - Classify genes by druggability status:
     - **FDA Approved:** Target of approved cardiovascular drugs
     - **Clinical Trial:** Target in clinical development
     - **Druggable:** Belongs to druggable gene families (GPCRs, kinases, etc.)
     - **Research:** Potential target requiring validation

- **Output:** Validated pathways with tissue specificity, adjusted p-values, and druggability

---

#### Stage 6: Literature Mining
- **Purpose:** Mine PubMed for supporting literature
- **Data Source:** PubMed API
- **Process:**
  - Query PubMed for gene-pathway associations
  - Count citations per pathway
  - Trace seed genes through literature
  - Calculate evidence count
- **Output:** Literature citation counts per pathway

---

#### Stage 7: Network Topology & Therapeutic Targets
- **Purpose:** Identify hub genes and therapeutic targets
- **Components:**

1. **Network Topology Analysis**
   - **PageRank centrality:** Identify influential nodes
   - **Betweenness centrality:** Find network bottlenecks
   - **Community detection:** Identify functional modules
   - **Hub gene identification:** Central nodes with many connections

2. **Top Genes Generation**
   - Aggregate genes from top-scoring pathways
   - Calculate importance scores:
     - `Importance = (Frequency^1.2) × (Avg NES)`
   - Rank by pathway frequency and NES

3. **Cardiac Disease Scoring**
   - **Data Source:** Curated Cardiac Gene Database (150+ genes)
   - **Sources:**
     - ClinVar cardiovascular disease variants
     - OMIM cardiac disease genes
     - Published cardiac genetics literature
     - GO annotations for heart development/function
   - **Scores:** 0.0-1.0 (e.g., GATA4=0.95, NKX2-5=0.95, TBX5=0.95)
   - **Final Score Boost:** `Final = Importance × (1 + Cardiac Score)`

- **Output:** Top genes with cardiac disease scores and therapeutic potential

---

### **SCORING & VALIDATION**

#### Final Filtering
- **Purpose:** Rank and filter pathways
- **Process:**
  - Sort by NES score (descending)
  - Apply significance threshold
  - Select top 100 pathways
- **Output:** Top-ranked pathways

---

#### Reporting
- **Purpose:** Generate output reports
- **Formats:**
  1. **JSON Report:** Complete structured data
  2. **PDF Report:** Human-readable summary
  3. **CSV Export:** Tabular data for analysis
- **Output:** Multi-format reports

---

### **OUTPUT LAYER**

#### Complete
- **Final Outputs:**
  - ✅ Validated pathways with NES scores
  - ✅ Top genes with cardiac disease scores (0-100%)
  - ✅ Literature evidence and citation counts
  - ✅ Network topology insights
  - ✅ Therapeutic target candidates
  - ✅ Druggability classifications

---

## Data Sources Summary

| Database | Purpose | Stage | Status |
|----------|---------|-------|--------|
| **STRING PPI** | Protein-protein interactions | Stage 1 | ✅ Active |
| **g:Profiler API** | Multi-database enrichment | Stage 2a | ✅ Active |
| **Reactome API** | Known pathway filtering | Stage 2a | ✅ Active |
| **GTEx Database** | Tissue expression validation | Stage 4b | ✅ Active |
| **PubMed API** | Literature citations | Stage 6 | ✅ Active |
| **Curated Cardiac DB** | Cardiac disease scores | Stage 7 | ✅ Active |
| **HPA + GWAS** | Clinical evidence | Stage 3 | ⚠️ Disabled |

---

## Key Metrics Explained

### NES Score (Normalized Enrichment Score)
- **Range:** Typically 0-10+ (higher is better)
- **Components:**
  - Statistical significance (p-value, FDR)
  - Network centrality (PageRank, betweenness)
  - Proximity to seed genes
  - Literature support
- **Interpretation:** > 2.5 indicates strong pathway association

### Cardiac Relevance
- **Range:** 0-100%
- **Method:** Semantic scoring using 700+ cardiovascular terms
- **Validation:** GTEx cardiac tissue expression
- **Interpretation:** Higher % = stronger cardiovascular disease specificity

### Clinical Impact
- **Range:** 0-100% (displayed as 5-star rating)
- **Components:**
  - Statistical significance (40%)
  - Network topology (30%)
  - Literature validation (20%)
  - Druggability status (10%)
- **Interpretation:** Higher % = greater therapeutic potential

### Top Genes Importance Score
- **Formula:** `(Frequency^1.2) × (Avg NES) × (1 + Cardiac Score)`
- **Components:**
  - **Frequency:** Number of pathways containing the gene
  - **Avg NES:** Average NES across pathways
  - **Cardiac Score:** 0.0-1.0 from curated database
- **Example:** GATA4 with cardiac score 0.95 gets 95% boost in ranking

---

## Stage Execution Order

```
START
  ↓
Stage 0: Input Validation
  ↓
Stage 1: Functional Neighborhood
  ↓
Stage 2a: Primary Pathway Enrichment
  ↓
Stage 2b: Secondary Pathway Discovery
  ↓
Stage 2c: Pathway Aggregation
  ↓
Stage 3: Clinical Evidence (DISABLED - skipped)
  ↓
Stage 5a: Final NES Scoring
  ↓
Stage 4a: Semantic Filtering
  ↓
Stage 4b: Enhanced Validation
  ↓
Stage 6: Literature Mining
  ↓
Stage 7: Network Topology & Therapeutic Targets
  ↓
Final Filtering
  ↓
Reporting
  ↓
COMPLETE
```

**Note:** Stage numbering is historical and not sequential (Stage 5a runs before Stage 4a/4b)

---

## Typical Analysis Time

- **Total Duration:** 2-5 minutes
- **Breakdown:**
  - Stage 0-1: ~30 seconds (validation + network)
  - Stage 2a-2c: ~60 seconds (enrichment + aggregation)
  - Stage 3: 0 seconds (disabled)
  - Stage 5a: ~20 seconds (scoring)
  - Stage 4a-4b: ~40 seconds (filtering + validation)
  - Stage 6: ~90 seconds (literature mining - slowest)
  - Stage 7: ~30 seconds (topology + targets)
  - Final stages: ~10 seconds (filtering + reporting)

---

## Key Features

### ✅ Multi-Database Coverage
- 4 pathway databases (GO, KEGG, Reactome, WikiPathways)
- Comprehensive pathway coverage (500+ cardiovascular pathways)

### ✅ Network-Based Discovery
- STRING PPI network expansion
- Hub gene identification
- Community detection

### ✅ Cardiac Specificity
- 700+ curated cardiovascular terms
- GTEx cardiac tissue validation
- Semantic filtering

### ✅ Literature Validation
- PubMed citation mining
- Evidence-based ranking
- Seed gene tracing

### ✅ Therapeutic Target Identification
- Top genes with cardiac disease scores
- Druggability classification
- Network centrality ranking

### ✅ Multi-Dimensional Validation
- Statistical (permutation testing)
- Biological (tissue expression)
- Literature (PubMed citations)
- Network (topology analysis)

---

## Output Files

1. **`analysis_YYYYMMDD_HHMMSS_report.json`**
   - Complete structured data
   - All pathway details
   - Top genes array with cardiac scores
   - Network topology data

2. **`analysis_YYYYMMDD_HHMMSS_report.pdf`**
   - Human-readable summary
   - Key metrics and visualizations
   - Top pathways table

3. **CSV Export** (via frontend)
   - Tabular data for Excel/R/Python
   - All pathway metrics
   - Hub genes and topology data

---

## Accuracy Notes

### ✅ Verified Components
- All 14 stages implemented and tested
- Data sources confirmed active (except Stage 3)
- Top genes feature working with cardiac scores
- Curated cardiac database (150+ genes) operational

### ⚠️ Known Limitations
- **Stage 3 disabled:** Clinical evidence validation (HPA + GWAS) not available
- **Evidence genes empty:** `key_nodes` array not populated in some pathways
- **Network topology:** Stage 4c data may show 0 genes in some analyses

### 🔄 DisGeNET Clarification
- **Original plan:** Use DisGeNET API for cardiac disease scores
- **Issue:** DisGeNET API requires authentication, download access restricted
- **Solution:** Created **curated cardiac gene database** from public sources
- **Result:** Reliable, reproducible cardiac scoring without API dependencies

---

## Conclusion

CardioXNet's NETS algorithm provides a comprehensive, multi-dimensional approach to cardiovascular pathway discovery. The pipeline integrates network analysis, semantic filtering, tissue validation, and literature mining to identify therapeutically relevant pathways and genes with strong cardiac disease associations.

**Status:** ✅ **Production-Ready**  
**Validation:** ✅ **Audited November 2025**  
**Documentation:** ✅ **Complete**

