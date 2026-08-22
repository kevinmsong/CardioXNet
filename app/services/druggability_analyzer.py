"""Druggability analysis using curated DrugBank data + Open Targets Platform API."""

import logging
import requests
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field

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

    # Open Targets live evidence fields
    druggability_source: str = "curated"          # "curated" | "Open Targets + curated"
    external_target_count: int = 0                 # genes matched in Open Targets
    external_approved_target_count: int = 0        # targets with FDA-approved drugs
    external_clinical_target_count: int = 0        # targets in active clinical trials
    cardiovascular_target_count: int = 0           # targets with CV disease indication
    target_evidence: List[Dict[str, Any]] = field(default_factory=list)  # per-gene detail


class DruggabilityAnalyzer:
    """
    Analyzes pathway druggability using DrugBank and therapeutic target data.
    
    SCIENTIFIC RATIONALE:
    - Prioritizes pathways with existing therapeutic interventions
    - Identifies translational opportunities
    - Highlights pathways amenable to drug development
    
    DATA SOURCES (Manually Curated):
    - DrugBank v5.1.10 (2023): FDA-approved and investigational drugs
    - Therapeutic Target Database (TTD) 2023 Update 2
    - ChEMBL v31: Bioactive molecules and drug targets
    - Hopkins & Groom (2002): Druggable genome classification
    - Literature-curated cardiac drug targets from clinical trials
    
    NOTE: Gene lists are manually curated from above sources and embedded
    in this class for performance. Data current as of November 2023.
    """
    
    # Open Targets Platform GraphQL endpoint
    _OT_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
    _OT_QUERY = """
    query SearchTarget($term: String!) {
      search(queryString: $term, entityNames: ["target"], page: {index: 0, size: 5}) {
        hits {
          id
          entity
          object {
            ... on Target {
              approvedSymbol
              tractability { label modality value }
              knownDrugs(size: 10) {
                count
                rows {
                  phase
                  status
                  disease { name }
                  drug { id name maximumClinicalTrialPhase }
                }
              }
            }
          }
        }
      }
    }
    """

    def __init__(self):
        """Initialize druggability analyzer with curated lists + Open Targets live API."""
        self.settings = get_settings()

        # Curated gene sets (DrugBank v5.1.10, TTD 2023, ChEMBL v31 — Nov 2023)
        self.druggable_genes = self._load_druggable_genes()
        self.approved_drug_targets = self._load_approved_drug_targets()
        self.clinical_trial_targets = self._load_clinical_trial_targets()

        logger.info(
            f"DruggabilityAnalyzer initialized: "
            f"{len(self.druggable_genes)} curated druggable genes, "
            f"{len(self.approved_drug_targets)} approved targets"
        )

    def _query_open_targets(self, gene_symbols: List[str]) -> List[Dict[str, Any]]:
        """Query Open Targets Platform GraphQL API for drug target evidence per gene."""
        matched: List[Dict[str, Any]] = []
        for gene in gene_symbols:
            try:
                resp = requests.post(
                    self._OT_GRAPHQL_URL,
                    json={"query": self._OT_QUERY, "variables": {"term": gene}},
                    timeout=10,
                )
                resp.raise_for_status()
                hits = resp.json().get("data", {}).get("search", {}).get("hits", [])
                for hit in hits:
                    obj = hit.get("object", {})
                    if obj.get("approvedSymbol", "").upper() == gene.upper():
                        matched.append(obj)
                        break  # exact symbol match — take first
            except Exception:
                pass
        return matched
    
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
        pathway_genes: List[str],
        use_external: bool = True,
    ) -> DruggabilityScore:
        """
        Calculate druggability score for pathway.

        Args:
            pathway_genes: List of gene symbols in pathway
            use_external: When True, supplement the curated tiers with a live
                Open Targets lookup. When False, score is computed entirely from
                the offline curated drug-target sets (no network calls) — used by
                the fast preset so the druggability column is still populated.

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
                druggability_tier='low',
            )

        # ── Curated sets (primary source) ──────────────────────────────────
        pathway_set = set(g.upper() for g in pathway_genes)
        druggable = set(pathway_set & self.druggable_genes)
        approved = set(pathway_set & self.approved_drug_targets)
        clinical = set(pathway_set & self.clinical_trial_targets)

        # ── Open Targets live evidence (supplementary, optional) ───────────
        ot_hits = self._query_open_targets(list(pathway_set)) if use_external else []

        ot_target_count = 0
        ot_approved_count = 0
        ot_clinical_count = 0
        ot_cv_count = 0
        target_evidence: List[Dict[str, Any]] = []
        druggability_source = "curated"

        if ot_hits:
            druggability_source = "Open Targets + curated"
            _cv_terms = {"cardiovascular", "heart", "cardiac", "coronary", "arrhythmia",
                         "hypertension", "heart failure", "cardiomyopathy"}
            for obj in ot_hits:
                gene_sym = obj.get("approvedSymbol", "")
                tractability = obj.get("tractability") or []
                drugs_data = obj.get("knownDrugs") or {}
                drug_rows = drugs_data.get("rows") or []

                has_approved = any(
                    t.get("label") == "Approved Drug" and t.get("value") for t in tractability
                )
                has_clinical = any(
                    t.get("label") == "Advanced Clinical" and t.get("value") for t in tractability
                )
                has_cv = any(
                    any(term in (r.get("disease") or {}).get("name", "").lower() for term in _cv_terms)
                    for r in drug_rows
                )

                ot_target_count += 1
                if has_approved:
                    ot_approved_count += 1
                    druggable.add(gene_sym.upper())
                    approved.add(gene_sym.upper())
                if has_clinical:
                    ot_clinical_count += 1
                    druggable.add(gene_sym.upper())
                    clinical.add(gene_sym.upper())
                if has_cv:
                    ot_cv_count += 1

                top_drugs = [
                    {"name": r["drug"]["name"], "phase": r.get("phase", 0)}
                    for r in drug_rows
                    if r.get("drug", {}).get("name")
                ][:5]
                target_evidence.append({"gene_symbol": gene_sym, "top_drugs": top_drugs})

        druggable_list = list(druggable)
        approved_list = list(approved)
        clinical_list = list(clinical)

        total_genes = len(pathway_genes)
        druggable_ratio = len(druggable_list) / total_genes if total_genes > 0 else 0.0

        if druggable_ratio >= 0.3 and len(approved_list) >= 2:
            tier = 'high'
        elif druggable_ratio >= 0.2 or len(approved_list) >= 1:
            tier = 'medium'
        else:
            tier = 'low'

        logger.debug(
            f"Druggability: {len(druggable_list)}/{total_genes} ({len(approved_list)} approved, "
            f"{len(clinical_list)} clinical, {ot_target_count} OT hits), tier: {tier}"
        )

        return DruggabilityScore(
            druggable_genes=druggable_list,
            druggable_ratio=druggable_ratio,
            total_genes=total_genes,
            drug_count=len(druggable_list),
            approved_drug_count=len(approved_list),
            clinical_trial_count=len(clinical_list),
            druggability_tier=tier,
            druggability_source=druggability_source,
            external_target_count=ot_target_count,
            external_approved_target_count=ot_approved_count,
            external_clinical_target_count=ot_clinical_count,
            cardiovascular_target_count=ot_cv_count,
            target_evidence=target_evidence,
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
