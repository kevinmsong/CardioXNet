import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Grid,
  Avatar,
} from '@mui/material';
import {
  ExpandMore,
  AccountTree,
  Timeline as TimelineIcon,
  Hub,
  TrendingUp,
  Link,
  Group,
  Favorite,
} from '@mui/icons-material';

interface SeedGene {
  input_id: string;
  symbol: string;
  entrez_id: string;
}

interface FunctionalNeighborhood {
  seed_genes: SeedGene[];
  neighbors: SeedGene[];
  size: number;
  interactions: Array<{
    gene1: string;
    gene2: string;
    source: string;
    score?: number;
  }>;
}

interface PathwayLineageProps {
  hypothesis: any;
  functionalNeighborhood: FunctionalNeighborhood;
  allResults: any;
}

export default function PathwayLineageVisualization({ 
  hypothesis, 
  functionalNeighborhood,
  allResults
}: PathwayLineageProps) {
  const pathway = hypothesis?.aggregated_pathway?.pathway;
  const tracedSeedGenes = hypothesis?.traced_seed_genes || [];
  const evidenceGenes = pathway?.evidence_genes || [];
  const sourcePrimaryPathways = hypothesis?.aggregated_pathway?.source_primary_pathways || [];
  
  // Get primary pathways from results
  const primaryPathways = allResults?.stage_2a?.pathway_details || [];
  
  // Find the primary pathways that led to this final pathway
  const contributingPrimaries = primaryPathways.filter((p: any) => 
    sourcePrimaryPathways.includes(p.pathway_id)
  );
  
  // Find interactions involving pathway genes
  const pathwayInteractions = functionalNeighborhood?.interactions?.filter(
    interaction => 
      evidenceGenes.includes(interaction.gene1) || 
      evidenceGenes.includes(interaction.gene2)
  ) || [];

  // Group interactions by source database
  const interactionsBySource = pathwayInteractions.reduce((acc, interaction) => {
    const source = interaction.source || 'Unknown';
    if (!acc[source]) acc[source] = [];
    acc[source].push(interaction);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <Card elevation={2} sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <TimelineIcon color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Pathway Discovery Lineage
          </Typography>
        </Box>

        {/* Specific Lineage Visualization */}
        <Card variant="outlined" sx={{ mb: 3, borderColor: 'primary.main', borderWidth: 2 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccountTree color="primary" />
              Discovery Path: Seed Genes → Primary Pathways → Final Pathway
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              This visualization shows the exact path that led to the discovery of this final pathway hypothesis.
            </Typography>

            <Grid container spacing={2}>
              {/* Step 1: Contributing Seed Genes */}
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'primary.50', borderRadius: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', mx: 'auto', mb: 1 }}>
                    <Group />
                  </Avatar>
                  <Typography variant="subtitle2" fontWeight={600} color="primary.main">
                    Step 1: Contributing Seed Genes
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Genes that specifically contributed to this pathway
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'center' }}>
                    {tracedSeedGenes.length > 0 ? tracedSeedGenes.map((gene: string, idx: number) => (
                      <Chip
                        key={idx}
                        label={gene}
                        size="small"
                        color="primary"
                        sx={{ fontWeight: 600, fontSize: '0.75rem' }}
                      />
                    )) : (
                      <Typography variant="caption" color="text.secondary">
                        No specific seed genes traced
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Grid>

              {/* Step 2: Primary Pathways */}
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'secondary.50', borderRadius: 2 }}>
                  <Avatar sx={{ bgcolor: 'secondary.main', mx: 'auto', mb: 1 }}>
                    <TrendingUp />
                  </Avatar>
                  <Typography variant="subtitle2" fontWeight={600} color="secondary.main">
                    Step 2: Primary Pathways
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Initial pathways enriched from seed gene neighborhoods
                  </Typography>
                  <Box sx={{ maxHeight: 120, overflow: 'auto' }}>
                    {contributingPrimaries.length > 0 ? contributingPrimaries.map((primary: any, idx: number) => (
                      <Tooltip key={idx} title={`${primary.pathway_name} (${primary.source_db}) - P-adj: ${primary.p_adj?.toExponential(2)}`} arrow>
                        <Chip
                          label={`${primary.pathway_name.substring(0, 20)}${primary.pathway_name.length > 20 ? '...' : ''}`}
                          size="small"
                          color="secondary"
                          variant="outlined"
                          sx={{ m: 0.25, fontSize: '0.7rem' }}
                        />
                      </Tooltip>
                    )) : (
                      <Typography variant="caption" color="text.secondary">
                        Primary pathway details not available
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Grid>

              {/* Step 3: Final Pathway */}
              <Grid item xs={12} md={4}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'success.50', borderRadius: 2 }}>
                  <Avatar sx={{ bgcolor: 'success.main', mx: 'auto', mb: 1 }}>
                    <AccountTree />
                  </Avatar>
                  <Typography variant="subtitle2" fontWeight={600} color="success.main">
                    Step 3: Final Pathway
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Aggregated and validated cardiovascular disease pathway
                  </Typography>
                  <Box sx={{ p: 1, bgcolor: 'white', borderRadius: 1, border: '1px solid', borderColor: 'success.main' }}>
                    <Typography variant="body2" fontWeight={600} color="success.main">
                      {pathway?.pathway_name || 'Unknown Pathway'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {pathway?.source_db || 'Unknown'} • NES: {hypothesis?.nes_score?.toFixed(2) || 'N/A'}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            </Grid>

            {/* Connection Arrows */}
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2, mb: 1 }}>
              <Typography variant="h6" color="primary.main">→</Typography>
              <Box sx={{ width: 40 }} />
              <Typography variant="h6" color="secondary.main">→</Typography>
            </Box>
          </CardContent>
        </Card>

        <Grid container spacing={3}>
          {/* Stage 1: Seed Genes */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'primary.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
                    <Group sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Stage 1: Input Seed Genes
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Original genes provided for analysis
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  {functionalNeighborhood?.seed_genes?.map((gene, idx) => (
                    <Chip
                      key={idx}
                      label={gene.symbol}
                      size="small"
                      color={tracedSeedGenes.includes(gene.symbol) ? 'primary' : 'default'}
                      sx={{ fontWeight: 600 }}
                    />
                  ))}
                </Box>
                {tracedSeedGenes.length > 0 && (
                  <Box sx={{ p: 1, bgcolor: 'primary.50', borderRadius: 1 }}>
                    <Typography variant="body2" color="primary.main" fontWeight={600}>
                      Contributing to this pathway: {tracedSeedGenes.join(', ')}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Stage 2: Functional Neighborhood */}
          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'secondary.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
                    <Hub sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Stage 2: Network Assembly
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Protein-protein interaction network expansion
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip label={`${functionalNeighborhood?.size || 0} Total Genes`} color="secondary" size="small" />
                  <Chip label={`${functionalNeighborhood?.neighbors?.length || 0} Neighbors`} variant="outlined" size="small" />
                  <Chip label={`${functionalNeighborhood?.interactions?.length || 0} Interactions`} variant="outlined" size="small" />
                </Box>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="body2" fontWeight={600}>
                      Database Sources
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List dense>
                      {Object.entries(interactionsBySource).map(([source, interactions]) => (
                        <ListItem key={source} sx={{ py: 0.5 }}>
                          <ListItemIcon sx={{ minWidth: 36 }}>
                            <Link fontSize="small" color="primary" />
                          </ListItemIcon>
                          <ListItemText
                            primary={source}
                            secondary={`${interactions.length} interactions with pathway genes`}
                            primaryTypographyProps={{ fontSize: '0.875rem' }}
                            secondaryTypographyProps={{ fontSize: '0.75rem' }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          </Grid>

          {/* Stage 3: Pathway Enrichment */}
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'success.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'success.main', width: 32, height: 32 }}>
                    <AccountTree sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Stage 3: Pathway Enrichment
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Statistical enrichment analysis
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip label={`${pathway?.source_db || 'Unknown'} Database`} color="success" size="small" />
                  <Chip label={`${evidenceGenes.length} Evidence Genes`} variant="outlined" size="small" />
                  <Chip label={`P-adj: ${pathway?.p_adj?.toExponential(2) || 'N/A'}`} variant="outlined" size="small" />
                </Box>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="body2" fontWeight={600}>
                      Evidence Genes
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {evidenceGenes.map((gene: string, idx: number) => {
                        const isSeedGene = functionalNeighborhood?.seed_genes?.some(sg => sg.symbol === gene);
                        const isNeighbor = functionalNeighborhood?.neighbors?.some(ng => ng.symbol === gene);
                        
                        return (
                          <Tooltip
                            key={idx}
                            title={isSeedGene ? 'Original seed gene' : isNeighbor ? 'Network neighbor' : 'Pathway gene'}
                            arrow
                          >
                            <Chip
                              label={gene}
                              size="small"
                              color={isSeedGene ? 'primary' : isNeighbor ? 'secondary' : 'default'}
                              sx={{ fontWeight: isSeedGene ? 600 : 400 }}
                            />
                          </Tooltip>
                        );
                      })}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          </Grid>

          {/* Stage 4: Cardiac Tissue Validation */}
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'error.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'error.main', width: 32, height: 32 }}>
                    <Favorite sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Stage 4: Cardiac Validation
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  GTEx cardiac tissue expression validation
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip label="GTEx Portal API" color="error" size="small" />
                  <Chip label="Heart-Specific" variant="outlined" size="small" />
                  <Chip 
                    label={`${evidenceGenes.filter((g: any) => g.cardiac_validated || false).length} Validated`} 
                    variant="outlined" 
                    size="small" 
                  />
                </Box>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="body2" fontWeight={600}>
                      Cardiac Tissues
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <List dense>
                      <ListItem sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <Favorite fontSize="small" color="error" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Heart - Atrial Appendage"
                          secondary="Primary cardiac tissue validation"
                          primaryTypographyProps={{ fontSize: '0.875rem' }}
                          secondaryTypographyProps={{ fontSize: '0.75rem' }}
                        />
                      </ListItem>
                      <ListItem sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <Favorite fontSize="small" color="error" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Heart - Left Ventricle"
                          secondary="Secondary cardiac tissue validation"
                          primaryTypographyProps={{ fontSize: '0.875rem' }}
                          secondaryTypographyProps={{ fontSize: '0.75rem' }}
                        />
                      </ListItem>
                    </List>
                  </AccordionDetails>
                </Accordion>
              </CardContent>
            </Card>
          </Grid>

          {/* Stage 5: Final Scoring */}
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ height: '100%', borderLeft: '4px solid', borderLeftColor: 'warning.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'warning.main', width: 32, height: 32 }}>
                    <TrendingUp sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography variant="h6" fontWeight={600}>
                    Stage 5: Scoring & Validation
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Multi-component biological scoring
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                  <Chip label={`NES: ${hypothesis?.nes_score?.toFixed(2) || 'N/A'}`} color="warning" size="small" />
                  <Chip label={`Rank: #${hypothesis?.rank || 'N/A'}`} variant="outlined" size="small" />
                  {hypothesis?.support_count && (
                    <Chip label={`${hypothesis.support_count} Supporting Pathways`} variant="outlined" size="small" />
                  )}
                </Box>

                {hypothesis?.score_components && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="body2" fontWeight={600}>
                        Score Components
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <List dense>
                        {Object.entries(hypothesis.score_components).map(([component, value]) => (
                          <ListItem key={component} sx={{ py: 0.25 }}>
                            <ListItemText
                              primary={component.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              secondary={typeof value === 'number' ? value.toFixed(3) : String(value)}
                              primaryTypographyProps={{ fontSize: '0.875rem' }}
                              secondaryTypographyProps={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </AccordionDetails>
                  </Accordion>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Summary */}
        <Divider sx={{ my: 3 }} />
        <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" fontWeight={600} gutterBottom>
            Discovery Summary
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This pathway was discovered by analyzing <strong>{tracedSeedGenes.length > 0 ? tracedSeedGenes.length : 'multiple'} seed gene(s)</strong>{' '}
            through a functional neighborhood of <strong>{functionalNeighborhood?.size || 0} genes</strong>, 
            resulting in statistical enrichment with <strong>{evidenceGenes.length} evidence genes</strong>{' '}
            and a final NES score of <strong>{hypothesis?.nes_score?.toFixed(2) || 'N/A'}</strong>.
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}