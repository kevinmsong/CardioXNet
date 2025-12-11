/**
 * Utility functions for normalizing and extracting data from pathway hypotheses
 * Handles both legacy (aggregated_pathway) and current (flat) data structures
 */

export interface NormalizedHypothesis {
  pathway_id: string;
  pathway_name: string;
  source_db: string;
  nes_score: number;
  p_adj: number;
  evidence_count: number;
  evidence_genes: string[];
  seed_genes: string[];
  key_nodes: Array<{gene: string; centrality: number; role?: string}>;
  literature_citations: number;
  score_components?: {
    cardiac_relevance?: number;
    centrality_weight?: number;
    cardiac_specificity_ratio?: number;
  };
  support_count?: number;
  citation_count?: number;
}

/**
 * Normalize hypothesis data to a consistent structure
 */
export function normalizeHypothesis(hyp: any): NormalizedHypothesis {
  // Check if using legacy aggregated_pathway structure
  const isLegacy = hyp.aggregated_pathway?.pathway;
  
  if (isLegacy) {
    const pathway = hyp.aggregated_pathway.pathway;
    return {
      pathway_id: pathway.pathway_id || '',
      pathway_name: pathway.pathway_name || 'Unknown Pathway',
      source_db: pathway.source || pathway.database || 'Unknown',
      nes_score: hyp.nes_score || 0,
      p_adj: pathway.p_adj || 1,
      evidence_count: pathway.evidence_genes?.length || 0,
      evidence_genes: pathway.evidence_genes || [],
      seed_genes: hyp.traced_seed_genes || hyp.aggregated_pathway.contributing_seed_genes || [],
      key_nodes: hyp.key_nodes || [],
      literature_citations: hyp.literature_associations?.total_citations || 0,
      score_components: hyp.score_components || {},
      support_count: hyp.support_count || 0,
      citation_count: hyp.literature_associations?.total_citations || 0,
    };
  }
  
  // Current flat structure
  return {
    pathway_id: hyp.pathway_id || '',
    pathway_name: hyp.pathway_name || 'Unknown Pathway',
    source_db: hyp.source_db || 'Unknown',
    nes_score: hyp.nes_score || 0,
    p_adj: hyp.p_adj !== undefined ? hyp.p_adj : 1,
    evidence_count: hyp.evidence_count || hyp.key_nodes?.length || 0,
    evidence_genes: hyp.key_nodes?.map((n: any) => n.gene) || [],
    seed_genes: hyp.seed_genes || [],
    key_nodes: hyp.key_nodes || [],
    literature_citations: hyp.citation_count || hyp.literature_associations?.total_citations || 0,
    score_components: hyp.score_components || {},
    support_count: hyp.support_count || 0,
    citation_count: hyp.citation_count || hyp.literature_associations?.total_citations || 0,
  };
}

/**
 * Get pathway name from hypothesis (supports both structures)
 */
export function getPathwayName(hyp: any): string {
  return hyp.pathway_name || 
         hyp.aggregated_pathway?.pathway?.pathway_name || 
         'Unknown Pathway';
}

/**
 * Get pathway ID from hypothesis (supports both structures)
 */
export function getPathwayId(hyp: any): string {
  return hyp.pathway_id || 
         hyp.aggregated_pathway?.pathway?.pathway_id || 
         '';
}

/**
 * Get source database from hypothesis (supports both structures)
 */
export function getSourceDb(hyp: any): string {
  return hyp.source_db || 
         hyp.aggregated_pathway?.pathway?.source || 
         hyp.aggregated_pathway?.pathway?.database || 
         'Unknown';
}

/**
 * Get p-adjusted value from hypothesis (supports both structures)
 */
export function getPAdj(hyp: any): number {
  if (hyp.p_adj !== undefined) return hyp.p_adj;
  if (hyp.aggregated_pathway?.pathway?.p_adj !== undefined) {
    return hyp.aggregated_pathway.pathway.p_adj;
  }
  return 1;
}

/**
 * Get evidence genes from hypothesis (supports both structures)
 */
export function getEvidenceGenes(hyp: any): string[] {
  // Current structure: key_nodes array
  if (hyp.key_nodes && Array.isArray(hyp.key_nodes)) {
    return hyp.key_nodes.map((n: any) => n.gene || n.gene_symbol || n);
  }
  
  // Legacy structure: aggregated_pathway.pathway.evidence_genes
  if (hyp.aggregated_pathway?.pathway?.evidence_genes) {
    return hyp.aggregated_pathway.pathway.evidence_genes;
  }
  
  return [];
}

/**
 * Get evidence count from hypothesis (supports both structures)
 */
export function getEvidenceCount(hyp: any): number {
  if (hyp.evidence_count !== undefined) return hyp.evidence_count;
  
  const genes = getEvidenceGenes(hyp);
  return genes.length;
}

/**
 * Get seed genes from hypothesis (supports both structures)
 */
export function getSeedGenes(hyp: any): string[] {
  if (hyp.seed_genes && Array.isArray(hyp.seed_genes)) {
    return hyp.seed_genes;
  }
  
  if (hyp.traced_seed_genes && Array.isArray(hyp.traced_seed_genes)) {
    return hyp.traced_seed_genes;
  }
  
  if (hyp.aggregated_pathway?.contributing_seed_genes) {
    return hyp.aggregated_pathway.contributing_seed_genes;
  }
  
  return [];
}

/**
 * Get literature citation count from hypothesis (supports both structures)
 */
export function getLiteratureCitations(hyp: any): number {
  if (hyp.citation_count !== undefined) return hyp.citation_count;
  if (hyp.literature_associations?.total_citations !== undefined) {
    return hyp.literature_associations.total_citations;
  }
  return 0;
}

/**
 * Get cardiac specificity ratio from hypothesis
 */
export function getCardiacSpecificityRatio(hyp: any): number | undefined {
  return hyp.score_components?.cardiac_specificity_ratio;
}

/**
 * Calculate cardiac relevance score
 */
export function calculateCardiacRelevance(hyp: any): number {
  const normalized = normalizeHypothesis(hyp);
  let score = 0;
  
  // Base NES score contribution (30%)
  score += Math.abs(normalized.nes_score) * 0.3;
  
  // Cardiovascular keyword matching (40%)
  const cardiacKeywords = [
    'cardiac', 'heart', 'cardiovascular', 'coronary', 'myocardial', 
    'vascular', 'arterial', 'circulation', 'hypertension', 'atherosclerosis',
    'cardiomyopathy', 'arrhythmia', 'ion channel', 'calcium', 'contraction'
  ];
  const pathwayName = normalized.pathway_name.toLowerCase();
  const keywordMatches = cardiacKeywords.filter(keyword => pathwayName.includes(keyword)).length;
  score += Math.min(keywordMatches * 0.1, 0.4);
  
  // Literature support boost (15%)
  score += Math.min(normalized.literature_citations / 10, 0.15);
  
  // Evidence gene count (15%)
  score += Math.min(normalized.evidence_count / 30, 0.15);
  
  return Math.min(score, 1.0);
}

/**
 * Calculate clinical significance score
 */
export function calculateClinicalSignificance(hyp: any): number {
  const normalized = normalizeHypothesis(hyp);
  let score = 0;
  
  // P-value contribution (40%)
  if (normalized.p_adj < 0.001) score += 0.4;
  else if (normalized.p_adj < 0.01) score += 0.3;
  else if (normalized.p_adj < 0.05) score += 0.2;
  else if (normalized.p_adj < 0.1) score += 0.1;
  
  // NES score contribution (30%)
  score += Math.min(Math.abs(normalized.nes_score) / 5, 0.3);
  
  // Literature support (30%)
  score += Math.min(normalized.literature_citations / 15, 0.3);
  
  return Math.min(score, 1.0);
}

/**
 * Calculate tissue specificity score
 */
export function calculateTissueSpecificity(hyp: any): number {
  const cardiacSpecificityRatio = getCardiacSpecificityRatio(hyp);
  
  if (cardiacSpecificityRatio && cardiacSpecificityRatio > 0) {
    // Normalize the ratio to 0-1 scale
    if (cardiacSpecificityRatio >= 10) return 1.0;
    if (cardiacSpecificityRatio >= 1) return 0.5 + (cardiacSpecificityRatio - 1) / 18;
    return cardiacSpecificityRatio / 2;
  }
  
  // Fallback to pathway name analysis
  const pathwayName = getPathwayName(hyp).toLowerCase();
  const tissueKeywords = ['cardiac', 'myocardial', 'coronary', 'heart'];
  const matches = tissueKeywords.filter(keyword => pathwayName.includes(keyword)).length;
  
  return Math.min(matches * 0.2 + 0.1, 0.6);
}

/**
 * Calculate pathway complexity score
 */
export function calculatePathwayComplexity(hyp: any): number {
  const normalized = normalizeHypothesis(hyp);
  const evidenceCount = normalized.evidence_count;
  const seedCount = normalized.seed_genes.length;
  const supportCount = normalized.support_count || 0;
  
  // Normalize complexity: more genes and support = higher complexity
  return Math.min((evidenceCount + seedCount + supportCount) / 50, 1.0);
}

/**
 * Format p-value for display
 */
export function formatPValue(pValue: number | undefined): string {
  if (pValue === undefined || pValue === null) return 'N/A';
  if (pValue === 0 || pValue < 0.001) return '< 0.001';
  if (pValue < 0.01) return pValue.toFixed(4);
  return pValue.toFixed(3);
}

/**
 * Get significance label for p-value
 */
export function getSignificanceLabel(pValue: number | undefined): string {
  if (pValue === undefined || pValue === null) return 'Unknown';
  if (pValue < 0.001) return 'Highly Significant';
  if (pValue < 0.01) return 'Very Significant';
  if (pValue < 0.05) return 'Significant';
  return 'Not Significant';
}

/**
 * Get color for cardiac relevance
 */
export function getCardiacRelevanceColor(score: number): 'error' | 'warning' | 'info' | 'success' {
  if (score >= 0.75) return 'success';
  if (score >= 0.5) return 'info';
  if (score >= 0.25) return 'warning';
  return 'error';
}

/**
 * Get database badge color
 */
export function getDatabaseColor(db: string): string {
  const dbUpper = db.toUpperCase();
  if (dbUpper.includes('REACTOME')) return '#0077B5';
  if (dbUpper.includes('KEGG')) return '#FF6B35';
  if (dbUpper.includes('GO:BP') || dbUpper.includes('BIOLOGICAL')) return '#4CAF50';
  if (dbUpper.includes('GO:MF') || dbUpper.includes('MOLECULAR')) return '#2196F3';
  if (dbUpper.includes('GO:CC') || dbUpper.includes('CELLULAR')) return '#9C27B0';
  if (dbUpper.includes('WIKI')) return '#FF9800';
  return '#757575';
}

