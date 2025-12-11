"""Fast service initialization - eager loading, no lazy initialization."""

from app.core.service_registry import ServiceRegistry

# Import all service classes
from app.services.gene_validator import GeneValidator
from app.services.string_client import STRINGClient
from app.services.gprofiler_client import GProfilerClient
from app.services.reactome_client import ReactomeClient
from app.services.input_validator import InputValidator
from app.services.functional_neighborhood import FunctionalNeighborhoodBuilder
from app.services.primary_pathway_analyzer import PrimaryPathwayAnalyzer
from app.services.pubmed_client import PubMedClient
from app.services.literature_expansion import LiteratureExpander
from app.services.secondary_pathway_analyzer import SecondaryPathwayAnalyzer
from app.services.pathway_aggregator_rigorous import RigorousPathwayAggregator
from app.services.nes_scorer import NESScorer
from app.services.topology_analyzer import TopologyAnalyzer
from app.services.literature_miner import LiteratureMiner
from app.services.hypothesis_validator import HypothesisValidator
from app.services.report_generator import ReportGenerator
from app.services.tissue_expression_validator import TissueExpressionValidator
from app.services.permutation_tester import PermutationTester
from app.services.druggability_analyzer import DruggabilityAnalyzer
from app.services.seed_gene_tracer import SeedGeneTracer
from app.services.hpa_client import HPAClient
from app.services.epigenomic_client import EpigenomicClient
from app.services.semantic_filter import SemanticFilter
from app.services.pipeline import Pipeline


# Global service registry
_services = {}


def initialize_services_fast():
    """
    Initialize ALL services eagerly - no lazy loading.
    All services are required, instantiated immediately.
    Fail fast if any service fails to initialize.
    """
    global _services
    
    # Clear existing services
    _services.clear()
    
    # Instantiate all services immediately
    _services = {
        # Core validators
        "input_validator": lambda: InputValidator(),
        "gene_validator": lambda: GeneValidator(),
        
        # API clients
        "string_client": lambda: STRINGClient(),
        "gprofiler_client": lambda: GProfilerClient(),
        "reactome_client": lambda: ReactomeClient(),
        "pubmed_client": lambda: PubMedClient(),
        "hpa_client": lambda: HPAClient(),
        "epigenomic_client": lambda: EpigenomicClient(),
        
        # Analysis components - ALL required
        "functional_neighborhood_builder": lambda: FunctionalNeighborhoodBuilder(),
        "primary_pathway_analyzer": lambda: PrimaryPathwayAnalyzer(),
        "secondary_pathway_analyzer": lambda: SecondaryPathwayAnalyzer(),
        "pathway_aggregator": lambda: RigorousPathwayAggregator(),
        "nes_scorer": lambda: NESScorer(),
        "topology_analyzer": lambda: TopologyAnalyzer(),
        "literature_miner": lambda: LiteratureMiner(),
        "literature_expander": lambda: LiteratureExpander(),
        
        # Validation and testing - ALL required
        "hypothesis_validator": lambda: HypothesisValidator(),
        "tissue_expression_validator": lambda: TissueExpressionValidator(),
        "permutation_tester": lambda: PermutationTester(),
        "semantic_filter": lambda: SemanticFilter(),
        
        # Advanced analyzers - ALL required
        "druggability_analyzer": lambda: DruggabilityAnalyzer(),
        "seed_gene_tracer": lambda: SeedGeneTracer(),
        
        # Report generation
        "report_generator": lambda: ReportGenerator(),
        
        # Pipeline
        "pipeline": lambda: Pipeline()
    }
    
    return _services


def get_service_fast(name: str):
    """
    Get service by name.
    No lazy loading - service must exist.
    Fail fast if service not found.
    """
    if name not in _services:
        raise RuntimeError(
            f"Service '{name}' not found. "
            f"Did you call initialize_services_fast()? "
            f"Available services: {list(_services.keys())}"
        )
    return _services[name]()


def get_all_services():
    """Get all initialized services."""
    return _services.copy()
