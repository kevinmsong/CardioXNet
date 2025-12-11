export interface GeneInfo {
  input_id: string;
  entrez_id: string;
  hgnc_id?: string;
  symbol: string;
  species: string;
}

export interface ValidationResult {
  valid_genes: GeneInfo[];
  invalid_genes: string[];
  warnings: string[];
}

export interface AnalysisRequest {
  seed_genes: string[];
  disease_context?: string;
  config_overrides?: Record<string, any>;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
  message: string;
}

export interface AnalysisStatus {
  analysis_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_stage?: string;
  progress_percentage?: number;
  message?: string;
  error?: string;
}

export interface PathwayHypothesis {
  rank: number;
  nes_score: number;
  traced_seed_genes?: string[];
  literature_associations?: {
    has_literature_support: boolean;
    total_citations?: number;
    associations?: Array<{
      seed_gene: string;
      citation_count: number;
      pmids: string[];
      has_support: boolean;
    }>;
    checked_seed_genes?: number;
  };
  aggregated_pathway?: {
    pathway?: {
      pathway_id: string;
      pathway_name: string;
      source_db: string;
      p_value: number;
      p_adj: number;
      evidence_count: number;
      evidence_genes: string[];
    };
    support_count: number;
    source_primary_pathways: string[];
    aggregation_score: number;
    combined_p_value: number;
    aggregated_nes: number;
    consistency_score: number;
    confidence_score: number;
    support_fraction: number;
    contributing_seed_genes: string[];
  };
  score_components?: {
    p_adj_component: number;
    evidence_component: number;
    db_weight: number;
    agg_weight: number;
    raw_p_adj: number;
    support_count: number;
    cardiac_relevance?: number;
    semantic_boost?: number;
    relevance_breakdown?: {
      overall: number;
      cardiac_repair: number;
      cardiac_processes: number;
      direct_cardiac: number;
      negative_penalty: number;
    };
    // GTEx tissue expression fields
    cardiac_expression_ratio?: number;
    cardiac_expressed_genes?: string[];
    tissue_validation_passed?: boolean;
    mean_cardiac_tpm?: number;
    cardiac_specificity_ratio?: number;
  };
  // Backward compatibility fields for test data
  pathway_id?: string;
  pathway_name?: string;
  source_db?: string;
  p_adj?: number;
  evidence_count?: number;
  support_count?: number;
  // Clinical evidence fields
  stage_3_clinical_evidence?: {
    hpa_tissue_expression?: {
      tissue: string;
      level: string;
      reliability: string;
    }[];
    gwas_associations?: {
      disease: string;
      p_value: number;
      odds_ratio?: number;
    }[];
    encode_marks?: {
      mark_type: string;
      count: number;
    }[];
  };
}

export interface KeyNode {
  gene_id: string;
  gene_symbol: string;
  betweenness_centrality: number;
  connects_to_seeds: string[];
  connects_to_pathway: string[];
  role: string;
}

export interface AnalysisResults {
  analysis_id: string;
  status: string;
  seed_genes: GeneInfo[];
  hypotheses?: {
    hypotheses: PathwayHypothesis[];
    total_count: number;
  };
  topology?: {
    hypothesis_networks: Record<string, {
      key_nodes: KeyNode[];
      lineage: any;
    }>;
  };
  stage_4c_topology?: {
    network_summary: {
      total_nodes: number;
      total_edges: number;
      density: number;
      average_clustering: number;
      average_degree: number;
      diameter: number;
      connected_components: number;
      largest_component_size: number;
      modularity: number;
    };
    hub_genes: Array<{
      gene_symbol: string;
      degree_centrality: number;
      betweenness_centrality: number;
      closeness_centrality: number;
      eigenvector_centrality: number;
      pagerank: number;
      hub_score: number;
      pathways: string[];
      pathway_count: number;
      is_druggable: boolean;
      druggability_tier?: string;
      rank: number;
    }>;
    therapeutic_targets: Array<{
      gene_symbol: string;
      therapeutic_score: number;
      centrality_score: number;
      druggability_score: number;
      evidence_score: number;
      pathway_count: number;
      pathways: string[];
      drugs?: string[];
      prioritization_rationale: string;
      rank: number;
    }>;
    functional_modules: Array<{
      module_id: number;
      genes: string[];
      size: number;
      internal_density: number;
      enriched_pathways: string[];
      hub_genes: string[];
      modularity_score: number;
    }>;
    pathway_crosstalk: Array<{
      pathway_1: string;
      pathway_2: string;
      shared_genes: string[];
      interaction_strength: number;
      crosstalk_type: string;
    }>;
  };
  report_urls?: Record<string, string>;
}

export interface StageResult {
  analysis_id: string;
  stage_id: string;
  stage_name: string;
  status: string;
  data: Record<string, any>;
}

export interface ConfigDefaults {
  config: {
    // ... existing config properties ...
    nets: {
      // ... existing nets properties ...
      semantic_relevance_threshold: number;
      semantic_repair_boost: number;
      semantic_max_results: number;
      semantic_progressive_thresholds: {
        high_cardiac: number;
        medium_cardiac: number;
        low_cardiac: number;
      };
      // ... rest of nets properties ...
    };
  };
}

export interface ProgressMessage {
  type: 'status' | 'progress' | 'complete';
  analysis_id: string;
  status: string;
  current_stage?: string;
  progress?: number;
  message?: string;
  error?: string;
  timestamp: string;
}
