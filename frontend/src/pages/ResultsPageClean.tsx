import { useMemo } from 'react';
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
  LocalHospital,
} from '@mui/icons-material';
import api from '../api/endpoints';
import UltraComprehensiveTable from '../components/UltraComprehensiveTable';
import { calculateKeyGenes, getKeyGeneScoreColor } from '../utils/keyGenesUtils';
import { getDruggabilityInfo } from '../utils/druggabilityUtils';
// Topology components removed for speed optimization

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

  const therapeuticSummary = useMemo(() => {
    const hypotheses = results?.hypotheses?.hypotheses || [];
    const pathwaysWithEvidence = hypotheses
      .map((hypothesis: any) => {
        const scoreComponents = hypothesis.score_components || {};
        return {
          pathwayName:
            hypothesis.aggregated_pathway?.pathway?.pathway_name ||
            hypothesis.pathway_name ||
            'Unknown',
          source: scoreComponents.druggability_source || 'curated',
          approvedTargetCount: scoreComponents.external_approved_target_count || 0,
          clinicalTargetCount: scoreComponents.external_clinical_target_count || 0,
          cardiovascularTargetCount: scoreComponents.cardiovascular_target_count || 0,
          liveTargetCount: scoreComponents.external_target_count || 0,
          targetEvidence: scoreComponents.target_evidence || [],
        };
      })
      .filter((item) => item.liveTargetCount > 0);

    const targetMap = new Map<string, any>();
    pathwaysWithEvidence.forEach((pathway) => {
      pathway.targetEvidence.forEach((target: any) => {
        if (!target?.gene_symbol) {
          return;
        }

        if (!targetMap.has(target.gene_symbol)) {
          targetMap.set(target.gene_symbol, {
            geneSymbol: target.gene_symbol,
            source: target.source || pathway.source,
            knownDrugCount: target.known_drug_count || 0,
            hasApprovedDrug: Boolean(target.has_approved_drug),
            hasClinicalDrug: Boolean(target.has_clinical_drug),
            hasCardiovascularEvidence: Boolean(target.has_cardiovascular_evidence),
            pathways: new Set<string>(),
            topDrugs: [],
          });
        }

        const existing = targetMap.get(target.gene_symbol);
        existing.knownDrugCount = Math.max(existing.knownDrugCount, target.known_drug_count || 0);
        existing.hasApprovedDrug = existing.hasApprovedDrug || Boolean(target.has_approved_drug);
        existing.hasClinicalDrug = existing.hasClinicalDrug || Boolean(target.has_clinical_drug);
        existing.hasCardiovascularEvidence =
          existing.hasCardiovascularEvidence || Boolean(target.has_cardiovascular_evidence);
        existing.pathways.add(pathway.pathwayName);

        (target.top_drugs || []).forEach((drug: any) => {
          if (existing.topDrugs.length >= 3) {
            return;
          }
          const duplicate = existing.topDrugs.some(
            (entry: any) => entry.name === drug.name && entry.disease === drug.disease
          );
          if (!duplicate) {
            existing.topDrugs.push(drug);
          }
        });
      });
    });

    const topTargets = Array.from(targetMap.values())
      .map((target) => ({
        ...target,
        pathwayCount: target.pathways.size,
        pathways: Array.from(target.pathways),
      }))
      .sort((a, b) => {
        const scoreA =
          (a.hasApprovedDrug ? 1000 : 0) +
          (a.hasCardiovascularEvidence ? 200 : 0) +
          (a.hasClinicalDrug ? 100 : 0) +
          a.knownDrugCount +
          a.pathwayCount * 5;
        const scoreB =
          (b.hasApprovedDrug ? 1000 : 0) +
          (b.hasCardiovascularEvidence ? 200 : 0) +
          (b.hasClinicalDrug ? 100 : 0) +
          b.knownDrugCount +
          b.pathwayCount * 5;
        return scoreB - scoreA;
      })
      .slice(0, 6);

    return {
      pathwayCount: pathwaysWithEvidence.length,
      approvedPathwayCount: pathwaysWithEvidence.filter((item) => item.approvedTargetCount > 0).length,
      cardiovascularPathwayCount: pathwaysWithEvidence.filter(
        (item) => item.cardiovascularTargetCount > 0
      ).length,
      topTargets,
    };
  }, [results?.hypotheses?.hypotheses]);

  const summaryMetrics = useMemo(() => {
    const hypotheses = results?.hypotheses?.hypotheses || [];
    const nesValues = hypotheses.map((hypothesis: any) => hypothesis.nes_score || 0).sort((a: number, b: number) => a - b);
    const medianNES =
      nesValues.length === 0
        ? 0
        : nesValues.length % 2 === 1
          ? nesValues[(nesValues.length - 1) / 2]
          : (nesValues[nesValues.length / 2 - 1] + nesValues[nesValues.length / 2]) / 2;

    return {
      finalPathways: hypotheses.length,
      literatureBacked: hypotheses.filter(
        (hypothesis: any) => (hypothesis.literature_associations?.total_citations || 0) > 0
      ).length,
      tissueValidated: hypotheses.filter(
        (hypothesis: any) => Boolean(hypothesis.score_components?.tissue_validation_passed)
      ).length,
      approvedTargetPathways: hypotheses.filter(
        (hypothesis: any) => (hypothesis.score_components?.approved_drug_count || 0) > 0
      ).length,
      medianNES,
    };
  }, [results?.hypotheses?.hypotheses]);

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
    const url = api.getReportDownloadUrl(analysisId!, 'pdf');
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
        therapeutic_source: (hypothesis.score_components as any)?.druggability_source || 'curated',
        live_target_genes: (hypothesis.score_components as any)?.external_target_count || 0,
        approved_target_genes: (hypothesis.score_components as any)?.approved_drug_count || 0,
        clinical_target_genes: (hypothesis.score_components as any)?.clinical_trial_count || 0,
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

  return (
    <Box sx={{ py: 3 }}>
      {/* Professional Results Header */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 5 },
          mb: 4,
          background: 'linear-gradient(180deg, #FFFFFF 0%, #F3FAF7 100%)',
          color: '#163C30',
          borderRadius: 3,
          border: '1px solid #D8E8E2',
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
            background: 'rgba(31, 90, 70, 0.05)',
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
                color: '#163C30',
                fontSize: { xs: '2rem', md: '2.5rem' },
                letterSpacing: '-0.5px',
              }}
            >
              Analysis Results
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, color: '#4D6A60' }}>
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
                borderColor: '#1F5A46',
                color: '#1F5A46',
                fontWeight: 700,
                fontSize: '0.9rem',
                '&:hover': { 
                  borderColor: '#163C30',
                  bgcolor: 'rgba(31, 90, 70, 0.06)',
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
                bgcolor: '#1F5A46',
                color: '#FFFFFF',
                fontWeight: 700,
                fontSize: '0.9rem',
                '&:hover': { 
                  bgcolor: '#163C30',
                }
              }}
            >
              Download Report
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} lg={2.4}>
          <Card sx={{ height: '100%', border: '1px solid #D8E8E2', boxShadow: 'none' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Final Pathways</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {summaryMetrics.finalPathways}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Pathways that survived the full funnel and final ranking.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={2.4}>
          <Card sx={{ height: '100%', border: '1px solid #D8E8E2', boxShadow: 'none' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Median NES</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {summaryMetrics.medianNES.toFixed(2)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Middle-ranked enrichment strength across final pathways.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={2.4}>
          <Card sx={{ height: '100%', border: '1px solid #D8E8E2', boxShadow: 'none' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Literature-backed</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {summaryMetrics.literatureBacked}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Final pathways with PubMed query hits in the report data.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={2.4}>
          <Card sx={{ height: '100%', border: '1px solid #D8E8E2', boxShadow: 'none' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">GTEx Tissue-passing</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {summaryMetrics.tissueValidated}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Final pathways passing cardiac tissue validation in Stage 8.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} lg={2.4}>
          <Card sx={{ height: '100%', border: '1px solid #D8E8E2', boxShadow: 'none' }}>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Approved-target Pathways</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {summaryMetrics.approvedTargetPathways}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Final pathways with at least one approved therapeutic target.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

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
      {therapeuticSummary.pathwayCount > 0 && (
        <Paper
          sx={{
            p: 3,
            mb: 3,
            background: 'linear-gradient(135deg, #F9FCFB 0%, #F1F7F4 100%)',
            border: '1px solid #D8E8E2',
            borderRadius: 2,
          }}
        >
          <Box sx={{ mb: 2 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main', mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <LocalHospital sx={{ fontSize: 30, color: '#FFB81C' }} />
              Therapeutic Target Evidence
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Stage 8 now annotates final pathways with live therapeutic target evidence from Open Targets, with curated fallback when no live match is available.
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Chip label={`${therapeuticSummary.pathwayCount} pathways with live target evidence`} color="primary" variant="outlined" />
            <Chip label={`${therapeuticSummary.approvedPathwayCount} pathways with approved targets`} sx={{ borderColor: '#1E6B52', color: '#1E6B52' }} variant="outlined" />
            <Chip label={`${therapeuticSummary.cardiovascularPathwayCount} pathways with cardiovascular drug evidence`} sx={{ borderColor: '#FFB81C', color: '#A66C00' }} variant="outlined" />
          </Stack>

          <Grid container spacing={2}>
            {therapeuticSummary.topTargets.map((target) => (
              <Grid item xs={12} md={6} lg={4} key={target.geneSymbol}>
                <Card
                  sx={{
                    height: '100%',
                    border: '1px solid #D8E8E2',
                    boxShadow: 'none',
                  }}
                >
                  <CardContent>
                    <Stack spacing={1.25}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="h6" sx={{ fontWeight: 700, color: 'primary.main', fontFamily: 'monospace' }}>
                          {target.geneSymbol}
                        </Typography>
                        <Chip
                          size="small"
                          label={target.hasApprovedDrug ? 'Approved target' : target.hasClinicalDrug ? 'Clinical target' : 'Tractable'}
                          sx={{
                            bgcolor: target.hasApprovedDrug ? '#1E6B52' : target.hasClinicalDrug ? '#FFB81C' : '#4A9B7F',
                            color: '#FFFFFF',
                            fontWeight: 600,
                          }}
                        />
                      </Stack>

                      <Typography variant="caption" color="text.secondary">
                        Source: {target.source} · {target.knownDrugCount} known drugs · in {target.pathwayCount} final pathway{target.pathwayCount === 1 ? '' : 's'}
                      </Typography>

                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {target.hasCardiovascularEvidence && (
                          <Chip size="small" label="Cardiovascular evidence" sx={{ bgcolor: '#FFF6DF', color: '#8A5A00' }} />
                        )}
                        {target.pathways.slice(0, 2).map((pathway: string) => (
                          <Chip key={pathway} size="small" label={pathway} variant="outlined" sx={{ maxWidth: '100%' }} />
                        ))}
                      </Stack>

                      {target.topDrugs.length > 0 && (
                        <Stack spacing={0.5}>
                          {target.topDrugs.slice(0, 2).map((drug: any) => (
                            <Typography key={`${target.geneSymbol}-${drug.name}-${drug.disease}`} variant="body2" color="text.secondary">
                              <strong>{drug.name}</strong>{drug.disease ? ` for ${drug.disease}` : ''}{drug.phase ? ` (Phase ${drug.phase})` : ''}
                            </Typography>
                          ))}
                        </Stack>
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

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
            <strong>Priority Ranking:</strong> These genes were prioritized through network
            expansion, recurrence across high-scoring pathways, and aggregate importance scoring.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Scoring:</strong> Importance = (Pathway Frequency<sup>1.2</sup>) × (Avg NES) × (1 + Cardiac Relevance). 
            Curated annotations and Open Targets evidence identify translational opportunities where available.
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
              importanceScore: gene.final_score || 0,
              druggabilityTier: gene.druggability_tier || 'unknown',
              isFDAApproved: Boolean(gene.is_fda_approved),
              isClinicalTrial: Boolean(gene.is_clinical_trial),
              druggabilitySource: gene.druggability_source || null,
              externalDrugEvidence: gene.external_drug_evidence || null,
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
                          const drugStatus =
                            gene.isFDAApproved
                              ? { label: 'Approved Target', color: '#1E6B52' }
                              : gene.isClinicalTrial
                                ? { label: 'Clinical Target', color: '#FFB81C' }
                                : gene.druggabilityTier && gene.druggabilityTier !== 'unknown'
                                  ? { label: 'Tractable', color: '#4A9B7F' }
                                  : getDruggabilityInfo(gene.symbol);
                          return (
                            <Stack spacing={0.5}>
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
                              {gene.druggabilitySource && (
                                <Typography variant="caption" color="text.secondary">
                                  {gene.druggabilitySource}
                                </Typography>
                              )}
                              {gene.externalDrugEvidence?.approved_name && (
                                <Typography variant="caption" color="text.secondary">
                                  {gene.externalDrugEvidence.approved_name}
                                </Typography>
                              )}
                            </Stack>
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
                          {gene.externalDrugEvidence && (
                            <>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                  Known Drugs:
                                </Typography>
                                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                                  {gene.externalDrugEvidence.known_drug_count || 0}
                                </Typography>
                              </Box>

                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                  Max Phase:
                                </Typography>
                                <Typography variant="caption" sx={{ fontWeight: 700 }}>
                                  {gene.externalDrugEvidence.max_clinical_phase || 0}
                                </Typography>
                              </Box>
                            </>
                          )}


                        </Stack>
                        {gene.externalDrugEvidence && (
                          <Stack spacing={0.75}>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                              {gene.externalDrugEvidence.has_cardiovascular_evidence && (
                                <Chip
                                  label={`Cardiovascular evidence (${gene.externalDrugEvidence.cardiovascular_example_count || 0})`}
                                  size="small"
                                  color="success"
                                  variant="outlined"
                                  sx={{ height: 22, fontSize: '0.68rem' }}
                                />
                              )}
                              {(gene.externalDrugEvidence.tractability_labels || []).slice(0, 2).map((label: string) => (
                                <Chip
                                  key={`${gene.symbol}-${label}`}
                                  label={label}
                                  size="small"
                                  variant="outlined"
                                  sx={{ height: 22, fontSize: '0.68rem' }}
                                />
                              ))}
                            </Stack>
                            {!!gene.externalDrugEvidence.top_drugs?.length && (
                              <Typography variant="caption" color="text.secondary">
                                Top drugs: {gene.externalDrugEvidence.top_drugs
                                  .slice(0, 2)
                                  .map((drug: { name?: string }) => drug.name || 'Unknown')
                                  .join(', ')}
                              </Typography>
                            )}
                          </Stack>
                        )}
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
          <Alert severity="info">
            <Typography variant="body2">
              <strong>Therapeutic Evidence:</strong> Important gene cards include curated target annotations and, when available,
              Open Targets-derived evidence such as known drug counts, highest clinical phase, cardiovascular disease examples,
              tractability labels, and example drugs.
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
