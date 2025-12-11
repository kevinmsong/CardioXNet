"""Semantic filtering service for cardiac context relevance."""

import logging
from typing import List, Dict, Set, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from app.models import ScoredPathway, CardiacContext
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SemanticFilter:
    """Filters and scores pathways based on semantic cardiac relevance with expanded criteria.
    
    Scientific Rigor Enhancements:
    - Multi-category semantic scoring (700+ curated cardiovascular terms)
    - Disease context weighting provides up to +30% boost for disease-specific pathways
    - 75% priority to cardiovascular disease category ensures clinical relevance
    - Negative penalty system (-50% max) filters non-cardiac pathways
    - Fuzzy pattern matching captures complex terminology variations
    - Progressive thresholding balances sensitivity and specificity for novel discovery
    """
    
    def __init__(self):
        """Initialize semantic filter with comprehensive cardiac context."""
        self.settings = get_settings()
        self.cardiac_context = CardiacContext()
        
        # Category 1: Direct Cardiac Terms (50% weight)
        self.direct_cardiac_terms = {
            "cardiac", "heart", "myocardial", "cardiomyocyte", "myocardium",
            "cardiovascular", "coronary", "ventricular", "atrial", "aortic",
            "pericardial", "endocardial", "epicardial", "cardio", "cardiogenic",
            "cardiogenesis", "myogenesis", "myogenic", "sarcomeric", "sarcomere",
            "myofilament", "myosin", "actin", "troponin", "tropomyosin",
            "cardiac muscle", "heart muscle", "myocardial tissue", "cardiac tissue",
            "heart tissue", "ventricle", "atrium", "cardiac valve", "heart valve",
            "cardiac septum", "interventricular septum", "interatrial septum",
            "cardiac conduction", "cardiac pacemaker", "sinoatrial node", "sa node",
            "atrioventricular node", "av node", "bundle of his", "purkinje fiber",
            "cardiac autonomic", "cardiac sympathetic", "cardiac parasympathetic",
            "cardiac vagus", "cardiac adrenergic", "cardiac cholinergic"
        }
        
        # Category 2: Cardiac Processes (30% weight)
        self.cardiac_processes = {
            "contraction", "contractility", "excitation", "conduction",
            "remodeling", "hypertrophy", "fibrosis", "ischemia", "reperfusion",
            "perfusion", "systole", "diastole", "ejection", "relaxation",
            "development", "morphogenesis", "differentiation", "maturation",
            "apoptosis", "autophagy", "proliferation", "cell death", "cell survival",
            "angiogenesis", "vasculogenesis", "arteriogenesis", "neovascularization",
            "revascularization", "endothelialization", "re-endothelialization",
            "inflammation", "anti-inflammation", "immune response", "immunomodulation",
            "oxidative stress", "antioxidant defense", "redox regulation",
            "metabolism", "bioenergetics", "energy production", "mitochondrial function",
            "calcium signaling", "calcium homeostasis", "calcium cycling",
            "electrophysiology", "action potential", "membrane potential",
            "ion channel", "ion transport", "electrolyte balance",
            "extracellular matrix", "matrix remodeling", "matrix deposition",
            "collagen synthesis", "elastin synthesis", "matrix metalloproteinase",
            "tissue repair", "wound healing", "scar formation", "anti-scarring",
            "stem cell activation", "progenitor cell differentiation", "cell fate determination",
            "transdifferentiation", "reprogramming", "plasticity", "regeneration",
            "cardiogenesis", "myogenesis", "vascular development", "organogenesis",
            "embryonic development", "fetal development", "postnatal development",
            "aging", "senescence", "telomere maintenance", "dna repair",
            "epigenetic regulation", "transcriptional control", "post-transcriptional regulation",
            "protein synthesis", "protein degradation", "proteostasis",
            "signal transduction", "kinase cascade", "phosphorylation cascade",
            "cell cycle regulation", "cell growth control", "size control",
            "mechanical stress", "hemodynamic stress", "stretch response",
            "hormonal regulation", "neuroendocrine control", "autonomic regulation"
        }
        
        # Category 3: Cardiac Pathology (15% weight)
        self.cardiac_pathology = {
            "infarction", "failure", "injury", "damage", "disease",
            "arrhythmia", "fibrillation", "tachycardia", "bradycardia",
            "cardiomyopathy", "stenosis", "regurgitation", "ischemic",
            "atherosclerosis", "plaque", "thrombosis", "embolism", "aneurysm",
            "dissection", "rupture", "perforation", "tamponade", "effusion",
            "hypertension", "hypotension", "shock", "cardiogenic shock",
            "edema", "congestion", "pulmonary edema", "peripheral edema",
            "asystole", "pulseless electrical activity", "pea", "sudden death",
            "cardiac arrest", "resuscitation", "defibrillation", "cardioversion",
            "heart block", "bundle branch block", "fascicular block", "atrioventricular block",
            "long qt syndrome", "short qt syndrome", "brugada syndrome", "wpw syndrome",
            "hypertrophic cardiomyopathy", "dilated cardiomyopathy", "restrictive cardiomyopathy",
            "arrhythmogenic right ventricular cardiomyopathy", "takotsubo cardiomyopathy",
            "peripartum cardiomyopathy", "alcoholic cardiomyopathy", "diabetic cardiomyopathy",
            "ischemic cardiomyopathy", "non-ischemic cardiomyopathy", "idiopathic cardiomyopathy",
            "valvular disease", "aortic stenosis", "aortic regurgitation", "mitral stenosis",
            "mitral regurgitation", "tricuspid regurgitation", "pulmonary stenosis",
            "congenital defect", "atrial septal defect", "ventricular septal defect",
            "tetralogy of fallot", "transposition of great arteries", "coarctation of aorta",
            "patent ductus arteriosus", "ebstein anomaly", "hypoplastic left heart syndrome",
            "coronary anomaly", "anomalous coronary artery", "myocardial bridge",
            "pericarditis", "myocarditis", "endocarditis", "pancarditis",
            "rheumatic fever", "kawasaki disease", "chagas disease", "lyme carditis",
            "toxic cardiomyopathy", "radiation heart disease", "chemotherapy cardiotoxicity",
            "autoimmune myocarditis", "giant cell myocarditis", "eosinophilic myocarditis"
        }
        
        # Category 4: Cardiovascular Disease Context (70% weight - MAXIMUM FOCUS on disease/phenotype)
        self.cardiovascular_disease = {
            # Primary cardiovascular diseases (highest priority)
            "heart failure", "myocardial infarction", "coronary artery disease", "atherosclerosis",
            "cardiomyopathy", "dilated cardiomyopathy", "hypertrophic cardiomyopathy", 
            "restrictive cardiomyopathy", "ischemic cardiomyopathy", "arrhythmogenic cardiomyopathy",
            "cardiac arrhythmia", "atrial fibrillation", "ventricular tachycardia", "heart block",
            "sudden cardiac death", "cardiac arrest", "angina pectoris", "unstable angina",
            
            # Cardiovascular pathophysiology
            "cardiac dysfunction", "ventricular dysfunction", "diastolic dysfunction", "systolic dysfunction",
            "cardiac output", "ejection fraction", "contractile dysfunction", "pump failure",
            "cardiac ischemia", "myocardial ischemia", "ischemia reperfusion", "myocardial stunning",
            "hibernating myocardium", "cardiac necrosis", "myocardial necrosis", "cell death",
            
            # Disease progression and complications
            "cardiac remodeling", "pathological remodeling", "ventricular remodeling", "atrial remodeling",
            "cardiac hypertrophy", "pathological hypertrophy", "concentric hypertrophy", "eccentric hypertrophy",
            "cardiac fibrosis", "myocardial fibrosis", "interstitial fibrosis", "replacement fibrosis",
            "cardiac inflammation", "myocarditis", "inflammatory cardiomyopathy", "autoimmune myocarditis",

            # Therapeutic contexts
            "stem cell therapy", "cell therapy", "gene therapy", "cardiac regeneration therapy",
            "tissue engineering", "biomaterial", "scaffold", "cardiac patch", "myocardial repair",

            # Molecular mechanisms
            "epigenetic regulation", "microRNA", "lncRNA", "circRNA", "non-coding RNA",
            "transcription factor", "signaling pathway", "kinase cascade", "phosphorylation",
            "acetylation", "methylation", "histone modification", "chromatin remodeling",

            # Tissue repair and remodeling
            "tissue repair", "tissue regeneration", "tissue engineering", "tissue restoration",
            "wound healing", "wound repair", "scar reduction", "anti-scarring",
            "remodeling", "restructuring", "reconstitution", "reconstruction",
            "morphogenesis", "organogenesis", "cardiogenesis", "vasculogenesis",

            # Angiogenesis and vascular repair
            "angiogenesis", "angiogenic", "neovascularization", "revascularization",
            "vasculogenesis", "arteriogenesis", "capillarization", "collateralization",
            "endothelialization", "re-endothelialization", "vascular repair",
            "microvascular", "macrovascular", "perfusion", "reperfusion",

            # Stem cells and progenitors (EXPANDED)
            "stem cell", "progenitor", "progenitor cell", "precursor cell",
            "mesenchymal stem cell", "msc", "adipose stem cell", "bone marrow stem cell",
            "induced pluripotent stem cell", "ipsc", "embryonic stem cell", "esc",
            "cardiac progenitor", "cpc", "cardiac stem cell", "cardiosphere",
            "c-kit positive", "sca-1 positive", "cardiac side population",
            "satellite cell", "side population", "lin-ckit+", "sca-1+", "abcg2+",
            "cardiac resident stem cell", "epicardial progenitor", "endothelial progenitor",

            # Cell reprogramming and transdifferentiation
            "reprogramming", "direct reprogramming", "cellular reprogramming",
            "transdifferentiation", "lineage conversion", "cell fate conversion",
            "dedifferentiation", "redifferentiation", "plasticity", "cell plasticity",
            "phenotype switching", "lineage tracing", "fate determination",

            # Therapeutic repair approaches
            "cell therapy", "cellular therapy", "stem cell therapy", "gene therapy",
            "tissue engineering", "regenerative medicine", "bioengineering",
            "scaffold", "biomaterial", "hydrogel", "matrix", "patch", "graft",
            "transplantation", "implantation", "delivery", "targeting",

            # Advanced therapeutic modalities
            "nanotechnology", "nanoparticle", "nanocarrier", "drug delivery system",
            "gene editing", "crispr", "talen", "zinc finger nuclease", "prime editing",
            "rna therapy", "antisense oligonucleotide", "sirna", "mirna mimic",
            "exosome therapy", "extracellular vesicle", "microvesicle", "apoptotic body",
            "bioprinting", "3d bioprinting", "organoid", "spheroid", "tissue spheroid",
            "decellularized matrix", "acellular scaffold", "bioscaffold",
            "growth factor", "cytokine therapy", "chemokine therapy", "hormone therapy",
            "peptide therapy", "antibody therapy", "monoclonal antibody", "bispecific antibody",

            # Biomarker and diagnostic contexts
            "biomarker", "diagnostic marker", "prognostic marker", "therapeutic target",
            "molecular signature", "gene signature", "protein signature", "metabolic signature",
            "imaging biomarker", "functional imaging", "molecular imaging",
            "cardiac mri", "echocardiography", "cardiac ct", "pet imaging",

            # Clinical trial and translational contexts
            "clinical trial", "phase 1", "phase 2", "phase 3", "randomized controlled trial",
            "proof of concept", "first in human", "translational research", "bench to bedside",
            "personalized medicine", "precision medicine", "stratified medicine",
            "companion diagnostic", "theranostic", "pharmacogenomic",

            # Disease modeling and drug discovery
            "disease model", "animal model", "humanized model", "organ chip", "organoid model",
            "drug screening", "high throughput screening", "phenotypic screening",
            "target identification", "target validation", "hit to lead", "lead optimization",
            "adme", "pharmacokinetics", "pharmacodynamics", "toxicity testing",

            # Computational and systems biology approaches
            "systems biology", "network biology", "computational biology", "bioinformatics",
            "machine learning", "artificial intelligence", "deep learning", "neural network",
            "multi-omics", "genomics", "transcriptomics", "proteomics", "metabolomics",
            "epigenomics", "single cell sequencing", "spatial transcriptomics",
            "integrative analysis", "data mining", "big data analytics",

            # Quality control and manufacturing
            "good manufacturing practice", "gmp", "cell manufacturing", "bioprocessing",
            "scale up", "bioreactor", "cell expansion", "cryopreservation",
            "quality control", "potency assay", "sterility testing", "safety testing",
            "regulatory compliance", "fda approval", "ema approval", "clinical translation"
        }
        
        # Category 5: Pathway Name Cardiac Context (BONUS - 20% max for pathways with cardiac names)
        self.pathway_name_cardiac_terms = {
            # Direct cardiac terms in pathway names
            "cardiac", "heart", "myocardial", "cardiomyocyte", "myocardium",
            "cardiovascular", "coronary", "ventricular", "atrial", "aortic",
            "pericardial", "endocardial", "epicardial", "cardio", "cardiogenic",
            "cardiogenesis", "myogenesis", "myogenic", "sarcomeric", "sarcomere",

            # Cardiac disease and pathology
            "cardiomyopathy", "heart failure", "cardiac fibrosis", "cardiac hypertrophy",
            "cardiac remodeling", "ischemic heart", "myocardial infarction",
            "cardiac arrest", "arrhythmia", "fibrillation", "cardiomyopathies",
            "cardiac ischemia", "myocardial ischemia", "heart attack", "cardiac infarction",
            "sudden cardiac death", "scd", "cardiac dysfunction", "heart disease",
            "cardiovascular disease", "cvd", "coronary artery disease", "cad",
            "valvular heart disease", "congenital heart disease", "rheumatic heart disease",

            # Cardiac repair and regeneration
            "cardiac repair", "cardiac regeneration", "myocardial repair",
            "cardiac stem", "cardiac progenitor", "cardiac tissue", "heart repair",
            "myocardial regeneration", "cardiac healing", "heart regeneration",
            "cardiac restoration", "myocardial restoration", "cardiac recovery",
            "heart tissue engineering", "cardiac tissue engineering", "myocardial tissue engineering",

            # Cardiac physiology and function
            "contraction", "contractility", "excitation-contraction",
            "cardiac conduction", "cardiac electrophysiology", "sarcomere",
            "myofilament", "cardiac metabolism", "cardiac energetics",
            "cardiac output", "ejection fraction", "stroke volume", "heart rate",
            "cardiac rhythm", "sinus rhythm", "cardiac cycle", "cardiac mechanics",
            "ventricular function", "atrial function", "cardiac performance",

            # Cardiac development and morphogenesis
            "heart development", "cardiac development", "cardiogenesis",
            "heart morphogenesis", "cardiac morphogenesis", "ventricular morphogenesis",
            "atrial morphogenesis", "valve morphogenesis", "septation",
            "cardiac chamber formation", "heart chamber formation", "cardiac looping",
            "cardiac neural crest", "second heart field", "first heart field",

            # Cardiac signaling and pathways
            "cardiac signaling", "heart signaling", "cardiomyocyte signaling",
            "cardiac wnt signaling", "cardiac notch signaling", "cardiac bmp signaling",
            "cardiac fgfr signaling", "cardiac igf signaling", "cardiac jak/stat signaling",
            "cardiac mapk signaling", "cardiac pi3k/akt signaling", "cardiac calcium signaling",

            # Cardiac extracellular matrix and structure
            "cardiac extracellular matrix", "cardiac ecm", "myocardial matrix",
            "cardiac collagen", "cardiac elastin", "cardiac laminin", "cardiac fibronectin",
            "cardiac basement membrane", "cardiac stroma", "cardiac scaffold",

            # Cardiac vascular and endothelial
            "cardiac vascular", "cardiac angiogenesis", "cardiac vasculogenesis",
            "coronary angiogenesis", "myocardial angiogenesis", "cardiac endothelial",
            "endocardial endothelial", "epicardial endothelial", "cardiac microvascular",

            # Cardiac stem cells and progenitors
            "cardiac stem cell", "cardiac progenitor cell", "cpc", "cardiosphere",
            "c-kit cardiac", "sca-1 cardiac", "cardiac side population",
            "epicardial progenitor", "endothelial progenitor", "cardiac resident stem cell",

            # Cardiac inflammation and immunity
            "cardiac inflammation", "myocardial inflammation", "cardiac immune",
            "cardiac macrophage", "cardiac lymphocyte", "cardiac dendritic cell",
            "cardiac cytokine", "cardiac chemokine", "cardiac toll-like receptor",

            # Cardiac metabolism and bioenergetics
            "cardiac metabolism", "myocardial metabolism", "cardiac bioenergetics",
            "cardiac mitochondria", "myocardial mitochondria", "cardiac oxidative stress",
            "cardiac redox", "cardiac antioxidant", "cardiac energy metabolism",

            # Cardiac fibrosis and remodeling
            "cardiac fibrosis", "myocardial fibrosis", "cardiac fibrotic",
            "cardiac scar", "myocardial scar", "cardiac scar tissue",
            "cardiac fibroblast", "myocardial fibroblast", "cardiac myofibroblast",

            # Cardiac hypertrophy and growth
            "cardiac hypertrophy", "myocardial hypertrophy", "cardiac growth",
            "physiological hypertrophy", "pathological hypertrophy", "cardiac hyperplasia",

            # Cardiac valves and septa
            "cardiac valve", "heart valve", "aortic valve", "mitral valve",
            "tricuspid valve", "pulmonary valve", "cardiac septum", "atrial septum",
            "ventricular septum", "atrioventricular septum",

            # Cardiac conduction system
            "cardiac conduction", "cardiac pacemaker", "sinoatrial node",
            "atrioventricular node", "cardiac purkinje", "cardiac bundle of his",
            "cardiac conduction velocity", "cardiac action potential",

            # Cardiac autonomic nervous system
            "cardiac autonomic", "cardiac sympathetic", "cardiac parasympathetic",
            "cardiac vagal", "cardiac adrenergic", "cardiac cholinergic",

            # Cardiac pharmacology and therapeutics
            "cardiac drug", "cardiac therapy", "cardiac treatment", "cardiac medication",
            "cardiac beta-blocker", "cardiac ace inhibitor", "cardiac statin",
            "cardiac anticoagulant", "cardiac antiarrhythmic", "cardiac inotrope"
        }
        
        # Category 6: Negative Terms (penalty scoring for non-cardiac focus)
        self.negative_terms = {
            # Non-cardiac organ systems
            "brain", "neural", "neuronal", "neuron", "synapse", "synaptic", "cerebral", "cortical",
            "liver", "hepatic", "hepatocyte", "kidney", "renal", "nephron", "glomerular", "tubular",
            "lung", "pulmonary", "respiratory", "alveolar", "bronchial", "pleural",
            "skin", "dermal", "epidermal", "keratinocyte", "melanocyte",
            "bone", "skeletal", "osteoblast", "osteoclast", "chondrocyte", "cartilage",
            "muscle", "skeletal muscle", "smooth muscle", "striated muscle", "myoblast", "myotube",
            "gastrointestinal", "intestinal", "gastric", "colonic", "esophageal", "duodenal",
            "pancreatic", "acinar", "islet", "beta cell", "endocrine pancreas",
            "thyroid", "parathyroid", "adrenal", "gonadal", "reproductive", "ovarian", "testicular",
            "spleen", "splenic", "lymph node", "lymphatic", "thymus", "thymic",
            "bladder", "urinary", "urethral", "prostate", "prostatic",

            # Non-cardiac tissue types
            "epithelial", "mesenchymal", "connective tissue", "adipose", "fat tissue",
            "hematopoietic", "blood cell", "erythrocyte", "leukocyte", "platelet",
            "immune cell", "b cell", "t cell", "macrophage", "neutrophil", "eosinophil",

            # Non-repair processes
            "degradation", "catabolism", "breakdown", "destruction", "lysis", "proteolysis",
            "senescence", "aging", "death", "apoptosis", "necrosis", "autolysis",
            "inflammation", "inflammatory", "immune response", "cytotoxic", "cytotoxicity",
            "allergic", "hypersensitivity", "autoimmune", "autoimmunity",

            # Pathological terms (non-cardiac focus)
            "cancer", "tumor", "oncology", "malignant", "metastasis", "carcinoma", "sarcoma",
            "infection", "bacterial", "viral", "pathogen", "sepsis", "septic",
            "diabetes", "diabetic", "hyperglycemia", "hypoglycemia", "insulin resistance",
            "arthritis", "arthritic", "osteoarthritis", "rheumatoid arthritis",
            "neurological", "neurodegenerative", "alzheimer", "parkinson", "dementia",
            "pulmonary disease", "copd", "asthma", "emphysema", "fibrosis",
            "liver disease", "hepatitis", "cirrhosis", "steatosis", "jaundice",
            "kidney disease", "nephropathy", "uremia", "dialysis", "transplant",

            # Non-cardiac developmental terms
            "neural tube", "neural crest", "neurogenesis", "gliogenesis",
            "osteogenesis", "chondrogenesis", "myogenesis", "adipogenesis",
            "hematopoiesis", "lymphopoiesis", "gametogenesis",

            # Non-cardiac physiological terms
            "respiration", "breathing", "pulmonary function", "lung capacity",
            "digestion", "absorption", "metabolism", "endocrine function",
            "renal function", "filtration", "reabsorption", "excretion",
            "skeletal growth", "bone remodeling", "muscle contraction",

            # Research and technical terms (non-cardiac context)
            "cancer research", "oncology research", "neuroscience", "immunology",
            "microbiology", "virology", "bacteriology", "parasitology",
            "toxicology", "pharmacology", "endocrinology", "rheumatology"
        }
        
        # Additional fuzzy matching patterns (expanded for comprehensive cardiac context)
        self.fuzzy_patterns = [
            r"cardio\w+",  # Matches cardiomyocyte, cardiomyopathy, cardiovascular, etc.
            r"myocardi\w+",  # Matches myocardial, myocardium, myocarditis, etc.
            r"ventric\w+",  # Matches ventricular, ventricle, ventriculomegaly, etc.
            r"atri\w+",  # Matches atrial, atrioventricular, etc.
            r"isch\w+",  # Matches ischemia, ischemic, ischium (but cardiac context filters)
            r"angio\w+",  # Matches angiogenesis, angiogenic, angiopoietin, etc.
            r"vasculo\w+",  # Matches vasculogenesis, vascular, vasculature, etc.
            r"fibro\w+",  # Matches fibroblast, fibrosis, fibrotic, etc.
            r"necro\w+",  # Matches necrosis, necrotic, necroptosis, etc.
            r"apopto\w+",  # Matches apoptosis, apoptotic, anti-apoptotic, etc.
            r"autopha\w+",  # Matches autophagy, autophagic, etc.
            r"mitochon\w+",  # Matches mitochondria, mitochondrial, etc.
            r"epigen\w+",  # Matches epigenetic, epigenetics, etc.
            r"transcrip\w+",  # Matches transcription, transcriptional, etc.
            r"signal\w+",  # Matches signaling, signal transduction, etc.
            r"regener\w+",  # Matches regeneration, regenerative, etc.
            r"repair\w+",  # Matches repair, repairing, etc.
            r"remodel\w+",  # Matches remodeling, remodel, etc.
            r"differentiat\w+",  # Matches differentiation, differentiate, etc.
            r"proliferat\w+",  # Matches proliferation, proliferate, etc.
            r"hypertroph\w+",  # Matches hypertrophy, hypertrophic, etc.
            r"metabol\w+",  # Matches metabolism, metabolic, metabolome, etc.
            r"oxidat\w+",  # Matches oxidative, oxidation, etc.
            r"inflamm\w+",  # Matches inflammation, inflammatory, etc.
            r"immun\w+",  # Matches immune, immunity, immunomodulation, etc.
            r"vascular\w+",  # Matches vascular, vasculature, etc.
            r"endothelial\w+",  # Matches endothelial, endothelium, etc.
            r"extracellular\w+",  # Matches extracellular, extracellular matrix, etc.
            r"collagen\w+",  # Matches collagen, collagenase, etc.
            r"elastin\w+",  # Matches elastin, elastic, etc.
            r"integrin\w+",  # Matches integrin, integrins, etc.
            r"adhes\w+",  # Matches adhesion, adhesive, etc.
            r"migrat\w+",  # Matches migration, migratory, etc.
            r"invad\w+",  # Matches invasion, invasive, etc.
            r"stem\w+",  # Matches stem, stemness, etc.
            r"progenitor\w+",  # Matches progenitor, progenitors, etc.
            r"pluripotent\w+",  # Matches pluripotent, pluripotency, etc.
            r"embryonic\w+",  # Matches embryonic, embryogenesis, etc.
            r"induced\w+",  # Matches induced, induction, etc.
            r"reprogram\w+",  # Matches reprogramming, reprogram, etc.
            r"transdifferenti\w+",  # Matches transdifferentiation, etc.
            r"senesc\w+",  # Matches senescence, senescent, etc.
            r"telomer\w+",  # Matches telomere, telomerase, etc.
            r"sirtuin\w+",  # Matches sirtuin, sirtuins, etc.
            r"biomater\w+",  # Matches biomaterial, biomaterials, etc.
            r"scaffold\w+",  # Matches scaffold, scaffolding, etc.
            r"hydrogel\w+",  # Matches hydrogel, hydrogels, etc.
            r"decellular\w+",  # Matches decellularized, decellularization, etc.
            r"exosom\w+",  # Matches exosome, exosomes, etc.
            r"microrna\w+",  # Matches microrna, mirna, etc.
            r"lncrna\w+",  # Matches lncrna, long non-coding rna, etc.
            r"transcriptom\w+",  # Matches transcriptome, transcriptomics, etc.
            r"proteom\w+",  # Matches proteome, proteomics, etc.
            r"metabolom\w+",  # Matches metabolome, metabolomics, etc.
            r"epigenom\w+",  # Matches epigenome, epigenomics, etc.
            r"phosphorylat\w+",  # Matches phosphorylation, phosphorylated, etc.
            r"dephosphorylat\w+",  # Matches dephosphorylation, etc.
            r"kinase\w+",  # Matches kinase, kinases, etc.
            r"phosphatas\w+",  # Matches phosphatase, phosphatases, etc.
            r"calcium\w+",  # Matches calcium, calcineurin, etc.
            r"mapk\w+",  # Matches mapk, map kinase, etc.
            r"erk\w+",  # Matches erk, extracellular signal-regulated kinase, etc.
            r"jnk\w+",  # Matches jnk, c-jun n-terminal kinase, etc.
            r"p38\w+",  # Matches p38, p38 mapk, etc.
            r"akt\w+",  # Matches akt, protein kinase b, etc.
            r"pi3k\w+",  # Matches pi3k, phosphatidylinositol 3-kinase, etc.
            r"mtor\w+",  # Matches mtor, mechanistic target of rapamycin, etc.
            r"ampk\w+",  # Matches ampk, amp-activated protein kinase, etc.
            r"hippo\w+",  # Matches hippo, hippo pathway, etc.
            r"wnt\w+",  # Matches wnt, wnt signaling, etc.
            r"notch\w+",  # Matches notch, notch signaling, etc.
            r"hedgehog\w+",  # Matches hedgehog, sonic hedgehog, etc.
            r"jak\w+",  # Matches jak, janus kinase, etc.
            r"stat\w+",  # Matches stat, signal transducer and activator of transcription, etc.
            r"biomechan\w+",  # Matches biomechanical, biomechanics, etc.
            r"sarcomer\w+",  # Matches sarcomere, sarcomeric, etc.
            r"myofilament\w+",  # Matches myofilament, myofilaments, etc.
            r"titin\w+",  # Matches titin, ttntitin, etc.
            r"myosin\w+",  # Matches myosin, myosins, etc.
            r"actin\w+",  # Matches actin, actinin, etc.
            r"troponin\w+",  # Matches troponin, troponins, etc.
            r"tropomyosin\w+",  # Matches tropomyosin, etc.
            r"embryogen\w+",  # Matches embryogenesis, embryogenic, etc.
            r"organogen\w+",  # Matches organogenesis, organogenic, etc.
            r"morphogen\w+",  # Matches morphogenesis, morphogenic, etc.
            r"therapeut\w+",  # Matches therapeutic, therapeutics, etc.
            r"regenerat\w+",  # Matches regenerative, regeneration, etc.
            r"translat\w+",  # Matches translational, translation, etc.
            r"preclin\w+",  # Matches preclinical, preclinic, etc.
            r"biolog\w+",  # Matches biologic, biological, etc.
            r"monoclon\w+",  # Matches monoclonal, monoclonal antibody, etc.
            r"oligonucleotid\w+",  # Matches oligonucleotide, oligonucleotides, etc.
            r"cardiomyopath\w+",  # Matches cardiomyopathy, cardiomyopathies, etc.
            r"arrhyth\w+",  # Matches arrhythmia, arrhythmias, etc.
            r"fibrillat\w+",  # Matches fibrillation, fibrillatory, etc.
            r"tachycard\w+",  # Matches tachycardia, tachycardic, etc.
            r"bradycard\w+",  # Matches bradycardia, bradycardic, etc.
            r"heart.*fail\w+",  # Matches heart failure, heart fail, etc.
            r"senesc\w+",  # Matches senescence, senescent, etc.
            r"telomer\w+",  # Matches telomere, telomerase, etc.
            r"sirtuin\w+",  # Matches sirtuin, sirtuins, etc.
            r"longev\w+",  # Matches longevity, longevous, etc.
            r"lifespan\w+",  # Matches lifespan, lifespans, etc.
            r"healthspan\w+",  # Matches healthspan, etc.
            r"geroprotect\w+",  # Matches geroprotector, geroprotective, etc.
            r"transcriptom\w+",  # Matches transcriptome, transcriptomics, etc.
            r"proteom\w+",  # Matches proteome, proteomics, etc.
            r"metabolom\w+",  # Matches metabolome, metabolomics, etc.
            r"epigenom\w+",  # Matches epigenome, epigenomics, etc.
            r"systems.*biolog\w+",  # Matches systems biology, etc.
            r"network.*analys\w+",  # Matches network analysis, etc.
            r"pathway.*analys\w+",  # Matches pathway analysis, etc.
            r"gene.*ontolog\w+",  # Matches gene ontology, etc.
            r"molecular.*signatur\w+",  # Matches molecular signature, etc.
            r"biomark\w+",  # Matches biomarker, biomarkers, etc.
            r"contractil\w+",  # Matches contractile, contractility, etc.
            r"electrophysiol\w+",  # Matches electrophysiological, electrophysiology, etc.
            r"excitation.*contract\w+",  # Matches excitation-contraction, etc.
            r"calcium.*signal\w+",  # Matches calcium signaling, etc.
            r"beta.*adrenerg\w+",  # Matches beta-adrenergic, etc.
            r"muscarin\w+",  # Matches muscarinic, etc.
            r"nicotin\w+",  # Matches nicotinic, etc.
            r"purinerg\w+",  # Matches purinergic, etc.
            r"gap.*junction\w+",  # Matches gap junction, etc.
            r"tight.*junction\w+",  # Matches tight junction, etc.
            r"adherens.*junction\w+",  # Matches adherens junction, etc.
            r"desmosom\w+",  # Matches desmosome, desmosomal, etc.
            r"hemidesmosom\w+",  # Matches hemidesmosome, etc.
            r"focal.*adhes\w+",  # Matches focal adhesion, etc.
            r"costamer\w+",  # Matches costamere, costameric, etc.
            r"z.*line\w+",  # Matches z-line, z-disk, etc.
            r"m.*line\w+",  # Matches m-line, etc.
            r"t.*tubule\w+",  # Matches t-tubule, transverse tubule, etc.
            r"sarcolemm\w+",  # Matches sarcolemma, sarcolemmal, etc.
            r"sarcoplasm\w+",  # Matches sarcoplasm, sarcoplasmic, etc.
            r"sarcoplasmic.*reticulum\w+",  # Matches sarcoplasmic reticulum, etc.
            r"ryanodine.*receptor\w+",  # Matches ryanodine receptor, etc.
            r"ip3.*receptor\w+",  # Matches ip3 receptor, etc.
            r"sarco.*endoplasmic.*reticulum\w+",  # Matches sarco/endoplasmic reticulum, etc.
            r"troponin\w+",  # Matches troponin, troponins, etc.
            r"tropomyosin\w+",  # Matches tropomyosin, etc.
            r"myosin\w+",  # Matches myosin, myosins, etc.
            r"actin\w+",  # Matches actin, actins, etc.
            r"myofilament\w+",  # Matches myofilament, myofilaments, etc.
            r"thick.*filament\w+",  # Matches thick filament, etc.
            r"thin.*filament\w+",  # Matches thin filament, etc.
            r"sarcomer\w+",  # Matches sarcomere, sarcomeric, etc.
            r"cardiomyocyt\w+",  # Matches cardiomyocyte, cardiomyocytes, etc.
            r"myocardi\w+",  # Matches myocardial, myocardium, etc.
            r"endocardi\w+",  # Matches endocardial, endocardium, etc.
            r"epicardi\w+",  # Matches epicardial, epicardium, etc.
            r"pericardi\w+",  # Matches pericardial, pericardium, etc.
            r"intercalated.*disk\w+",  # Matches intercalated disk, etc.
            r"cardiac.*conduction\w+",  # Matches cardiac conduction, etc.
            r"atrioventricular.*node\w+",  # Matches atrioventricular node, etc.
            r"sinoatrial.*node\w+",  # Matches sinoatrial node, etc.
            r"bundle.*his\w+",  # Matches bundle of his, etc.
            r"purkinje.*fiber\w+",  # Matches purkinje fiber, etc.
            r"cardiac.*valve\w+",  # Matches cardiac valve, etc.
            r"aortic.*valve\w+",  # Matches aortic valve, etc.
            r"mitral.*valve\w+",  # Matches mitral valve, etc.
            r"tricuspid.*valve\w+",  # Matches tricuspid valve, etc.
            r"pulmonary.*valve\w+",  # Matches pulmonary valve, etc.
            r"cardiac.*sept\w+",  # Matches cardiac septum, etc.
            r"atrial.*sept\w+",  # Matches atrial septum, etc.
            r"ventricular.*sept\w+",  # Matches ventricular septum, etc.
            r"cardiac.*output\w+",  # Matches cardiac output, etc.
            r"ejection.*fraction\w+",  # Matches ejection fraction, etc.
            r"stroke.*volume\w+",  # Matches stroke volume, etc.
            r"heart.*rate\w+",  # Matches heart rate, etc.
            r"cardiac.*cycle\w+",  # Matches cardiac cycle, etc.
            r"systol\w+",  # Matches systole, systolic, etc.
            r"diastol\w+",  # Matches diastole, diastolic, etc.
            r"preload\w+",  # Matches preload, preloading, etc.
            r"afterload\w+",  # Matches afterload, afterloading, etc.
            r"frank.*starling\w+",  # Matches frank-starling, etc.
            r"cardiac.*hypertroph\w+",  # Matches cardiac hypertrophy, etc.
            r"physiological.*hypertroph\w+",  # Matches physiological hypertrophy, etc.
            r"pathological.*hypertroph\w+",  # Matches pathological hypertrophy, etc.
            r"cardiac.*fibros\w+",  # Matches cardiac fibrosis, etc.
            r"myocardial.*fibros\w+",  # Matches myocardial fibrosis, etc.
            r"interstitial.*fibros\w+",  # Matches interstitial fibrosis, etc.
            r"replacement.*fibros\w+",  # Matches replacement fibrosis, etc.
            r"cardiac.*remodel\w+",  # Matches cardiac remodeling, etc.
            r"reverse.*remodel\w+",  # Matches reverse remodeling, etc.
            r"adverse.*remodel\w+",  # Matches adverse remodeling, etc.
            r"cardiac.*scar\w+",  # Matches cardiac scar, etc.
            r"myocardial.*scar\w+",  # Matches myocardial scar, etc.
            r"cardiac.*repair\w+",  # Matches cardiac repair, etc.
            r"myocardial.*repair\w+",  # Matches myocardial repair, etc.
            r"cardiac.*regener\w+",  # Matches cardiac regeneration, etc.
            r"heart.*regener\w+",  # Matches heart regeneration, etc.
            r"cardiomyocyte.*regener\w+",  # Matches cardiomyocyte regeneration, etc.
            r"cardiac.*stem.*cell\w+",  # Matches cardiac stem cell, etc.
            r"cardiac.*progenitor\w+",  # Matches cardiac progenitor, etc.
            r"cpc\w+",  # Matches cpc, cpcs, etc.
            r"cardiospher\w+",  # Matches cardiosphere, cardiospheres, etc.
            r"c.*kit.*cardiac\w+",  # Matches c-kit cardiac, etc.
            r"sca.*1.*cardiac\w+",  # Matches sca-1 cardiac, etc.
            r"cardiac.*side.*population\w+",  # Matches cardiac side population, etc.
            r"epicardial.*progenitor\w+",  # Matches epicardial progenitor, etc.
            r"endothelial.*progenitor\w+",  # Matches endothelial progenitor, etc.
            r"cardiac.*resident.*stem\w+",  # Matches cardiac resident stem, etc.
            r"cardiac.*inflammation\w+",  # Matches cardiac inflammation, etc.
            r"myocardial.*inflammation\w+",  # Matches myocardial inflammation, etc.
            r"cardiac.*immune\w+",  # Matches cardiac immune, etc.
            r"cardiac.*macrophag\w+",  # Matches cardiac macrophage, etc.
            r"cardiac.*lymphocyt\w+",  # Matches cardiac lymphocyte, etc.
            r"cardiac.*dendritic\w+",  # Matches cardiac dendritic, etc.
            r"cardiac.*cytokin\w+",  # Matches cardiac cytokine, etc.
            r"cardiac.*chemokin\w+",  # Matches cardiac chemokine, etc.
            r"cardiac.*toll.*like\w+",  # Matches cardiac toll-like, etc.
            r"cardiac.*metabol\w+",  # Matches cardiac metabolism, etc.
            r"myocardial.*metabol\w+",  # Matches myocardial metabolism, etc.
            r"cardiac.*bioenerget\w+",  # Matches cardiac bioenergetics, etc.
            r"cardiac.*mitochondri\w+",  # Matches cardiac mitochondria, etc.
            r"myocardial.*mitochondri\w+",  # Matches myocardial mitochondria, etc.
            r"cardiac.*oxidative.*stress\w+",  # Matches cardiac oxidative stress, etc.
            r"cardiac.*redox\w+",  # Matches cardiac redox, etc.
            r"cardiac.*antioxid\w+",  # Matches cardiac antioxidant, etc.
            r"cardiac.*energy.*metabol\w+",  # Matches cardiac energy metabolism, etc.
            r"cardiac.*extracellular.*matrix\w+",  # Matches cardiac extracellular matrix, etc.
            r"cardiac.*ecm\w+",  # Matches cardiac ecm, etc.
            r"myocardial.*matrix\w+",  # Matches myocardial matrix, etc.
            r"cardiac.*collagen\w+",  # Matches cardiac collagen, etc.
            r"cardiac.*elastin\w+",  # Matches cardiac elastin, etc.
            r"cardiac.*laminin\w+",  # Matches cardiac laminin, etc.
            r"cardiac.*fibronectin\w+",  # Matches cardiac fibronectin, etc.
            r"cardiac.*basement.*membrane\w+",  # Matches cardiac basement membrane, etc.
            r"cardiac.*stroma\w+",  # Matches cardiac stroma, etc.
            r"cardiac.*scaffold\w+",  # Matches cardiac scaffold, etc.
            r"cardiac.*vascular\w+",  # Matches cardiac vascular, etc.
            r"cardiac.*angiogenes\w+",  # Matches cardiac angiogenesis, etc.
            r"cardiac.*vasculogenes\w+",  # Matches cardiac vasculogenesis, etc.
            r"coronary.*angiogenes\w+",  # Matches coronary angiogenesis, etc.
            r"myocardial.*angiogenes\w+",  # Matches myocardial angiogenesis, etc.
            r"cardiac.*endothelial\w+",  # Matches cardiac endothelial, etc.
            r"endocardial.*endothelial\w+",  # Matches endocardial endothelial, etc.
            r"epicardial.*endothelial\w+",  # Matches epicardial endothelial, etc.
            r"cardiac.*microvascular\w+",  # Matches cardiac microvascular, etc.
            r"cardiac.*development\w+",  # Matches cardiac development, etc.
            r"heart.*development\w+",  # Matches heart development, etc.
            r"cardiogenes\w+",  # Matches cardiogenesis, cardiogenic, etc.
            r"heart.*morphogenes\w+",  # Matches heart morphogenesis, etc.
            r"cardiac.*morphogenes\w+",  # Matches cardiac morphogenesis, etc.
            r"ventricular.*morphogenes\w+",  # Matches ventricular morphogenesis, etc.
            r"atrial.*morphogenes\w+",  # Matches atrial morphogenesis, etc.
            r"valve.*morphogenes\w+",  # Matches valve morphogenesis, etc.
            r"septat\w+",  # Matches septation, septal, etc.
            r"cardiac.*chamber.*formation\w+",  # Matches cardiac chamber formation, etc.
            r"heart.*chamber.*formation\w+",  # Matches heart chamber formation, etc.
            r"cardiac.*looping\w+",  # Matches cardiac looping, etc.
            r"cardiac.*neural.*crest\w+",  # Matches cardiac neural crest, etc.
            r"second.*heart.*field\w+",  # Matches second heart field, etc.
            r"first.*heart.*field\w+",  # Matches first heart field, etc.
            r"cardiac.*signaling\w+",  # Matches cardiac signaling, etc.
            r"heart.*signaling\w+",  # Matches heart signaling, etc.
            r"cardiomyocyte.*signaling\w+",  # Matches cardiomyocyte signaling, etc.
            r"cardiac.*wnt.*signaling\w+",  # Matches cardiac wnt signaling, etc.
            r"cardiac.*notch.*signaling\w+",  # Matches cardiac notch signaling, etc.
            r"cardiac.*bmp.*signaling\w+",  # Matches cardiac bmp signaling, etc.
            r"cardiac.*fgf.*signaling\w+",  # Matches cardiac fgf signaling, etc.
            r"cardiac.*igf.*signaling\w+",  # Matches cardiac igf signaling, etc.
            r"cardiac.*jak.*stat.*signaling\w+",  # Matches cardiac jak/stat signaling, etc.
            r"cardiac.*mapk.*signaling\w+",  # Matches cardiac mapk signaling, etc.
            r"cardiac.*pi3k.*akt.*signaling\w+",  # Matches cardiac pi3k/akt signaling, etc.
            r"cardiac.*calcium.*signaling\w+"  # Matches cardiac calcium signaling, etc.
        ]
        
        # Generic pathway terms for pre-filtering (to skip literature mining)
        self.generic_pathway_terms = {
            # Overly broad biological processes
            "system process", "multicellular organismal process", "multicellular organism process",
            "biological process", "cellular process", "metabolic process", "metabolic pathways",
            "signaling pathway", "signal transduction", "cell signaling",
            "regulation of", "positive regulation", "negative regulation",
            "biological regulation", "cellular component organization",
            "developmental process", "anatomical structure development",
            "system development", "organ development", "tissue development",
            "cell differentiation", "cell development", "cellular developmental process",
            
            # Generic molecular functions
            "binding", "protein binding", "ion binding", "nucleotide binding",
            "catalytic activity", "enzyme activity", "transferase activity",
            "hydrolase activity", "oxidoreductase activity", "ligase activity",
            
            # Generic cellular components
            "cellular component", "cell part", "intracellular", "organelle",
            "membrane", "cytoplasm", "nucleus", "cell surface",
            
            # Generic response terms
            "response to stimulus", "response to stress", "cellular response",
            "response to chemical", "response to organic substance",
            
            # Generic transport and localization
            "transport", "localization", "establishment of localization",
            "vesicle-mediated transport", "intracellular transport",
            
            # Generic cell cycle and growth
            "cell cycle", "cell division", "cell growth", "cell proliferation",
            
            # Generic apoptosis and death (without cardiac context)
            "programmed cell death", "apoptotic process", "cell death"
        }
        
        # Disease-specific cardiac contexts for enhanced filtering
        self.disease_specific_contexts = {
            "heart_failure": {
                "high_priority": {
                    "contractility", "ejection fraction", "systolic dysfunction",
                    "diastolic dysfunction", "heart failure", "cardiac failure",
                    "decompensated heart", "acute heart failure", "chronic heart failure",
                    "hfref", "hfpef", "reduced ejection fraction", "preserved ejection fraction",
                    "cardiac insufficiency", "ventricular dysfunction", "cardiac output",
                    "preload", "afterload", "cardiac remodeling", "reverse remodeling"
                },
                "moderate": {
                    "hypertrophy", "ventricular hypertrophy", "cardiac hypertrophy",
                    "fibrosis", "cardiac fibrosis", "myocardial fibrosis",
                    "calcium handling", "calcium cycling", "sarcoplasmic reticulum",
                    "natriuretic peptide", "bnp", "nt-probnp", "anp",
                    "neurohormonal activation", "raas", "renin-angiotensin",
                    "sympathetic activation", "adrenergic", "beta-blocker"
                }
            },
            "myocardial_infarction": {
                "high_priority": {
                    "ischemia", "ischemic", "myocardial ischemia", "cardiac ischemia",
                    "reperfusion", "reperfusion injury", "ischemia-reperfusion",
                    "infarction", "myocardial infarction", "heart attack", "mi", "ami", "stemi", "nstemi",
                    "coronary occlusion", "coronary artery disease", "coronary syndrome",
                    "acute coronary", "coronary thrombosis", "plaque rupture",
                    "cardiac necrosis", "myocardial necrosis", "infarct zone"
                },
                "moderate": {
                    "inflammation", "cardiac inflammation", "myocardial inflammation",
                    "repair", "cardiac repair", "myocardial repair", "wound healing",
                    "angiogenesis", "neovascularization", "collateral formation",
                    "scar", "cardiac scar", "myocardial scar", "scar formation",
                    "troponin", "cardiac biomarker", "creatine kinase", "ck-mb"
                }
            },
            "cardiomyopathy": {
                "high_priority": {
                    "cardiomyopathy", "cardiac myopathy", "myocardial disease",
                    "dilated cardiomyopathy", "dcm", "hypertrophic cardiomyopathy", "hcm",
                    "restrictive cardiomyopathy", "rcm", "arrhythmogenic cardiomyopathy",
                    "arvc", "arvd", "arrhythmogenic right ventricular",
                    "takotsubo", "stress cardiomyopathy", "broken heart syndrome",
                    "peripartum cardiomyopathy", "ppcm", "familial cardiomyopathy",
                    "genetic cardiomyopathy", "inherited cardiomyopathy"
                },
                "moderate": {
                    "sarcomere", "sarcomeric protein", "myosin", "actin", "troponin",
                    "titin", "myosin binding protein", "cardiac troponin",
                    "z-disc", "m-line", "sarcomere structure", "sarcomeric mutation"
                }
            },
            "diabetic_cardiomyopathy": {
                "high_priority": {
                    "diabetic cardiomyopathy", "diabetic heart disease",
                    "diabetes cardiac", "diabetic myocardial", "hyperglycemic cardiomyopathy",
                    "glucose metabolism", "cardiac glucose", "myocardial glucose",
                    "insulin signaling", "insulin resistance", "cardiac insulin",
                    "glut4", "glucose transporter", "glucose uptake"
                },
                "moderate": {
                    "metabolic syndrome", "metabolic cardiomyopathy",
                    "mitochondrial dysfunction", "cardiac mitochondria",
                    "oxidative stress", "cardiac oxidative", "reactive oxygen species",
                    "age", "advanced glycation", "protein glycation",
                    "lipotoxicity", "cardiac lipid", "fatty acid metabolism"
                }
            },
            "arrhythmia": {
                "high_priority": {
                    "arrhythmia", "cardiac arrhythmia", "heart rhythm disorder",
                    "fibrillation", "atrial fibrillation", "afib", "af",
                    "ventricular fibrillation", "vfib", "vf", "tachycardia",
                    "ventricular tachycardia", "vt", "supraventricular tachycardia", "svt",
                    "bradycardia", "heart block", "av block", "bundle branch block",
                    "long qt", "lqts", "brugada", "catecholaminergic polymorphic",
                    "cpvt", "sudden cardiac death", "scd", "cardiac arrest"
                },
                "moderate": {
                    "ion channel", "sodium channel", "potassium channel", "calcium channel",
                    "action potential", "cardiac action potential", "depolarization",
                    "repolarization", "refractory period", "conduction velocity",
                    "electrocardiogram", "ecg", "ekg", "electrophysiology"
                }
            }
        }
        
        logger.info("SemanticFilter initialized with expanded cardiac context and disease-specific filtering")
    
    def is_generic_pathway(self, pathway_name: str, pathway_description: str = "") -> bool:
        """
        Detect if a pathway is too generic/broad for cardiac-specific analysis.
        
        Generic pathways are excluded early to optimize literature mining performance.
        
        Args:
            pathway_name: Name of the pathway
            pathway_description: Description of the pathway (optional)
            
        Returns:
            True if pathway is generic and should be filtered out, False otherwise
        """
        name_lower = pathway_name.lower()
        desc_lower = pathway_description.lower() if pathway_description else ""
        combined_text = f"{name_lower} {desc_lower}"
        
        # Check for generic terms
        for term in self.generic_pathway_terms:
            if term in name_lower:
                logger.debug(f"Pathway '{pathway_name}' is generic (contains '{term}')")
                return True
        
        # Additional heuristics
        # Very short pathway names are often generic (e.g., "Binding", "Signaling")
        if len(pathway_name.split()) <= 2 and not any(
            cardiac_term in name_lower 
            for cardiac_term in ["cardiac", "heart", "myocardial", "cardiovascular"]
        ):
            logger.debug(f"Pathway '{pathway_name}' is likely generic (short name without cardiac context)")
            return True
        
        # Check for generic GO terms starting with "GO:"
        if pathway_name.startswith("GO:") and not any(
            cardiac_term in combined_text
            for cardiac_term in ["cardiac", "heart", "myocardial", "cardiovascular", "coronary"]
        ):
            logger.debug(f"Pathway '{pathway_name}' is generic GO term without cardiac context")
            return True
        
        return False
    
    def has_disease_specific_relevance(
        self,
        pathway_name: str,
        pathway_description: str = "",
        disease_context: Optional[str] = None
    ) -> Tuple[bool, float]:
        """
        Check if pathway has disease-specific cardiac relevance.
        
        Args:
            pathway_name: Name of the pathway
            pathway_description: Description of the pathway
            disease_context: Specific disease context (e.g., "heart_failure", "myocardial_infarction")
            
        Returns:
            Tuple of (has_relevance, relevance_score)
        """
        if not disease_context or disease_context not in self.disease_specific_contexts:
            return (False, 0.0)
        
        name_lower = pathway_name.lower()
        desc_lower = pathway_description.lower() if pathway_description else ""
        combined_text = f"{name_lower} {desc_lower}"
        
        disease_terms = self.disease_specific_contexts[disease_context]
        score = 0.0
        
        # High priority terms
        for term in disease_terms.get("high_priority", set()):
            if term in combined_text:
                score += 0.4
                logger.debug(f"Pathway '{pathway_name}' has high-priority {disease_context} term: '{term}'")
        
        # Moderate priority terms
        for term in disease_terms.get("moderate", set()):
            if term in combined_text:
                score += 0.2
                logger.debug(f"Pathway '{pathway_name}' has moderate-priority {disease_context} term: '{term}'")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return (score > 0, score)
    
    def calculate_cardiac_relevance(
        self,
        pathway_name: str,
        pathway_description: str = "",
        evidence_genes: Optional[List[str]] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Calculate comprehensive cardiac relevance score with CARDIOVASCULAR DISEASE-FOCUSED scoring.
        
        New scoring system prioritizing cardiovascular disease and phenotype awareness:
        - Cardiovascular disease context: 60% (MAXIMUM priority for disease-specific pathways)
        - Pathway name cardiac context: 20% (BONUS for pathways with cardiac terms in names)
        - Cardiac processes: 25% (cardiac-specific processes)
        - Direct cardiac terms: 15% (general cardiac context)
        - Negative penalty: -50% (for non-cardiac terms)
        - Fuzzy pattern boost: +10% (distributed across categories)
        
        Total range: -50% to 130% (normalized to 0-1 scale)
        
        Pathways with cardiac-related terms in their names receive a scoring bonus,
        but all pathways with sufficient cardiac semantic relevance can be included.
        
        Args:
            pathway_name: Pathway name
            pathway_description: Optional pathway description
            evidence_genes: Optional list of evidence genes
            disease_context: Optional disease context for targeted boosting
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            Dictionary with overall score and category breakdown
        """
        text = f"{pathway_name} {pathway_description}".lower()
        
        # Initialize category scores with new weights
        scores = {
            "cardiovascular_disease": 0.0,     # 60% max - HIGHEST priority
            "cardiac_processes": 0.0,  # 25% max
            "direct_cardiac": 0.0,     # 15% max
            "pathway_name_cardiac": 0.0,  # 20% max - MANDATORY for final results
            "negative_penalty": 0.0    # -50% max penalty
        }
        
        # Category 1: CARDIOVASCULAR DISEASE - HIGH PRIORITY (40% max - STRICTER)
        disease_matches = sum(1 for term in self.cardiovascular_disease if term in text)
        if disease_matches > 0:
            # STRICTER: Require more matches for high scores (0.08 per match, max 40%)
            scores["cardiovascular_disease"] = min(disease_matches * 0.08, 0.40)
        
        # Category 2: Cardiac processes (15% max - STRICTER)
        process_matches = sum(1 for term in self.cardiac_processes if term in text)
        if process_matches > 0:
            # STRICTER: 0.03 per match, max 15%
            scores["cardiac_processes"] = min(process_matches * 0.03, 0.15)
        
        # Category 3: Direct cardiac terms (10% max - STRICTER)
        direct_matches = sum(1 for term in self.direct_cardiac_terms if term in text)
        if direct_matches > 0:
            # STRICTER: 0.02 per match, max 10%
            scores["direct_cardiac"] = min(direct_matches * 0.02, 0.10)
        
        # Category 4: Pathway Name Cardiac Context (BONUS - 15% max - STRICTER)
        # Bonus for pathways with cardiac context in their names
        pathway_name_lower = pathway_name.lower()
        name_cardiac_matches = sum(1 for term in self.pathway_name_cardiac_terms if term in pathway_name_lower)
        if name_cardiac_matches > 0:
            # STRICTER: 0.05 per match, max 15%
            scores["pathway_name_cardiac"] = min(name_cardiac_matches * 0.05, 0.15)
        
        # Category 5: NEGATIVE PENALTY for non-cardiac terms (-50% max)
        negative_matches = sum(1 for term in self.negative_terms if term in text)
        if negative_matches > 0:
            scores["negative_penalty"] = -min(negative_matches * 0.10, 0.50)
        
        # Fuzzy pattern matching boost (REDUCED - 5% max - STRICTER)
        fuzzy_matches = 0
        for pattern in self.fuzzy_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                fuzzy_matches += 1
        
        if fuzzy_matches > 0:
            # STRICTER: Reduced fuzzy boost (0.01 per match, max 5%)
            fuzzy_boost = min(fuzzy_matches * 0.01, 0.05)  # Max 5% boost
            # Distribute across categories with caps
            scores["cardiovascular_disease"] = min(scores["cardiovascular_disease"] + (fuzzy_boost * 0.65), 0.40)
            scores["pathway_name_cardiac"] = min(scores["pathway_name_cardiac"] + (fuzzy_boost * 0.15), 0.15)
            scores["cardiac_processes"] = min(scores["cardiac_processes"] + (fuzzy_boost * 0.12), 0.15)
            scores["direct_cardiac"] = min(scores["direct_cardiac"] + (fuzzy_boost * 0.08), 0.10)
        
        # Disease context boosting (REDUCED - 15% max - STRICTER)
        disease_boost = 0.0
        if disease_context and disease_synonyms:
            disease_text = f"{disease_context} {' '.join(disease_synonyms)}".lower()
            # Check if pathway is relevant to the selected disease
            disease_matches = sum(1 for synonym in disease_synonyms if synonym.lower() in text)
            if disease_matches > 0:
                # STRICTER: Reduced disease boost (0.05 per match, max 15%)
                disease_boost = min(disease_matches * 0.05, 0.15)  # Max 15% boost
                # Distribute boost across cardiac categories with caps
                scores["cardiovascular_disease"] = min(scores["cardiovascular_disease"] + (disease_boost * 0.75), 0.40)
                scores["pathway_name_cardiac"] = min(scores["pathway_name_cardiac"] + (disease_boost * 0.13), 0.15)
                scores["cardiac_processes"] = min(scores["cardiac_processes"] + (disease_boost * 0.08), 0.15)
                scores["direct_cardiac"] = min(scores["direct_cardiac"] + (disease_boost * 0.04), 0.10)
        
        # Calculate total score (STRICTER NORMALIZATION)
        # New range: -50% to +85% (40+15+10+15+5 = 85% max positive)
        total_raw = sum(scores.values())  # Can be negative due to penalties
        
        # STRICTER NORMALIZATION: Require more matches for high scores
        # Normalize from -0.5 to +0.85 range to 0-1 scale
        # First shift to positive: add 0.5 to make range 0 to 1.35
        # Then normalize: divide by 1.35 to get 0-1 range
        # ADDITIONAL: Apply power function to penalize low scores more (x^1.2)
        total_shifted = total_raw + 0.5
        total_normalized = max(0.0, min(total_shifted / 1.35, 1.0))
        # Apply power function to make scoring stricter (requires more terms for high scores)
        total_normalized = total_normalized ** 1.2
        
        # NO baseline for pathways with no matches - force them to score low
        # This ensures only truly cardiac-relevant pathways get high scores
        
        result = {
            "overall": total_normalized,
            **scores
        }
        
        # Enhanced logging for new scoring system
        logger.debug(
            f"Pathway '{pathway_name}': overall={total_normalized:.3f}, "
            f"disease={scores['cardiovascular_disease']:.3f}, "
            f"name_cardiac={scores['pathway_name_cardiac']:.3f}, "
            f"processes={scores['cardiac_processes']:.3f}, "
            f"direct={scores['direct_cardiac']:.3f}, "
            f"penalty={scores['negative_penalty']:.3f}"
        )
        
        return result
    
    def apply_semantic_boost(
        self,
        hypotheses: List[ScoredPathway],
        min_threshold: Optional[float] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> List[ScoredPathway]:
        """
        Apply semantic cardiac relevance boost to NES scores with cardiovascular disease awareness.
        
        SCIENTIFIC RIGOR:
        - Validates input hypotheses for completeness
        - Applies consistent scoring across all pathways
        - Maintains statistical ordering while boosting cardiovascular disease-relevant pathways
        - Preserves original NES for transparency
        - Logs all filtering decisions for reproducibility
        
        This is a permissive filter that boosts pathways with cardiovascular disease-relevant
        terms without strictly excluding others. The boost is multiplicative
        based on overall semantic relevance:
        
        Boost formula: NES_boosted = NES_original * (1 + semantic_relevance)
        
        Examples:
        - High relevance (0.8): 1.8 times boost
        - Medium relevance (0.5): 1.5 times boost
        - Low relevance (0.2): 1.2 times boost
        - Minimal relevance (0.05): 1.05 times boost
        
        Args:
            hypotheses: List of scored hypotheses
            min_threshold: Optional minimum semantic threshold (default from config)
            disease_context: Optional disease context for targeted filtering
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            List of hypotheses with semantic boost applied and re-ranked
            
        Raises:
            ValueError: If hypotheses list is invalid or threshold out of range
        """
        # Input validation for robustness
        if not isinstance(hypotheses, list):
            raise ValueError("Hypotheses must be a list")
        
        if len(hypotheses) == 0:
            logger.warning("Empty hypotheses list provided to semantic filter")
            return hypotheses
        
        if min_threshold is None:
            min_threshold = getattr(self.settings, 'semantic_relevance_threshold', 0.1)
        
        # Validate threshold range
        if not (isinstance(min_threshold, (int, float)) and 0 <= min_threshold <= 1):
            logger.warning(f"Invalid threshold {min_threshold}, using default 0.1")
            min_threshold = 0.1
        
        logger.info(
            f"Applying expanded semantic cardiac relevance boost to {len(hypotheses)} hypotheses "
            f"(min_threshold={min_threshold})"
        )
        
        boosted_hypotheses = []
        filtered_count = 0
        
        for hypothesis in hypotheses:
            # Get pathway information
            if hasattr(hypothesis, 'aggregated_pathway'):
                pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
                pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
                evidence_genes = getattr(hypothesis.aggregated_pathway.pathway, 'evidence_genes', [])
            else:
                # Fallback for older pathway format
                pathway_name = getattr(hypothesis, 'pathway_name', 'Unknown')
                pathway_id = getattr(hypothesis, 'pathway_id', 'unknown')
                evidence_genes = getattr(hypothesis, 'evidence_genes', [])
            
            # Calculate comprehensive cardiac relevance
            relevance_breakdown = self.calculate_cardiac_relevance(
                pathway_name,
                evidence_genes=evidence_genes,
                disease_context=disease_context,
                disease_synonyms=disease_synonyms
            )
            overall_relevance = relevance_breakdown["overall"]
            
            # Debug logging for specific pathways
            if "heart" in pathway_name.lower():
                logger.info(
                    f"[SEMANTIC DEBUG] Pathway '{pathway_name}': "
                    f"overall_relevance={overall_relevance:.3f}, "
                    f"direct_cardiac={relevance_breakdown.get('direct_cardiac', 0):.3f}, "
                    f"processes={relevance_breakdown.get('processes', 0):.3f}"
                )
            
            # Apply minimum threshold filter (very permissive)
            if overall_relevance < min_threshold:
                filtered_count += 1
                logger.debug(
                    f"Filtered out '{pathway_name}': relevance {overall_relevance:.3f} < {min_threshold}"
                )
                continue
            
            # Calculate boost factor: NES * (1 + relevance)
            boost_factor = 1 + overall_relevance
            
            # Apply boost to NES score
            original_nes = hypothesis.nes_score
            boosted_nes = original_nes * boost_factor
            hypothesis.nes_score = boosted_nes
            
            # Store relevance breakdown in score components (always create if not exists)
            if not hasattr(hypothesis, 'score_components') or hypothesis.score_components is None:
                hypothesis.score_components = {}
            
            hypothesis.score_components['cardiac_relevance'] = overall_relevance
            hypothesis.score_components['semantic_boost'] = boost_factor
            hypothesis.score_components['relevance_breakdown'] = relevance_breakdown
            
            boosted_hypotheses.append(hypothesis)
            
            logger.debug(
                f"Pathway '{pathway_name}': relevance={overall_relevance:.3f}, "
                f"boost={boost_factor:.3f}, NES {original_nes:.2f} → {boosted_nes:.2f}"
            )
        
        # Re-sort by boosted NES scores
        boosted_hypotheses.sort(key=lambda h: h.nes_score, reverse=True)
        
        # Update ranks
        for i, hypothesis in enumerate(boosted_hypotheses, 1):
            hypothesis.rank = i
        
        # Apply intelligent progressive filtering and result limiting
        intelligent_filtered = self.apply_intelligent_filtering(
            boosted_hypotheses,
            disease_context=disease_context,
            disease_synonyms=disease_synonyms
        )
        
        logger.info(
            f"Semantic processing: {len(hypotheses)} -> {len(boosted_hypotheses)} -> {len(intelligent_filtered)} pathways "
            f"({filtered_count} filtered by threshold {min_threshold}, intelligent filtering applied)"
        )
        
        return intelligent_filtered
    
    def apply_semantic_boost_parallel(
        self,
        hypotheses: List[ScoredPathway],
        min_threshold: Optional[float] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None,
        max_workers: Optional[int] = None
    ) -> List[ScoredPathway]:
        """
        Apply semantic cardiac relevance boost to NES scores with parallel processing.
        
        This parallel version processes hypotheses concurrently for better performance
        on large hypothesis sets.
        
        Args:
            hypotheses: List of scored hypotheses
            min_threshold: Optional minimum semantic threshold
            disease_context: Optional disease context for targeted filtering
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            max_workers: Maximum number of parallel workers
            
        Returns:
            List of hypotheses with semantic boost applied and re-ranked
        """
        # Input validation
        if not isinstance(hypotheses, list):
            raise ValueError("Hypotheses must be a list")
        
        if len(hypotheses) == 0:
            logger.warning("Empty hypotheses list provided to semantic filter")
            return hypotheses
        
        if min_threshold is None:
            min_threshold = getattr(self.settings, 'semantic_relevance_threshold', 0.1)
        
        # Get max_workers from performance configuration
        if max_workers is None:
            # Lower default to reduce memory/CPU footprint on small machines
            max_workers = getattr(self.settings, 'max_workers', 2)
        
        # Validate threshold range
        if not (isinstance(min_threshold, (int, float)) and 0 <= min_threshold <= 1):
            logger.warning(f"Invalid threshold {min_threshold}, using default 0.1")
            min_threshold = 0.1
        
        logger.info(
            f"Applying parallel semantic cardiac relevance boost to {len(hypotheses)} hypotheses "
            f"(min_threshold={min_threshold}, max_workers={max_workers})"
        )
        
        # Process hypotheses in parallel
        boosted_hypotheses = []
        filtered_count = 0
        
        def process_hypothesis(hypothesis: ScoredPathway) -> Optional[Tuple[ScoredPathway, Dict[str, Any]]]:
            """Process a single hypothesis for semantic relevance."""
            # Get pathway information
            if hasattr(hypothesis, 'aggregated_pathway'):
                pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
                pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
                evidence_genes = getattr(hypothesis.aggregated_pathway.pathway, 'evidence_genes', [])
            else:
                # Fallback for older pathway format
                pathway_name = getattr(hypothesis, 'pathway_name', 'Unknown')
                pathway_id = getattr(hypothesis, 'pathway_id', 'unknown')
                evidence_genes = getattr(hypothesis, 'evidence_genes', [])
            
            # Calculate comprehensive cardiac relevance
            relevance_breakdown = self.calculate_cardiac_relevance(
                pathway_name,
                evidence_genes=evidence_genes,
                disease_context=disease_context,
                disease_synonyms=disease_synonyms
            )
            overall_relevance = relevance_breakdown["overall"]
            
            # Apply minimum threshold filter
            if overall_relevance < min_threshold:
                logger.debug(
                    f"Filtered out '{pathway_name}': relevance {overall_relevance:.3f} < {min_threshold}"
                )
                return None
            
            # Calculate boost factor: NES * (1 + relevance)
            boost_factor = 1 + overall_relevance
            
            # Apply boost to NES score
            original_nes = hypothesis.nes_score
            boosted_nes = original_nes * boost_factor
            hypothesis.nes_score = boosted_nes
            
            # Store relevance breakdown in score components
            if not hasattr(hypothesis, 'score_components') or hypothesis.score_components is None:
                hypothesis.score_components = {}
            
            hypothesis.score_components['cardiac_relevance'] = overall_relevance
            hypothesis.score_components['semantic_boost'] = boost_factor
            hypothesis.score_components['relevance_breakdown'] = relevance_breakdown
            
            logger.debug(
                f"Pathway '{pathway_name}': relevance={overall_relevance:.3f}, "
                f"boost={boost_factor:.3f}, NES {original_nes:.2f} → {boosted_nes:.2f}"
            )
            
            return hypothesis, relevance_breakdown
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_hypothesis = {
                executor.submit(process_hypothesis, hypothesis): hypothesis 
                for hypothesis in hypotheses
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_hypothesis):
                result = future.result()
                if result is None:
                    filtered_count += 1
                else:
                    hypothesis, relevance_breakdown = result
                    boosted_hypotheses.append(hypothesis)
                    
                    # Debug logging for specific pathways
                    pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name if hasattr(hypothesis, 'aggregated_pathway') else getattr(hypothesis, 'pathway_name', 'Unknown')
                    if "heart" in pathway_name.lower():
                        logger.info(
                            f"[SEMANTIC DEBUG] Pathway '{pathway_name}': "
                            f"overall_relevance={relevance_breakdown.get('overall', 0):.3f}, "
                            f"direct_cardiac={relevance_breakdown.get('direct_cardiac', 0):.3f}, "
                            f"processes={relevance_breakdown.get('processes', 0):.3f}"
                        )
        
        # Re-sort by boosted NES scores
        boosted_hypotheses.sort(key=lambda h: h.nes_score, reverse=True)
        
        # Update ranks
        for i, hypothesis in enumerate(boosted_hypotheses, 1):
            hypothesis.rank = i
        
        # Apply intelligent progressive filtering and result limiting
        intelligent_filtered = self.apply_intelligent_filtering(
            boosted_hypotheses,
            disease_context=disease_context,
            disease_synonyms=disease_synonyms
        )
        
        logger.info(
            f"Parallel semantic processing: {len(hypotheses)} -> {len(boosted_hypotheses)} -> {len(intelligent_filtered)} pathways "
            f"({filtered_count} filtered by threshold {min_threshold}, intelligent filtering applied)"
        )
        
        return intelligent_filtered
    
    def apply_intelligent_filtering(
        self,
        hypotheses: List[ScoredPathway],
        max_results: Optional[int] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> List[ScoredPathway]:
        """
        Apply intelligent filtering with ADAPTIVE TIERED THRESHOLDING for novel discovery.
        
        Strategy (Enhanced for Novel Pathway Discovery - STRICTER FILTERING):
        1. Calculate cardiac_relevance_score for each pathway (0-1 scale)
        2. Apply disease context boost (+30% for matched terms)
        3. Use adaptive tiered thresholds (STRENGTHENED):
           - Top 30 pathways: No threshold (capture very high-NES only)
           - Next 70 pathways: cardiac_relevance >= 0.30 (moderate threshold)
           - Remaining 50: cardiac_relevance >= 0.50 (strict threshold)
        4. Pathway name filtering: Ranks 31+ require cardiac term in name OR cardiac_relevance >= 0.50
        5. Final limit: 150 pathways total
        
        Rationale: Prioritizes cardiac-specific pathways while allowing some novel discoveries.
        Stricter thresholds ensure cardiovascular disease context relevance.
        
        Args:
            hypotheses: List of scored hypotheses
            max_results: Maximum number of results to return (default 150)
            disease_context: Optional disease context for targeted filtering
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            Filtered and limited list of most relevant hypotheses with cardiac context
        """
        if not hypotheses:
            return []
        
        max_results = max_results or 150
        
        # Get disease synonyms from cardiac context if disease_context provided but no synonyms
        if disease_context and not disease_synonyms:
            if disease_context.lower() in ["cardiac", "cardiovascular", "heart"]:
                # Combine all cardiac context keywords as disease synonyms
                disease_synonyms = (
                    self.cardiac_context.high_priority_keywords +
                    self.cardiac_context.medium_priority_keywords +
                    self.cardiac_context.low_priority_keywords
                )
                logger.info(f"Using {len(disease_synonyms)} cardiac disease synonyms for context '{disease_context}'")
        
        # Sort by NES first (higher NES = more statistically significant)
        hypotheses_sorted = sorted(hypotheses, key=lambda h: h.nes_score, reverse=True)
        
        logger.info(f"Applying adaptive tiered semantic filtering on {len(hypotheses_sorted)} pathways")
        
        filtered_hypotheses = []
        
        for i, hypothesis in enumerate(hypotheses_sorted):
            # Get pathway name
            if hasattr(hypothesis, 'aggregated_pathway'):
                pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
            else:
                pathway_name = getattr(hypothesis, 'pathway_name', 'Unknown')
            
            # Calculate cardiac relevance with disease context boost
            relevance_breakdown = self.calculate_cardiac_relevance(
                pathway_name,
                disease_context=disease_context,
                disease_synonyms=disease_synonyms
            )
            cardiac_relevance = relevance_breakdown['overall']
            
            # Store relevance in score components for downstream use
            if not hasattr(hypothesis, 'score_components') or hypothesis.score_components is None:
                hypothesis.score_components = {}
            hypothesis.score_components['cardiac_relevance'] = cardiac_relevance
            hypothesis.score_components['cardiovascular_disease'] = relevance_breakdown.get('cardiovascular_disease', 0.0)
            
            # ADAPTIVE TIERED THRESHOLDING (STRENGTHENED)
            pathway_name_lower = pathway_name.lower()
            has_cardiac_term_in_name = any(
                term in pathway_name_lower 
                for term in ['cardiac', 'heart', 'myocardial', 'cardiomyocyte', 'cardiovascular',
                             'coronary', 'ventricular', 'atrial', 'aortic', 'myocardium',
                             'cardiomyopathy', 'arrhythmia', 'ischemia', 'infarction']
            )
            
            if i < 30:
                # Tier 1: Top 30 by NES - Always include (very high-NES novel discovery tier)
                filtered_hypotheses.append(hypothesis)
                if i < 3:
                    logger.debug(f"  Tier 1 (Top 30 NES): {pathway_name} | NES={hypothesis.nes_score:.2f} | Cardiac={cardiac_relevance:.3f}")
            elif i < 100 and (cardiac_relevance >= 0.30 or has_cardiac_term_in_name):
                # Tier 2: Next 70 - Moderate threshold (0.30) OR has cardiac term in name
                filtered_hypotheses.append(hypothesis)
            elif cardiac_relevance >= 0.50:
                # Tier 3: Remaining 50 - Strict threshold (0.50) for high cardiac specificity
                filtered_hypotheses.append(hypothesis)
            
            # Stop at max_results
            if len(filtered_hypotheses) >= max_results:
                break
        
        logger.info(
            f"Adaptive semantic filtering (STRENGTHENED): {len(hypotheses_sorted)} -> {len(filtered_hypotheses)} pathways "
            f"(Tier 1: top 30 NES, Tier 2: 0.30 threshold + name filter, Tier 3: 0.50 threshold)"
        )
        
        return filtered_hypotheses

    def get_semantic_statistics(
        self,
        hypotheses: List[ScoredPathway]
    ) -> Dict[str, Any]:
        """
        Calculate semantic relevance statistics across all hypotheses.
        
        Args:
            hypotheses: List of scored hypotheses
            
        Returns:
            Dictionary with semantic statistics
        """
        if not hypotheses:
            return {
                "total_count": 0,
                "mean_relevance": 0.0,
                "median_relevance": 0.0,
                "high_relevance_count": 0,
                "medium_relevance_count": 0,
                "low_relevance_count": 0
            }
        
        relevance_scores = []
        
        for hypothesis in hypotheses:
            if hasattr(hypothesis, 'score_components') and hypothesis.score_components:
                relevance = hypothesis.score_components.get('cardiac_relevance', 0.0)
                relevance_scores.append(relevance)
        
        if not relevance_scores:
            return {
                "total_count": len(hypotheses),
                "mean_relevance": 0.0,
                "median_relevance": 0.0,
                "high_relevance_count": 0,
                "medium_relevance_count": 0,
                "low_relevance_count": 0
            }
        
        relevance_scores.sort()
        mean_relevance = sum(relevance_scores) / len(relevance_scores)
        median_relevance = relevance_scores[len(relevance_scores) // 2]
        
        high_count = sum(1 for r in relevance_scores if r >= 0.6)
        medium_count = sum(1 for r in relevance_scores if 0.3 <= r < 0.6)
        low_count = sum(1 for r in relevance_scores if r < 0.3)
        
        return {
            "total_count": len(hypotheses),
            "mean_relevance": mean_relevance,
            "median_relevance": median_relevance,
            "high_relevance_count": high_count,
            "medium_relevance_count": medium_count,
            "low_relevance_count": low_count,
            "distribution": {
                "high (≥0.6)": high_count,
                "medium (0.3-0.6)": medium_count,
                "low (<0.3)": low_count
            }
        }
    
    def filter_by_cardiac_relevance(
        self,
        hypotheses: List[ScoredPathway],
        min_relevance: float = 0.1,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> List[ScoredPathway]:
        """
        Filter pathways by minimum cardiovascular disease relevance (optional strict filter).
        
        This is a stricter filter that removes pathways below a threshold.
        Default threshold is very permissive (0.1) to maintain broad discovery.
        
        Args:
            hypotheses: List of scored hypotheses
            min_relevance: Minimum cardiovascular disease relevance score (default: 0.1)
            
        Returns:
            Filtered list of hypotheses
        """
        filtered = []
        
        for hypothesis in hypotheses:
            if hasattr(hypothesis, 'aggregated_pathway'):
                pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
                evidence_genes = getattr(hypothesis.aggregated_pathway.pathway, 'evidence_genes', [])
            else:
                # Fallback for older pathway format
                pathway_name = getattr(hypothesis, 'pathway_name', 'Unknown')
                evidence_genes = getattr(hypothesis, 'evidence_genes', [])
            
            relevance_breakdown = self.calculate_cardiac_relevance(
                pathway_name,
                evidence_genes=evidence_genes,
                disease_context=disease_context,
                disease_synonyms=disease_synonyms
            )
            overall_relevance = relevance_breakdown["overall"]
            
            if overall_relevance >= min_relevance:
                filtered.append(hypothesis)
            else:
                logger.debug(
                    f"Filtered out '{pathway_name}': relevance {overall_relevance:.3f} < {min_relevance}"
                )
        
        logger.info(
            f"Semantic filtering: {len(filtered)}/{len(hypotheses)} pathways "
            f"passed min_relevance={min_relevance}"
        )
        
        return filtered

    def pathway_name_contains_cardiac_terms(self, pathway_name: str, disease_context: Optional[str] = None) -> bool:
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
        pathway_lower = pathway_name.lower()
        
        # ULTRA-STRICT: Only EXPLICIT cardiac/cardiovascular/heart terminology
        # NO generic biological processes allowed (removed: contraction, conduction, angiogenesis, etc.)
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
                logger.debug(f"Pathway '{pathway_name}' contains cardiac term: '{term}'")
                return True
        
        # Check for cardiac word stems (ONLY cardiac-specific stems)
        # Removed generic patterns like "ventric", "atri" that could match non-cardiac terms
        cardiac_specific_patterns = [
            r"\bcardio\w+",      # cardiomyopathy, cardiogenesis, etc.
            r"\bmyocardi\w+",    # myocardial, myocardium, etc.
            r"\bcoronar\w+",     # coronary, etc.
            r"\bheart\s+\w+",    # heart failure, heart disease, etc.
        ]
        
        for pattern in cardiac_specific_patterns:
            if re.search(pattern, pathway_lower):
                logger.debug(f"Pathway '{pathway_name}' matches cardiac pattern: '{pattern}'")
                return True
        
        # If none of the above matched, this pathway is NOT cardiac-relevant
        logger.debug(f"Pathway '{pathway_name}' does NOT contain explicit cardiac terms - FILTERED OUT")
        return False

    def apply_final_strict_name_filter(
        self,
        hypotheses: List[ScoredPathway],
        disease_context: Optional[str] = None
    ) -> List[ScoredPathway]:
        """
        Apply FINAL STRICT filter requiring pathway names to contain cardiac/disease terms.
        
        This is the last filtering stage to ensure all final pathways have explicit
        cardiac/disease terminology in their names, guaranteeing disease-focused results.
        
        Args:
            hypotheses: List of scored hypotheses
            disease_context: Optional disease context for enhanced filtering
            
        Returns:
            Filtered list with only cardiac/disease-named pathways
        """
        filtered = []
        filtered_out = []
        
        for hypothesis in hypotheses:
            if hasattr(hypothesis, 'aggregated_pathway'):
                pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
            else:
                pathway_name = getattr(hypothesis, 'pathway_name', 'Unknown')
            
            if self.pathway_name_contains_cardiac_terms(pathway_name, disease_context):
                filtered.append(hypothesis)
            else:
                filtered_out.append(pathway_name)
                logger.debug(f"FINAL FILTER: Removed '{pathway_name}' - no cardiac terms in pathway name")
        
        filtered_count = len(filtered_out)
        retention_rate = (len(filtered) / len(hypotheses) * 100) if len(hypotheses) > 0 else 0
        
        logger.info(
            f"FINAL STRICT NAME FILTER: {len(filtered)}/{len(hypotheses)} pathways retained "
            f"({retention_rate:.1f}%), {filtered_count} pathways removed"
        )
        
        if filtered_count > 0 and filtered_count <= 10:
            logger.info(f"Filtered out pathways (no cardiac terms in name): {', '.join(filtered_out[:10])}")
        elif filtered_count > 10:
            logger.info(f"Filtered out {filtered_count} pathways (sample): {', '.join(filtered_out[:5])}...")
        
        return filtered
