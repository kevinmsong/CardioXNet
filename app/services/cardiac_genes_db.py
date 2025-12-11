"""
Curated Cardiac Gene Database

Compiled from public sources including:
- ClinVar cardiovascular disease variants
- OMIM cardiac disease genes
- Published literature on cardiac genetics
- GO annotations for heart development/function
"""

# Cardiac disease association scores (0.0-1.0) based on literature evidence
CARDIAC_GENE_SCORES = {
    # Core cardiac transcription factors (very high confidence)
    "GATA4": 0.95,
    "NKX2-5": 0.95,
    "TBX5": 0.95,
    "HAND2": 0.90,
    "ISL1": 0.90,
    "MEF2C": 0.90,
    "TBX20": 0.88,
    "GATA6": 0.85,
    "TBX1": 0.85,
    "TBX3": 0.82,
    
    # Ion channels and arrhythmia genes (high confidence)
    "SCN5A": 0.95,
    "KCNQ1": 0.93,
    "KCNH2": 0.93,
    "RYR2": 0.92,
    "KCNE1": 0.90,
    "KCNE2": 0.88,
    "CACNA1C": 0.90,
    "HCN4": 0.88,
    "SCN1B": 0.85,
    "SCN3B": 0.82,
    "KCNJ2": 0.88,
    "KCNJ5": 0.85,
    "ANK2": 0.88,
    "CAV3": 0.85,
    
    # Cardiomyopathy genes (high confidence)
    "MYH7": 0.95,
    "MYBPC3": 0.95,
    "TNNT2": 0.93,
    "TNNI3": 0.92,
    "TPM1": 0.90,
    "MYL2": 0.88,
    "MYL3": 0.85,
    "ACTC1": 0.90,
    "TTN": 0.92,
    "LMNA": 0.88,
    "DES": 0.85,
    "PLN": 0.88,
    "DSP": 0.88,
    "PKP2": 0.88,
    "DSG2": 0.85,
    "DSC2": 0.82,
    "JUP": 0.80,
    "TMEM43": 0.80,
    
    # Signaling pathways (moderate-high confidence)
    "NOTCH1": 0.85,
    "JAG1": 0.82,
    "NOTCH2": 0.75,
    "HEY1": 0.78,
    "HEY2": 0.78,
    "HEYL": 0.75,
    "BMP4": 0.80,
    "BMP2": 0.75,
    "SMAD4": 0.72,
    "SMAD1": 0.70,
    "SMAD5": 0.70,
    "WNT5A": 0.75,
    "WNT11": 0.72,
    "CTNNB1": 0.70,
    
    # Structural proteins (moderate-high confidence)
    "ACTN2": 0.85,
    "CSRP3": 0.82,
    "TCAP": 0.80,
    "LDB3": 0.80,
    "MYOZ2": 0.78,
    "NEXN": 0.75,
    "VCL": 0.78,
    "ANKRD1": 0.75,
    
    # Metabolic/mitochondrial (moderate confidence)
    "PRKAG2": 0.82,
    "GLA": 0.80,
    "LAMP2": 0.78,
    "TAZ": 0.80,
    "SCO2": 0.75,
    "COX15": 0.72,
    
    # Calcium handling (high confidence)
    "CASQ2": 0.88,
    "CALM1": 0.85,
    "CALM2": 0.85,
    "CALM3": 0.85,
    "TRDN": 0.80,
    "CALR3": 0.75,
    
    # Congenital heart disease (high confidence)
    "CHD7": 0.88,
    "ZIC3": 0.85,
    "NODAL": 0.82,
    "LEFTY2": 0.80,
    "CFC1": 0.82,
    "ACVR2B": 0.78,
    "GDF1": 0.78,
    "FOXH1": 0.75,
    "NKX2-6": 0.80,
    "HAND1": 0.82,
    
    # Aortic disease (moderate-high confidence)
    "FBN1": 0.88,
    "TGFBR1": 0.85,
    "TGFBR2": 0.85,
    "SMAD3": 0.80,
    "TGFB2": 0.78,
    "TGFB3": 0.75,
    "ACTA2": 0.85,
    "MYH11": 0.82,
    "MYLK": 0.75,
    
    # Familial hypercholesterolemia/CAD (moderate confidence)
    "LDLR": 0.75,
    "APOB": 0.72,
    "PCSK9": 0.75,
    "LDLRAP1": 0.70,
    "APOE": 0.68,
    
    # Heart failure/dilated cardiomyopathy (high confidence)
    "BAG3": 0.85,
    "FLNC": 0.82,
    "RBM20": 0.82,
    "LMNA": 0.88,
    "EMD": 0.80,
    "SYNE1": 0.75,
    "SYNE2": 0.72,
    
    # Pulmonary hypertension (moderate confidence)
    "BMPR2": 0.82,
    "ENG": 0.78,
    "ACVRL1": 0.78,
    "SMAD9": 0.72,
    "CAV1": 0.70,
    
    # Atrial fibrillation (moderate confidence)
    "NPPA": 0.78,
    "NPPB": 0.75,
    "GJA5": 0.75,
    "PITX2": 0.72,
    "ZFHX3": 0.70,
}

# Disease categories for each gene
CARDIAC_DISEASE_CATEGORIES = {
    "arrhythmia": ["SCN5A", "KCNQ1", "KCNH2", "RYR2", "KCNE1", "KCNE2", "CACNA1C", 
                   "HCN4", "SCN1B", "SCN3B", "KCNJ2", "KCNJ5", "ANK2", "CAV3", 
                   "CASQ2", "CALM1", "CALM2", "CALM3", "TRDN"],
    "cardiomyopathy": ["MYH7", "MYBPC3", "TNNT2", "TNNI3", "TPM1", "MYL2", "MYL3", 
                       "ACTC1", "TTN", "LMNA", "DES", "PLN", "DSP", "PKP2", "DSG2", 
                       "DSC2", "JUP", "TMEM43", "BAG3", "FLNC", "RBM20"],
    "congenital_heart_disease": ["GATA4", "NKX2-5", "TBX5", "HAND2", "ISL1", "MEF2C", 
                                  "TBX20", "GATA6", "TBX1", "TBX3", "CHD7", "ZIC3", 
                                  "NODAL", "LEFTY2", "CFC1", "ACVR2B", "GDF1", "FOXH1", 
                                  "NKX2-6", "HAND1"],
    "aortic_disease": ["FBN1", "TGFBR1", "TGFBR2", "SMAD3", "TGFB2", "TGFB3", 
                       "ACTA2", "MYH11", "MYLK"],
    "heart_failure": ["BAG3", "FLNC", "RBM20", "LMNA", "EMD", "SYNE1", "SYNE2", 
                      "TTN", "MYH7", "MYBPC3"],
}


def get_cardiac_score(gene_symbol: str) -> float:
    """
    Get cardiac disease association score for a gene.
    
    Args:
        gene_symbol: Gene symbol (e.g., "GATA4")
    
    Returns:
        Cardiac disease association score (0.0-1.0)
    """
    return CARDIAC_GENE_SCORES.get(gene_symbol.upper(), 0.0)


def get_disease_categories(gene_symbol: str) -> list:
    """
    Get cardiac disease categories for a gene.
    
    Args:
        gene_symbol: Gene symbol
    
    Returns:
        List of disease category names
    """
    categories = []
    gene_upper = gene_symbol.upper()
    
    for category, genes in CARDIAC_DISEASE_CATEGORIES.items():
        if gene_upper in genes:
            categories.append(category)
    
    return categories


def is_cardiac_gene(gene_symbol: str, threshold: float = 0.5) -> bool:
    """
    Check if a gene is considered cardiac-relevant.
    
    Args:
        gene_symbol: Gene symbol
        threshold: Minimum score threshold (default 0.5)
    
    Returns:
        True if gene has cardiac score >= threshold
    """
    return get_cardiac_score(gene_symbol) >= threshold


def get_batch_scores(gene_symbols: list) -> dict:
    """
    Get cardiac scores for multiple genes.
    
    Args:
        gene_symbols: List of gene symbols
    
    Returns:
        Dictionary mapping gene symbol to cardiac score
    """
    return {gene: get_cardiac_score(gene) for gene in gene_symbols}




def calculate_pathway_cardiac_score(evidence_genes: list) -> float:
    """
    Calculate pathway-level cardiac disease score based on evidence genes.
    
    Uses a weighted approach:
    - Takes top 10 genes by cardiac score (or all if fewer)
    - Calculates weighted average with exponential decay
    - Higher-scoring genes contribute more to the pathway score
    
    Args:
        evidence_genes: List of gene symbols in the pathway
    
    Returns:
        Pathway cardiac disease score (0.0-1.0)
    """
    if not evidence_genes:
        return 0.0
    
    # Get scores for all genes
    gene_scores = []
    for gene in evidence_genes:
        score = get_cardiac_score(gene)
        if score > 0:
            gene_scores.append(score)
    
    if not gene_scores:
        return 0.0
    
    # Sort descending
    gene_scores.sort(reverse=True)
    
    # Take top 10 genes (or all if fewer)
    top_genes = gene_scores[:10]
    
    # Calculate weighted average with exponential decay
    # First gene: weight 1.0, second: 0.9, third: 0.81, etc.
    weights = [0.9 ** i for i in range(len(top_genes))]
    weighted_sum = sum(score * weight for score, weight in zip(top_genes, weights))
    weight_sum = sum(weights)
    
    pathway_score = weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    return round(pathway_score, 3)


def get_pathway_cardiac_stats(evidence_genes: list) -> dict:
    """
    Get detailed cardiac statistics for a pathway.
    
    Args:
        evidence_genes: List of gene symbols in the pathway
    
    Returns:
        Dictionary with cardiac statistics
    """
    if not evidence_genes:
        return {
            "pathway_score": 0.0,
            "cardiac_gene_count": 0,
            "total_gene_count": 0,
            "cardiac_gene_fraction": 0.0,
            "top_cardiac_genes": []
        }
    
    # Get scores for all genes
    gene_scores = {gene: get_cardiac_score(gene) for gene in evidence_genes}
    cardiac_genes = {gene: score for gene, score in gene_scores.items() if score > 0}
    
    # Calculate pathway score
    pathway_score = calculate_pathway_cardiac_score(evidence_genes)
    
    # Get top cardiac genes
    top_genes = sorted(cardiac_genes.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "pathway_score": pathway_score,
        "cardiac_gene_count": len(cardiac_genes),
        "total_gene_count": len(evidence_genes),
        "cardiac_gene_fraction": len(cardiac_genes) / len(evidence_genes) if evidence_genes else 0.0,
        "top_cardiac_genes": [{"gene": gene, "score": score} for gene, score in top_genes]
    }

