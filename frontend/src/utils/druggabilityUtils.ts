/**
 * Utility functions for drug target classification and druggability assessment
 */

// Curated drug target databases
const APPROVED_TARGETS = new Set([
  'ADRB1', 'ADRB2', 'ACE', 'AGTR1', 'CACNA1C', 'CACNA1D',
  'SLC12A3', 'SLC12A1', 'SCNN1A', 'F2', 'F10', 'SERPINC1',
  'PTGS1', 'P2RY12', 'ITGB3', 'HMGCR', 'GUCY1A1', 'GUCY1B1',
  'ATP1A1', 'ATP1A2', 'ATP1A3', 'SCN5A', 'KCNH2', 'KCNQ1'
]);

const CLINICAL_TRIAL_TARGETS = new Set([
  'SGLT2', 'PCSK9', 'ANGPTL3', 'IL1B', 'IL6', 'TNF',
  'NLRP3', 'GLP1R', 'DPP4', 'SGLT1', 'KCNJ11', 'ABCC8'
]);

const PRECLINICAL_TARGETS = new Set([
  'NLRP3', 'SIRT1', 'AMPK', 'mTOR', 'FOXO1', 'FOXO3',
  'NRF2', 'HIF1A', 'VEGFA', 'FGF21', 'ADIPOQ', 'LEP'
]);

export type DruggabilityStatus = 'approved' | 'clinical_trial' | 'preclinical' | 'research';

export interface DruggabilityInfo {
  status: DruggabilityStatus;
  label: string;
  color: string;
}

/**
 * Get druggability status for a gene
 */
export function getDruggabilityStatus(gene: string): DruggabilityStatus {
  const upperGene = gene.toUpperCase();
  
  if (APPROVED_TARGETS.has(upperGene)) {
    return 'approved';
  } else if (CLINICAL_TRIAL_TARGETS.has(upperGene)) {
    return 'clinical_trial';
  } else if (PRECLINICAL_TARGETS.has(upperGene)) {
    return 'preclinical';
  }
  
  return 'research';
}

/**
 * Get druggability information including label and color
 */
export function getDruggabilityInfo(gene: string): DruggabilityInfo {
  const status = getDruggabilityStatus(gene);
  
  const infoMap: Record<DruggabilityStatus, DruggabilityInfo> = {
    approved: {
      status: 'approved',
      label: 'FDA Approved',
      color: '#1E6B52', // Dark green
    },
    clinical_trial: {
      status: 'clinical_trial',
      label: 'Clinical Trial',
      color: '#FFB81C', // Gold
    },
    preclinical: {
      status: 'preclinical',
      label: 'Preclinical',
      color: '#4A9B7F', // Medium green
    },
    research: {
      status: 'research',
      label: 'Research',
      color: '#9E9E9E', // Gray
    },
  };
  
  return infoMap[status];
}

/**
 * Check if a gene is a known drug target (any status)
 */
export function isKnownDrugTarget(gene: string): boolean {
  const upperGene = gene.toUpperCase();
  return APPROVED_TARGETS.has(upperGene) || 
         CLINICAL_TRIAL_TARGETS.has(upperGene) || 
         PRECLINICAL_TARGETS.has(upperGene);
}

/**
 * Get all genes by druggability status
 */
export function groupGenesByDruggability(genes: string[]): Record<DruggabilityStatus, string[]> {
  const groups: Record<DruggabilityStatus, string[]> = {
    approved: [],
    clinical_trial: [],
    preclinical: [],
    research: [],
  };
  
  genes.forEach(gene => {
    const status = getDruggabilityStatus(gene);
    groups[status].push(gene);
  });
  
  return groups;
}
