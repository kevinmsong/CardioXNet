import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Button,
  Stack,
  Chip,
  Alert,
} from '@mui/material';
import {
  Download,
  BiotechOutlined,
  Hub,
} from '@mui/icons-material';
import api from '../api/endpoints';
import UltraComprehensiveTable from '../components/UltraComprehensiveTable';
import { calculateKeyGenes, getKeyGeneScoreColor } from '../utils/keyGenesUtils';
import { getDruggabilityInfo } from '../utils/druggabilityUtils';
// Topology components removed for speed optimization

export default function ResultsPage() {
  const { analysisId } = useParams<{ analysisId: string }>();

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['analysis-results', analysisId],
    queryFn: async () => {
      try {
        const result = await api.getAnalysisResults(analysisId!);
        return result;
      } catch (error) {
        // Re-throw error to be handled by React Query
        throw error;
      }
    },
    enabled: !!analysisId,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading analysis results...
        </Typography>
      </Box>
    );
  }

  if (!analysisId) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h5" color="error">
          No analysis ID provided
        </Typography>
      </Box>
    );
  }

  if (!results) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h5" color="warning">
          No results data found
        </Typography>
        <Typography variant="body1">
          Analysis ID: {analysisId}
        </Typography>
      </Box>
    );
  }

  const handleDownloadReport = () => {
    const url = `http://localhost:8000/api/v1/analysis/${analysisId}/report/pdf`;
    window.open(url, '_blank');
  };

  const handleDownloadCSV = () => {
    // Export ALL final pathway results with Stage 4c topology data
    const allHypotheses = results?.hypotheses?.hypotheses || [];
    
    if (allHypotheses.length === 0) {
      alert('No results to export');
      return;
    }

    // Build hub gene lookup map from Stage 4c topology
    const hubGeneMap = new Map();
    if (results?.stage_4c_topology?.hub_genes) {
      results.stage_4c_topology.hub_genes.forEach((hub: any) => {
        hubGeneMap.set(hub.gene_symbol, {
          hub_score: hub.hub_score.toFixed(3),
          is_druggable: hub.is_druggable ? 'Yes' : 'No',
          centrality_betweenness: hub.centrality_scores?.betweenness?.toFixed(4) || 'N/A',
          centrality_pagerank: hub.centrality_scores?.pagerank?.toFixed(4) || 'N/A',
        });
      });
    }

    // NES scores calculated in backend with log10 transformation
    const csvData = allHypotheses.map((hypothesis: any) => {
      const pathwayGenes = hypothesis.aggregated_pathway?.pathway?.evidence_genes || [];
      const hubGenesInPathway = pathwayGenes.filter((gene: string) => hubGeneMap.has(gene));
      
      return {
        pathway_name: hypothesis.aggregated_pathway?.pathway?.pathway_name || hypothesis.pathway_name || 'Unknown',
        nes_score: hypothesis.nes_score?.toFixed(3) || '0.000',
        p_adj: hypothesis.aggregated_pathway?.pathway?.p_adj?.toExponential(2) || hypothesis.p_adj?.toExponential(2) || '1.00e+00',
        cardiac_relevance: ((hypothesis.score_components?.cardiac_relevance || 0) * 100).toFixed(1) + '%',
        clinical_significance: ((hypothesis.score_components?.clinical_significance || 0) * 100).toFixed(1) + '%',
        evidence_genes: hypothesis.aggregated_pathway?.pathway?.evidence_genes?.length || hypothesis.evidence_count || 0,
        literature_citations: hypothesis.literature_associations?.total_citations || 0,
        database: hypothesis.aggregated_pathway?.pathway?.source_db || hypothesis.source_db || 'Unknown',
        gtex_cardiac_specificity: ((hypothesis.score_components as any)?.cardiac_specificity_ratio || 0).toFixed(2),
        disease_context_score: ((hypothesis.score_components?.disease_context_score || 0) * 100).toFixed(1) + '%',
        hub_genes_count: hubGenesInPathway.length,
        hub_genes_list: hubGenesInPathway.join(';'),
        top_hub_score: hubGenesInPathway.length > 0 ? 
          Math.max(...hubGenesInPathway.map((g: string) => parseFloat(hubGeneMap.get(g)?.hub_score || '0'))) : 0,
      };
    });

    const csvContent = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map((row: any) => Object.values(row).map((val: any) => 
        typeof val === 'string' && val.includes(',') ? `"${val}"` : val
      ).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cardioxnet_all_results_${analysisId}_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  // Calculate total pathways for display
  const totalPathways = results?.hypotheses?.total_count || 0;

  return (
    <Box sx={{ py: 3 }}>
      {/* Professional Results Header */}
      <Paper
        elevation={4}
        sx={{
          p: { xs: 3, md: 5 },
          mb: 4,
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          color: 'white',
          borderRadius: 3,
          boxShadow: '0 12px 48px rgba(30, 107, 82, 0.2)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Accent decoration */}
        <Box
          sx={{
            position: 'absolute',
            top: -50,
            right: -50,
            width: 350,
            height: 350,
            borderRadius: '50%',
            background: 'rgba(255, 184, 28, 0.08)',
            zIndex: 0,
          }}
        />

        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={3} sx={{ position: 'relative', zIndex: 1 }}>
          <Box>
            <Typography 
              variant="h3" 
              sx={{ 
                fontWeight: 800, 
                mb: 1, 
                color: '#FFFFFF',
                fontSize: { xs: '2rem', md: '2.5rem' },
                letterSpacing: '-0.5px',
              }}
            >
              Analysis Results
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, color: 'rgba(255,255,255,0.85)' }}>
              Analysis ID: <strong>{analysisId}</strong>
            </Typography>
          </Box>
          <Stack direction={{ xs: 'column', md: 'column' }} spacing={1.5} sx={{ minWidth: { md: '220px' } }}>
            <Button 
              variant="outlined" 
              startIcon={<Download />}
              onClick={handleDownloadCSV}
              fullWidth
              sx={{ 
                borderColor: 'white',
                color: 'white',
                fontWeight: 700,
                borderWidth: '2px',
                fontSize: '0.9rem',
                '&:hover': { 
                  borderColor: '#FFB81C',
                  bgcolor: 'rgba(255, 184, 28, 0.15)',
                }
              }}
            >
              Export CSV
            </Button>
            <Button 
              variant="contained" 
              startIcon={<Download />}
              onClick={handleDownloadReport}
              fullWidth
              sx={{ 
                bgcolor: '#FFB81C',
                color: '#000',
                fontWeight: 800,
                boxShadow: '0 6px 16px rgba(255, 184, 28, 0.4)',
                fontSize: '0.9rem',
                '&:hover': { 
                  bgcolor: '#E5A31A',
                  boxShadow: '0 8px 20px rgba(255, 184, 28, 0.5)',
                }
              }}
            >
              Download Report
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Seed Genes - Compact */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: '#FAFAFA' }}>
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600, color: 'primary.main' }}>
          Seed Genes ({results?.seed_genes?.length || 0})
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {results?.seed_genes?.map((gene: any, index: number) => (
            <Chip
              key={index}
              label={typeof gene === 'string' ? gene : (gene.symbol || gene.input_id)}
              size="small"
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                fontWeight: 600,
                fontSize: '0.8rem',
              }}
            />
          ))}
        </Stack>
      </Paper>

      {/* Key Genes - Intersection across pathways with weighted scoring */}
      {(() => {
        const hypotheses = results?.hypotheses?.hypotheses || [];
        const keyGenes = calculateKeyGenes(hypotheses, 1, 15); // Min frequency 1, top 15 genes
        
        if (keyGenes.length === 0) {
          return null;
        }

        return (
          <Paper 
            sx={{ 
              p: 3, 
              mb: 3,
              background: 'linear-gradient(135deg, #E8F5E9 0%, #F1F8E9 100%)',
              border: '2px solid #FFB81C',
              borderRadius: 2
            }}
          >
            <Box sx={{ mb: 2 }}>
              <Typography variant="h5" sx={{ fontWeight: 700, color: '#1E6B52', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Hub sx={{ fontSize: 32, color: '#FFB81C' }} />
                Key Genes
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Pathway Intersection:</strong> Genes appearing across multiple final pathways, weighted by pathway quality (NES score) and rank.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Scoring:</strong> Weighted score = (Frequency × 0.4) + (Avg NES × 0.4) + (Rank Quality × 0.2). Higher scores indicate genes central to multiple high-quality pathways.
              </Typography>
            </Box>

            <Grid container spacing={2}>
              {keyGenes.map((keyGene, index) => (
                <Grid item xs={12} sm={6} md={4} key={keyGene.gene}>
                  <Card 
                    elevation={2}
                    sx={{ 
                      height: '100%',
                      border: `2px solid ${getKeyGeneScoreColor(keyGene.score)}`,
                      '&:hover': {
                        transform: 'scale(1.02)',
                        transition: 'transform 0.2s',
                        boxShadow: 3,
                      }
                    }}
                  >
                    <CardContent>
                      <Stack spacing={1}>
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                          <Typography 
                            variant="h6" 
                            sx={{ 
                              fontWeight: 700, 
                              fontFamily: 'monospace',
                              color: getKeyGeneScoreColor(keyGene.score)
                            }}
                          >
                            {keyGene.gene}
                          </Typography>
                          <Chip 
                            label={`#${index + 1}`} 
                            size="small" 
                            sx={{ 
                              bgcolor: getKeyGeneScoreColor(keyGene.score),
                              color: 'white',
                              fontWeight: 700
                            }} 
                          />
                        </Stack>
                        
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                          <Chip 
                            label={`Score: ${keyGene.score.toFixed(3)}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                          <Chip 
                            label={`${keyGene.frequency} pathway${keyGene.frequency > 1 ? 's' : ''}`}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                          <Chip 
                            label={`NES: ${keyGene.avgNesScore.toFixed(2)}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        </Stack>

                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                          Found in: {keyGene.pathways.slice(0, 2).join(', ')}
                          {keyGene.pathways.length > 2 && ` +${keyGene.pathways.length - 2} more`}
                        </Typography>
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        );
      })()}

      {/* Top Genes Across All Pathways - MOVED ABOVE TABLE FOR VISIBILITY */}
      <Paper 
        sx={{ 
          p: 3, 
          background: 'linear-gradient(135deg, #F5F5F5 0%, #FAFAFA 100%)',
          border: '2px solid #1E6B52',
          borderRadius: 2
        }}
      >
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <BiotechOutlined sx={{ fontSize: 32 }} />
            Important Genes
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            <strong>Novel Discovery:</strong> These genes were prioritized by AI through network expansion, frequency across high-scoring pathways, 
            and aggregate importance scoring—many may not have been in your original seed list.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Scoring:</strong> Importance = (Pathway Frequency<sup>1.2</sup>) × (Avg NES) × (1 + Cardiac Relevance). 
            Druggability annotations from curated databases identify translational opportunities.
          </Typography>
        </Box>

        {(() => {


          // Use top_genes from API if available, otherwise calculate from pathways
          let topGenes: any[] = [];
          
          if (results?.top_genes && Array.isArray(results.top_genes) && results.top_genes.length > 0) {
            // Use pre-calculated top_genes from API
            topGenes = results.top_genes.slice(0, 20).map((gene: any) => ({
              symbol: gene.gene,
              frequency: gene.pathway_count || 0,
              avgNES: gene.importance_score || 0,
              pathways: gene.pathways || [],
              cardiacRelevance: gene.disgenet_cardiac_score || 0,
              importanceScore: gene.final_score || 0
            }));
          } else {
            // Fallback: Calculate from ranked_hypotheses
            const geneScores = new Map<string, {
              symbol: string;
              frequency: number;
              totalNES: number;
              avgNES: number;
              pathways: string[];
              cardiacRelevance: number;
              importanceScore: number;
            }>();

            // Aggregate gene data from all pathways
            results?.ranked_hypotheses?.forEach((hypothesis: any) => {
              const pathwayNES = hypothesis.nes_score || 0;
              const pathwayName = hypothesis.pathway_name || 'Unknown';
              const cardiacRelevance = hypothesis.cardiac_relevance || 0;
              
              // Get genes from pathway
              const genes = hypothesis.evidence_genes || [];
              
              genes.forEach((gene: string) => {
                if (!geneScores.has(gene)) {
                  geneScores.set(gene, {
                    symbol: gene,
                    frequency: 0,
                    totalNES: 0,
                    avgNES: 0,
                    pathways: [],
                    cardiacRelevance: 0,
                    importanceScore: 0
                  });
                }
                
                const geneData = geneScores.get(gene)!;
                geneData.frequency += 1;
                geneData.totalNES += pathwayNES;
                geneData.pathways.push(pathwayName);
                geneData.cardiacRelevance = Math.max(geneData.cardiacRelevance, cardiacRelevance);
              });
            });

            // Calculate importance scores and average NES
            geneScores.forEach((data) => {
              data.avgNES = data.totalNES / data.frequency;
              const rawImportance = Math.pow(data.frequency, 1.2) * data.avgNES * (1 + data.cardiacRelevance);
              data.importanceScore = Math.log10(rawImportance + 1);
            });

            // Sort by importance score and take top 20
            topGenes = Array.from(geneScores.values())
              .sort((a, b) => b.importanceScore - a.importanceScore)
              .slice(0, 20);
          }
          
          return (
            <Grid container spacing={2}>
              {topGenes.map((gene, index) => (
                <Grid item xs={12} sm={6} md={4} lg={2.4} key={gene.symbol}>
                  <Card 
                    sx={{ 
                      height: '100%',
                      border: index < 3 ? '2px solid #FFB81C' : '1px solid #E0E0E0',
                      bgcolor: index < 3 ? '#FFFBF0' : 'white',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-4px)',
                        boxShadow: '0 8px 16px rgba(30, 107, 82, 0.15)',
                        borderColor: 'primary.main'
                      }
                    }}
                  >
                    <CardContent>
                      <Stack spacing={1}>
                        {/* Rank Badge */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Chip 
                            label={`#${index + 1}`}
                            size="small"
                            sx={{
                              bgcolor: index < 3 ? '#FFB81C' : 'primary.main',
                              color: 'white',
                              fontWeight: 700,
                              fontSize: '0.9rem'
                            }}
                          />
                          {index < 3 && (
                            <Typography variant="caption" sx={{ color: '#FFB81C', fontWeight: 700 }}>
                              ⭐ TOP {index + 1}
                            </Typography>
                          )}
                        </Box>

                        {/* Gene Symbol */}
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            fontWeight: 700, 
                            color: 'primary.main',
                            fontFamily: 'monospace',
                            fontSize: '1.2rem'
                          }}
                        >
                          {gene.symbol}
                        </Typography>

                        {/* Druggability Badge */}
                        {(() => {
                          const drugStatus = getDruggabilityInfo(gene.symbol);
                          return (
                            <Chip
                              label={drugStatus.label}
                              size="small"
                              sx={{
                                bgcolor: drugStatus.color,
                                color: 'white',
                                fontWeight: 600,
                                fontSize: '0.65rem',
                                height: 20,
                              }}
                            />
                          );
                        })()}

                        {/* Metrics */}
                        <Stack spacing={0.5}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              Importance:
                            </Typography>
                            <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main' }}>
                              {gene.importanceScore.toFixed(2)}
                            </Typography>
                          </Box>

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              Pathways:
                            </Typography>
                            <Chip 
                              label={gene.frequency}
                              size="small"
                              sx={{ 
                                height: 20,
                                bgcolor: 'info.light',
                                color: 'info.dark',
                                fontWeight: 700,
                                fontSize: '0.7rem'
                              }}
                            />
                          </Box>

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              Avg NES:
                            </Typography>
                            <Typography variant="caption" sx={{ fontWeight: 700 }}>
                              {gene.avgNES.toFixed(2)}
                            </Typography>
                          </Box>


                        </Stack>
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          );
        })()}

        <Stack spacing={2} sx={{ mt: 3 }}>
          <Alert severity="info">
            <Typography variant="body2">
              <strong>Gene Importance Calculation:</strong> Importance = (Frequency<sup>1.2</sup>) × (Avg NES) × (1 + Cardiac Relevance).
              This metric prioritizes genes appearing in multiple high-scoring pathways with strong cardiac context.
            </Typography>
          </Alert>
          

        </Stack>
      </Paper>

      {/* Main Results Table */}
      <Paper sx={{ p: 2, mb: 3, mt: 3 }}>
        <UltraComprehensiveTable
          hypotheses={results?.hypotheses?.hypotheses || []} 
          analysisId={analysisId}
        />
      </Paper>

      {/* Network topology sections removed for speed optimization */}
      {/* Drug Targets section removed per user request */}
    </Box>
  );
}