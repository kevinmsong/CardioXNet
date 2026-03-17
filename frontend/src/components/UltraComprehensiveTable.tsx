import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Button,
  Box,
  Tooltip,
  Chip,
  Typography,
  LinearProgress,
  Stack,
  Paper,
  Rating,
  Badge,
} from '@mui/material';
import {
  Download,
  Science,
  MenuBook,
  TrendingUp,
  Favorite,
  LocalHospital,
  BiotechOutlined,
  Assessment,
} from '@mui/icons-material';
import type { PathwayHypothesis } from '../api/types';
import {
  normalizeHypothesis,
  getPAdj,
  getEvidenceCount,
  getLiteratureCitations,
  calculateCardiacRelevance,
  calculateClinicalSignificance,
  calculateTissueSpecificity,
  calculatePathwayComplexity,
  getCardiacRelevanceColor,
} from '../utils/hypothesisUtils';

interface UltraComprehensiveTableProps {
  hypotheses: PathwayHypothesis[];
  analysisId?: string;
}

type Order = 'asc' | 'desc';
type OrderBy = 'nes_score' | 'p_adj' | 'evidence_count' | 'support_count' | 'cardiac_relevance' | 'literature_support' | 'clinical_significance' | 'pathway_complexity' | 'tissue_specificity' | 'actions';

// Column tooltips with comprehensive explanations
const columnTooltips: Record<string, string> = {
  pathway_name: 'Biological pathway or gene set name from curated databases (Reactome, KEGG, GO)',
  nes_score: 'Normalized Enrichment Score = -log10(p_adj) × √(gene_count) × db_weight × agg_weight × centrality_weight. Combines statistical significance with sqrt gene set size normalization (GSEA standard), database quality weights, multi-source validation, and network centrality. Range: 2-5 for significant pathways, >3.5 for highly significant.',
  p_adj: 'FDR-adjusted p-value from g:Profiler enrichment analysis. Controls false discovery rate across multiple pathway tests. Values < 0.05 indicate statistically significant enrichment (FDR < 5%). Computed using Benjamini-Hochberg correction.',
  empirical_pvalue: 'Permutation-based empirical p-value from 1000 degree-preserving network permutations. More conservative than parametric tests. Values < 0.05 indicate pathway enrichment is unlikely by chance given network topology. Uses stratified sampling by degree quintiles.',
  fdr_qvalue: 'False Discovery Rate q-value from Benjamini-Hochberg correction of empirical p-values. Controls expected proportion of false positives among all discoveries. q < 0.05 means < 5% of pathways at this threshold are expected to be false positives.',
  fold_enrichment: 'Observed/Expected overlap ratio. Measures effect size beyond statistical significance. Value of 2.0 means pathway genes are 2× more enriched than expected by chance. Minimum threshold: 2.0 for biological meaningfulness.',
  cardiac_relevance: 'Cardiac-specific relevance score (0-100%) based on: cardiovascular keywords (40%), NES score (30%), literature support (15%), evidence genes (15%). Semantic scoring using 700+ curated cardiac disease terms.',
  clinical_significance: 'Clinical impact score (0-100%) combining: p-value significance threshold (40%), NES effect size (30%), literature validation (30%). Higher scores indicate greater translational potential.',
  evidence_count: 'Number of genes from the functional neighborhood (seed + neighbors) that overlap with this pathway. Higher counts indicate stronger pathway-gene associations.',
  literature_support: 'Number of PubMed citations reported in literature linking seed genes to pathway-related concepts. Based on PubMed abstract mining (30 abstracts per gene). Higher counts indicate well-studied pathway-gene associations.',
  tissue_specificity: 'GTEx cardiac tissue specificity score (0-100%): Ratio of cardiac vs. non-cardiac tissue expression for pathway genes. Based on GTEx v8 median TPM values across 54 tissues. Higher = more cardiac-specific expression.',
  pathway_complexity: 'Pathway size and complexity score (0-100%) based on number of evidence genes, seed gene contributors, and pathway interconnectedness. Larger pathways may represent broader biological processes.',
  cardiac_disease_score: 'Gene-disease association score (0-100%) from curated cardiovascular disease gene database. Based on gold-standard cardiac disease genes (OMIM, ClinGen), cardiac pathway membership, and literature evidence. Higher scores indicate stronger cardiovascular disease relevance.',
};

// Ultra-comprehensive column definitions for cardiovascular analysis
const headCells = [
  { id: 'pathway_name' as const, label: 'Pathway Name', align: 'left' as const, width: 240, tooltip: columnTooltips.pathway_name },
  { id: 'nes_score' as OrderBy, label: 'NES Score', align: 'center' as const, width: 110, tooltip: columnTooltips.nes_score },
  { id: 'p_adj' as OrderBy, label: 'P-value (adj)', align: 'center' as const, width: 100, tooltip: columnTooltips.p_adj },
  { id: 'cardiac_relevance' as OrderBy, label: 'Cardiac Relevance', align: 'center' as const, width: 140, tooltip: columnTooltips.cardiac_relevance },
  { id: 'clinical_significance' as OrderBy, label: 'Clinical Impact', align: 'center' as const, width: 110, tooltip: columnTooltips.clinical_significance },
  { id: 'evidence_count' as OrderBy, label: 'Evidence Genes', align: 'center' as const, width: 100, tooltip: columnTooltips.evidence_count },
  { id: 'literature_support' as OrderBy, label: 'Literature Reported', align: 'center' as const, width: 120, tooltip: columnTooltips.literature_support },
  { id: 'tissue_specificity' as OrderBy, label: 'GTEx Cardiac Specificity', align: 'center' as const, width: 140, tooltip: columnTooltips.tissue_specificity },
];

// NES scores include log10 transformation in the backend calculation for improved interpretability
// No need for frontend transformation

export default function UltraComprehensiveTable({ hypotheses, analysisId }: UltraComprehensiveTableProps) {
  const navigate = useNavigate();

  // Pagination state - default to 20 rows per page
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  
  // Sorting state - Default to NES score descending
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<OrderBy>('nes_score');

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleRequestSort = (property: OrderBy) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
    setPage(0); // Reset to first page when sorting
  };

  // Enhanced sorting with comprehensive metrics
  const sortedHypotheses = useMemo(() => {
    const comparator = (a: PathwayHypothesis, b: PathwayHypothesis) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'nes_score':
          // NES scores calculated in backend with log10 transformation
          aValue = a.nes_score || 0;
          bValue = b.nes_score || 0;
          break;
        case 'p_adj':
          // Sort by p-value (lower is better)
          aValue = getPAdj(a);
          bValue = getPAdj(b);
          break;
        case 'evidence_count':
          aValue = getEvidenceCount(a);
          bValue = getEvidenceCount(b);
          break;
        case 'cardiac_relevance':
          // Enhanced cardiovascular relevance calculation
          aValue = calculateCardiacRelevance(a);
          bValue = calculateCardiacRelevance(b);
          break;
        case 'clinical_significance':
          aValue = calculateClinicalSignificance(a);
          bValue = calculateClinicalSignificance(b);
          break;
        case 'literature_support':
          aValue = getLiteratureCitations(a);
          bValue = getLiteratureCitations(b);
          break;
        case 'tissue_specificity':
          aValue = calculateTissueSpecificity(a);
          bValue = calculateTissueSpecificity(b);
          break;
        case 'pathway_complexity':
          aValue = calculatePathwayComplexity(a);
          bValue = calculatePathwayComplexity(b);
          break;
        default:
          aValue = 0;
          bValue = 0;
      }

      if (order === 'desc') {
        return bValue < aValue ? -1 : bValue > aValue ? 1 : 0;
      } else {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      }
    };

    return [...hypotheses].sort(comparator);
  }, [hypotheses, order, orderBy]);

  // Calculation functions moved to hypothesisUtils.ts

  // Paginated results
  const paginatedHypotheses = sortedHypotheses.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleExportCSV = () => {
    // Export ALL hypotheses, not just the current page
    const csvData = hypotheses.map((hypothesis) => {
      const normalized = normalizeHypothesis(hypothesis);
      return {
        pathway_name: normalized.pathway_name,
        pathway_id: normalized.pathway_id,
        nes_score: normalized.nes_score.toFixed(3),

        cardiac_relevance: (calculateCardiacRelevance(hypothesis) * 100).toFixed(1) + '%',
        clinical_significance: (calculateClinicalSignificance(hypothesis) * 100).toFixed(1) + '%',
        evidence_genes: normalized.evidence_count,
        literature_citations: normalized.literature_citations,
        tissue_specificity: (calculateTissueSpecificity(hypothesis) * 100).toFixed(1) + '%',
        p_adj: normalized.p_adj ? normalized.p_adj.toExponential(2) : '1.00e+00',
        empirical_pvalue: (hypothesis as any).empirical_pvalue !== undefined 
          ? ((hypothesis as any).empirical_pvalue as number).toExponential(2) 
          : 'N/A',
        fold_enrichment: (hypothesis as any).fold_enrichment !== undefined 
          ? ((hypothesis as any).fold_enrichment as number).toFixed(2)
          : 'N/A',
        // GTEx tissue expression data
        gtex_cardiac_specificity_ratio: (hypothesis.score_components as any)?.cardiac_specificity_ratio?.toFixed(2) || 'N/A',
        gtex_mean_cardiac_tpm: (hypothesis.score_components as any)?.mean_cardiac_tpm?.toFixed(1) || 'N/A',
        gtex_cardiac_expression_ratio: (hypothesis.score_components as any)?.cardiac_expression_ratio ? 
          `${((hypothesis.score_components as any).cardiac_expression_ratio * 100).toFixed(1)}%` : 'N/A',
        gtex_cardiac_expressed_genes: (hypothesis.score_components as any)?.cardiac_expressed_genes?.length || 0,
        gtex_tissue_validation_passed: (hypothesis.score_components as any)?.tissue_validation_passed ? 'Yes' : 'No',
      };
    });

    const csvContent = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cardioxnet_comprehensive_results_${analysisId || 'export'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  // formatPValue and getCardiacRelevanceColor moved to hypothesisUtils.ts

  if (!hypotheses.length) {
    return (
      <Paper 
        elevation={2} 
        sx={{ 
          p: 6, 
          textAlign: 'center',
          borderRadius: 3,
          border: '2px solid #E8F5E9',
        }}
      >
        <Box
          sx={{
            background: 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)',
            borderRadius: '50%',
            width: 100,
            height: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto',
            mb: 3,
          }}
        >
          <Science sx={{ fontSize: 56, color: '#1E6B52' }} />
        </Box>
        <Typography variant="h6" sx={{ color: '#1E6B52', fontWeight: 700, mb: 2 }}>
          No Pathway Analysis Results Available
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No pathway hypotheses were generated for this analysis. This may occur if the input genes did not produce significant pathway enrichment.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Enhanced Header with Export */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Assessment color="primary" />
          <Typography variant="h5" sx={{ fontWeight: 600, color: '#1E6B52' }}>
            Comprehensive Pathway Analysis Results
          </Typography>
          <Chip 
            label={`${hypotheses.length} pathways`} 
            color="primary" 
            size="small"
            icon={<TrendingUp />}
          />
        </Stack>
        <Button
          variant="outlined"
          startIcon={<Download />}
          onClick={handleExportCSV}
          color="primary"
        >
          Export CSV
        </Button>
      </Box>

      {/* Ultra-Comprehensive Table */}
      <TableContainer 
        component={Paper} 
        elevation={3}
        sx={{
          borderRadius: 2,
          border: '2px solid #E8F5E9',
          maxHeight: 'calc(100vh - 200px)',  // Increased from 400px to 200px for taller table
          minHeight: '600px',  // Ensure minimum height
        }}
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {headCells.map((headCell) => (
                <TableCell
                  key={headCell.id}
                  align={headCell.align}
                  style={{ width: headCell.width }}
                  sx={{ 
                    bgcolor: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
                    background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
                    color: 'white',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    borderBottom: '3px solid #FFB81C',
                    py: 2,
                    position: 'sticky',
                    top: 0,
                    zIndex: 100,
                  }}
                >
                  <Tooltip
                    title={headCell.tooltip}
                    arrow
                    placement="top"
                    enterDelay={300}
                    slotProps={{
                      tooltip: {
                        sx: {
                          bgcolor: 'rgba(0, 0, 0, 0.9)',
                        }
                      }
                    }}
                  >
                    <Box>
                      {headCell.id !== 'pathway_name' && headCell.id !== 'actions' ? (
                        <TableSortLabel
                          active={orderBy === headCell.id}
                          direction={orderBy === headCell.id ? order : 'asc'}
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            handleRequestSort(headCell.id as OrderBy);
                          }}
                          sx={{
                            color: 'white !important',
                            '& .MuiTableSortLabel-icon': {
                              color: '#FFB81C !important',
                            },
                            '&.Mui-active': {
                              color: 'white !important',
                            },
                            '&:hover': {
                              color: '#FFB81C !important',
                            }
                          }}
                        >
                          {headCell.label}
                        </TableSortLabel>
                      ) : (
                        headCell.label
                      )}
                    </Box>
                  </Tooltip>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedHypotheses.map((hypothesis, index) => {
              const normalized = normalizeHypothesis(hypothesis);
              const cardiacRelevance = calculateCardiacRelevance(hypothesis);
              const clinicalSignificance = calculateClinicalSignificance(hypothesis);
              const tissueSpecificity = calculateTissueSpecificity(hypothesis);

              const pathwayId = normalized.pathway_id || String(index);

              return (
                <TableRow
                  key={`${pathwayId}`}
                  hover
                  onClick={() => analysisId && navigate(`/results/${analysisId}/pathway/${encodeURIComponent(pathwayId)}`)}
                  sx={{
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: 'rgba(30, 107, 82, 0.08)',
                      transform: 'scale(1.001)',
                      transition: 'all 0.2s ease-in-out',
                    },
                    height: 56,
                    borderBottom: '1px solid #E8F5E9',
                  }}
                >
                  {/* Pathway Name */}
                  <TableCell>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                        {normalized.pathway_name}
                      </Typography>
                      {normalized.pathway_id && (
                        <Typography variant="caption" color="text.secondary">
                          ID: {normalized.pathway_id}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>

                  {/* NES Score */}
                  <TableCell align="center">
                    <Stack spacing={0.5} alignItems="center">
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          fontWeight: 600,
                          color: (hypothesis.nes_score || 0) > 0 ? '#1E6B52' : '#d32f2f',
                          fontSize: '0.9rem'
                        }}
                      >
                        {hypothesis.nes_score?.toFixed(3) || '0.000'}
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(Math.abs(hypothesis.nes_score || 0) * 50, 100)}
                        sx={{ 
                          width: 40, 
                          height: 4,
                          bgcolor: '#f0f0f0',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: (hypothesis.nes_score || 0) > 0 ? '#1E6B52' : '#d32f2f'
                          }
                        }}
                      />
                    </Stack>
                  </TableCell>

                  {/* P-value (adjusted) */}
                  <TableCell align="center">
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        color: (normalized.p_adj || 0) < 0.05 ? '#2E7D32' : '#757575'
                      }}
                    >
                      {normalized.p_adj ? normalized.p_adj.toExponential(2) : '1.00e+00'}
                    </Typography>
                  </TableCell>

                  {/* Cardiac Relevance */}
                  <TableCell align="center">
                    <Stack spacing={0.5} alignItems="center">
                      <Chip
                        label={`${(cardiacRelevance * 100).toFixed(0)}%`}
                        color={getCardiacRelevanceColor(cardiacRelevance)}
                        size="small"
                        icon={<Favorite />}
                        sx={{ fontSize: '0.75rem', height: 24 }}
                      />
                      <LinearProgress
                        variant="determinate"
                        value={cardiacRelevance * 100}
                        color={getCardiacRelevanceColor(cardiacRelevance)}
                        sx={{ width: 50, height: 3 }}
                      />
                    </Stack>
                  </TableCell>

                  {/* Clinical Impact */}
                  <TableCell align="center">
                    <Stack spacing={0.5} alignItems="center">
                      <Rating
                        value={clinicalSignificance * 5}
                        precision={0.5}
                        size="small"
                        readOnly
                        icon={<LocalHospital fontSize="inherit" />}
                        emptyIcon={<LocalHospital fontSize="inherit" />}
                        sx={{ fontSize: '1rem' }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {(clinicalSignificance * 100).toFixed(0)}%
                      </Typography>
                    </Stack>
                  </TableCell>

                  {/* Evidence Genes */}
                  <TableCell align="center">
                    <Badge 
                      badgeContent={normalized.evidence_count}
                      color="primary"
                      max={999}
                    >
                      <BiotechOutlined color="action" />
                    </Badge>
                  </TableCell>

                  {/* Literature Support */}
                  <TableCell align="center">
                    <Stack spacing={0.5} alignItems="center">
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: 700,
                          color: normalized.literature_citations > 0 ? '#2E7D32' : '#C62828',
                        }}
                      >
                        {normalized.literature_citations}
                      </Typography>
                      <MenuBook
                        fontSize="small"
                        sx={{ color: normalized.literature_citations > 0 ? '#2E7D32' : '#C62828' }}
                      />
                    </Stack>
                  </TableCell>

                  {/* Tissue Specificity */}
                  <TableCell align="center">
                    <Tooltip title={
                      hypothesis.score_components?.cardiac_specificity_ratio 
                        ? `GTEx Cardiac Specificity: ${hypothesis.score_components.cardiac_specificity_ratio.toFixed(2)}x higher in cardiac tissue` +
                          (hypothesis.score_components.mean_cardiac_tpm 
                            ? ` (Mean Cardiac TPM: ${hypothesis.score_components.mean_cardiac_tpm.toFixed(1)})` 
                            : '') +
                          (hypothesis.score_components.cardiac_expressed_genes 
                            ? ` • ${hypothesis.score_components.cardiac_expressed_genes.length} genes with cardiac expression` 
                            : '')
                        : "Cardiac specificity based on pathway name analysis"
                    }>
                      <Stack spacing={0.5} alignItems="center">
                        <LinearProgress
                          variant="determinate"
                          value={tissueSpecificity * 100}
                          sx={{ 
                            width: 60, 
                            height: 8,
                            borderRadius: 4,
                            bgcolor: '#f0f0f0',
                            '& .MuiLinearProgress-bar': { 
                              bgcolor: hypothesis.score_components?.cardiac_specificity_ratio ? '#E57373' : '#FFB81C' 
                            }
                          }}
                        />
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <Typography variant="caption" color="text.secondary">
                            {(tissueSpecificity * 100).toFixed(0)}%
                          </Typography>
                          {hypothesis.score_components?.cardiac_specificity_ratio && (
                            <Favorite fontSize="small" sx={{ color: '#E57373', fontSize: 12 }} />
                          )}
                        </Stack>
                      </Stack>
                    </Tooltip>
                  </TableCell>

                  {/* Cardiac Disease Score - REMOVED, now using cardiac_relevance */}

                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Enhanced Pagination */}
      <TablePagination
        rowsPerPageOptions={[10, 20, 50, 100]}
        component="div"
        count={hypotheses.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        sx={{ borderTop: '1px solid #e0e0e0' }}
      />
    </Box>
  );
}