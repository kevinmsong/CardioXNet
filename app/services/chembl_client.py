"""ChEMBL REST API client for live druggability lookups."""

import logging
import requests
from typing import Dict, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


@dataclass
class ChEMBLDruggability:
    """Live druggability result from ChEMBL."""
    gene_symbol: str
    target_chembl_id: Optional[str]
    max_phase: int        # 0=not druggable, 1-3=clinical, 4=approved
    drug_count: int
    target_type: Optional[str]


class ChEMBLClient:
    """
    Queries the ChEMBL REST API for real-time druggability information.

    ChEMBL is an open-access chemical database maintained by EMBL-EBI.
    API documentation: https://www.ebi.ac.uk/chembl/api/data/docs
    No authentication required.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._cache: Dict[str, ChEMBLDruggability] = {}
        logger.info("ChEMBLClient initialized (live API)")

    def lookup_gene(self, gene_symbol: str, timeout: int = 10) -> Optional[ChEMBLDruggability]:
        """
        Look up a gene symbol in ChEMBL to determine druggability.

        Args:
            gene_symbol: HGNC gene symbol (e.g., 'ADRB1')
            timeout: Request timeout in seconds

        Returns:
            ChEMBLDruggability with max_phase and drug count, or None on failure
        """
        key = gene_symbol.upper()
        if key in self._cache:
            return self._cache[key]

        try:
            # Step 1: Find target by gene symbol via target search
            url = f"{BASE_URL}/target/search.json"
            params = {
                "q": gene_symbol,
                "limit": 5,
            }
            response = self.session.get(url, params=params, timeout=timeout)
            if response.status_code != 200:
                logger.debug(f"ChEMBL target search returned {response.status_code} for {gene_symbol}")
                return self._cache_and_return(key, None)

            data = response.json()
            targets = data.get("targets", [])
            if not targets:
                logger.debug(f"ChEMBL: no targets found for {gene_symbol}")
                return self._cache_and_return(key, None)

            # Find best match: prefer SINGLE PROTEIN targets with gene_name match
            best_target = None
            for t in targets:
                pref_name = t.get("pref_name", "").upper()
                target_type = t.get("target_type", "")
                if (
                    gene_symbol.upper() in pref_name
                    and target_type in ("SINGLE PROTEIN", "PROTEIN FAMILY")
                ):
                    best_target = t
                    break

            if best_target is None:
                best_target = targets[0]

            target_id = best_target.get("target_chembl_id")
            target_type = best_target.get("target_type", "")

            if not target_id:
                return self._cache_and_return(key, None)

            # Step 2: Get drug activities for this target
            url2 = f"{BASE_URL}/activity.json"
            params2 = {
                "target_chembl_id": target_id,
                "limit": 1,
                "assay_type": "B",  # Binding assays only
            }
            response2 = self.session.get(url2, params=params2, timeout=timeout)
            drug_count = 0
            if response2.status_code == 200:
                data2 = response2.json()
                drug_count = data2.get("page_meta", {}).get("total_count", 0)

            # Step 3: Get max clinical phase from molecule targets
            url3 = f"{BASE_URL}/mechanism.json"
            params3 = {
                "target_chembl_id": target_id,
                "limit": 25,
            }
            max_phase = 0
            response3 = self.session.get(url3, params=params3, timeout=timeout)
            if response3.status_code == 200:
                data3 = response3.json()
                mechanisms = data3.get("mechanisms", [])
                for mech in mechanisms:
                    phase = mech.get("max_phase", 0) or 0
                    if phase > max_phase:
                        max_phase = phase

            result = ChEMBLDruggability(
                gene_symbol=gene_symbol,
                target_chembl_id=target_id,
                max_phase=max_phase,
                drug_count=drug_count,
                target_type=target_type,
            )
            logger.debug(
                f"ChEMBL {gene_symbol}: target={target_id}, max_phase={max_phase}, "
                f"drug_count={drug_count}, type={target_type}"
            )
            return self._cache_and_return(key, result)

        except requests.exceptions.Timeout:
            logger.debug(f"ChEMBL API timeout for {gene_symbol}")
            return self._cache_and_return(key, None)
        except Exception as e:
            logger.debug(f"ChEMBL lookup error for {gene_symbol}: {e}")
            return self._cache_and_return(key, None)

    def _cache_and_return(self, key: str, result: Optional[ChEMBLDruggability]) -> Optional[ChEMBLDruggability]:
        self._cache[key] = result
        return result

    def batch_lookup(self, gene_symbols: list, timeout: int = 10) -> Dict[str, ChEMBLDruggability]:
        """Look up multiple genes sequentially with caching."""
        results = {}
        for gene in gene_symbols:
            result = self.lookup_gene(gene, timeout=timeout)
            if result:
                results[gene.upper()] = result
        logger.info(f"ChEMBL batch: {len(results)}/{len(gene_symbols)} genes resolved")
        return results

    def classify_tier(self, result: Optional[ChEMBLDruggability]) -> str:
        """
        Classify ChEMBL result into druggability tier.

        Returns: 'high' (FDA approved, phase 4), 'medium' (clinical phase 1-3),
                 'low' (druggable by target type), or 'unknown'
        """
        if result is None:
            return "unknown"

        if result.max_phase >= 4:
            return "high"
        elif result.max_phase >= 1:
            return "medium"
        elif result.target_type in ("SINGLE PROTEIN", "PROTEIN FAMILY") and result.drug_count > 0:
            return "low"
        elif result.target_type in ("GPCR", "ION CHANNEL", "KINASE", "NUCLEAR RECEPTOR"):
            return "low"
        return "unknown"
