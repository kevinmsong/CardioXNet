import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Chip,
  Stack,
  Grid,
  Tooltip,
  LinearProgress,
  Divider,
  Alert,
} from '@mui/material';
import {
  Hub,
  AccountTree,
  TrendingUp,
  Science,
} from '@mui/icons-material';

const GREEN = '#1E6B52';
const GOLD = '#FFB81C';

interface HubGene {
  gene_symbol: string;
  degree_centrality: number;
  betweenness_centrality: number;
  closeness_centrality: number;
  eigenvector_centrality: number;
  pagerank: number;
  hub_score: number;
  pathway_count: number;
  pathways: string[];
  is_druggable: boolean;
  druggability_tier: string | null;
  rank: number;
}

interface NetworkSummary {
  total_nodes: number;
  total_edges: number;
  density: number;
  average_clustering: number;
  average_degree: number;
  diameter: number;
  connected_components: number;
  largest_component_size: number;
  modularity: number;
}

interface NetworkTopologyData {
  network_summary?: NetworkSummary;
  hub_genes?: HubGene[];
  therapeutic_targets?: any[];
  functional_modules?: any[];
  pathway_crosstalk?: any[];
}

interface NetworkTopologyPanelProps {
  networkTopology: NetworkTopologyData | null | undefined;
}

type SortKey = keyof Pick<HubGene,
  'rank' | 'hub_score' | 'betweenness_centrality' | 'pagerank' |
  'degree_centrality' | 'closeness_centrality' | 'eigenvector_centrality' | 'pathway_count'
>;

function hubScoreColor(score: number): string {
  if (score >= 0.7) return '#2E7D32';
  if (score >= 0.4) return '#1565C0';
  if (score >= 0.2) return '#E65100';
  return '#757575';
}

function druggabilityChip(tier: string | null, isDruggable: boolean) {
  if (tier === 'approved') return { label: 'FDA Approved', color: '#4CAF50' };
  if (tier === 'clinical_trial') return { label: 'Clinical Trial', color: '#2196F3' };
  if (tier === 'druggable' || isDruggable) return { label: 'Druggable', color: '#9C27B0' };
  return null;
}

function MetricBar({ value, max = 1, color }: { value: number; max?: number; color: string }) {
  return (
    <LinearProgress
      variant="determinate"
      value={Math.min((value / max) * 100, 100)}
      sx={{
        height: 5, borderRadius: 2, bgcolor: '#F0F0F0',
        '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 2 },
      }}
    />
  );
}

export default function NetworkTopologyPanel({ networkTopology }: NetworkTopologyPanelProps) {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  if (!networkTopology) return null;

  const { network_summary, hub_genes = [] } = networkTopology;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'rank' ? 'asc' : 'desc');
    }
  };

  const sorted = [...hub_genes].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return sortDir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const maxHubScore = Math.max(...hub_genes.map(g => g.hub_score), 0.001);

  const summaryStats = network_summary ? [
    { label: 'Nodes', value: network_summary.total_nodes, tip: 'Total genes in the unified PPI network' },
    { label: 'Edges', value: network_summary.total_edges, tip: 'Protein-protein interactions' },
    { label: 'Density', value: network_summary.density?.toFixed(4), tip: 'Fraction of possible edges present' },
    { label: 'Avg Clustering', value: network_summary.average_clustering?.toFixed(3), tip: 'Average clustering coefficient' },
    { label: 'Avg Degree', value: network_summary.average_degree?.toFixed(1), tip: 'Mean number of connections per gene' },
    { label: 'Modularity', value: network_summary.modularity?.toFixed(3), tip: 'Community structure quality (0–1)' },
    { label: 'Components', value: network_summary.connected_components, tip: 'Number of connected subgraphs' },
    { label: 'Largest Component', value: network_summary.largest_component_size, tip: 'Genes in the main connected component' },
  ] : [];

  const cols: Array<{ id: SortKey; label: string; tip: string; width?: number }> = [
    { id: 'rank', label: '#', tip: 'Hub rank', width: 44 },
    { id: 'hub_score', label: 'Hub Score', tip: 'Composite: 35% betweenness + 25% PageRank + 20% degree + 15% eigenvector + 5% closeness' },
    { id: 'betweenness_centrality', label: 'Betweenness', tip: 'Fraction of shortest paths passing through this gene (35% of hub score)' },
    { id: 'pagerank', label: 'PageRank', tip: 'Network influence by neighbor quality (25% of hub score)' },
    { id: 'degree_centrality', label: 'Degree', tip: 'Normalized number of direct connections (20% of hub score)' },
    { id: 'closeness_centrality', label: 'Closeness', tip: 'Inverse average path length to all other genes (5% of hub score)' },
    { id: 'eigenvector_centrality', label: 'Eigenvector', tip: 'Influence based on neighbor importance (15% of hub score)' },
    { id: 'pathway_count', label: 'Pathways', tip: 'Number of top pathways this gene appears in', width: 80 },
  ];

  return (
    <Paper sx={{ p: 3, mb: 3, border: `2px solid ${GREEN}30`, borderRadius: 2 }}>
      {/* Header */}
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2.5 }}>
        <Box sx={{ p: 1, bgcolor: `${GREEN}15`, borderRadius: 1.5, display: 'flex' }}>
          <Hub sx={{ color: GREEN, fontSize: 26 }} />
        </Box>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: GREEN, lineHeight: 1.2 }}>
            Network Topology Analysis
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Hub gene identification via PageRank, betweenness, closeness, degree &amp; eigenvector centrality on the unified PPI network
          </Typography>
        </Box>
      </Stack>

      {/* Network Summary Stats */}
      {network_summary && (
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
            <AccountTree sx={{ color: GREEN, fontSize: 18 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: GREEN }}>Unified PPI Network</Typography>
          </Stack>
          <Grid container spacing={1.5}>
            {summaryStats.map(({ label, value, tip }) => (
              <Grid item xs={6} sm={3} md={1.5} key={label}>
                <Tooltip title={tip} arrow placement="top">
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 1.5, textAlign: 'center', borderRadius: 1.5,
                      bgcolor: '#F8FAF9', borderColor: `${GREEN}30`,
                      cursor: 'help',
                      '&:hover': { borderColor: GREEN, bgcolor: `${GREEN}08` }
                    }}
                  >
                    <Typography variant="h6" sx={{ color: GREEN, fontWeight: 700, lineHeight: 1, fontSize: '1.1rem' }}>
                      {value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                      {label}
                    </Typography>
                  </Paper>
                </Tooltip>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      <Divider sx={{ mb: 2.5 }} />

      {/* Hub Genes Table */}
      {hub_genes.length > 0 ? (
        <>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
            <TrendingUp sx={{ color: GREEN, fontSize: 18 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: GREEN }}>
              Hub Genes ({hub_genes.length})
            </Typography>
            <Chip
              label="Scores feed therapeutic target ranking"
              size="small"
              icon={<Science sx={{ fontSize: '0.8rem !important' }} />}
              sx={{ bgcolor: `${GOLD}25`, color: '#7A5800', fontWeight: 600, fontSize: '0.65rem', height: 20, ml: 1 }}
            />
          </Stack>

          <TableContainer sx={{ maxHeight: 480 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, bgcolor: '#F8FAF9', color: GREEN, width: 160, position: 'sticky', left: 0, zIndex: 3 }}>
                    Gene
                  </TableCell>
                  {cols.map(col => (
                    <TableCell
                      key={col.id}
                      align="center"
                      sx={{ fontWeight: 700, bgcolor: '#F8FAF9', color: GREEN, width: col.width, whiteSpace: 'nowrap', cursor: 'pointer' }}
                    >
                      <Tooltip title={col.tip} arrow placement="top">
                        <TableSortLabel
                          active={sortKey === col.id}
                          direction={sortKey === col.id ? sortDir : 'desc'}
                          onClick={() => handleSort(col.id)}
                          sx={{ '& .MuiTableSortLabel-icon': { color: `${GREEN} !important` } }}
                        >
                          {col.label}
                        </TableSortLabel>
                      </Tooltip>
                    </TableCell>
                  ))}
                  <TableCell align="center" sx={{ fontWeight: 700, bgcolor: '#F8FAF9', color: GREEN }}>
                    Druggability
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sorted.map((gene, idx) => {
                  const drug = druggabilityChip(gene.druggability_tier, gene.is_druggable);
                  const isTop3 = gene.rank <= 3;
                  return (
                    <TableRow
                      key={gene.gene_symbol}
                      sx={{
                        bgcolor: isTop3 ? '#FFFBF0' : idx % 2 === 0 ? '#FAFAFA' : 'white',
                        '&:hover': { bgcolor: `${GREEN}08` },
                        borderLeft: isTop3 ? `3px solid ${GOLD}` : '3px solid transparent',
                      }}
                    >
                      {/* Gene name — sticky */}
                      <TableCell
                        sx={{
                          fontFamily: 'monospace', fontWeight: 700, fontSize: '0.9rem',
                          color: isTop3 ? GREEN : '#1A1A1A',
                          position: 'sticky', left: 0,
                          bgcolor: isTop3 ? '#FFFBF0' : idx % 2 === 0 ? '#FAFAFA' : 'white',
                          zIndex: 1,
                          display: 'flex', alignItems: 'center', gap: 0.5,
                        }}
                      >
                        {isTop3 && <span style={{ color: GOLD, fontSize: '0.75rem' }}>★</span>}
                        {gene.gene_symbol}
                      </TableCell>

                      {/* Rank */}
                      <TableCell align="center" sx={{ width: 44 }}>
                        <Chip
                          label={gene.rank}
                          size="small"
                          sx={{
                            bgcolor: isTop3 ? GOLD : `${GREEN}20`,
                            color: isTop3 ? '#000' : GREEN,
                            fontWeight: 700, fontSize: '0.7rem', height: 20,
                          }}
                        />
                      </TableCell>

                      {/* Hub Score */}
                      <TableCell align="center">
                        <Tooltip title={`Hub score: ${gene.hub_score.toFixed(4)}`} arrow>
                          <Box>
                            <Typography variant="caption" sx={{ fontWeight: 700, color: hubScoreColor(gene.hub_score), fontFamily: 'monospace', fontSize: '0.78rem' }}>
                              {gene.hub_score.toFixed(3)}
                            </Typography>
                            <MetricBar value={gene.hub_score} max={maxHubScore} color={hubScoreColor(gene.hub_score)} />
                          </Box>
                        </Tooltip>
                      </TableCell>

                      {/* Betweenness */}
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {gene.betweenness_centrality.toFixed(4)}
                        </Typography>
                        <MetricBar value={gene.betweenness_centrality} color="#E65100" />
                      </TableCell>

                      {/* PageRank */}
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {gene.pagerank.toFixed(4)}
                        </Typography>
                        <MetricBar value={gene.pagerank} color="#1565C0" />
                      </TableCell>

                      {/* Degree */}
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {gene.degree_centrality.toFixed(4)}
                        </Typography>
                        <MetricBar value={gene.degree_centrality} color={GREEN} />
                      </TableCell>

                      {/* Closeness */}
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {gene.closeness_centrality.toFixed(4)}
                        </Typography>
                        <MetricBar value={gene.closeness_centrality} color="#512DA8" />
                      </TableCell>

                      {/* Eigenvector */}
                      <TableCell align="center">
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {gene.eigenvector_centrality.toFixed(4)}
                        </Typography>
                        <MetricBar value={gene.eigenvector_centrality} color="#00838F" />
                      </TableCell>

                      {/* Pathway count */}
                      <TableCell align="center">
                        <Chip
                          label={gene.pathway_count}
                          size="small"
                          sx={{ bgcolor: '#E3F2FD', color: '#1565C0', fontWeight: 700, height: 20, fontSize: '0.7rem' }}
                        />
                      </TableCell>

                      {/* Druggability */}
                      <TableCell align="center">
                        {drug ? (
                          <Chip
                            label={drug.label}
                            size="small"
                            sx={{ bgcolor: drug.color, color: 'white', fontWeight: 600, fontSize: '0.65rem', height: 20 }}
                          />
                        ) : (
                          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.65rem' }}>—</Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Legend / Methodology note */}
          <Alert
            severity="info"
            icon={<Hub />}
            sx={{ mt: 2.5, bgcolor: '#E3F2FD', border: '1px solid #BBDEFB' }}
          >
            <Typography variant="body2" sx={{ mb: 0.75 }}>
              <strong>Hub Score:</strong> Composite centrality — 35% Betweenness + 25% PageRank + 20% Degree + 15% Eigenvector + 5% Closeness.
              Genes with high betweenness are network bottlenecks; high PageRank genes are connected to other well-connected hubs.
            </Typography>
            <Typography variant="body2">
              <strong>Therapeutic target link:</strong> Hub scores feed directly into therapeutic target ranking via a centrality bonus
              (Centrality Bonus = hub_score × 0.5), so top hub genes are strongly prioritized as drug target candidates.
            </Typography>
          </Alert>
        </>
      ) : (
        <Alert severity="warning">
          Network topology data was not computed for this analysis. Re-run the analysis to generate hub gene centrality metrics.
        </Alert>
      )}
    </Paper>
  );
}
