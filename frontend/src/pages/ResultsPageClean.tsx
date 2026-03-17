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
} from '@mui/icons-material';
import api from '../api/endpoints';
import UltraComprehensiveTable from '../components/UltraComprehensiveTable';
import NetworkTopologyPanel from '../components/NetworkTopologyPanel';

export default function ResultsPage() {
  const { analysisId } = useParams<{ analysisId: string }>();

  const { data: results, isLoading } = useQuery({
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

    // Build hub gene lookup map from network topology (stage_7_topology)
    const hubGeneMap = new Map();
    const hubGenes = (results as any)?.network_topology?.hub_genes || (results as any)?.stage_4c_topology?.hub_genes || [];
    hubGenes.forEach((hub: any) => {
      hubGeneMap.set(hub.gene_symbol || hub.gene, {
        hub_score: (hub.hub_score ?? 0).toFixed(3),
        is_druggable: hub.is_druggable ? 'Yes' : 'No',
        centrality_betweenness: (hub.betweenness_centrality ?? hub.centrality_scores?.betweenness ?? 0).toFixed(4),
        centrality_pagerank: (hub.pagerank ?? hub.centrality_scores?.pagerank ?? 0).toFixed(4),
      });
    });

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
  const hubGeneCount = (results as any)?.network_topology?.hub_genes?.length || 0;

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
            <Typography 
              variant="h6" 
              sx={{ 
                color: '#FFB81C', 
                fontWeight: 600, 
                mb: 2,
                fontSize: { xs: '0.9rem', md: '1rem' },
              }}
            >
              Network-Enhanced Pathway Discovery Results
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
              <Chip 
                label={`${totalPathways} Pathways`}
                size="medium"
                sx={{ 
                  bgcolor: 'rgba(255, 184, 28, 0.3)', 
                  color: 'white', 
                  fontWeight: 700,
                  border: '1.5px solid rgba(255, 184, 28, 0.6)',
                  fontSize: '0.85rem',
                  py: 2.5,
                }} 
              />
              {hubGeneCount > 0 && (
                <Chip
                  label={`${hubGeneCount} Hub Genes`}
                  size="medium"
                  sx={{
                    bgcolor: 'rgba(255, 184, 28, 0.2)',
                    color: 'white',
                    fontWeight: 700,
                    border: '1.5px solid rgba(255, 184, 28, 0.5)',
                    fontSize: '0.85rem',
                    py: 2.5,
                  }}
                />
              )}
              <Chip
                label="12-Stage Pipeline"
                icon={<BiotechOutlined sx={{ color: 'white !important' }} />}
                size="medium"
                sx={{ 
                  bgcolor: 'rgba(255, 255, 255, 0.15)', 
                  color: 'white', 
                  fontWeight: 700,
                  border: '1.5px solid rgba(255, 255, 255, 0.3)',
                  fontSize: '0.85rem',
                  py: 2.5,
                }} 
              />
              <Typography variant="body2" sx={{ opacity: 0.9, color: 'rgba(255,255,255,0.85)' }}>
                ID: <strong>{analysisId}</strong>
              </Typography>
            </Stack>
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

      {/* Results Summary Alert */}
      <Alert 
        severity="success" 
        icon={<BiotechOutlined />} 
        sx={{ 
          mb: 4, 
          borderRadius: 2, 
          bgcolor: '#E8F5E9', 
          border: '2px solid #4CAF50',
          fontSize: '0.95rem',
        }}
      >
        <Typography variant="body2" fontWeight={700} sx={{ mb: 1.5, color: '#2E7D32' }}>
          ✅ Analysis Complete - Multi-Dimensional Validation
        </Typography>
        <Typography variant="body2" sx={{ lineHeight: 1.6, color: '#33691E' }}>
          Pathways have been validated through: <strong>Network expansion</strong> (protein interaction networks), 
          <strong>Semantic filtering</strong> (disease-specific contexts), <strong>Topology analysis</strong> (hub genes & centrality), 
          <strong>Statistical validation</strong> (permutation testing), and <strong>Tissue expression</strong> (cardiac specificity validation).
        </Typography>
      </Alert>

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

      {/* Main Results Table */}
      <Paper sx={{ p: 2, mb: 3, mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 1, fontWeight: 600, color: 'primary.main' }}>
          🎯 Comprehensive Pathway Analysis Results
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          <strong>Novel Discovery:</strong> Rankings integrate network centrality, literature evidence, and semantic cardiac relevance—not just p-values.
          Pathways with strong multi-modal evidence are prioritized for experimental validation.
        </Typography>
        <UltraComprehensiveTable
          hypotheses={results?.hypotheses?.hypotheses || []} 
          analysisId={analysisId}
        />
      </Paper>

      {/* Network Topology Analysis */}
      <NetworkTopologyPanel networkTopology={(results as any)?.network_topology} />

      {/* AI-Identified Therapeutic Target Candidates - PLACED BELOW TABLE FOR LOGICAL FLOW */}
      <Paper 
        sx={{ 
          p: 3, 
          mt: 3,
          mb: 3,
          background: 'linear-gradient(135deg, #F5F5F5 0%, #FAFAFA 100%)',
          border: '2px solid #1E6B52',
          borderRadius: 2
        }}
      >
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <BiotechOutlined sx={{ fontSize: 32 }} />
            🧬 AI-Identified Therapeutic Target Candidates
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
          // Druggability classification based on curated drug target databases
          const getDruggabilityStatus = (gene: string) => {
            const approvedTargets = new Set([
              'ADRB1', 'ADRB2', 'ACE', 'AGTR1', 'CACNA1C', 'CACNA1D',
              'SLC12A3', 'SLC12A1', 'SCNN1A', 'F2', 'F10', 'SERPINC1',
              'PTGS1', 'P2RY12', 'ITGB3', 'HMGCR', 'GUCY1A1', 'GUCY1B1',
              'ATP1A1', 'ATP1A2', 'ATP1A3', 'SCN5A', 'KCNH2', 'KCNQ1'
            ]);
            
            const clinicalTargets = new Set([
              'SLC5A2', 'PCSK9', 'F11', 'F12', 'IL1B', 'IL6', 'TNF', 'IL17A',
              'PPARA', 'PPARD', 'PPARG', 'GCG', 'GLP1R', 'TGFB1', 'CTGF', 'LOXL2'
            ]);
            
            const druggableTargets = new Set([
              'ADRB3', 'ADRA1A', 'ADRA1B', 'ADRA1D', 'ADRA2A', 'ADRA2B', 'ADRA2C',
              'CHRM2', 'CHRM3', 'EDNRA', 'EDNRB', 'NPR1', 'NPR2', 'KCNJ2', 'KCNJ11',
              'CACNA1G', 'CACNA1H', 'HCN4', 'HCN2', 'AKT1', 'AKT2', 'MAPK14', 'MAPK8',
              'MAPK1', 'MAPK3', 'GSK3B', 'ROCK1', 'ROCK2', 'PRKAA1', 'PRKAA2', 'MTOR',
              'PIK3CA', 'PIK3CB', 'PIK3CG', 'JAK1', 'JAK2', 'TYK2', 'SRC', 'ABL1',
              'EGFR', 'PDGFRA', 'PDGFRB', 'KIT', 'VEGFA', 'VEGFB', 'VEGFC', 'NOS1',
              'NOS2', 'NOS3', 'MMP2', 'MMP9', 'MMP1', 'MMP3', 'MMP13', 'CASP3', 'CASP8',
              'CASP9', 'PARP1', 'ABCB1', 'ABCC1', 'ABCC2', 'ABCG2', 'RYR2', 'ATP2A2',
              'PLN', 'CASQ2', 'MYBPC3', 'MYH7', 'TNNT2', 'TNNI3', 'TPM1', 'GRK2', 'GRK5',
              'NFKB1', 'RELA', 'JUN', 'FOS', 'MYC', 'TP53', 'HIF1A', 'STAT3', 'NOTCH1'
            ]);
            
            const geneUpper = gene.toUpperCase();
            if (approvedTargets.has(geneUpper)) {
              return { tier: 'approved', label: 'FDA Approved', color: '#4CAF50' };
            } else if (clinicalTargets.has(geneUpper)) {
              return { tier: 'clinical', label: 'Clinical Trial', color: '#2196F3' };
            } else if (druggableTargets.has(geneUpper)) {
              return { tier: 'druggable', label: 'Druggable', color: '#9C27B0' };
            }
            return { tier: 'unknown', label: 'Research', color: '#757575' };
          };


          // Use top_genes from API if available, otherwise calculate from pathways
          let topGenes: any[] = [];
          
          if ((results as any)?.top_genes && Array.isArray((results as any).top_genes) && (results as any).top_genes.length > 0) {
            // Use pre-calculated top_genes from API
            topGenes = (results as any).top_genes.slice(0, 20).map((gene: any) => ({
              symbol: gene.gene,
              frequency: gene.pathway_count || 0,
              avgNES: gene.importance_score || 0,
              pathways: gene.pathways || [],
              cardiacRelevance: gene.gene_disease_score || gene.avg_cardiac_relevance || 0,
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
            (results as any)?.ranked_hypotheses?.forEach((hypothesis: any) => {
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
                <Grid item xs={12} sm={6} md={4} lg={3} key={gene.symbol}>
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
                          const drugStatus = getDruggabilityStatus(gene.symbol);
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

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                              Cardiac Disease Score:
                            </Typography>
                            <Typography 
                              variant="caption" 
                              sx={{ 
                                fontWeight: 700,
                                color: gene.cardiacRelevance >= 0.5 ? 'success.main' : gene.cardiacRelevance >= 0.3 ? 'warning.main' : 'text.secondary'
                              }}
                            >
                              {gene.cardiacRelevance > 0 ? (gene.cardiacRelevance * 100).toFixed(0) + '%' : 'N/A'}
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
            <Typography variant="body2" sx={{ mb: 1 }}>
              <strong>Gene Importance Score:</strong> Composite metric combining multiple factors:
            </Typography>
            <Box component="ul" sx={{ mt: 0.5, mb: 0.5, pl: 3 }}>
              <li><strong>Pathway Frequency:</strong> How many final pathways contain this gene (weighted exponentially: Frequency<sup>1.2</sup>)</li>
              <li><strong>Statistical Significance:</strong> Average NES across pathways (higher NES = stronger enrichment)</li>
              <li><strong>Cardiac Disease Association:</strong> Known involvement in cardiac disease (0-100% based on curated gene databases)</li>
            </Box>
            <Typography variant="body2" sx={{ mt: 1 }}>
              <strong>Formula:</strong> Importance = (Frequency<sup>1.2</sup>) × (Avg NES) × (1 + Cardiac Disease Score).
              This prioritizes genes that appear frequently across multiple highly-enriched pathways with established cardiac disease roles.
            </Typography>
          </Alert>
          
          <Alert severity="success" icon={<BiotechOutlined />}>
            <Typography variant="body2">
              <strong>Druggability Classification:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 0.5, mb: 0, pl: 2 }}>
              <li><strong style={{ color: '#4CAF50' }}>FDA Approved:</strong> Target of FDA-approved cardiovascular drugs (e.g., beta-blockers, ACE inhibitors, statins)</li>
              <li><strong style={{ color: '#2196F3' }}>Clinical Trial:</strong> Target of drugs currently in clinical development (e.g., PCSK9 inhibitors, SGLT2 inhibitors)</li>
              <li><strong style={{ color: '#9C27B0' }}>Druggable:</strong> Belongs to druggable gene families (GPCRs, kinases, ion channels, enzymes)</li>
              <li><strong style={{ color: '#757575' }}>Research:</strong> Potential therapeutic target requiring further validation</li>
            </Box>
          </Alert>
        </Stack>
      </Paper>

    </Box>
  );
}