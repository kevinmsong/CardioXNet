"""Service initialization and registration."""

from app.core.service_registry import register_service
from app.core.config import get_settings

# Import service classes
from .gene_validator import GeneValidator
from .api_client import APIClient
from .string_client import STRINGClient
from .gprofiler_client import GProfilerClient
from .reactome_client import ReactomeClient
from .input_validator import InputValidator
from .functional_neighborhood import FunctionalNeighborhoodBuilder
from .primary_pathway_analyzer import PrimaryPathwayAnalyzer
from .pubmed_client import PubMedClient
from .literature_expansion import LiteratureExpander
from .secondary_pathway_analyzer import SecondaryPathwayAnalyzer
from .pathway_aggregator_rigorous import RigorousPathwayAggregator
from .nes_scorer import NESScorer
from .topology_analyzer import TopologyAnalyzer
from .literature_miner import LiteratureMiner
from .hypothesis_validator import HypothesisValidator
from .report_generator import ReportGenerator
from .tissue_expression_validator import TissueExpressionValidator
from .permutation_tester import PermutationTester
from .druggability_analyzer import DruggabilityAnalyzer
from .seed_gene_tracer import SeedGeneTracer
from .hpa_client import HPAClient
from .epigenomic_client import EpigenomicClient
from .semantic_filter import SemanticFilter
from .modular_pipeline import ModularCardioXNetPipeline


def initialize_services():
    """Initialize and register all services with lazy loading."""
    settings = get_settings()

    # Core validators
    register_service("input_validator", InputValidator)
    register_service("gene_validator", GeneValidator)

    # API clients
    register_service("api_client", APIClient)
    register_service("string_client", STRINGClient)
    register_service("gprofiler_client", GProfilerClient)
    register_service("reactome_client", ReactomeClient)
    register_service("pubmed_client", PubMedClient)
    register_service("hpa_client", HPAClient)
    register_service("epigenomic_client", EpigenomicClient)

    # Analysis components
    register_service("functional_neighborhood_builder", FunctionalNeighborhoodBuilder)
    register_service("primary_pathway_analyzer", PrimaryPathwayAnalyzer)
    register_service("secondary_pathway_analyzer", SecondaryPathwayAnalyzer)
    register_service("pathway_aggregator", RigorousPathwayAggregator)
    register_service("nes_scorer", NESScorer)
    register_service("topology_analyzer", TopologyAnalyzer)
    register_service("literature_miner", LiteratureMiner)
    register_service("literature_expander", LiteratureExpander)

    # Validation and testing
    register_service("hypothesis_validator", HypothesisValidator)
    register_service("tissue_expression_validator", TissueExpressionValidator)
    register_service("permutation_tester", PermutationTester)
    register_service("semantic_filter", SemanticFilter)

    # Advanced analyzers (required)
    register_service("druggability_analyzer", DruggabilityAnalyzer)
    register_service("seed_gene_tracer", SeedGeneTracer)

    # Report generation
    register_service("report_generator", ReportGenerator)

    # Pipeline
    register_service("pipeline", ModularCardioXNetPipeline)


# Initialize services on import
# initialize_services()  # Commented out to prevent double initialization
