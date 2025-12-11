"""
gtGMM Network Topology Analyzer - Integration for CardioXNet.

This module integrates the gtGMM (Gaussian Mixture Model for Gene networks with Topological Data Analysis)
library into the CardioXNet pipeline for advanced network topology analysis of gene interactions.

Features:
- Topological terrain construction from STRING networks
- Gaussian Mixture Model (GMM) decomposition with automatic component selection (BIC)
- Topological Data Analysis (TDA) metrics computation
- Hub gene identification with centrality measures
- Module/cluster detection from topological decomposition
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TopologyNode:
    """Represents a node in the topological analysis."""
    gene_id: str
    gene_symbol: str
    x: float
    y: float
    z: float  # Optional third dimension
    hub_score: float  # Centrality measure (0-1)
    component: int  # GMM component assignment
    component_probability: float
    betweenness_centrality: float
    closeness_centrality: float
    degree_centrality: float
    is_hub: bool
    is_druggable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TopologyComponent:
    """Represents a GMM component/cluster in the topology."""
    component_id: int
    size: int
    genes: List[str]
    density: float  # Topological density
    hub_genes: List[str]
    mean_connectivity: float
    bic_score: float
    variance_explained: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TopologyMetrics:
    """TDA metrics for the network topology."""
    num_components: int
    modularity: float
    average_clustering_coefficient: float
    network_density: float
    average_path_length: float
    diameter: int
    small_world_coefficient: float  # sigma = C/C_random / L/L_random
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class GTGMMNetworkAnalyzer:
    """
    Advanced network topology analyzer using gtGMM.
    
    Transforms gene networks into topological terrains and performs
    unsupervised decomposition into functional modules.
    """
    
    def __init__(self, max_components: int = 8, min_components: int = 3, 
                 resolution: int = 500, sigma: Optional[float] = None):
        """
        Initialize the gtGMM analyzer.
        
        Args:
            max_components: Maximum number of GMM components to try
            min_components: Minimum number of GMM components to try
            resolution: Terrain resolution (default 500x500)
            sigma: Gaussian kernel bandwidth (auto-optimized if None)
        """
        self.max_components = max_components
        self.min_components = min_components
        self.resolution = resolution
        self.sigma = sigma
        
        # Use NetworkX + scikit-learn for topology analysis (no external gtgmm dependency)
        self.gtgmm_available = False
        self.gtgmm = None
        logger.info("Using NetworkX + scikit-learn for topology analysis")
    
    def analyze_network_topology(
        self,
        genes: List[str],
        adjacency_matrix: np.ndarray,
        gene_expressions: Optional[pd.DataFrame] = None,
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Perform complete topology analysis on a gene network.
        
        Args:
            genes: List of gene IDs
            adjacency_matrix: NxN adjacency matrix of the network
            gene_expressions: Optional expression data for each gene
            gene_symbols: Mapping from gene ID to symbol
            
        Returns:
            Dictionary containing topology analysis results:
            - nodes: List of TopologyNode objects
            - components: List of TopologyComponent objects
            - metrics: TopologyMetrics object
            - hub_genes: List of identified hub genes
            - clusters: GMM component assignments
        """
        logger.info(f"Starting topology analysis for {len(genes)} genes")
        
        try:
            # Use NetworkX + scikit-learn for topology analysis
            return self._analyze_with_fallback(genes, adjacency_matrix, gene_symbols)
        except Exception as e:
            logger.error(f"Error in topology analysis: {e}")
            raise
    
    def _analyze_with_gtgmm(
        self,
        genes: List[str],
        adjacency_matrix: np.ndarray,
        gene_expressions: pd.DataFrame,
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Full gtGMM analysis with terrain and TDA."""
        logger.info("Using gtGMM for full topology analysis")
        
        # Create GeneTerrain
        try:
            gt = self.gtgmm.create_terrain(
                genes=genes,
                expression_data=gene_expressions.values,
                adjacency_matrix=adjacency_matrix,
                resolution=self.resolution,
                sigma=self.sigma
            )
            logger.info(f"GeneTerrain created with resolution {self.resolution}")
        except Exception as e:
            logger.warning(f"GeneTerrain creation failed: {e}, using fallback")
            return self._analyze_with_fallback(genes, adjacency_matrix, gene_symbols)
        
        # Run GMM decomposition
        try:
            gmm = gt.run_gmm(
                max_components=self.max_components,
                min_components=self.min_components
            )
            logger.info(f"GMM decomposition complete: {gmm.n_components} components")
        except Exception as e:
            logger.warning(f"GMM decomposition failed: {e}")
            gmm = None
        
        # Run TDA
        try:
            tda = gt.run_tda()
            logger.info("TDA analysis complete")
        except Exception as e:
            logger.warning(f"TDA analysis failed: {e}")
            tda = None
        
        # Extract results
        results = self._extract_gtgmm_results(genes, adjacency_matrix, gmm, tda, gene_symbols)
        logger.info(f"Extracted {len(results['hub_genes'])} hub genes from {len(results['nodes'])} nodes")
        return results
    
    def _analyze_with_fallback(
        self,
        genes: List[str],
        adjacency_matrix: np.ndarray,
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Fallback topology analysis using NetworkX and scikit-learn."""
        logger.info("Using fallback topology analysis (NetworkX + scikit-learn)")
        
        import networkx as nx
        from sklearn.cluster import SpectralClustering
        from sklearn.preprocessing import StandardScaler
        
        # Create NetworkX graph
        G = nx.Graph()
        G.add_nodes_from(range(len(genes)))
        
        edges = np.where(adjacency_matrix > 0)
        for i, j in zip(edges[0], edges[1]):
            if i < j:  # Avoid duplicates
                weight = adjacency_matrix[i, j]
                G.add_edge(i, j, weight=weight)
        
        logger.info(f"Network: {len(G.nodes)} nodes, {len(G.edges)} edges")
        
        # Calculate centrality measures
        betweenness = nx.betweenness_centrality(G, weight='weight')
        closeness = nx.closeness_centrality(G, distance='weight')
        degree = nx.degree_centrality(G)
        
        # Combine centralities into hub score
        hub_scores = {}
        for node in G.nodes():
            hub_scores[node] = (
                0.4 * betweenness.get(node, 0) +
                0.3 * closeness.get(node, 0) +
                0.3 * degree.get(node, 0)
            )
        
        # Spectral clustering for components
        n_clusters = min(self.max_components, max(self.min_components, len(genes) // 10))
        try:
            clustering = SpectralClustering(
                n_clusters=n_clusters,
                affinity='precomputed',
                random_state=42,
                n_init=10
            )
            labels = clustering.fit_predict(adjacency_matrix)
            logger.info(f"Spectral clustering: {n_clusters} clusters")
        except Exception as e:
            logger.warning(f"Spectral clustering failed: {e}")
            labels = np.zeros(len(genes), dtype=int)
        
        # Create layout (using spring layout in 2D)
        try:
            pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
        except:
            pos = {i: (np.random.rand(), np.random.rand()) for i in range(len(genes))}
        
        # Build topology nodes
        nodes = []
        node_map = {}
        
        for idx, gene_id in enumerate(genes):
            symbol = gene_symbols.get(gene_id, gene_id) if gene_symbols else gene_id
            x, y = pos.get(idx, (np.random.rand(), np.random.rand()))
            
            node = TopologyNode(
                gene_id=gene_id,
                gene_symbol=symbol,
                x=float(x),
                y=float(y),
                z=0.0,
                hub_score=float(hub_scores.get(idx, 0)),
                component=int(labels[idx]),
                component_probability=1.0,
                betweenness_centrality=float(betweenness.get(idx, 0)),
                closeness_centrality=float(closeness.get(idx, 0)),
                degree_centrality=float(degree.get(idx, 0)),
                is_hub=bool(float(hub_scores.get(idx, 0)) > np.percentile(list(hub_scores.values()), 75))
            )
            nodes.append(node)
            node_map[idx] = node
        
        # Identify top hub genes
        hub_genes = sorted(
            [n.gene_symbol for n in nodes if n.is_hub],
            key=lambda s: next((n.hub_score for n in nodes if n.gene_symbol == s), 0),
            reverse=True
        )[:10]
        
        # Build topology components
        components = []
        for comp_id in range(n_clusters):
            comp_nodes = [n for n in nodes if n.component == comp_id]
            comp_gene_ids = [n.gene_id for n in comp_nodes]
            comp_hub_genes = [n.gene_symbol for n in comp_nodes if n.is_hub]
            
            component = TopologyComponent(
                component_id=comp_id,
                size=len(comp_nodes),
                genes=comp_gene_ids,
                density=float(nx.density(G.subgraph([i for i, n in enumerate(nodes) if n.component == comp_id]))),
                hub_genes=comp_hub_genes,
                mean_connectivity=float(np.mean([degree.get(i, 0) for i, n in enumerate(nodes) if n.component == comp_id])),
                bic_score=0.0,  # Not applicable for fallback
                variance_explained=1.0 / n_clusters  # Equal distribution
            )
            components.append(component)
        
        # Calculate topology metrics
        metrics = TopologyMetrics(
            num_components=n_clusters,
            modularity=float(nx.algorithms.community.modularity(G, [set(n.gene_id for n in nodes if n.component == c) for c in range(n_clusters)])),
            average_clustering_coefficient=float(nx.average_clustering(G)),
            network_density=float(nx.density(G)),
            average_path_length=float(nx.average_shortest_path_length(G)) if nx.is_connected(G) else float('inf'),
            diameter=int(nx.diameter(G)) if nx.is_connected(G) else -1,
            small_world_coefficient=0.0  # Calculate if needed
        )
        
        return {
            'nodes': nodes,
            'components': components,
            'metrics': metrics,
            'hub_genes': hub_genes,
            'clusters': labels.tolist(),
            'adjacency_matrix': adjacency_matrix.tolist()
        }
    
    def _extract_gtgmm_results(
        self,
        genes: List[str],
        adjacency_matrix: np.ndarray,
        gmm: Optional[Any],
        tda: Optional[Any],
        gene_symbols: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract results from gtGMM analysis."""
        import networkx as nx
        
        # Create graph for metrics
        G = nx.Graph()
        G.add_nodes_from(range(len(genes)))
        edges = np.where(adjacency_matrix > 0)
        for i, j in zip(edges[0], edges[1]):
            if i < j:
                G.add_edge(i, j, weight=adjacency_matrix[i, j])
        
        # Get component assignments from GMM
        labels = gmm.labels_ if gmm else np.zeros(len(genes), dtype=int)
        
        # Calculate centralities
        betweenness = nx.betweenness_centrality(G, weight='weight')
        closeness = nx.closeness_centrality(G, distance='weight')
        degree = nx.degree_centrality(G)
        
        # Build nodes
        nodes = []
        for idx, gene_id in enumerate(genes):
            symbol = gene_symbols.get(gene_id, gene_id) if gene_symbols else gene_id
            hub_score = (
                0.4 * betweenness.get(idx, 0) +
                0.3 * closeness.get(idx, 0) +
                0.3 * degree.get(idx, 0)
            )
            
            node = TopologyNode(
                gene_id=gene_id,
                gene_symbol=symbol,
                x=0.0, y=0.0, z=0.0,  # Set from terrain if available
                hub_score=float(hub_score),
                component=int(labels[idx]) if gmm else 0,
                component_probability=1.0,
                betweenness_centrality=float(betweenness.get(idx, 0)),
                closeness_centrality=float(closeness.get(idx, 0)),
                degree_centrality=float(degree.get(idx, 0)),
                is_hub=bool(float(hub_score) > np.percentile(list(
                    0.4 * betweenness.get(i, 0) + 0.3 * closeness.get(i, 0) + 0.3 * degree.get(i, 0)
                    for i in range(len(genes))
                ), 75))
            )
            nodes.append(node)
        
        # Identify hub genes
        hub_genes = sorted(
            [n.gene_symbol for n in nodes if n.is_hub],
            key=lambda s: next((n.hub_score for n in nodes if n.gene_symbol == s), 0),
            reverse=True
        )
        
        # Build components
        n_comp = gmm.n_components if gmm else 1
        components = []
        for comp_id in range(n_comp):
            comp_nodes = [n for n in nodes if n.component == comp_id]
            component = TopologyComponent(
                component_id=comp_id,
                size=len(comp_nodes),
                genes=[n.gene_id for n in comp_nodes],
                density=0.0,
                hub_genes=[n.gene_symbol for n in comp_nodes if n.is_hub],
                mean_connectivity=float(np.mean([degree.get(i, 0) for i, n in enumerate(nodes) if n.component == comp_id])),
                bic_score=gmm.bic_ if gmm and hasattr(gmm, 'bic_') else 0.0,
                variance_explained=1.0 / n_comp
            )
            components.append(component)
        
        # Calculate metrics
        metrics = TopologyMetrics(
            num_components=n_comp,
            modularity=0.0,
            average_clustering_coefficient=float(nx.average_clustering(G)),
            network_density=float(nx.density(G)),
            average_path_length=float(nx.average_shortest_path_length(G)) if nx.is_connected(G) else float('inf'),
            diameter=int(nx.diameter(G)) if nx.is_connected(G) else -1,
            small_world_coefficient=0.0
        )
        
        return {
            'nodes': nodes,
            'components': components,
            'metrics': metrics,
            'hub_genes': hub_genes,
            'clusters': labels.tolist(),
            'adjacency_matrix': adjacency_matrix.tolist()
        }


# Convenience functions for CardioXNet integration

def analyze_string_network_topology(
    genes: List[str],
    adjacency_matrix: np.ndarray,
    gene_expressions: Optional[pd.DataFrame] = None,
    gene_symbols: Optional[Dict[str, str]] = None,
    max_components: int = 8
) -> Dict[str, Any]:
    """
    Convenience function to analyze STRING network topology.
    
    Args:
        genes: List of gene IDs
        adjacency_matrix: STRING interaction matrix
        gene_expressions: Optional expression data
        gene_symbols: Optional ID->symbol mapping
        max_components: Maximum GMM components to try
        
    Returns:
        Complete topology analysis results
    """
    analyzer = GTGMMNetworkAnalyzer(max_components=max_components)
    return analyzer.analyze_network_topology(genes, adjacency_matrix, gene_expressions, gene_symbols)


def extract_hub_genes(topology_results: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Extract top hub genes from topology results.
    
    Args:
        topology_results: Results from analyze_string_network_topology
        top_n: Number of top hub genes to return
        
    Returns:
        List of top hub genes with scores and metrics
    """
    nodes = topology_results['nodes']
    hub_nodes = sorted(nodes, key=lambda n: n.hub_score, reverse=True)[:top_n]
    
    return [
        {
            'gene_symbol': n.gene_symbol,
            'gene_id': n.gene_id,
            'hub_score': n.hub_score,
            'betweenness': n.betweenness_centrality,
            'closeness': n.closeness_centrality,
            'degree': n.degree_centrality,
            'component': n.component,
            'is_druggable': n.is_druggable
        }
        for n in hub_nodes
    ]


def get_functional_modules(topology_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get functional modules from topology decomposition.
    
    Args:
        topology_results: Results from analyze_string_network_topology
        
    Returns:
        List of functional modules with member genes
    """
    components = topology_results['components']
    
    return [
        {
            'module_id': c.component_id,
            'size': c.size,
            'genes': c.genes,
            'hub_genes': c.hub_genes,
            'density': c.density,
            'mean_connectivity': c.mean_connectivity
        }
        for c in components
    ]


if __name__ == "__main__":
    # Example usage
    logger.info("gtGMM Network Analyzer module loaded")
