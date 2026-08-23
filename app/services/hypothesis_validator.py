"""Hypothesis validation service for comprehensive evidence scoring."""

import logging
from typing import Dict, List, Optional
import math

from app.models import ScoredPathway, GeneInfo
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class HypothesisValidator:
    """Validates and scores hypotheses based on multiple evidence types (Stage 4a).
    
    Scientific Rigor Enhancements:
    - Multi-evidence composite scoring (statistical + replication + literature + network + novelty)
    - Statistical strength combines p-value significance and evidence count robustness
    - Replication support rewards cross-database validation (minimum 2 sources required)
    - Literature evidence integrates citation count and relevance scoring
    - Network evidence evaluates key mediating nodes and connectivity patterns
    - Novelty scoring penalizes high seed gene overlap to prioritize discovery
    - Normalized weighting ensures balanced contribution from all evidence types
    """
    
    def __init__(self):
        """Initialize hypothesis validator."""
        self.settings = get_settings()
        logger.info("HypothesisValidator initialized - Enhanced multi-evidence validation")
    
    # Corpus size at which a pathway is considered fully saturated in the
    # literature. log-scaled, so 1 paper -> 0.10, 10 -> 0.33, 100 -> 0.67,
    # 1000 -> 1.00. Chosen so that the metric keeps resolution across the
    # 0-1000 range where observed intersection corpora actually fall.
    SATURATION_CEILING = 1000

    # A pathway concept needs at least this many PubMed records of its own before
    # an empty intersection can be read as a genuine gap rather than a name that
    # PubMed cannot match.
    MIN_CONCEPT_CORPUS = 20

    # Corpus size substituted when novelty cannot be verified. Chosen at the
    # Emerging/Novel boundary so unverifiable pathways are neither promoted to
    # the top of the ranking nor silently discarded.
    UNVERIFIED_CORPUS_PROXY = 60

    # The seed genes must have at least this many PubMed records in the chosen
    # disease context before any per-pathway novelty claim is meaningful. Below
    # it, a zero intersection says nothing about the pathway.
    MIN_SEED_DISEASE_CORPUS = 100

    @staticmethod
    def _citation_relevance(citation) -> float:
        """Relevance of a citation, accepting both Citation objects and dicts."""
        if isinstance(citation, dict):
            return float(citation.get('relevance_score', citation.get('relevance', 0.0)) or 0.0)
        return float(getattr(citation, 'relevance_score', 0.0) or 0.0)

    def calculate_validation_score(
        self,
        hypothesis: ScoredPathway,
        literature_citations: List,
        network_analysis: Dict,
        seed_genes: List[GeneInfo],
        pubmed_hit_count: Optional[int] = None,
        concept_hit_count: Optional[int] = None,
        seed_disease_corpus: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Calculate comprehensive validation score combining multiple evidence types.
        
        Validation Score Components:
        1. Statistical Strength (0-0.3): Based on P-value and evidence count
        2. Replication Support (0-0.2): Based on support count across primaries
        3. Literature Evidence (0-0.2): Based on citation count and relevance
        4. Network Evidence (0-0.2): Based on key mediating nodes
        5. Novelty Score (0-0.1): Based on seed gene overlap
        
        Args:
            hypothesis: Scored pathway hypothesis
            literature_citations: List of literature citations
            network_analysis: Network topology analysis results
            seed_genes: Original seed genes
            
        Returns:
            Dictionary with validation score and component breakdown
        """
        scores = {}
        
        # 1. Statistical Strength (0-0.3)
        p_adj = hypothesis.aggregated_pathway.pathway.p_adj if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.p_adj
        evidence_count = hypothesis.aggregated_pathway.pathway.evidence_count if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.evidence_count
        
        # P-value component (0-0.15)
        if p_adj > 0:
            log_p = min(-math.log10(p_adj), 50)
            p_score = min(log_p / 50.0, 1.0) * 0.15
        else:
            p_score = 0.15
        
        # Evidence count component (0-0.15)
        evidence_score = min(evidence_count / 20.0, 1.0) * 0.15
        
        scores['statistical_strength'] = p_score + evidence_score
        
        # 2. Replication Support (0-0.2)
        support_count = hypothesis.aggregated_pathway.support_count if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.support_count
        support_score = min(support_count / 5.0, 1.0) * 0.2
        scores['replication_support'] = support_score
        
        # ── 3. Literature Evidence (0-0.15) ────────────────────────────────
        # Uses only *relevance-filtered* citations (relevance ≥ 0.15) so that
        # incidental PubMed hits don't inflate the literature coverage score.
        RELEVANCE_THRESHOLD = 0.15
        if literature_citations:
            relevant_cits = [
                c for c in literature_citations
                if self._citation_relevance(c) >= RELEVANCE_THRESHOLD
            ]
            n_relevant = len(relevant_cits)

            # Average relevance of relevant-only citations (0-0.075)
            if relevant_cits:
                avg_rel = sum(
                    self._citation_relevance(c) for c in relevant_cits
                ) / n_relevant
                relevance_score = avg_rel * 0.075
            else:
                relevance_score = 0.0

            # Normalised citation count (0-0.075); saturates at 10 relevant hits
            citation_score = min(n_relevant / 10.0, 1.0) * 0.075
            scores['literature_evidence'] = citation_score + relevance_score

            # Store for novelty calculation below
            scores['_n_relevant_citations'] = n_relevant
        else:
            scores['literature_evidence'] = 0.0
            scores['_n_relevant_citations'] = 0

        # ── 4. Network Evidence (0-0.2) ─────────────────────────────────────
        if network_analysis and 'key_nodes' in network_analysis:
            key_nodes = network_analysis['key_nodes']
            mediator_count = sum(1 for node in key_nodes if node.get('role') == 'mediator')
            mediator_score = min(mediator_count / 5.0, 1.0) * 0.1
            if key_nodes:
                avg_centrality = sum(node.get('betweenness_centrality', 0) for node in key_nodes) / len(key_nodes)
                centrality_score = min(avg_centrality / 0.3, 1.0) * 0.1
            else:
                centrality_score = 0.0
            scores['network_evidence'] = mediator_score + centrality_score
        else:
            scores['network_evidence'] = 0.0

        # ── 5. Literature-Based Novelty (0-0.15) ────────────────────────────
        # "Novelty" = the pathway is enriched by the seed gene network BUT has
        # little published evidence specifically at the intersection of
        # (pathway × seed genes × disease context).
        #
        # literature_saturation = log(relevant_cits + 1) / log(10 + 1)
        #   → 0 relevant cits  → saturation = 0  → novelty = 1.0 (highly novel)
        #   → 10 relevant cits → saturation ≈ 1  → novelty = 0.0 (well-studied)
        n_relevant = scores.pop('_n_relevant_citations', 0)

        # Saturation is computed from the TOTAL number of PubMed records at the
        # (pathway x seed genes x disease) intersection, not from the number of
        # abstracts actually downloaded. Retrieval is capped at a few dozen
        # records, so counting downloaded citations makes saturation hit its
        # ceiling for every pathway and destroys the novelty signal entirely.
        if pubmed_hit_count is not None and pubmed_hit_count >= 0:
            corpus_size = pubmed_hit_count
            saturation_basis = 'pubmed_corpus'

            # An empty intersection only counts as evidence of a gap if the
            # pathway concept is searchable in the first place. Identifier-heavy
            # names ("TGFBR3 PTM regulation", "GAB1 signalosome") match no
            # abstracts at all, so their zero is an artefact of the vocabulary,
            # not a finding. Without this check those pathways take the top of
            # the ranking on maximal novelty they have not earned.
            # Novelty is only interpretable when the seed genes have a
            # literature footprint in this disease to begin with. If they do
            # not, every pathway returns zero records and every pathway looks
            # maximally novel -- absence of literature about the seeds, not a
            # discovery.
            #
            # This is what the negative controls exposed: olfactory-receptor and
            # random gene panels produced *more* Highly Novel calls (13/13 and
            # 21/23) than any real cardiovascular panel, purely because nobody
            # has written about those genes in heart failure.
            if (seed_disease_corpus is not None
                    and 0 <= seed_disease_corpus < self.MIN_SEED_DISEASE_CORPUS):
                scores['novelty_confidence'] = 'ungrounded_seeds'
                scores['seed_disease_corpus'] = seed_disease_corpus
                corpus_size = max(corpus_size, self.UNVERIFIED_CORPUS_PROXY)
                saturation_basis = 'ungrounded_seeds'
            elif pubmed_hit_count == 0 and concept_hit_count is not None and concept_hit_count >= 0:
                if concept_hit_count < self.MIN_CONCEPT_CORPUS:
                    scores['novelty_confidence'] = 'unverified'
                    scores['concept_hit_count'] = concept_hit_count
                    # Treat as mid-corpus rather than unstudied: the claim is
                    # "we cannot tell", not "nobody has looked".
                    corpus_size = self.UNVERIFIED_CORPUS_PROXY
                    saturation_basis = 'unverified_concept'
                else:
                    scores['novelty_confidence'] = 'verified_gap'
                    scores['concept_hit_count'] = concept_hit_count
        else:
            # The corpus size was never measured for this pathway -- either the
            # count lookup failed or the pathway fell outside the literature
            # mining window. Falling back to the retrieved citation count would
            # report 0 records and hand the pathway maximal novelty it has not
            # earned, floating unmeasured pathways to the top of the ranking.
            corpus_size = max(n_relevant, self.UNVERIFIED_CORPUS_PROXY)
            saturation_basis = 'not_measured'
            scores['novelty_confidence'] = 'unverified'

        literature_saturation = math.log10(corpus_size + 1) / math.log10(self.SATURATION_CEILING + 1)
        literature_saturation = max(0.0, min(literature_saturation, 1.0))
        literature_novelty = 1.0 - literature_saturation
        scores['pubmed_hit_count'] = corpus_size
        scores['saturation_basis'] = saturation_basis

        # Secondary novelty signal: low seed gene overlap in pathway evidence
        pathway_genes = set(
            hypothesis.aggregated_pathway.pathway.evidence_genes
            if hasattr(hypothesis, 'aggregated_pathway') else []
        )
        seed_gene_symbols = {gene.symbol for gene in seed_genes}
        if pathway_genes:
            overlap_ratio = len(pathway_genes & seed_gene_symbols) / len(pathway_genes)
            gene_novelty = 1.0 - min(overlap_ratio * 2, 1.0)  # penalise heavy overlap
        else:
            gene_novelty = 0.5

        # Composite novelty (literature novelty weighted 2:1 over gene novelty)
        composite_novelty = (2 * literature_novelty + gene_novelty) / 3.0
        scores['novelty_score'] = composite_novelty * 0.15
        scores['literature_saturation'] = round(literature_saturation, 4)
        scores['n_relevant_citations'] = n_relevant
        # When the seed genes have no literature footprint in this disease, the
        # tier is not a weak result -- it is an undefined one, and reporting it
        # on the same scale as a grounded call invites exactly the
        # misinterpretation the negative controls produced. It is labelled as
        # undefined instead.
        if scores.get('novelty_confidence') == 'ungrounded_seeds':
            scores['novelty_tier'] = 'Ungrounded'
        else:
            scores['novelty_tier'] = (
                'Highly Novel' if composite_novelty >= 0.80 else
                'Novel'        if composite_novelty >= 0.55 else
                'Emerging'     if composite_novelty >= 0.30 else
                'Established'
            )

        # ── Discovery Score (NES × novelty) ─────────────────────────────────
        # Surfaces pathways that are strongly enriched AND under-reported -
        # the primary scientific goal of this tool.
        nes = hypothesis.nes_score if hasattr(hypothesis, 'nes_score') else 0.0
        scores['discovery_score'] = round(nes * composite_novelty, 4)

        # ── Total validation score ───────────────────────────────────────────
        component_keys = [
            'statistical_strength', 'replication_support',
            'literature_evidence', 'network_evidence', 'novelty_score',
        ]
        total_score = sum(scores.get(k, 0) for k in component_keys)
        scores['total_validation_score'] = total_score

        if total_score >= 0.7:
            scores['confidence_level'] = 'high'
        elif total_score >= 0.5:
            scores['confidence_level'] = 'medium'
        else:
            scores['confidence_level'] = 'low'

        logger.debug(
            f"Validation: total={total_score:.3f} "
            f"stat={scores['statistical_strength']:.3f} "
            f"rep={scores['replication_support']:.3f} "
            f"lit={scores['literature_evidence']:.3f} "
            f"net={scores['network_evidence']:.3f} "
            f"novelty={composite_novelty:.3f} "
            f"discovery={scores['discovery_score']:.3f}"
        )
        return scores
    
