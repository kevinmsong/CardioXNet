# How Cardiac Context Influences CardioXNet Results

CardioXNet uses the provided cardiac disease context to ensure the analysis is highly relevant to cardiovascular research. The context is applied at multiple stages of the pipeline to filter, score, and prioritize pathways.

---

## 1. Semantic Filtering (Stage 4a)

**What it does:** Filters pathways based on semantic relevance to the cardiac context.

**How it works:**
- Pathway names are matched against a curated list of **700+ cardiovascular terms**.
- Pathways with names containing cardiac terms get a **+30% relevance boost**.
- Non-cardiac pathways receive a **-50% penalty**.
- This ensures pathways with direct cardiac relevance are prioritized.

## 2. Final Strict Name Filtering (Stage 6c)

**What it does:** Applies a final strict filter requiring pathway names to contain cardiac terms.

**How it works:**
- Only pathways with names containing **direct cardiac terms** (e.g., "cardiac", "heart", "myocardial") are kept.
- This guarantees all final results are explicitly cardiac-related.

## 3. Cardiac Disease Scoring

**What it does:** Scores pathways based on their association with cardiovascular disease genes.

**How it works:**
- Pathways are scored based on the presence of genes from a curated **cardiovascular disease gene database** (200+ genes).
- The score is a weighted average of the top 10 cardiac genes in the pathway.
- This provides a quantitative measure of cardiac relevance.

## 4. Evidence Integration (Literature & Databases)

**What it does:** Cross-references pathways with literature and databases for cardiac relevance.

**How it works:**
- **PubMed:** Searches for co-occurrence of pathway name and cardiac terms.
- **DisGeNET:** Scores genes based on association with cardiovascular diseases.
- This adds another layer of evidence for cardiac relevance.

---

By integrating cardiac context at multiple stages, CardioXNet delivers highly relevant and accurate results for cardiovascular research.
