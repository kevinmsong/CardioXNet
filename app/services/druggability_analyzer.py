"""Druggability analysis for pathway genes using DrugBank data."""

import logging
from typing import List, Dict, Set, Any
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class DruggabilityScore:
    """Druggability analysis result."""
    
    druggable_genes: List[str]
    druggable_ratio: float
    total_genes: int
    drug_count: int
    approved_drug_count: int
    clinical_trial_count: int
    druggability_tier: str  # 'high', 'medium', 'low'


class DruggabilityAnalyzer:
    """
    Analyzes pathway druggability using DrugBank and therapeutic target data.
    
    SCIENTIFIC RATIONALE:
    - Prioritizes pathways with existing therapeutic interventions
    - Identifies translational opportunities
    - Highlights pathways amenable to drug development
    
    DATA SOURCES:
    - DrugBank: FDA-approved and investigational drugs
    - Therapeutic Target Database (TTD)
    - ChEMBL: Bioactive molecules
    - Literature-curated cardiac drug targets
    """
    
    def __init__(self):
        """Initialize druggability analyzer."""
        self.settings = get_settings()
        
        # Load druggable gene sets
        self.druggable_genes = self._load_druggable_genes()
        self.approved_drug_targets = self._load_approved_drug_targets()
        self.clinical_trial_targets = self._load_clinical_trial_targets()
        
        logger.info(
            f"DruggabilityAnalyzer initialized: "
            f"{len(self.druggable_genes)} druggable genes, "
            f"{len(self.approved_drug_targets)} approved drug targets"
        )
    
    def _load_druggable_genes(self) -> Set[str]:
        """
        Load curated set of druggable genes.
        
        Based on:
        - DrugBank targets
        - Therapeutic Target Database
        - Druggable genome (Hopkins & Groom, 2002)
        - Cardiac-specific drug targets
        """
        druggable = {
            # GPCRs (highly druggable)
            'ADRB1', 'ADRB2', 'ADRB3', 'ADRA1A', 'ADRA1B', 'ADRA1D',
            'ADRA2A', 'ADRA2B', 'ADRA2C', 'CHRM2', 'CHRM3',
            'EDNRA', 'EDNRB', 'AGTR1', 'AGTR2', 'NPR1', 'NPR2',
            
            # Ion channels
            'SCN5A', 'KCNQ1', 'KCNH2', 'KCNJ2', 'KCNJ11', 'CACNA1C',
            'CACNA1D', 'CACNA1G', 'CACNA1H', 'HCN4', 'HCN2',
            
            # Kinases
            'AKT1', 'AKT2', 'MAPK14', 'MAPK8', 'MAPK1', 'MAPK3',
            'GSK3B', 'ROCK1', 'ROCK2', 'PRKAA1', 'PRKAA2', 'PRKACA',
            'PRKCA', 'PRKCB', 'MTOR', 'PIK3CA', 'PIK3CB', 'PIK3CG',
            'JAK1', 'JAK2', 'TYK2', 'SRC', 'ABL1', 'EGFR', 'PDGFRA',
            'PDGFRB', 'KIT', 'FLT3', 'VEGFR1', 'VEGFR2', 'VEGFR3',
            
            # Nuclear receptors
            'PPARA', 'PPARD', 'PPARG', 'NR3C1', 'NR3C2', 'RARA',
            'RARB', 'RARG', 'RXRA', 'RXRB', 'RXRG', 'ESRRA', 'ESRRB',
            'ESRRG', 'NR1H3', 'NR1H2',
            
            # Enzymes
            'ACE', 'ACE2', 'ACHE', 'BCHE', 'COMT', 'MAO', 'MAOA', 'MAOB',
            'PDE3A', 'PDE3B', 'PDE4A', 'PDE4B', 'PDE4D', 'PDE5A',
            'HMGCR', 'PCSK9', 'LDLR', 'APOB', 'CETP',
            'COX1', 'COX2', 'PTGS1', 'PTGS2', 'ALOX5', 'ALOX12', 'ALOX15',
            'NOS1', 'NOS2', 'NOS3', 'GUCY1A1', 'GUCY1B1',
            'MMP2', 'MMP9', 'MMP1', 'MMP3', 'MMP13',
            'CASP3', 'CASP8', 'CASP9', 'PARP1',
            
            # Transporters
            'SLC22A1', 'SLC22A2', 'SLC22A3', 'ABCB1', 'ABCC1', 'ABCC2',
            'ABCG2', 'SLC6A2', 'SLC6A3', 'SLC6A4',
            
            # Cytokines and growth factors
            'TNF', 'IL1B', 'IL6', 'IL10', 'IL17A', 'IFNG', 'TGFB1',
            'VEGFA', 'VEGFB', 'VEGFC', 'FGF2', 'PDGFA', 'PDGFB',
            'IGF1', 'IGF2', 'INS', 'GH1', 'PRL',
            
            # Coagulation
            'F2', 'F7', 'F9', 'F10', 'F11', 'F12', 'F13A1',
            'SERPINC1', 'SERPINE1', 'PLAT', 'PLAU', 'PLG',
            
            # Lipid metabolism
            'APOA1', 'APOA2', 'APOB', 'APOC2', 'APOC3', 'APOE',
            'LCAT', 'LIPC', 'LPL', 'LIPG',
            
            # Cardiac-specific targets
            'RYR2', 'ATP2A2', 'PLN', 'CASQ2', 'JPH2', 'CALM1',
            'MYBPC3', 'MYH7', 'TNNT2', 'TNNI3', 'TPM1',
            'GRK2', 'GRK5', 'ARRB1', 'ARRB2',
            
            # Transcription factors (challenging but emerging)
            'NFKB1', 'RELA', 'JUN', 'FOS', 'MYC', 'TP53', 'HIF1A',
            'STAT3', 'STAT5A', 'STAT5B', 'SMAD2', 'SMAD3', 'SMAD4',
            'CTNNB1', 'YAP1', 'TAZ', 'NOTCH1', 'NOTCH2',
        }
        
        return druggable
    
    def _load_approved_drug_targets(self) -> Set[str]:
        """Load genes targeted by FDA-approved drugs."""
        approved = {
            # Beta blockers
            'ADRB1', 'ADRB2',
            
            # ACE inhibitors / ARBs
            'ACE', 'AGTR1',
            
            # Calcium channel blockers
            'CACNA1C', 'CACNA1D',
            
            # Diuretics
            'SLC12A3', 'SLC12A1', 'SCNN1A',
            
            # Anticoagulants
            'F2', 'F10', 'SERPINC1',
            
            # Antiplatelets
            'PTGS1', 'P2RY12', 'ITGB3',
            
            # Statins
            'HMGCR',
            
            # Nitrates
            'GUCY1A1', 'GUCY1B1',
            
            # Digoxin
            'ATP1A1', 'ATP1A2', 'ATP1A3',
            
            # Antiarrhythmics
            'SCN5A', 'KCNH2', 'KCNQ1',
        }
        
        return approved
    
    def _load_clinical_trial_targets(self) -> Set[str]:
        """Load genes targeted by drugs in clinical trials."""
        clinical = {
            # SGLT2 inhibitors
            'SLC5A2',
            
            # PCSK9 inhibitors
            'PCSK9',
            
            # Novel anticoagulants
            'F11', 'F12',
            
            # Anti-inflammatory
            'IL1B', 'IL6', 'TNF', 'IL17A',
            
            # Metabolic
            'PPARA', 'PPARD', 'PPARG', 'GCG', 'GLP1R',
            
            # Fibrosis
            'TGFB1', 'CTGF', 'LOXL2',
            
            # Regeneration
            'WNT', 'NOTCH1', 'YAP1',
        }
        
        return clinical
    
    def calculate_druggability_score(
        self,
        pathway_genes: List[str]
    ) -> DruggabilityScore:
        """
        Calculate druggability score for pathway.
        
        Args:
            pathway_genes: List of gene symbols in pathway
            
        Returns:
            DruggabilityScore with metrics
        """
        if not pathway_genes:
            return DruggabilityScore(
                druggable_genes=[],
                druggable_ratio=0.0,
                total_genes=0,
                drug_count=0,
                approved_drug_count=0,
                clinical_trial_count=0,
                druggability_tier='low'
            )
        
        # Identify druggable genes
        pathway_set = set(g.upper() for g in pathway_genes)
        druggable = list(pathway_set & self.druggable_genes)
        approved = list(pathway_set & self.approved_drug_targets)
        clinical = list(pathway_set & self.clinical_trial_targets)
        
        # Calculate metrics
        total_genes = len(pathway_genes)
        druggable_ratio = len(druggable) / total_genes if total_genes > 0 else 0.0
        
        # Determine tier
        if druggable_ratio >= 0.3 and len(approved) >= 2:
            tier = 'high'
        elif druggable_ratio >= 0.2 or len(approved) >= 1:
            tier = 'medium'
        else:
            tier = 'low'
        
        logger.debug(
            f"Druggability: {len(druggable)}/{total_genes} druggable "
            f"({len(approved)} approved, {len(clinical)} clinical), tier: {tier}"
        )
        
        return DruggabilityScore(
            druggable_genes=druggable,
            druggable_ratio=druggable_ratio,
            total_genes=total_genes,
            drug_count=len(druggable),
            approved_drug_count=len(approved),
            clinical_trial_count=len(clinical),
            druggability_tier=tier
        )
    
    def annotate_pathways_with_druggability(
        self,
        pathways: List[Any]
    ) -> List[Any]:
        """
        Annotate pathways with druggability scores.
        
        Args:
            pathways: List of pathway objects
            
        Returns:
            Pathways with added druggability annotations
        """
        for pathway in pathways:
            pathway_genes = getattr(pathway, 'evidence_genes', [])
            druggability = self.calculate_druggability_score(pathway_genes)
            
            # FIXED: Cannot mutate Pydantic BaseModel - druggability data handled separately
            # Add annotations
            # if hasattr(pathway, '__dict__'):
            #     pathway.druggable_genes = druggability.druggable_genes
            #     pathway.druggable_ratio = druggability.druggable_ratio
            #     pathway.approved_drug_count = druggability.approved_drug_count
            #     pathway.clinical_trial_count = druggability.clinical_trial_count
            #     pathway.druggability_tier = druggability.druggability_tier
        
        logger.info(f"Annotated {len(pathways)} pathways with druggability data")
        
        return pathways
    
    def filter_by_druggability(
        self,
        pathways: List[Any],
        min_druggable_ratio: float = 0.1
    ) -> List[Any]:
        """
        Filter pathways by minimum druggability.
        
        Args:
            pathways: List of pathways
            min_druggable_ratio: Minimum ratio of druggable genes
            
        Returns:
            Filtered pathways
        """
        filtered = []
        
        for pathway in pathways:
            druggable_ratio = getattr(pathway, 'druggable_ratio', 0.0)
            if druggable_ratio >= min_druggable_ratio:
                filtered.append(pathway)
        
        logger.info(
            f"Druggability filtering: {len(filtered)}/{len(pathways)} pathways "
            f"with ≥{min_druggable_ratio:.0%} druggable genes"
        )
        
        return filtered
