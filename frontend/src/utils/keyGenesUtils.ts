/**
 * Utility functions for calculating key genes from pathway intersections
 * Uses weighted scoring based on pathway frequency and quality
 */

export interface KeyGene {
  gene: string;
  score: number;
  frequency: number;
  pathways: string[];
  avgNesScore: number;
}

/**
 * Calculate key genes from pathway intersections using weighted scoring
 * 
 * Algorithm:
 * 1. Count gene frequency across pathways
 * 2. Weight by pathway NES scores
 * 3. Normalize and rank genes
 * 
 * @param hypotheses - Array of pathway hypotheses
 * @param minFrequency - Minimum number of pathways a gene must appear in (default: 2)
 * @param topN - Number of top genes to return (default: 20)
 */
export function calculateKeyGenes(
  hypotheses: any[],
  minFrequency: number = 2,
  topN: number = 20
): KeyGene[] {
  if (!hypotheses || hypotheses.length === 0) {
    return [];
  }

  // Map to store gene information
  const geneMap = new Map<string, {
    pathways: string[];
    nesScores: number[];
    ranks: number[];
  }>();

  // Collect genes from all pathways
  hypotheses.forEach((hyp, index) => {
    const pathway = hyp.aggregated_pathway?.pathway;
    if (!pathway) return;

    const pathwayId = pathway.pathway_id;
    const pathwayName = pathway.pathway_name || pathwayId;
    const genes = pathway.evidence_genes || [];
    const nesScore = hyp.nes_score || 0;
    const rank = hyp.rank || index + 1;

    genes.forEach((gene: string) => {
      if (!geneMap.has(gene)) {
        geneMap.set(gene, {
          pathways: [],
          nesScores: [],
          ranks: [],
        });
      }

      const geneData = geneMap.get(gene)!;
      geneData.pathways.push(pathwayName);
      geneData.nesScores.push(nesScore);
      geneData.ranks.push(rank);
    });
  });

  // Calculate weighted scores for each gene
  const keyGenes: KeyGene[] = [];
  const totalPathways = hypotheses.length;

  geneMap.forEach((data, gene) => {
    const frequency = data.pathways.length;

    // Skip genes that don't meet minimum frequency
    if (frequency < minFrequency) {
      return;
    }

    // Calculate average NES score across pathways containing this gene
    const avgNesScore = data.nesScores.reduce((a, b) => a + b, 0) / data.nesScores.length;

    // Calculate average rank (lower is better, so invert)
    const avgRank = data.ranks.reduce((a, b) => a + b, 0) / data.ranks.length;
    const rankScore = 1 / avgRank; // Inverse rank for scoring

    // Weighted score calculation:
    // - Frequency weight: 40% (how many pathways contain this gene)
    // - NES weight: 40% (average quality of pathways containing this gene)
    // - Rank weight: 20% (average rank of pathways containing this gene)
    const frequencyScore = frequency / totalPathways;
    const nesScoreNormalized = Math.min(avgNesScore / 5.0, 1.0); // Normalize assuming max NES ~5
    const rankScoreNormalized = Math.min(rankScore * 10, 1.0); // Normalize rank score

    const weightedScore = 
      (frequencyScore * 0.4) +
      (nesScoreNormalized * 0.4) +
      (rankScoreNormalized * 0.2);

    keyGenes.push({
      gene,
      score: weightedScore,
      frequency,
      pathways: data.pathways,
      avgNesScore,
    });
  });

  // Sort by score descending and return top N
  return keyGenes
    .sort((a, b) => b.score - a.score)
    .slice(0, topN);
}

/**
 * Get a descriptive label for key gene frequency
 */
export function getFrequencyLabel(frequency: number, totalPathways: number): string {
  const percentage = (frequency / totalPathways) * 100;
  
  if (percentage >= 50) {
    return 'High frequency';
  } else if (percentage >= 25) {
    return 'Moderate frequency';
  } else {
    return 'Low frequency';
  }
}

/**
 * Get color for key gene score visualization
 */
export function getKeyGeneScoreColor(score: number): string {
  if (score >= 0.7) {
    return '#1E6B52'; // Dark green for high scores
  } else if (score >= 0.5) {
    return '#4A9B7F'; // Medium green
  } else if (score >= 0.3) {
    return '#FFB81C'; // Gold for moderate scores
  } else {
    return '#9E9E9E'; // Gray for low scores
  }
}
