import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Card,
  CardContent,
  Tooltip,
  Stack,
  Divider,
  Alert,
  AlertTitle,
} from '@mui/material';
import {
  TrendingUp,
  AccountTree,
  Science,
  Hub as HubIcon,
  BiotechOutlined,
  Medication,
  NetworkCheck,
} from '@mui/icons-material';

interface TopologyInsightsProps {
  topologyData: any;
}

const TopologyInsights: React.FC<TopologyInsightsProps> = ({ topologyData }) => {
  if (!topologyData) {
    return (
      <Alert severity="info" sx={{ mt: 3 }}>
        <AlertTitle>Network Topology Analysis Unavailable</AlertTitle>
        Topology analysis requires completed pathway enrichment. Please run a complete analysis to view network insights.
      </Alert>
    );
  }

  // Safely extract topology data with defaults
  const network_summary = topologyData?.network_summary || {};
  const hub_genes = topologyData?.hub_genes || [];
  const therapeutic_targets = topologyData?.therapeutic_targets || [];
  const functional_modules = topologyData?.functional_modules || [];
  const pathway_crosstalk = topologyData?.pathway_crosstalk || [];

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <NetworkCheck color="primary" />
        Network Topology Insights (Stage 4c)
      </Typography>

      <Alert severity="success" sx={{ mb: 3 }}>
        <AlertTitle>What is Network Topology Analysis?</AlertTitle>
        Stage 4c analyzes the protein-protein interaction network formed by genes across all top pathways.
        It identifies <strong>hub genes</strong> (central nodes with many connections), prioritizes <strong>therapeutic targets</strong> 
        based on druggability and network importance, detects <strong>functional modules</strong> (communities of related genes), 
        and reveals <strong>pathway crosstalk</strong> (how pathways interact).
      </Alert>

      {/* Network Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#E3F2FD' }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h4" color="primary">{network_summary?.total_nodes || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">Network Genes</Typography>
                </Box>
                <AccountTree sx={{ fontSize: 40, color: '#1976d2', opacity: 0.3 }} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#F3E5F5' }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h4" color="secondary">{network_summary?.total_edges || 0}</Typography>
                  <Typography variant="body2" color="text.secondary">Interactions</Typography>
                </Box>
                <NetworkCheck sx={{ fontSize: 40, color: '#9c27b0', opacity: 0.3 }} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#E8F5E9' }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h4" color="success.main">
                    {network_summary?.density ? (network_summary.density * 100).toFixed(1) : '0.0'}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">Network Density</Typography>
                </Box>
                <HubIcon sx={{ fontSize: 40, color: '#2e7d32', opacity: 0.3 }} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%', bgcolor: '#FFF3E0' }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h4" color="warning.main">
                    {network_summary?.average_clustering ? (network_summary.average_clustering * 100).toFixed(1) : '0.0'}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">Clustering</Typography>
                </Box>
                <Science sx={{ fontSize: 40, color: '#ed6c02', opacity: 0.3 }} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Hub Genes Table */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <HubIcon color="primary" />
          Hub Genes (Top 30 by Composite Centrality)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Hub genes are central nodes in the network with many connections. High centrality indicates biological importance and potential drug targets.
        </Typography>
        <Divider sx={{ mb: 2 }} />
        
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell><strong>Rank</strong></TableCell>
                <TableCell><strong>Gene</strong></TableCell>
                <TableCell><strong>Hub Score</strong></TableCell>
                <TableCell><strong>Betweenness</strong></TableCell>
                <TableCell><strong>PageRank</strong></TableCell>
                <TableCell><strong>Pathways</strong></TableCell>
                <TableCell><strong>Druggability</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {hub_genes?.map((hub: any) => (
                <TableRow key={hub.gene_symbol} hover>
                  <TableCell>{hub.rank}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold" color="primary">
                      {hub.gene_symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={hub.hub_score.toFixed(3)} 
                      size="small" 
                      color={hub.hub_score > 0.5 ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell>{hub.betweenness_centrality.toFixed(3)}</TableCell>
                  <TableCell>{hub.pagerank.toFixed(3)}</TableCell>
                  <TableCell>
                    <Tooltip title={hub.pathways?.join(', ') || 'N/A'}>
                      <Chip label={hub.pathway_count} size="small" />
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    {hub.is_druggable ? (
                      <Chip 
                        label={hub.druggability_tier || 'druggable'} 
                        size="small" 
                        color="success"
                        icon={<Medication />}
                      />
                    ) : (
                      <Chip label="N/A" size="small" variant="outlined" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Therapeutic Targets Table */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Medication color="error" />
          Prioritized Therapeutic Targets (Top 20)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Therapeutic targets are druggable hub genes ranked by a composite score: 40% network centrality + 30% druggability + 20% evidence + 10% pathway diversity.
        </Typography>
        <Divider sx={{ mb: 2 }} />
        
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell><strong>Rank</strong></TableCell>
                <TableCell><strong>Gene</strong></TableCell>
                <TableCell><strong>Therapeutic Score</strong></TableCell>
                <TableCell><strong>Centrality</strong></TableCell>
                <TableCell><strong>Druggability</strong></TableCell>
                <TableCell><strong>Evidence</strong></TableCell>
                <TableCell><strong>Pathways</strong></TableCell>
                <TableCell><strong>Known Drugs</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {therapeutic_targets?.map((target: any) => (
                <TableRow key={target.gene_symbol} hover>
                  <TableCell>{target.rank}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold" color="error">
                      {target.gene_symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={(target.therapeutic_score * 100).toFixed(0)} 
                      size="small" 
                      color={target.therapeutic_score > 0.7 ? 'error' : target.therapeutic_score > 0.5 ? 'warning' : 'default'}
                    />
                  </TableCell>
                  <TableCell>{(target.centrality_score * 100).toFixed(0)}</TableCell>
                  <TableCell>{(target.druggability_score * 100).toFixed(0)}</TableCell>
                  <TableCell>{(target.evidence_score * 100).toFixed(0)}</TableCell>
                  <TableCell>
                    <Tooltip title={target.pathways?.join(', ') || 'N/A'}>
                      <Chip label={target.pathway_count} size="small" color="primary" />
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    {target.drugs && target.drugs.length > 0 ? (
                      <Tooltip title={target.drugs.join(', ')}>
                        <Chip label={target.drugs.length} size="small" color="success" />
                      </Tooltip>
                    ) : (
                      <Chip label="0" size="small" variant="outlined" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Functional Modules */}
      {functional_modules && functional_modules.length > 0 && (
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BiotechOutlined color="secondary" />
            Functional Modules ({functional_modules.length} detected)
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Functional modules are communities of genes that cluster together in the network, often representing distinct biological functions.
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Grid container spacing={2}>
            {functional_modules.map((module: any) => (
              <Grid item xs={12} md={6} key={module.module_id}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                      Module {module.module_id}
                    </Typography>
                    <Stack spacing={1}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">Size:</Typography>
                        <Chip label={`${module.size} genes`} size="small" />
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="text.secondary">Density:</Typography>
                        <Typography variant="body2">{(module.internal_density * 100).toFixed(1)}%</Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>Enriched Pathways:</Typography>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {module.enriched_pathways?.map((pathway: string, idx: number) => (
                            <Chip key={idx} label={pathway.substring(0, 30) + '...'} size="small" variant="outlined" />
                          ))}
                        </Stack>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">Hub Genes:</Typography>
                        <Typography variant="body2">{module.hub_genes?.join(', ')}</Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Pathway Crosstalk */}
      {pathway_crosstalk && pathway_crosstalk.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TrendingUp color="warning" />
            Pathway Crosstalk ({pathway_crosstalk.length} interactions)
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Pathway crosstalk reveals how pathways interact through shared genes, indicating biological coordination and potential therapeutic synergies.
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <TableContainer sx={{ maxHeight: 500 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Pathway 1</strong></TableCell>
                  <TableCell><strong>Pathway 2</strong></TableCell>
                  <TableCell><strong>Shared Genes</strong></TableCell>
                  <TableCell><strong>Interaction Strength</strong></TableCell>
                  <TableCell><strong>Type</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pathway_crosstalk.slice(0, 20).map((interaction: any, idx: number) => (
                  <TableRow key={idx} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {interaction.pathway_1}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {interaction.pathway_2}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Tooltip title={interaction.shared_genes?.join(', ') || ''}>
                        <Chip label={interaction.shared_genes?.length || 0} size="small" color="primary" />
                      </Tooltip>
                    </TableCell>
                    <TableCell>{interaction.interaction_strength.toFixed(2)}</TableCell>
                    <TableCell>
                      <Chip 
                        label={interaction.crosstalk_type} 
                        size="small" 
                        color={interaction.crosstalk_type === 'overlap' ? 'warning' : 'default'}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
};

export default TopologyInsights;
