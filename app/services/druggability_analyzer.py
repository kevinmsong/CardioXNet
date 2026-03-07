"""Druggability analysis for pathway genes using curated targets plus live target evidence."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)


OPEN_TARGETS_SEARCH_QUERY = """
query SearchTarget($queryString: String!, $drugLimit: Int!) {
  search(
    queryString: $queryString
    entityNames: ["target"]
    page: { index: 0, size: 3 }
  ) {
    hits {
      id
      entity
      object {
        ... on Target {
          approvedSymbol
          approvedName
          tractability {
            label
            modality
            value
          }
          knownDrugs(size: $drugLimit) {
            count
            rows {
              phase
              status
              disease {
                name
              }
              drug {
                id
                name
                maximumClinicalTrialPhase
              }
            }
          }
        }
      }
    }
  }
}
"""

CARDIO_DISEASE_KEYWORDS = (
    "cardio",
    "heart",
    "cardiac",
    "arrhythm",
    "atrial",
    "ventric",
    "myocard",
    "coronary",
    "hypertension",
    "hypertens",
    "ischemi",
    "stroke",
    "thrombo",
    "vascular",
    "fibrillation",
    "heart failure",
    "cardiomyopathy",
)


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
    druggability_source: str = "curated"
    external_target_count: int = 0
    external_approved_target_count: int = 0
    external_clinical_target_count: int = 0
    cardiovascular_target_count: int = 0
    target_evidence: List[Dict[str, Any]] = field(default_factory=list)


class DruggabilityAnalyzer:
    """
    Analyzes pathway druggability using curated target sets plus live therapeutic evidence.

    Default live provider: Open Targets GraphQL API.
    Curated sets are retained as a fallback and for fast coarse screening.
    """

    def __init__(self):
        """Initialize druggability analyzer."""
        self.settings = get_settings()

        # Load curated druggable gene sets
        self.druggable_genes = self._load_druggable_genes()
        self.approved_drug_targets = self._load_approved_drug_targets()
        self.clinical_trial_targets = self._load_clinical_trial_targets()

        # Live evidence configuration
        self.external_druggability_enabled = getattr(
            self.settings.nets, "external_druggability_enabled", True
        )
        self.external_druggability_gene_limit = getattr(
            self.settings.nets, "external_druggability_gene_limit", 8
        )
        self.external_drug_examples_per_gene = getattr(
            self.settings.nets, "external_drug_examples_per_gene", 5
        )
        self.external_druggability_timeout = getattr(
            self.settings.nets, "external_druggability_timeout", 12
        )
        self.opentargets_api_url = getattr(
            self.settings.nets,
            "opentargets_api_url",
            "https://api.platform.opentargets.org/api/v4/graphql",
        )

        self._gene_evidence_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._pathway_score_cache: Dict[tuple, DruggabilityScore] = {}
        self._cache_lock = threading.Lock()

        logger.info(
            "DruggabilityAnalyzer initialized: %s curated druggable genes, %s approved curated targets, "
            "external_live_evidence=%s",
            len(self.druggable_genes),
            len(self.approved_drug_targets),
            self.external_druggability_enabled,
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
            "ADRB1",
            "ADRB2",
            "ADRB3",
            "ADRA1A",
            "ADRA1B",
            "ADRA1D",
            "ADRA2A",
            "ADRA2B",
            "ADRA2C",
            "CHRM2",
            "CHRM3",
            "EDNRA",
            "EDNRB",
            "AGTR1",
            "AGTR2",
            "NPR1",
            "NPR2",
            # Ion channels
            "SCN5A",
            "KCNQ1",
            "KCNH2",
            "KCNJ2",
            "KCNJ11",
            "CACNA1C",
            "CACNA1D",
            "CACNA1G",
            "CACNA1H",
            "HCN4",
            "HCN2",
            # Kinases
            "AKT1",
            "AKT2",
            "MAPK14",
            "MAPK8",
            "MAPK1",
            "MAPK3",
            "GSK3B",
            "ROCK1",
            "ROCK2",
            "PRKAA1",
            "PRKAA2",
            "PRKACA",
            "PRKCA",
            "PRKCB",
            "MTOR",
            "PIK3CA",
            "PIK3CB",
            "PIK3CG",
            "JAK1",
            "JAK2",
            "TYK2",
            "SRC",
            "ABL1",
            "EGFR",
            "PDGFRA",
            "PDGFRB",
            "KIT",
            "FLT3",
            "VEGFR1",
            "VEGFR2",
            "VEGFR3",
            # Nuclear receptors
            "PPARA",
            "PPARD",
            "PPARG",
            "NR3C1",
            "NR3C2",
            "RARA",
            "RARB",
            "RARG",
            "RXRA",
            "RXRB",
            "RXRG",
            "ESRRA",
            "ESRRB",
            "ESRRG",
            "NR1H3",
            "NR1H2",
            # Enzymes
            "ACE",
            "ACE2",
            "ACHE",
            "BCHE",
            "COMT",
            "MAO",
            "MAOA",
            "MAOB",
            "PDE3A",
            "PDE3B",
            "PDE4A",
            "PDE4B",
            "PDE4D",
            "PDE5A",
            "HMGCR",
            "PCSK9",
            "LDLR",
            "APOB",
            "CETP",
            "COX1",
            "COX2",
            "PTGS1",
            "PTGS2",
            "ALOX5",
            "ALOX12",
            "ALOX15",
            "NOS1",
            "NOS2",
            "NOS3",
            "GUCY1A1",
            "GUCY1B1",
            "MMP2",
            "MMP9",
            "MMP1",
            "MMP3",
            "MMP13",
            "CASP3",
            "CASP8",
            "CASP9",
            "PARP1",
            # Transporters
            "SLC22A1",
            "SLC22A2",
            "SLC22A3",
            "ABCB1",
            "ABCC1",
            "ABCC2",
            "ABCG2",
            "SLC6A2",
            "SLC6A3",
            "SLC6A4",
            # Cytokines and growth factors
            "TNF",
            "IL1B",
            "IL6",
            "IL10",
            "IL17A",
            "IFNG",
            "TGFB1",
            "VEGFA",
            "VEGFB",
            "VEGFC",
            "FGF2",
            "PDGFA",
            "PDGFB",
            "IGF1",
            "IGF2",
            "INS",
            "GH1",
            "PRL",
            # Coagulation
            "F2",
            "F7",
            "F9",
            "F10",
            "F11",
            "F12",
            "F13A1",
            "SERPINC1",
            "SERPINE1",
            "PLAT",
            "PLAU",
            "PLG",
            # Lipid metabolism
            "APOA1",
            "APOA2",
            "APOB",
            "APOC2",
            "APOC3",
            "APOE",
            "LCAT",
            "LIPC",
            "LPL",
            "LIPG",
            # Cardiac-specific targets
            "RYR2",
            "ATP2A2",
            "PLN",
            "CASQ2",
            "JPH2",
            "CALM1",
            "MYBPC3",
            "MYH7",
            "TNNT2",
            "TNNI3",
            "TPM1",
            "GRK2",
            "GRK5",
            "ARRB1",
            "ARRB2",
            # Transcription factors (challenging but emerging)
            "NFKB1",
            "RELA",
            "JUN",
            "FOS",
            "MYC",
            "TP53",
            "HIF1A",
            "STAT3",
            "STAT5A",
            "STAT5B",
            "SMAD2",
            "SMAD3",
            "SMAD4",
            "CTNNB1",
            "YAP1",
            "TAZ",
            "NOTCH1",
            "NOTCH2",
        }

        return druggable

    def _load_approved_drug_targets(self) -> Set[str]:
        """Load genes targeted by FDA-approved drugs."""
        return {
            "ADRB1",
            "ADRB2",
            "ACE",
            "AGTR1",
            "CACNA1C",
            "CACNA1D",
            "SLC12A3",
            "SLC12A1",
            "SCNN1A",
            "F2",
            "F10",
            "SERPINC1",
            "PTGS1",
            "P2RY12",
            "ITGB3",
            "HMGCR",
            "GUCY1A1",
            "GUCY1B1",
            "ATP1A1",
            "ATP1A2",
            "ATP1A3",
            "SCN5A",
            "KCNH2",
            "KCNQ1",
        }

    def _load_clinical_trial_targets(self) -> Set[str]:
        """Load genes targeted by drugs in clinical trials."""
        return {
            "SLC5A2",
            "PCSK9",
            "F11",
            "F12",
            "IL1B",
            "IL6",
            "TNF",
            "IL17A",
            "PPARA",
            "PPARD",
            "PPARG",
            "GCG",
            "GLP1R",
            "TGFB1",
            "CTGF",
            "LOXL2",
            "WNT",
            "NOTCH1",
            "YAP1",
        }

    def _is_cardiovascular_disease(self, disease_name: str) -> bool:
        """Return True when a disease label looks cardiovascular."""
        lowered = (disease_name or "").lower()
        return any(keyword in lowered for keyword in CARDIO_DISEASE_KEYWORDS)

    def _select_external_lookup_genes(self, pathway_genes: List[str]) -> List[str]:
        """Prioritize evidence genes for live target lookup while keeping Stage 8 bounded."""
        unique_genes: List[str] = []
        seen: Set[str] = set()
        for gene in pathway_genes:
            normalized = gene.upper()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_genes.append(normalized)

        curated_priority = [
            gene
            for gene in unique_genes
            if gene in self.druggable_genes
            or gene in self.approved_drug_targets
            or gene in self.clinical_trial_targets
        ]
        remaining = [gene for gene in unique_genes if gene not in curated_priority]
        return (curated_priority + remaining)[: self.external_druggability_gene_limit]

    def select_external_lookup_genes(self, pathway_genes: List[str]) -> List[str]:
        """Public wrapper for bounded live therapeutic-target gene selection."""
        return self._select_external_lookup_genes(pathway_genes)

    def _query_open_targets(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch live target evidence from Open Targets for a gene symbol."""
        response = requests.post(
            self.opentargets_api_url,
            json={
                "query": OPEN_TARGETS_SEARCH_QUERY,
                "variables": {
                    "queryString": gene_symbol,
                    "drugLimit": self.external_drug_examples_per_gene,
                },
            },
            timeout=self.external_druggability_timeout,
        )
        response.raise_for_status()

        payload = response.json()
        if payload.get("errors"):
            raise ValueError(payload["errors"][0].get("message", "Open Targets query failed"))

        hits = payload.get("data", {}).get("search", {}).get("hits", [])
        match = None
        for hit in hits:
            target_obj = hit.get("object") or {}
            approved_symbol = (target_obj.get("approvedSymbol") or "").upper()
            if approved_symbol == gene_symbol.upper():
                match = target_obj
                break

        if not match:
            return None

        known_drugs = match.get("knownDrugs", {}) or {}
        rows = known_drugs.get("rows", []) or []
        tractability_rows = match.get("tractability", []) or []
        tractability_labels = [
            f"{row.get('modality')}:{row.get('label')}"
            for row in tractability_rows
            if row.get("value")
        ]

        has_approved_drug = any(
            row.get("label") == "Approved Drug" and row.get("value")
            for row in tractability_rows
        )
        has_clinical_drug = any(
            row.get("label") in {"Advanced Clinical", "Phase 1 Clinical"} and row.get("value")
            for row in tractability_rows
        )

        top_drugs: List[Dict[str, Any]] = []
        cardiovascular_examples = 0
        max_clinical_phase = 0
        for row in rows:
            disease_name = ((row.get("disease") or {}).get("name")) or ""
            phase = row.get("phase") or 0
            max_clinical_phase = max(max_clinical_phase, int(phase))
            is_cardio = self._is_cardiovascular_disease(disease_name)
            if is_cardio:
                cardiovascular_examples += 1
            top_drugs.append(
                {
                    "name": ((row.get("drug") or {}).get("name")) or "Unknown",
                    "drug_id": ((row.get("drug") or {}).get("id")) or "",
                    "disease": disease_name,
                    "phase": phase,
                    "status": row.get("status"),
                    "is_cardiovascular": is_cardio,
                }
            )

        return {
            "gene_symbol": match.get("approvedSymbol", gene_symbol.upper()),
            "approved_name": match.get("approvedName", ""),
            "source": "Open Targets",
            "known_drug_count": known_drugs.get("count", len(rows)) or 0,
            "has_approved_drug": has_approved_drug,
            "has_clinical_drug": has_clinical_drug,
            "has_cardiovascular_evidence": cardiovascular_examples > 0,
            "cardiovascular_example_count": cardiovascular_examples,
            "max_clinical_phase": max_clinical_phase,
            "tractability_labels": tractability_labels,
            "top_drugs": top_drugs[: self.external_drug_examples_per_gene],
        }

    def get_gene_evidence(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """Return cached live evidence for a gene, fetching if necessary."""
        normalized = gene_symbol.upper()
        with self._cache_lock:
            if normalized in self._gene_evidence_cache:
                return self._gene_evidence_cache[normalized]

        evidence: Optional[Dict[str, Any]] = None
        try:
            if self.external_druggability_enabled:
                evidence = self._query_open_targets(normalized)
        except Exception as exc:
            logger.debug("Live therapeutic target lookup failed for %s: %s", normalized, exc)

        with self._cache_lock:
            self._gene_evidence_cache[normalized] = evidence
        return evidence

    def get_cached_gene_evidence(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """Return cached therapeutic evidence without triggering a new lookup."""
        return self._gene_evidence_cache.get(gene_symbol.upper())

    def prefetch_gene_evidence(self, gene_symbols: List[str], max_workers: int = 4) -> None:
        """
        Warm live therapeutic-evidence cache for a deduplicated gene set.

        This avoids repeated Open Targets lookups for the same genes across
        multiple top-ranked pathways during Stage 8.
        """
        if not self.external_druggability_enabled:
            return

        unique_genes: List[str] = []
        seen: Set[str] = set()
        for gene_symbol in gene_symbols:
            normalized = gene_symbol.upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            if normalized in self._gene_evidence_cache:
                continue
            unique_genes.append(normalized)

        if not unique_genes:
            return

        worker_count = min(len(unique_genes), max(1, max_workers))
        logger.info("Prefetching live therapeutic evidence for %s genes", len(unique_genes))

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(self.get_gene_evidence, gene_symbol) for gene_symbol in unique_genes]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    logger.debug("Live therapeutic evidence prefetch failed: %s", exc)

    def calculate_druggability_score(
        self, pathway_genes: List[str], use_live_lookup: Optional[bool] = None
    ) -> DruggabilityScore:
        """
        Calculate druggability score for pathway.

        Uses curated targets as the floor and live Open Targets evidence where available.
        """
        if not pathway_genes:
            return DruggabilityScore(
                druggable_genes=[],
                druggable_ratio=0.0,
                total_genes=0,
                drug_count=0,
                approved_drug_count=0,
                clinical_trial_count=0,
                druggability_tier="low",
            )

        if use_live_lookup is None:
            use_live_lookup = self.external_druggability_enabled

        pathway_cache_key = (
            tuple(sorted({gene.upper() for gene in pathway_genes if gene})),
            bool(use_live_lookup),
        )
        with self._cache_lock:
            cached_score = self._pathway_score_cache.get(pathway_cache_key)
        if cached_score is not None:
            return cached_score

        pathway_set = {gene.upper() for gene in pathway_genes}
        curated_druggable = set(pathway_set & self.druggable_genes)
        curated_approved = set(pathway_set & self.approved_drug_targets)
        curated_clinical = set(pathway_set & self.clinical_trial_targets)

        live_target_evidence: List[Dict[str, Any]] = []
        if use_live_lookup:
            for gene_symbol in self._select_external_lookup_genes(pathway_genes):
                evidence = self.get_gene_evidence(gene_symbol)
                if evidence:
                    live_target_evidence.append(evidence)

        live_druggable = {
            evidence["gene_symbol"]
            for evidence in live_target_evidence
            if evidence.get("known_drug_count", 0) > 0 or evidence.get("tractability_labels")
        }
        live_approved = {
            evidence["gene_symbol"]
            for evidence in live_target_evidence
            if evidence.get("has_approved_drug")
        }
        live_clinical = {
            evidence["gene_symbol"]
            for evidence in live_target_evidence
            if evidence.get("has_clinical_drug")
        }
        live_cardiovascular = {
            evidence["gene_symbol"]
            for evidence in live_target_evidence
            if evidence.get("has_cardiovascular_evidence")
        }

        druggable = sorted(curated_druggable | live_druggable)
        approved_targets = curated_approved | live_approved
        clinical_targets = curated_clinical | live_clinical
        druggable_ratio = len(druggable) / len(pathway_genes) if pathway_genes else 0.0

        if len(approved_targets) >= 2 or len(live_cardiovascular) >= 2:
            tier = "high"
        elif len(approved_targets) >= 1 or len(clinical_targets) >= 1 or druggable_ratio >= 0.2:
            tier = "medium"
        else:
            tier = "low"

        logger.debug(
            "Druggability: %s/%s druggable (%s approved targets, %s clinical targets, %s live targets), tier=%s",
            len(druggable),
            len(pathway_genes),
            len(approved_targets),
            len(clinical_targets),
            len(live_target_evidence),
            tier,
        )

        score = DruggabilityScore(
            druggable_genes=druggable,
            druggable_ratio=druggable_ratio,
            total_genes=len(pathway_genes),
            drug_count=len(druggable),
            approved_drug_count=len(approved_targets),
            clinical_trial_count=len(clinical_targets),
            druggability_tier=tier,
            druggability_source="Open Targets + curated" if live_target_evidence else "curated",
            external_target_count=len(live_druggable),
            external_approved_target_count=len(live_approved),
            external_clinical_target_count=len(live_clinical),
            cardiovascular_target_count=len(live_cardiovascular),
            target_evidence=live_target_evidence,
        )
        with self._cache_lock:
            self._pathway_score_cache[pathway_cache_key] = score
        return score

    def annotate_pathways_with_druggability(self, pathways: List[Any]) -> List[Any]:
        """Preserve API compatibility for modular stages."""
        for pathway in pathways:
            pathway_genes = getattr(pathway, "evidence_genes", [])
            self.calculate_druggability_score(pathway_genes)

        logger.info("Annotated %s pathways with druggability data", len(pathways))
        return pathways

    def filter_by_druggability(
        self, pathways: List[Any], min_druggable_ratio: float = 0.1
    ) -> List[Any]:
        """Filter pathways by minimum druggability ratio."""
        filtered = []
        for pathway in pathways:
            druggable_ratio = getattr(pathway, "druggable_ratio", 0.0)
            if druggable_ratio >= min_druggable_ratio:
                filtered.append(pathway)

        logger.info(
            "Druggability filtering: %s/%s pathways with >=%s%% druggable genes",
            len(filtered),
            len(pathways),
            int(min_druggable_ratio * 100),
        )
        return filtered
