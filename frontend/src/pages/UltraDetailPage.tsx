import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Stack,
  Card,
  CardContent,
  Button,
  CircularProgress,
  LinearProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  Rating,
} from '@mui/material';
import {
  ArrowBack,
  Science,
  TrendingUp,
  Favorite,
  Assessment,
  MenuBook,
} from '@mui/icons-material';
import api from '../api/endpoints';
import PathwayLineage from '../components/PathwayLineage';
import {
  normalizeHypothesis,
  calculateClinicalSignificance,
  calculateTissueSpecificity,
  calculatePathwayComplexity,
  formatPValue,
} from '../utils/hypothesisUtils';

export default function UltraDetailPageFixed() {
  const { analysisId, pathwayId } = useParams();
  const navigate = useNavigate();

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['analysis-results', analysisId],
    queryFn: () => api.getAnalysisResults(analysisId!),
    enabled: !!analysisId,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading pathway data: {String(error)}
        </Alert>
        <Button variant="contained" onClick={() => navigate(`/results/${analysisId}`)}>
          Back to Results
        </Button>
      </Box>
    );
  }

  const hypothesisData = results?.hypotheses?.hypotheses?.find(
    (h: any) => {
      // Check both top-level pathway_id and aggregated_pathway.pathway.pathway_id
      const topLevelId = h.pathway_id;
      const aggregatedId = h.aggregated_pathway?.pathway?.pathway_id;
      return topLevelId === pathwayId || aggregatedId === pathwayId;
    }
  );

  if (!hypothesisData) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Pathway not found in analysis results
        </Alert>
        <Button variant="contained" onClick={() => navigate(`/results/${analysisId}`)}>
          Back to Results
        </Button>
      </Box>
    );
  }

  const normalized = normalizeHypothesis(hypothesisData);
  const clinicalSignificance = calculateClinicalSignificance(hypothesisData);
  const tissueSpecificity = calculateTissueSpecificity(hypothesisData);
  const pathwayComplexity = calculatePathwayComplexity(hypothesisData);

  return (
    <Box sx={{ py: 2, px: 3 }}>
      {/* Header */}
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate(`/results/${analysisId}`)}
        sx={{ mb: 3 }}
      >
        Back to Results
      </Button>

      {/* Main Header Card */}
      <Paper
        elevation={4}
        sx={{
          p: 4,
          mb: 4,
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          color: 'white',
          borderRadius: 3,
        }}
      >
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <Science sx={{ fontSize: 40, color: '#FFB81C' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
              {normalized.pathway_name}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip 
                label={`Rank #${hypothesisData.rank || 'N/A'}`} 
                sx={{ bgcolor: '#FFB81C', color: '#000', fontWeight: 700 }} 
              />
              <Chip label={normalized.source_db} sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
              <Chip label={`ID: ${normalized.pathway_id}`} variant="outlined" sx={{ color: 'white', borderColor: 'white' }} />
            </Stack>
          </Box>
        </Stack>
      </Paper>

      {/* Pathway Lineage Visualization */}
      {hypothesisData.lineage && (
        <PathwayLineage lineage={hypothesisData.lineage} />
      )}

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Card elevation={3}>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <TrendingUp color="primary" />
                <Typography variant="subtitle2" color="text.secondary">
                  NES Score
                </Typography>
              </Stack>
              <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {normalized.nes_score.toFixed(3)}
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={Math.min((normalized.nes_score / 5) * 100, 100)} 
                sx={{ mt: 2, height: 8, borderRadius: 4 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card elevation={3}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Clinical Impact
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 700, color: '#ff9800' }}>
                {(clinicalSignificance * 100).toFixed(0)}%
              </Typography>
              <Rating 
                value={clinicalSignificance * 5} 
                readOnly 
                precision={0.1}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Evidence Genes Section */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Science color="primary" />
          Evidence Genes ({normalized.key_nodes.length})
        </Typography>
        <Divider sx={{ my: 2 }} />
        
        <Typography variant="body2" color="text.secondary" paragraph>
          These genes were identified through network expansion and show significant association with this pathway.
        </Typography>

        {normalized.key_nodes.length > 0 ? (
          <>
            <Grid container spacing={1}>
              {normalized.key_nodes.slice(0, 30).map((node, idx) => (
                <Grid item key={idx}>
                  <Chip
                    label={`${node.gene} (${node.centrality?.toFixed(3) || 'N/A'})`}
                    size="small"
                    color={node.role === 'seed' ? 'secondary' : 'default'}
                    sx={{ fontFamily: 'monospace' }}
                  />
                </Grid>
              ))}
            </Grid>

            {normalized.key_nodes.length > 30 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                Showing 30 of {normalized.key_nodes.length} genes. Download CSV for complete list.
              </Typography>
            )}
          </>
        ) : (
          <Alert severity="info" sx={{ mt: 2 }}>
            Evidence genes are being calculated. This pathway contains {normalized.evidence_count || 'multiple'} genes from the database.
            The seed genes below are the primary contributors to this pathway discovery.
          </Alert>
        )}
      </Paper>

      {/* Seed Genes Section */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Favorite sx={{ color: '#e91e63' }} />
          Seed Genes ({normalized.seed_genes.length})
        </Typography>
        <Divider sx={{ my: 2 }} />
        
        <Typography variant="body2" color="text.secondary" paragraph>
          Original input genes that contributed to this pathway discovery.
        </Typography>

        <Stack direction="row" spacing={1} flexWrap="wrap">
          {normalized.seed_genes.map((gene, idx) => (
            <Chip
              key={idx}
              label={gene}
              color="secondary"
              sx={{ fontFamily: 'monospace', fontWeight: 600 }}
            />
          ))}
        </Stack>
      </Paper>

      {/* Pathway Genes Section */}
      {hypothesisData.aggregated_pathway?.pathway?.evidence_genes && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Assessment color="primary" />
            Pathway Genes ({hypothesisData.aggregated_pathway.pathway.evidence_genes.length})
          </Typography>
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="body2" color="text.secondary" paragraph>
            All genes contained in this pathway according to the {normalized.source_db} database (Pathway ID: {normalized.pathway_id}).
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {hypothesisData.aggregated_pathway.pathway.evidence_genes.map((gene: string, idx: number) => (
              <Chip
                key={idx}
                label={gene}
                size="small"
                variant="outlined"
                color="primary"
                sx={{ fontFamily: 'monospace' }}
              />
            ))}
          </Stack>
        </Paper>
      )}

      {/* Pathway Statistics */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Pathway Statistics
        </Typography>
        <Divider sx={{ my: 2 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="Database Source" 
                  secondary={normalized.source_db}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="Pathway ID" 
                  secondary={normalized.pathway_id}
                  primaryTypographyProps={{ fontWeight: 600 }}
                  secondaryTypographyProps={{ fontFamily: 'monospace' }}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="Evidence Gene Count" 
                  secondary={normalized.evidence_count}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItem>
            </List>
          </Grid>

          <Grid item xs={12} md={6}>
            <List dense>
              <ListItem>
                <ListItemText 
                  primary="GTEx Cardiac Specificity" 
                  secondary={`${(tissueSpecificity * 100).toFixed(1)}%`}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="Pathway Complexity" 
                  secondary={`${(pathwayComplexity * 100).toFixed(0)}%`}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="Literature Citations" 
                  secondary={normalized.literature_citations || 'Not available'}
                  primaryTypographyProps={{ fontWeight: 600 }}
                />
              </ListItem>
            </List>
          </Grid>
        </Grid>
      </Paper>

      {/* Literature Citations */}
      {normalized.literature_citations > 0 && hypothesisData.literature_associations?.associations && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MenuBook color="primary" />
            Literature Evidence ({normalized.literature_citations} citations)
          </Typography>
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="body2" color="text.secondary" paragraph>
            PubMed citations linking seed genes to this pathway. Click to view full articles.
          </Typography>

          {hypothesisData.literature_associations.associations.map((assoc: any, idx: number) => (
            <Box key={idx} sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1, color: 'primary.main' }}>
                {assoc.seed_gene} ({assoc.citation_count} {assoc.citation_count === 1 ? 'citation' : 'citations'})
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {assoc.pmids?.map((pmid: string, pidx: number) => (
                  <Button
                    key={pidx}
                    size="small"
                    variant="outlined"
                    href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    startIcon={<MenuBook />}
                    sx={{ textTransform: 'none' }}
                  >
                    PMID: {pmid}
                  </Button>
                ))}
              </Stack>
            </Box>
          ))}
        </Paper>
      )}

      {/* Interpretation Guide */}
      <Paper elevation={2} sx={{ p: 3, bgcolor: '#f5f5f5' }}>
        <Typography variant="h6" gutterBottom>
          Interpretation Guide
        </Typography>
        <Divider sx={{ my: 2 }} />

        <Typography variant="body2" paragraph>
          <strong>NES Score:</strong> Normalized Enrichment Score combining statistical significance, network centrality, and literature support. Higher scores (typically &gt; 2.5) indicate stronger pathway associations.
        </Typography>

        <Typography variant="body2" paragraph>
          <strong>Clinical Impact:</strong> Translational potential score based on statistical significance, literature validation, druggability annotations, and cardiac tissue specificity. Higher scores suggest greater therapeutic potential.
        </Typography>

        <Typography variant="body2" paragraph>
          <strong>Evidence Genes:</strong> Genes from network expansion (STRING database) that overlap with this pathway. Hub genes with high centrality scores are prioritized as therapeutic targets.
        </Typography>

        <Typography variant="body2">
          <strong>Pathway Discovery:</strong> Identified through AI-powered network expansion and multi-dimensional validation using the NETS algorithm.
        </Typography>
      </Paper>
    </Box>
  );
}

