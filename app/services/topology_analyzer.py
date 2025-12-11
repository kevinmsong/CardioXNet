"""Network topology analysis service (Stage 4)."""

import logging
from typing import List, Dict, Set, Tuple
import networkx as nx

from app.models import (
    GeneInfo,
    FunctionalNeighborhood,
    ScoredPathway,
    KeyNode,
    PathwayLineage,
    NetworkAnalysis,
    TopologyResult
)
from app.services import STRINGClient, APIClientError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TopologyAnalyzer:
    """Analyzes network topology and identifies key nodes (Stage 4)."""
    
    def __init__(self):
        """Initialize topology analyzer."""
        self.settings = get_settings()
        self.string_client = STRINGClient()
        
        logger.info("TopologyAnalyzer initialized")
    
    def analyze(
        self,
        hypotheses: List[ScoredPathway],
        fn: FunctionalNeighborhood,
        primary_pathways: List,
        top_n: int = None
    ) -> TopologyResult:
        """
        Analyze network topology for top N hypotheses.
        
        Args:
            hypotheses: Scored pathway hypotheses
            fn: Functional neighborhood from Stage 1
            primary_pathways: Primary pathways from Stage 2a
            top_n: Number of top hypotheses to analyze (default from config)
            
        Returns:
            TopologyResult with network analysis for each hypothesis
        """
        top_n = top_n or self.settings.nets.top_hypotheses_count
        
        logger.info(
            f"Analyzing network topology for top {top_n} hypotheses"
        )
        
        hypothesis_networks = {}
        
        # Analyze top N hypotheses
        for i, hypothesis in enumerate(hypotheses[:top_n], 1):
            pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
            
            logger.info(f"[TOPOLOGY] Analyzing {i}/{min(top_n, len(hypotheses))}: {pathway_id}")
            print(f"[TOPOLOGY DEBUG] Analyzing pathway {i}/{min(top_n, len(hypotheses))}: {pathway_id}")
            
            try:
                network_analysis = self._analyze_hypothesis(
                    hypothesis,
                    fn,
                    primary_pathways
                )
                
                hypothesis_networks[pathway_id] = network_analysis
                
                logger.info(f"[TOPOLOGY] Successfully analyzed {pathway_id}: {len(network_analysis.key_nodes)} key nodes")
                print(f"[TOPOLOGY DEBUG] Found {len(network_analysis.key_nodes)} key nodes for {pathway_id}")
                
            except Exception as e:
                logger.error(
                    f"Failed to analyze topology for {pathway_id}: {str(e)}"
                )
                print(f"[TOPOLOGY ERROR] Failed for {pathway_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        result = TopologyResult(
            hypothesis_networks=hypothesis_networks
        )
        
        logger.info(
            f"Topology analysis complete for {len(hypothesis_networks)} hypotheses"
        )
        
        return result
    
    def _analyze_hypothesis(
        self,
        hypothesis: ScoredPathway,
        fn: FunctionalNeighborhood,
        primary_pathways: List
    ) -> NetworkAnalysis:
        """
        Analyze network topology for a single hypothesis.
        
        Args:
            hypothesis: Scored pathway hypothesis
            fn: Functional neighborhood
            primary_pathways: Primary pathways
            
        Returns:
            NetworkAnalysis for the hypothesis
        """
        # Step 1: Trace pathway lineage
        lineage = self._trace_lineage(hypothesis, fn, primary_pathways)
        
        # Step 2: Build network graph
        graph = self._build_network_graph(lineage, fn)
        
        # Step 3: Calculate centrality and identify key nodes
        key_nodes = self._identify_key_nodes(graph, lineage, fn)
        
        # Step 4: Determine seed-specific vs shared connections
        seed_connections, shared_connections = self._analyze_connections(
            key_nodes,
            lineage,
            fn
        )
        
        # Step 5: Generate network visualization data
        network_data = self._generate_network_data(graph, lineage)
        
        return NetworkAnalysis(
            lineage=lineage,
            key_nodes=key_nodes,
            seed_specific_connections=seed_connections,
            shared_connections=shared_connections,
            network_data=network_data
        )
    
    def _trace_lineage(
        self,
        hypothesis: ScoredPathway,
        fn: FunctionalNeighborhood,
        primary_pathways: List
    ) -> PathwayLineage:
        """
        Trace pathway lineage from seeds to final pathway.
        
        Args:
            hypothesis: Scored pathway hypothesis
            fn: Functional neighborhood
            primary_pathways: Primary pathways
            
        Returns:
            PathwayLineage tracing the discovery path
        """
        # Extract seed genes
        seed_genes = [gene.symbol for gene in fn.seed_genes]
        
        # Extract F_N genes
        fn_genes = [gene.symbol for gene in fn.neighbors]
        
        # Find primary pathways that led to this final pathway
        primary_pathway_ids = hypothesis.aggregated_pathway.source_primary_pathways
        
        # Extract primary pathway genes
        primary_pathway_genes = []
        for primary in primary_pathways:
            if primary.pathway_id in primary_pathway_ids:
                primary_pathway_genes.extend(primary.evidence_genes)
        
        # Remove duplicates
        primary_pathway_genes = list(set(primary_pathway_genes))
        
        # Extract final pathway genes
        final_pathway_genes = hypothesis.aggregated_pathway.pathway.evidence_genes
        
        return PathwayLineage(
            seed_genes=seed_genes,
            fn_genes=fn_genes,
            primary_pathways=primary_pathway_ids,
            primary_pathway_genes=primary_pathway_genes,
            final_pathway_genes=final_pathway_genes
        )
    
    def _build_network_graph(
        self,
        lineage: PathwayLineage,
        fn: FunctionalNeighborhood
    ) -> nx.Graph:
        """
        Build NetworkX graph from STRING interactions.
        
        Args:
            lineage: Pathway lineage
            fn: Functional neighborhood
            
        Returns:
            NetworkX graph
        """
        # Collect all genes involved
        all_genes = list(set(
            lineage.seed_genes +
            lineage.fn_genes +
            lineage.primary_pathway_genes +
            lineage.final_pathway_genes
        ))
        
        # Convert to GeneInfo objects
        gene_info_list = [
            GeneInfo(
                input_id=gene,
                entrez_id="",
                symbol=gene,
                species="Homo sapiens"
            )
            for gene in all_genes
        ]
        
        # Query STRING for interactions
        try:
            string_result = self.string_client.get_interactions(gene_info_list)
            interactions = string_result.get("interactions", [])
        except APIClientError as e:
            logger.warning(f"Failed to query STRING: {str(e)}")
            interactions = []
        
        # Build NetworkX graph
        graph = nx.Graph()
        
        # Add nodes
        for gene in all_genes:
            graph.add_node(gene)
        
        # Add edges
        for interaction in interactions:
            from_gene = interaction["from"]
            to_gene = interaction["to"]
            score = interaction["score"]
            
            if from_gene in all_genes and to_gene in all_genes:
                graph.add_edge(from_gene, to_gene, weight=score)
        
        logger.debug(
            f"Built network graph: {graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )
        
        return graph
    
    def _identify_key_nodes(
        self,
        graph: nx.Graph,
        lineage: PathwayLineage,
        fn: FunctionalNeighborhood
    ) -> List[KeyNode]:
        """
        Identify key mediating nodes using betweenness centrality.
        
        Args:
            graph: NetworkX graph
            lineage: Pathway lineage
            fn: Functional neighborhood
            
        Returns:
            List of KeyNode objects
        """
        if graph.number_of_nodes() == 0:
            return []
        
        # Calculate betweenness centrality
        try:
            centrality = nx.betweenness_centrality(graph)
        except:
            logger.warning("Failed to calculate betweenness centrality")
            return []
        
        # Filter for high centrality nodes
        threshold = 0.01  # Minimum centrality threshold (lowered to capture more nodes)
        key_nodes = []
        
        seed_set = set(lineage.seed_genes)
        pathway_set = set(lineage.final_pathway_genes)
        
        for gene, centrality_score in centrality.items():
            if centrality_score >= threshold:
                # Determine connections
                neighbors = list(graph.neighbors(gene))
                
                connects_to_seeds = [n for n in neighbors if n in seed_set]
                connects_to_pathway = [n for n in neighbors if n in pathway_set]
                
                # Classify node role
                role = self._classify_node_role(
                    gene,
                    centrality_score,
                    connects_to_seeds,
                    connects_to_pathway,
                    seed_set,
                    pathway_set
                )
                
                key_node = KeyNode(
                    gene_id="",
                    gene_symbol=gene,
                    betweenness_centrality=centrality_score,
                    connects_to_seeds=connects_to_seeds,
                    connects_to_pathway=connects_to_pathway,
                    role=role
                )
                
                key_nodes.append(key_node)
        
        # Sort by centrality
        key_nodes.sort(key=lambda n: n.betweenness_centrality, reverse=True)
        
        # Return top 10 key nodes (or all if less than 10)
        top_key_nodes = key_nodes[:10]
        
        logger.debug(f"Identified {len(key_nodes)} key nodes, returning top {len(top_key_nodes)}")
        
        return top_key_nodes
    
    def _classify_node_role(
        self,
        gene: str,
        centrality: float,
        connects_to_seeds: List[str],
        connects_to_pathway: List[str],
        seed_set: Set[str],
        pathway_set: Set[str]
    ) -> str:
        """
        Enhanced node role classification based on connectivity patterns.
        
        Args:
            gene: Gene symbol
            centrality: Betweenness centrality score
            connects_to_seeds: Seed genes connected to
            connects_to_pathway: Pathway genes connected to
            seed_set: Set of seed genes
            pathway_set: Set of pathway genes
            
        Returns:
            Role classification: mediator, hub, bridge, or connector
        """
        seed_connections = len(connects_to_seeds)
        pathway_connections = len(connects_to_pathway)
        
        # Mediator: connects multiple seeds to multiple pathway genes (most important)
        if seed_connections >= 2 and pathway_connections >= 2:
            return "mediator"
        
        # Hub: very high centrality with many connections
        if centrality > 0.3 and (seed_connections + pathway_connections) >= 5:
            return "hub"
        
        # Connector: connects seeds to pathway (even if just one of each)
        if seed_connections > 0 and pathway_connections > 0:
            return "connector"
        
        # Bridge: high centrality but connects to only one side
        if centrality > 0.2:
            return "bridge"
        
        # Default
        return "intermediate"
    
    def _analyze_connections(
        self,
        key_nodes: List[KeyNode],
        lineage: PathwayLineage,
        fn: FunctionalNeighborhood
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        """
        Determine seed-specific vs shared connections.
        
        Args:
            key_nodes: List of key nodes
            lineage: Pathway lineage
            fn: Functional neighborhood
            
        Returns:
            Tuple of (seed_specific_connections, shared_connections)
        """
        seed_connections = {seed: [] for seed in lineage.seed_genes}
        shared_nodes = []
        
        # Track which seeds each key node connects to
        for key_node in key_nodes:
            connected_seeds = key_node.connects_to_seeds
            
            if len(connected_seeds) == 1:
                # Seed-specific
                seed_connections[connected_seeds[0]].append(key_node.gene_symbol)
            elif len(connected_seeds) > 1:
                # Shared
                shared_nodes.append(key_node.gene_symbol)
        
        return seed_connections, shared_nodes
    
    def _generate_network_data(
        self,
        graph: nx.Graph,
        lineage: PathwayLineage
    ) -> Dict:
        """
        Generate filtered network visualization data.
        
        Filters to show only the most relevant nodes:
        - All seed genes
        - All final pathway genes
        - Top intermediate nodes by degree (max 50)
        
        Args:
            graph: NetworkX graph
            lineage: Pathway lineage
            
        Returns:
            Dictionary with nodes and edges for visualization
        """
        # Identify node types
        seed_set = set(lineage.seed_genes)
        pathway_set = set(lineage.final_pathway_genes)
        
        # Always include seeds and pathway genes
        important_nodes = seed_set | pathway_set
        
        # Find intermediate nodes (not seed or pathway)
        intermediate_nodes = [
            node for node in graph.nodes()
            if node not in important_nodes
        ]
        
        # Filter intermediates by degree (connectivity)
        # Keep only top 20 most connected intermediate nodes for faster rendering
        if len(intermediate_nodes) > 20:
            node_degrees = {node: graph.degree(node) for node in intermediate_nodes}
            sorted_intermediates = sorted(
                node_degrees.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_intermediates = [node for node, _ in sorted_intermediates[:20]]
            filtered_nodes = important_nodes | set(top_intermediates)
        else:
            filtered_nodes = important_nodes | set(intermediate_nodes)
        
        # Additional safety: if still too many nodes, limit to max 100 total
        if len(filtered_nodes) > 100:
            # Prioritize: all seeds, top pathway genes by degree, top intermediates
            seed_list = list(seed_set)
            pathway_list = list(pathway_set)
            
            # Get degrees for pathway genes
            pathway_degrees = {node: graph.degree(node) for node in pathway_list}
            sorted_pathway = sorted(pathway_degrees.items(), key=lambda x: x[1], reverse=True)
            top_pathway = [node for node, _ in sorted_pathway[:30]]  # Top 30 pathway genes
            
            # Get top intermediates
            intermediate_degrees = {node: graph.degree(node) for node in intermediate_nodes}
            sorted_inter = sorted(intermediate_degrees.items(), key=lambda x: x[1], reverse=True)
            top_inter = [node for node, _ in sorted_inter[:10]]  # Top 10 intermediates
            
            filtered_nodes = set(seed_list) | set(top_pathway) | set(top_inter)
        
        logger.debug(
            f"Filtered network: {len(filtered_nodes)} nodes "
            f"(from {graph.number_of_nodes()} total)"
        )
        
        # Build node list
        nodes = []
        for node in filtered_nodes:
            node_type = "seed" if node in seed_set else \
                       "pathway" if node in pathway_set else \
                       "intermediate"
            
            nodes.append({
                "id": node,
                "label": node,
                "type": node_type
            })
        
        # Build edge list (only edges between filtered nodes)
        edges = []
        for edge in graph.edges(data=True):
            if edge[0] in filtered_nodes and edge[1] in filtered_nodes:
                edges.append({
                    "from": edge[0],
                    "to": edge[1],
                    "weight": edge[2].get("weight", 0.5)
                })
        
        logger.debug(f"Filtered network: {len(edges)} edges")
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def close(self):
        """Close API client sessions."""
        self.string_client.close()
        logger.debug("TopologyAnalyzer closed API client sessions")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
