"""
ULTRA-STRICT cardiac pathway name filter.
This replaces the permissive filter to ensure ALL final pathways have cardiac-relevant names.
"""

def pathway_name_contains_cardiac_terms_strict(pathway_name: str, disease_context: str = None) -> bool:
    """
    ULTRA-STRICT final filter: pathway NAME must contain EXPLICIT cardiac/cardiovascular terms.
    
    Generic biological processes (contraction, conduction, phosphorylation, etc.) are NOT sufficient.
    The pathway name MUST explicitly mention cardiac/heart/cardiovascular terminology.
    
    Args:
        pathway_name: Name of the pathway to check
        disease_context: Optional disease context (currently not used in strict mode)
        
    Returns:
        True ONLY if pathway name contains explicit cardiac/cardiovascular terms
    """
    import re
    
    pathway_lower = pathway_name.lower()
    
    # ULTRA-STRICT: Only EXPLICIT cardiac/cardiovascular/heart terminology
    # NO generic biological processes allowed
    explicit_cardiac_terms = {
        # Cardiac anatomy - MUST have "cardiac", "heart", "myocardial", etc.
        "cardiac", "heart", "myocardial", "cardiomyocyte", "myocardium",
        "cardiovascular", "coronary", "ventricular", "atrial", "aortic",
        "endocardial", "epicardial", "pericardial", "valvular",
        "cardiac muscle", "heart muscle", "cardiac tissue", "heart tissue",
        
        # Cardiac pathology - MUST explicitly mention cardiac disease
        "cardiomyopathy", "heart failure", "heart disease",
        "myocardial infarction", "cardiac ischemia", "cardiac arrhythmia",
        "cardiac fibrillation", "cardiac arrest",
        
        # Cardiac development - MUST have "cardiac" or "heart" prefix
        "cardiogenesis", "heart development", "cardiac development",
        "cardiac differentiation", "cardiac morphogenesis",
        
        # Cardiac-specific proteins/structures
        "cardiac troponin", "cardiac myosin", "cardiac actin",
        "cardiac sarcomere", "cardiac ion channel",
        
        # Cardiovascular system (broader but still specific)
        "cardiovascular disease", "coronary artery", "coronary disease",
        "cardiac vascular", "myocardial vascular", "cardiac angiogenesis",
        "cardiac hypertrophy", "cardiac remodeling", "cardiac fibrosis"
    }
    
    # Check for explicit cardiac terms (exact substring match)
    for term in explicit_cardiac_terms:
        if term in pathway_lower:
            return True
    
    # Check for cardiac word stems (ONLY cardiac-specific stems)
    # These are VERY specific to avoid false positives
    cardiac_specific_patterns = [
        r"\bcardio\w+",      # cardiomyopathy, cardiogenesis, etc.
        r"\bmyocardi\w+",    # myocardial, myocardium, etc.
        r"\bcoronar\w+",     # coronary, etc.
        r"\bheart\s+\w+",    # heart failure, heart disease, etc.
    ]
    
    for pattern in cardiac_specific_patterns:
        if re.search(pattern, pathway_lower):
            return True
    
    # If none of the above matched, this pathway is NOT cardiac-relevant
    return False
