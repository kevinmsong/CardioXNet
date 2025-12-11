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
  IconButton,
  Box,
  Tooltip,
  Chip,
  Typography,
  LinearProgress,
  Stack,
  Paper,
} from '@mui/material';
import { 
  Download, 
  InfoOutlined, 
  Visibility, 
  Science,
  MenuBook,
  TrendingUp,
  AccountTree,
  Favorite,
  LocalHospital,
} from '@mui/icons-material';
import type { PathwayHypothesis } from '../api/types';

interface EnhancedHypothesesTableProps {
  hypotheses: PathwayHypothesis[];
  analysisId?: string;
}

type Order = 'asc' | 'desc';
type OrderBy = 'rank' | 'nes_score' | 'p_adj' | 'evidence_count' | 'support_count' | 'cardiac_relevance' | 'literature_support';

// Enhanced column definitions with more comprehensive data
const headCells = [
  { id: 'rank' as OrderBy, label: 'Rank', align: 'center' as const, width: 80 },
  { id: 'pathway_name' as const, label: 'Pathway Name', align: 'left' as const, width: 280 },
  { id: 'nes_score' as OrderBy, label: 'NES Score', align: 'center' as const, width: 120 },
  { id: 'p_adj' as OrderBy, label: 'FDR P-value', align: 'center' as const, width: 120 },
  { id: 'cardiac_relevance' as OrderBy, label: 'Cardiovascular Relevance', align: 'center' as const, width: 180 },
  { id: 'evidence_count' as OrderBy, label: 'Evidence Genes', align: 'center' as const, width: 120 },
  { id: 'support_count' as OrderBy, label: 'Support Count', align: 'center' as const, width: 120 },
  { id: 'literature_support' as OrderBy, label: 'Literature Citations', align: 'center' as const, width: 140 },
  { id: 'database_source' as const, label: 'Source Database', align: 'center' as const, width: 140 },
  { id: 'actions' as const, label: 'Actions', align: 'center' as const, width: 120 },
];

export default function EnhancedHypothesesTable({ hypotheses, analysisId }: EnhancedHypothesesTableProps) {
  const navigate = useNavigate();
  
  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25); // Reduced for better UX
  
  // Sorting state
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
  };

  // Enhanced sorting logic with better handling of undefined values
  const sortedHypotheses = useMemo(() => {
    const comparator = (a: PathwayHypothesis, b: PathwayHypothesis) => {
      let aValue: any;
      let bValue: any;

      switch (orderBy) {
        case 'rank':
          aValue = a.rank || 999;
          bValue = b.rank || 999;
          break;
        case 'nes_score':
          aValue = a.nes_score || 0;
          bValue = b.nes_score || 0;
          break;
        case 'p_adj':
          aValue = a.aggregated_pathway?.pathway?.p_adj || 1;
          bValue = b.aggregated_pathway?.pathway?.p_adj || 1;
          break;
        case 'evidence_count':
          aValue = a.aggregated_pathway?.pathway?.evidence_genes?.length || 0;
          bValue = b.aggregated_pathway?.pathway?.evidence_genes?.length || 0;
          break;
        case 'support_count':
          aValue = a.support_count || 0;
          bValue = b.support_count || 0;
          break;
        case 'cardiac_relevance':
          aValue = a.score_components?.cardiac_relevance || 0;
          bValue = b.score_components?.cardiac_relevance || 0;
          break;
        case 'literature_support':
          aValue = a.score_components?.evidence_component || 0;
          bValue = b.score_components?.evidence_component || 0;
          break;
        default:
          aValue = 0;
          bValue = 0;
      }

      if (order === 'desc') {
        return bValue - aValue;
      }
      return aValue - bValue;
    };

    return [...hypotheses].sort(comparator);
  }, [hypotheses, order, orderBy]);

  const paginatedHypotheses = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return sortedHypotheses.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedHypotheses, page, rowsPerPage]);

  const handleViewDetails = (pathwayId: string) => {
    if (analysisId) {
      navigate(`/detail/${analysisId}/${pathwayId}`);
    }
  };

  const handleDownloadCSV = () => {
    // Enhanced CSV export with more columns
    const headers = [
      'Rank', 'Pathway Name', 'NES Score', 'FDR P-value', 'Cardiovascular Relevance', 
      'Evidence Count', 'Support Count', 'Literature Citations', 'Database Source',
      'Pathway ID', 'Description'
    ];
    
    const csvData = hypotheses.map(h => [
      h.rank || '',
      h.aggregated_pathway?.pathway?.pathway_name || '',
      h.nes_score?.toFixed(2) || '',
      h.aggregated_pathway?.pathway?.p_adj?.toExponential(2) || '',
      h.score_components?.cardiac_relevance?.toFixed(3) || '',
      h.aggregated_pathway?.pathway?.evidence_genes?.length || 0,
      h.support_count || 0,
      h.score_components?.evidence_component || 0,
      h.aggregated_pathway?.pathway?.source_db || '',
      h.aggregated_pathway?.pathway?.pathway_id || '',
      h.aggregated_pathway?.pathway?.pathway_name || ''
    ]);

    const csvContent = [headers, ...csvData]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `cardioxnet_results_${analysisId || 'export'}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Helper function to get cardiovascular relevance color
  const getRelevanceColor = (relevance: number) => {
    if (relevance >= 0.7) return 'success';
    if (relevance >= 0.5) return 'warning';
    return 'error';
  };

  // Helper function to get database icon
  const getDatabaseIcon = (database: string) => {
    switch (database?.toLowerCase()) {
      case 'reactome': return <Science fontSize="small" />;
      case 'kegg': return <AccountTree fontSize="small" />;
      case 'wikipathways': return <MenuBook fontSize="small" />;
      case 'go': return <TrendingUp fontSize="small" />;
      default: return <InfoOutlined fontSize="small" />;
    }
  };

  return (
    <Paper elevation={2} sx={{ width: '100%', mb: 2 }}>
      {/* Enhanced Table Header */}
      <Box sx={{ p: 2, bgcolor: '#FAFAFA', borderBottom: '1px solid #E0E0E0' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Favorite sx={{ color: '#1E6B52' }} />
              Cardiovascular Disease Pathway Hypotheses
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {hypotheses.length} pathway hypotheses discovered and ranked by cardiovascular disease relevance
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleDownloadCSV}
            sx={{ textTransform: 'none' }}
          >
            Export Results
          </Button>
        </Stack>
      </Box>

      <TableContainer>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              {headCells.map((headCell) => (
                <TableCell
                  key={headCell.id}
                  align={headCell.align}
                  sx={{ 
                    width: headCell.width,
                    bgcolor: '#F5F5F5',
                    fontWeight: 600,
                    fontSize: '0.875rem'
                  }}
                >
                  {headCell.id !== 'pathway_name' && headCell.id !== 'database_source' && headCell.id !== 'actions' ? (
                    <TableSortLabel
                      active={orderBy === headCell.id}
                      direction={orderBy === headCell.id ? order : 'asc'}
                      onClick={() => handleRequestSort(headCell.id as OrderBy)}
                    >
                      {headCell.label}
                    </TableSortLabel>
                  ) : (
                    headCell.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedHypotheses.map((hypothesis, index) => {
              const pathway = hypothesis.aggregated_pathway?.pathway;
              const cardiacRelevance = hypothesis.score_components?.cardiac_relevance || 0;
              const literatureSupport = hypothesis.score_components?.evidence_component || 0;
              
              return (
                <TableRow 
                  key={pathway?.pathway_id || index}
                  hover
                  sx={{ 
                    '&:hover': { bgcolor: '#F8F9FA' },
                    '& td': { borderBottom: '1px solid #F0F0F0' }
                  }}
                >
                  {/* Rank */}
                  <TableCell align="center">
                    <Chip 
                      label={hypothesis.rank || (page * rowsPerPage + index + 1)}
                      color={hypothesis.rank && hypothesis.rank <= 3 ? 'primary' : 'default'}
                      size="small"
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>

                  {/* Pathway Name */}
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                        {pathway?.pathway_name || 'Unknown Pathway'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {pathway?.pathway_id || 'N/A'}
                      </Typography>
                      <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                        Database: {pathway?.source_db || 'Unknown'}
                      </Typography>
                    </Box>
                  </TableCell>

                  {/* NES Score */}
                  <TableCell align="center">
                    <Box>
                      <Typography variant="body2" fontWeight={600} color="primary">
                        {hypothesis.nes_score?.toFixed(1) || '0.0'}
                      </Typography>
                      <LinearProgress 
                        variant="determinate" 
                        value={Math.min((hypothesis.nes_score || 0) / 200 * 100, 100)}
                        sx={{ 
                          width: 40, 
                          height: 4, 
                          mt: 0.5,
                          bgcolor: 'grey.200',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: '#1E6B52'
                          }
                        }}
                      />
                    </Box>
                  </TableCell>

                  {/* FDR P-value */}
                  <TableCell align="center">
                    <Typography variant="body2" color="text.secondary">
                      {hypothesis.aggregated_pathway?.pathway?.p_adj?.toExponential(2) || 'N/A'}
                    </Typography>
                  </TableCell>

                  {/* Cardiovascular Relevance */}
                  <TableCell align="center">
                    <Box>
                      <Chip
                        label={`${(cardiacRelevance * 100).toFixed(0)}%`}
                        color={getRelevanceColor(cardiacRelevance) as any}
                        variant="outlined"
                        size="small"
                        icon={<LocalHospital fontSize="small" />}
                      />
                      <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                        CV Disease Focus
                      </Typography>
                    </Box>
                  </TableCell>

                  {/* Evidence Count */}
                  <TableCell align="center">
                    <Typography variant="body2" fontWeight={600}>
                      {pathway?.evidence_genes?.length || 0}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      genes
                    </Typography>
                  </TableCell>

                  {/* Support Count */}
                  <TableCell align="center">
                    <Chip
                      label={hypothesis.support_count || 0}
                      color={hypothesis.support_count && hypothesis.support_count >= 3 ? 'success' : 'default'}
                      variant="outlined"
                      size="small"
                    />
                  </TableCell>

                  {/* Literature Support */}
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                      <MenuBook fontSize="small" color="primary" />
                      <Typography variant="body2" fontWeight={600}>
                        {literatureSupport}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      citations
                    </Typography>
                  </TableCell>

                  {/* Database Source */}
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                      {getDatabaseIcon(pathway?.source_db || '')}
                      <Typography variant="body2">
                        {pathway?.source_db || 'Unknown'}
                      </Typography>
                    </Box>
                  </TableCell>

                  {/* Actions */}
                  <TableCell align="center">
                    <Tooltip title="View detailed analysis">
                      <IconButton
                        color="primary"
                        onClick={() => handleViewDetails(pathway?.pathway_id || '')}
                        disabled={!analysisId || !pathway?.pathway_id}
                        size="small"
                      >
                        <Visibility />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={hypotheses.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[10, 25, 50, 100]}
        sx={{
          borderTop: '1px solid #E0E0E0',
          '& .MuiTablePagination-toolbar': {
            bgcolor: '#FAFAFA'
          }
        }}
      />
    </Paper>
  );
}