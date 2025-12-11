"""Cardiovascular disease and phenotype-aware context configuration."""

from typing import List, Dict
from pydantic import BaseModel, Field


class CardiacContext(BaseModel):
    """Cardiovascular disease and phenotype-aware search context with weighted keywords."""
    
    species: str = Field(default="Homo sapiens", description="Target species")
    
    # High priority keywords (weight: 2.0)
    high_priority_keywords: List[str] = Field(
        default_factory=lambda: [
            "cardiovascular disease",
            "heart failure",
            "myocardial infarction",
            "cardiomyopathy",
            "hypertensive heart disease",
            "cardiac hypertrophy",
            "cardiac fibrosis",
            "atherosclerosis",
            "coronary artery disease",
            "cardiac arrhythmias"
        ],
        description="High priority cardiovascular disease keywords"
    )
    
    # Medium priority keywords (weight: 1.5)
    medium_priority_keywords: List[str] = Field(
        default_factory=lambda: [
            "cardiac remodeling",
            "cardiomyocyte",
            "apoptosis",
            "cardiac inflammation",
            "cardiac fibrosis",
            "angiogenesis",
            "cell survival",
            "myocardial infarction",
            "heart failure",
            "ischemic heart disease",
            "ventricular remodeling",
            "atrial remodeling",
            "cardiac hypertrophy",
            "pathological hypertrophy",
            "physiological hypertrophy",
            "cardiac stem cells",
            "cardiac progenitor cells",
            "endothelial progenitor cells",
            "mesenchymal stem cells",
            "induced pluripotent stem cells",
            "cell therapy",
            "stem cell transplantation",
            "cardiac tissue engineering",
            "myocardial salvage",
            "infarct size",
            "scar formation",
            "wound healing"
        ],
        description="Medium priority cardiac keywords"
    )
    
    # Low priority keywords (weight: 1.0)
    low_priority_keywords: List[str] = Field(
        default_factory=lambda: [
            "cardiac function",
            "cardiac metabolism",
            "contractility",
            "ejection fraction",
            "mitochondrial function",
            "oxidative stress",
            "cardiac performance",
            "hemodynamics",
            "stroke volume",
            "cardiac index",
            "ventricular function",
            "atrial function",
            "diastolic dysfunction",
            "systolic dysfunction",
            "heart rate variability",
            "arrhythmia",
            "electrophysiology",
            "ion channels",
            "calcium handling",
            "excitation-contraction coupling"
        ],
        description="Low priority cardiac keywords"
    )
    
    # Comprehensive keyword list (all priorities combined)
    keywords: List[str] = Field(
        default_factory=lambda: [
            # Core cardiovascular disease and phenotype processes
            "cardiovascular disease",
            "cardiac remodeling",
            "myocardial repair",
            "heart repair",
            "heart regeneration",
            "cardiac regeneration",
            "myocardial regeneration",
            "cardiac healing",
            "myocardial healing",
            "ventricular remodeling",
            "atrial remodeling",
            "reverse remodeling",
            "adaptive remodeling",
            "maladaptive remodeling",
            
            # Cell types and differentiation
            "cardiomyocyte",
            "cardiac progenitor",
            "cardiac stem cell",
            "cardiomyocyte differentiation",
            "cardiomyocyte proliferation",
            "cardiomyocyte maturation",
            "cardiac fibroblast",
            "myofibroblast",
            "endothelial cell",
            "vascular smooth muscle",
            "pericyte",
            "cardiac progenitor cells",
            "endothelial progenitor cells",
            "mesenchymal stem cells",
            "induced pluripotent stem cells",
            "embryonic stem cells",
            "adult stem cells",
            "resident cardiac stem cells",
            
            # Pathological conditions
            "myocardial infarction",
            "heart failure",
            "ischemic heart disease",
            "dilated cardiomyopathy",
            "hypertrophic cardiomyopathy",
            "restrictive cardiomyopathy",
            "cardiac injury",
            "ischemia reperfusion",
            "ischemia reperfusion injury",
            "acute myocardial infarction",
            "chronic heart failure",
            "congestive heart failure",
            "coronary artery disease",
            "atherosclerosis",
            "myocardial ischemia",
            "cardiac arrest",
            "sudden cardiac death",
            "arrhythmogenic cardiomyopathy",
            
            # Cell death and survival mechanisms
            "apoptosis",
            "necrosis",
            "necroptosis",
            "pyroptosis",
            "ferroptosis",
            "autophagy",
            "mitophagy",
            "cell survival",
            "cell death",
            "anti-apoptotic",
            "pro-apoptotic",
            "cardioprotection",
            "cardiomyocyte death",
            "cardiomyocyte survival",
            "programmed cell death",
            "caspase activation",
            "BCL2 family",
            
            # Inflammation and immune response
            "cardiac inflammation",
            "myocarditis",
            "inflammatory response",
            "immune cell infiltration",
            "cytokine",
            "chemokine",
            "interleukin",
            "tumor necrosis factor",
            "macrophage",
            "neutrophil infiltration",
            "lymphocyte",
            "T cell",
            "B cell",
            "monocyte",
            "inflammatory cytokines",
            "pro-inflammatory",
            "anti-inflammatory",
            "innate immunity",
            "adaptive immunity",
            "immune modulation",
            
            # Fibrosis and ECM remodeling
            "cardiac fibrosis",
            "myocardial fibrosis",
            "interstitial fibrosis",
            "perivascular fibrosis",
            "replacement fibrosis",
            "reactive fibrosis",
            "extracellular matrix",
            "ECM remodeling",
            "collagen deposition",
            "collagen synthesis",
            "matrix metalloproteinase",
            "MMP",
            "TIMP",
            "fibroblast activation",
            "fibroblast proliferation",
            "myofibroblast differentiation",
            "tissue inhibitor of metalloproteinase",
            
            # Angiogenesis and vascularization
            "angiogenesis",
            "neovascularization",
            "vasculogenesis",
            "vascular remodeling",
            "endothelial dysfunction",
            "capillary density",
            "microvascular dysfunction",
            "coronary microcirculation",
            "collateral circulation",
            "arteriogenesis",
            "VEGF",
            "vascular endothelial growth factor",
            "angiopoietin",
            "endothelial nitric oxide synthase",
            
            # Signaling pathways (cardiac-specific)
            "Wnt signaling",
            "Notch signaling",
            "Hippo pathway",
            "YAP/TAZ",
            "TGF-beta",
            "TGF-beta signaling",
            "SMAD signaling",
            "NF-kappa B",
            "NF-kappaB signaling",
            "MAPK signaling",
            "ERK signaling",
            "JNK signaling",
            "p38 MAPK",
            "PI3K/Akt",
            "mTOR signaling",
            "JAK/STAT",
            "Hedgehog signaling",
            "BMP signaling",
            "cAMP signaling",
            "PKA signaling",
            "PKC signaling",
            "calcineurin signaling",
            "NFAT signaling",
            
            # Contractility and function
            "cardiac function",
            "contractility",
            "ejection fraction",
            "systolic function",
            "diastolic function",
            "cardiac output",
            "stroke volume",
            "cardiac performance",
            "ventricular function",
            "atrial function",
            "left ventricular function",
            "right ventricular function",
            "fractional shortening",
            "wall motion",
            "regional wall motion",
            "global longitudinal strain",
            "cardiac mechanics",
            
            # Metabolism and energetics
            "cardiac metabolism",
            "mitochondrial function",
            "oxidative stress",
            "metabolic remodeling",
            "fatty acid oxidation",
            "glucose metabolism",
            "glycolysis",
            "oxidative phosphorylation",
            "ATP production",
            "energy metabolism",
            "metabolic switch",
            "substrate utilization",
            "ketone metabolism",
            "lactate metabolism",
            "mitochondrial biogenesis",
            "mitochondrial dynamics",
            "mitochondrial fission",
            "mitochondrial fusion",
            "reactive oxygen species",
            "ROS",
            "antioxidant",
            
            # Electrophysiology and ion handling
            "arrhythmia",
            "electrophysiology",
            "ion channels",
            "calcium handling",
            "excitation-contraction coupling",
            "action potential",
            "sodium channels",
            "potassium channels",
            "calcium channels",
            "sarcoplasmic reticulum",
            "ryanodine receptor",
            "SERCA",
            "sodium-calcium exchanger",
            "gap junctions",
            "connexin",
            "conduction system",
            
            # Therapeutic interventions
            "cell therapy",
            "stem cell transplantation",
            "cardiac tissue engineering",
            "gene therapy",
            "exosome therapy",
            "growth factor therapy",
            "cytokine therapy",
            "pharmacological intervention",
            "reperfusion therapy",
            "preconditioning",
            "postconditioning",
            "remote ischemic conditioning",
            
            # Cardiac structure and anatomy
            "myocardium",
            "endocardium",
            "epicardium",
            "pericardium",
            "left ventricle",
            "right ventricle",
            "left atrium",
            "right atrium",
            "interventricular septum",
            "cardiac valve",
            "coronary vessels",
            "coronary circulation",
            
            # Molecular markers and biomarkers
            "troponin",
            "BNP",
            "NT-proBNP",
            "CK-MB",
            "cardiac biomarkers",
            "natriuretic peptide",
            "galectin-3",
            "ST2",
            "microRNA",
            "miRNA",
            "long non-coding RNA",
            "lncRNA",
            "circular RNA",
            
            # Hemodynamics and physiology
            "hemodynamics",
            "blood pressure",
            "preload",
            "afterload",
            "cardiac index",
            "heart rate",
            "heart rate variability",
            "autonomic nervous system",
            "sympathetic activation",
            "parasympathetic",
            "baroreceptor",
            "renin-angiotensin system",
            "RAAS",
            "neurohormonal activation",
            
            # Pathophysiological processes
            "myocardial salvage",
            "infarct size",
            "area at risk",
            "no-reflow phenomenon",
            "microvascular obstruction",
            "stunning",
            "hibernating myocardium",
            "scar formation",
            "scar tissue",
            "border zone",
            "remote zone",
            "wound healing",
            "tissue repair",
            "diastolic dysfunction",
            "systolic dysfunction",
            "heart failure with preserved ejection fraction",
            "HFpEF",
            "heart failure with reduced ejection fraction",
            "HFrEF"
        ],
        description="Comprehensive list of cardiac-related keywords"
    )
    
    # Keyword weights for relevance scoring
    keyword_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "high_priority": 2.0,
            "medium_priority": 1.5,
            "low_priority": 1.0
        },
        description="Weight multipliers for keyword categories"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "species": "Homo sapiens",
                "high_priority_keywords": [
                    "cardiovascular disease",
                    "heart failure"
                ],
                "medium_priority_keywords": [
                    "cardiac remodeling",
                    "cardiomyocyte"
                ],
                "low_priority_keywords": [
                    "cardiac function",
                    "cardiac metabolism"
                ],
                "keyword_weights": {
                    "high_priority": 2.0,
                    "medium_priority": 1.5,
                    "low_priority": 1.0
                }
            }
        }
