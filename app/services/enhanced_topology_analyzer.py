"""
Enhanced Topology Analyzer with gtGMM integration (Stage 7).

This module integrates gtGMM for advanced topological data analysis
of the functional neighborhood around seed genes and pathways.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Any
import time

from app.services.gtgmm_analyzer import GTGMMNetworkAnalyzer, extract_hub_genes, get_functional_modules
from app.services.string_client import STRINGClient
from app.core.config import get_settings
from app.models import FunctionalNeighborhood

logger = logging.getLogger(__name__)


class EnhancedTopologyAnalyzer:
    """
    Advanced network topology analysis with gtGMM integration.
    
    Performs TDA (Topological Data Analysis) on gene networks to identify:
    - Hub genes and keystone proteins
    - Functional modules/clusters
    - Network organization and centrality measures
    - Small-world properties
    """
    
    def __init__(self):
        """Initialize enhanced topology analyzer."""
        self.settings = get_settings()
        self.string_client = STRINGClient()
        self.gmm_analyzer = GTGMMNetworkAnalyzer(
            max_components=min(8, self.settings.nets.top_hypotheses_count),
            min_components=max(2, self.settings.nets.top_hypotheses_count // 3),
            resolution=500,
            sigma=None  # Auto-optimize
        )
        logger.info("EnhancedTopologyAnalyzer initialized with gtGMM")
    
    def analyze_functional_neighborhood_topology(
        self,
        fn: FunctionalNeighborhood,
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze the topology of the functional neighborhood.
        
        Args:
            fn: Functional neighborhood from Stage 1
            gene_symbols: Optional mapping of gene IDs to symbols
            
        Returns:
            Topology analysis results including hub genes and modules
        """
        logger.info(f"Analyzing topology of functional neighborhood with {fn.size} genes")
        start_time = time.time()
        
        try:
            # Get adjacency matrix from STRING interactions
            adjacency_matrix = self._build_adjacency_matrix(fn)
            
            # Run topology analysis
            results = self.gmm_analyzer.analyze_network_topology(
                genes=fn.seed_genes + fn.neighbors,
                adjacency_matrix=adjacency_matrix,
                gene_symbols=gene_symbols
            )
            
            # Extract meaningful results
            hub_genes = extract_hub_genes(results, top_n=min(10, fn.size // 2))
            modules = get_functional_modules(results)
            
            elapsed = time.time() - start_time
            logger.info(f"Topology analysis complete: {len(hub_genes)} hubs, {len(modules)} modules ({elapsed:.2f}s)")
            
            return {
                'hub_genes': hub_genes,
                'modules': modules,
                'metrics': results['metrics'].__dict__ if hasattr(results['metrics'], '__dict__') else results['metrics'],
                'nodes': [n.to_dict() if hasattr(n, 'to_dict') else n.__dict__ for n in results['nodes']],
                'components': [c.to_dict() if hasattr(c, 'to_dict') else c.__dict__ for c in results['components']],
                'processing_time_seconds': elapsed
            }
        except Exception as e:
            logger.error(f"Error analyzing functional neighborhood topology: {e}")
            import traceback
            traceback.print_exc()
            return {
                'hub_genes': [],
                'modules': [],
                'metrics': {},
                'error': str(e)
            }
    
    def analyze_pathway_network(
        self,
        pathway_genes: List[str],
        fn: FunctionalNeighborhood,
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze topology of genes within a specific pathway.
        
        Args:
            pathway_genes: Genes in the pathway
            fn: Full functional neighborhood for context
            gene_symbols: Optional gene symbol mapping
            
        Returns:
            Topology metrics specific to this pathway
        """
        logger.info(f"Analyzing pathway-specific topology for {len(pathway_genes)} genes")
        start_time = time.time()
        
        try:
            # Get adjacency matrix for pathway genes
            all_genes = fn.seed_genes + fn.neighbors
            pathway_gene_indices = [all_genes.index(g) for g in pathway_genes if g in all_genes]
            
            # Build full adjacency matrix
            full_adj = self._build_adjacency_matrix(fn)
            
            # Extract submatrix for pathway genes
            pathway_adj = full_adj[np.ix_(pathway_gene_indices, pathway_gene_indices)]
            
            # Run topology analysis
            results = self.gmm_analyzer.analyze_network_topology(
                genes=pathway_genes,
                adjacency_matrix=pathway_adj,
                gene_symbols=gene_symbols
            )
            
            hub_genes = extract_hub_genes(results, top_n=min(5, len(pathway_genes) // 3))
            
            elapsed = time.time() - start_time
            logger.info(f"Pathway topology analysis complete: {len(hub_genes)} hubs ({elapsed:.2f}s)")
            
            return {
                'pathway_size': len(pathway_genes),
                'hub_genes': hub_genes,
                'metrics': results['metrics'].__dict__ if hasattr(results['metrics'], '__dict__') else results['metrics'],
                'processing_time_seconds': elapsed
            }
        except Exception as e:
            logger.error(f"Error analyzing pathway network: {e}")
            return {'error': str(e)}
    
    def _build_adjacency_matrix(self, fn: FunctionalNeighborhood) -> np.ndarray:
        """
        Build adjacency matrix from functional neighborhood.
        
        Args:
            fn: Functional neighborhood with interactions
            
        Returns:
            NxN adjacency matrix
        """
        all_genes = fn.seed_genes + fn.neighbors
        n = len(all_genes)
        
        # Initialize matrix
        adj = np.zeros((n, n))
        
        # Build gene index mapping
        gene_index = {gene: idx for idx, gene in enumerate(all_genes)}
        
        # Fill matrix from interactions
        for interaction in fn.interactions:
            if interaction.gene1 in gene_index and interaction.gene2 in gene_index:
                i = gene_index[interaction.gene1]
                j = gene_index[interaction.gene2]
                adj[i, j] = interaction.score
                adj[j, i] = interaction.score
        
        logger.debug(f"Built adjacency matrix {n}x{n} with {np.count_nonzero(adj)} non-zero entries")
        return adj
    
    def get_topology_summary(self, topology_results: Dict[str, Any]) -> str:
        """
        Get a text summary of topology analysis results.
        
        Args:
            topology_results: Results from topology analysis
            
        Returns:
            Human-readable summary
        """
        summary = "Network Topology Analysis Summary\n"
        summary += "=" * 50 + "\n"
        
        if 'hub_genes' in topology_results and topology_results['hub_genes']:
            summary += f"\nTop Hub Genes ({len(topology_results['hub_genes'])}):\n"
            for hub in topology_results['hub_genes'][:5]:
                summary += f"  - {hub['gene_symbol']}: score={hub['hub_score']:.3f}\n"
        
        if 'modules' in topology_results and topology_results['modules']:
            summary += f"\nFunctional Modules ({len(topology_results['modules'])}):\n"
            for module in topology_results['modules']:
                summary += f"  - Module {module['module_id']}: {module['size']} genes\n"
        
        if 'metrics' in topology_results and topology_results['metrics']:
            summary += "\nTopology Metrics:\n"
            metrics = topology_results['metrics']
            for key, value in metrics.items():
                if isinstance(value, float):
                    summary += f"  - {key}: {value:.3f}\n"
                else:
                    summary += f"  - {key}: {value}\n"
        
        if 'processing_time_seconds' in topology_results:
            summary += f"\nProcessing Time: {topology_results['processing_time_seconds']:.2f}s\n"
        
        return summary


if __name__ == "__main__":
    logger.info("Enhanced Topology Analyzer module loaded")
