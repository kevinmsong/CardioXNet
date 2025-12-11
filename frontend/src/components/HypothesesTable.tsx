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
} from '@mui/material';
import { Download, InfoOutlined, Visibility } from '@mui/icons-material';
import type { PathwayHypothesis } from '../api/types';

interface HypothesesTableProps {
  hypotheses: PathwayHypothesis[];
  analysisId?: string;
}

type Order = 'asc' | 'desc';
type OrderBy = 'rank' | 'nes_score' | 'p_adj' | 'evidence_count' | 'support_count';

export default function HypothesesTable({ hypotheses, analysisId }: HypothesesTableProps) {
  const navigate = useNavigate();
  
  // Pagination state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  
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

  const handleDownloadCSV = () => {
    // Create CSV content
    const headers = ['Rank', 'Pathway Name', 'Pathway ID', 'NES Score', 'P-adj', 'Evidence Count', 'Support Count', 'Source DB'];
    const rows = sortedHypotheses.map(h => [
      h.rank,
      `"${h.aggregated_pathway?.pathway?.pathway_name || h.pathway_name || 'N/A'}"`, // Quote to handle commas in names
      h.aggregated_pathway?.pathway?.pathway_id || h.pathway_id || 'N/A',
      h.nes_score.toFixed(4),
      (h.aggregated_pathway?.pathway?.p_adj ?? h.p_adj)?.toExponential(4) ?? 'N/A',
      h.aggregated_pathway?.pathway?.evidence_count ?? h.evidence_count ?? 0,
      h.aggregated_pathway?.support_count ?? h.support_count ?? 0,
      h.aggregated_pathway?.pathway?.source_db || h.source_db || 'N/A'
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `analysis_results_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Sort hypotheses
  const sortedHypotheses = useMemo(() => {
    const comparator = (a: PathwayHypothesis, b: PathwayHypothesis) => {
      let aValue: number;
      let bValue: number;

      switch (orderBy) {
        case 'nes_score':
          aValue = a.nes_score;
          bValue = b.nes_score;
          break;
        case 'p_adj':
          aValue = a.aggregated_pathway?.pathway?.p_adj ?? a.p_adj ?? 0;
          bValue = b.aggregated_pathway?.pathway?.p_adj ?? b.p_adj ?? 0;
          break;
        case 'evidence_count':
          aValue = a.aggregated_pathway?.pathway?.evidence_count ?? a.evidence_count ?? 0;
          bValue = b.aggregated_pathway?.pathway?.evidence_count ?? b.evidence_count ?? 0;
          break;
        case 'support_count':
          aValue = a.aggregated_pathway?.support_count ?? a.support_count ?? 0;
          bValue = b.aggregated_pathway?.support_count ?? b.support_count ?? 0;
          break;

        case 'rank':
        default:
          aValue = a.rank;
          bValue = b.rank;
          break;
      }

      if (order === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    };

    return [...hypotheses].sort(comparator);
  }, [hypotheses, order, orderBy]);

  // Paginate hypotheses
  const paginatedHypotheses = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return sortedHypotheses.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedHypotheses, page, rowsPerPage]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<Download />}
          onClick={handleDownloadCSV}
          disabled={hypotheses.length === 0}
        >
          Download CSV
        </Button>
      </Box>

      <TableContainer>
        <Table size="small" sx={{ '& .MuiTableCell-root': { py: 0.5, px: 1 } }}>
          <TableHead>
            <TableRow sx={{ bgcolor: '#FAFAFA' }}>
              <TableCell sx={{ width: 60, fontWeight: 600 }}>
                <TableSortLabel
                  active={orderBy === 'rank'}
                  direction={orderBy === 'rank' ? order : 'asc'}
                  onClick={() => handleRequestSort('rank')}
                >
                  Rank
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Pathway Name</TableCell>
              <TableCell sx={{ width: 120, fontWeight: 600 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'nes_score'}
                    direction={orderBy === 'nes_score' ? order : 'desc'}
                    onClick={() => handleRequestSort('nes_score')}
                  >
                    NES Score
                  </TableSortLabel>
                  <Tooltip 
                    title="Normalized Enrichment Score: Combines statistical significance (calculated using -log10(P-adj)), evidence count (number of genes), database quality weight, and aggregation weight. Higher scores indicate stronger, more novel pathway associations."
                    arrow
                    placement="top"
                  >
                    <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              </TableCell>
              <TableCell sx={{ width: 130, fontWeight: 600 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'p_adj'}
                    direction={orderBy === 'p_adj' ? order : 'asc'}
                    onClick={() => handleRequestSort('p_adj')}
                  >
                    P-adj
                  </TableSortLabel>
                  <Tooltip 
                    title="Adjusted P-value: Statistical significance after FDR (False Discovery Rate) correction for multiple testing. Lower values indicate stronger statistical evidence. Combined across primaries using Fisher's method."
                    arrow
                    placement="top"
                  >
                    <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              </TableCell>
              <TableCell sx={{ width: 90, fontWeight: 600 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'evidence_count'}
                    direction={orderBy === 'evidence_count' ? order : 'desc'}
                    onClick={() => handleRequestSort('evidence_count')}
                  >
                    Evidence
                  </TableSortLabel>
                  <Tooltip 
                    title="Evidence Count: Number of genes from the functional neighborhood that are annotated to this pathway. Higher counts indicate broader pathway involvement."
                    arrow
                    placement="top"
                  >
                    <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              </TableCell>
              <TableCell sx={{ width: 90, fontWeight: 600 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'support_count'}
                    direction={orderBy === 'support_count' ? order : 'desc'}
                    onClick={() => handleRequestSort('support_count')}
                  >
                    Support
                  </TableSortLabel>
                  <Tooltip 
                    title="Support Count: Number of independent primary pathways that led to discovery of this secondary pathway. Higher support indicates more robust, replicated findings across multiple biological contexts."
                    arrow
                    placement="top"
                  >
                    <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              </TableCell>
              <TableCell sx={{ width: 120, fontWeight: 600 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  Literature
                  <Tooltip 
                    title="Literature Association: Indicates whether this pathway has been reported in scientific literature to be associated with your seed genes. Based on PubMed co-mention analysis with cardiac context."
                    arrow
                    placement="top"
                  >
                    <InfoOutlined sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                  </Tooltip>
                </Box>
              </TableCell>
              <TableCell sx={{ width: 100, fontWeight: 600 }}>
                Details
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedHypotheses.map((hypothesis) => (
              <TableRow 
key={hypothesis.aggregated_pathway?.pathway?.pathway_id || hypothesis.pathway_id || hypothesis.rank} 
                hover
                sx={{ 
                  '&:hover': { bgcolor: '#F5F5F5' },
                  transition: 'background-color 0.2s',
                  height: 40,
                }}
              >
                <TableCell sx={{ fontWeight: 600, color: 'primary.main', py: 1 }}>
                  {hypothesis.rank}
                </TableCell>
                <TableCell sx={{ fontSize: '0.875rem', py: 1 }}>
                  {hypothesis.aggregated_pathway?.pathway?.pathway_name || hypothesis.pathway_name || 'N/A'}
                </TableCell>
                <TableCell sx={{ fontWeight: 600, color: 'success.main', py: 1 }}>
                  {hypothesis.nes_score.toFixed(2)}
                </TableCell>
                <TableCell sx={{ fontSize: '0.875rem', fontFamily: 'monospace', py: 1 }}>
                  {(hypothesis.aggregated_pathway?.pathway?.p_adj ?? hypothesis.p_adj)?.toExponential(2) ?? 'N/A'}
                </TableCell>
                <TableCell sx={{ textAlign: 'center', py: 1 }}>
                  {hypothesis.aggregated_pathway?.pathway?.evidence_count ?? hypothesis.evidence_count ?? 0}
                </TableCell>
                <TableCell sx={{ textAlign: 'center', fontWeight: 600, py: 1 }}>
                  {hypothesis.aggregated_pathway?.support_count ?? hypothesis.support_count ?? 0}
                </TableCell>
                <TableCell 
                  sx={{ 
                    textAlign: 'center', 
                    py: 1,
                    bgcolor: hypothesis.literature_associations && !hypothesis.literature_associations.has_literature_support 
                      ? 'rgba(255, 193, 7, 0.1)' 
                      : 'transparent'
                  }}
                >
                  {hypothesis.literature_associations?.has_literature_support ? (
                    <Tooltip 
                      title={`Found ${hypothesis.literature_associations.total_citations || 0} citations linking this pathway to ${hypothesis.traced_seed_genes?.length || 0} seed gene(s)`}
                      arrow
                    >
                      <Chip
                        label="Reported"
                        size="small"
                        color="success"
                        sx={{ fontWeight: 600, minWidth: 90 }}
                      />
                    </Tooltip>
                  ) : hypothesis.literature_associations ? (
                    <Tooltip title="No literature evidence found for pathway-seed gene association - this may represent a novel finding" arrow>
                      <Chip
                        label="Not Reported"
                        size="small"
                        sx={{ 
                          fontWeight: 600, 
                          minWidth: 90,
                          bgcolor: '#FFC107',
                          color: '#000',
                          '&:hover': {
                            bgcolor: '#FFB300'
                          }
                        }}
                      />
                    </Tooltip>
                  ) : (
                    <Chip
                      label="N/A"
                      size="small"
                      variant="outlined"
                      sx={{ fontWeight: 600, minWidth: 90 }}
                    />
                  )}
                </TableCell>
                <TableCell>
                  <Tooltip title="View detailed evidence, literature citations, and network topology" arrow>
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => analysisId && navigate(`/analysis/${analysisId}/pathway/${hypothesis.aggregated_pathway?.pathway?.pathway_id || hypothesis.pathway_id}`)}
                      sx={{
                        '&:hover': {
                          bgcolor: 'primary.light',
                          color: 'white',
                        },
                      }}
                    >
                      <Visibility fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[25, 50, 100, 200]}
        component="div"
        count={sortedHypotheses.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </Box>
  );
}
