import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Stack,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Chip,
} from '@mui/material';
import {
  Science,
  TrendingUp,
  AccountTree,
  Timeline,
  Speed,
  BiotechOutlined,
  Storage,
  Cloud,
  Favorite,
} from '@mui/icons-material';

export default function DocumentationPageSimplified() {
  return (
    <Box sx={{ py: 2 }}>
      {/* Clean Header */}
      <Paper
        elevation={2}
        sx={{
          p: 3,
          mb: 3,
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          color: 'white',
          borderRadius: 2,
        }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600, mb: 0.5, color: 'white' }}>
            Documentation
          </Typography>
          <Typography variant="subtitle1" sx={{ color: 'white', fontWeight: 500 }}>
            NETS (Neighborhood Enrichment Triage and Scoring) Algorithm for Cardiovascular Pathway Discovery
          </Typography>
        </Box>
      </Paper>

      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} md={8}>
          {/* Overview */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                Overview
              </Typography>
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.7 }}>
                CardioXNet implements the <strong>NETS (Neighborhood Enrichment Triage and Scoring)</strong> algorithm 
                specifically optimized for cardiovascular disease pathway discovery. The system processes 
                seed genes through a multi-stage pipeline to identify cardiac-relevant pathways and their 
                associations with cardiovascular conditions.
              </Typography>
              
              <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2, color: '#1E6B52' }}>
                Key Features
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon><BiotechOutlined color="primary" /></ListItemIcon>
                  <ListItemText 
                    primary="Cardiovascular-Focused Analysis" 
                    secondary="Specialized pathway prioritization using 700+ curated cardiac terms and 200+ cardiovascular disease genes"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><AccountTree color="primary" /></ListItemIcon>
                  <ListItemText 
                    primary="Multi-Stage NETS Pipeline" 
                    secondary="Neighborhood enrichment → Primary pathways → Secondary pathways → Semantic filtering → Final scoring"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Timeline color="primary" /></ListItemIcon>
                  <ListItemText 
                    primary="Evidence Integration" 
                    secondary="Literature validation (PubMed), tissue expression (GTEx), and multi-database cross-referencing"
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>

          {/* Cardiac Context Influence */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Favorite color="error" />
                How Cardiac Context Influences Results
              </Typography>
              
              <Typography variant="body1" paragraph sx={{ lineHeight: 1.7, mt: 2 }}>
                The user-provided <strong>cardiac disease context</strong> (e.g., "cardiovascular disease", "heart failure", "arrhythmia") 
                is integrated throughout the entire analysis pipeline to ensure cardiac-relevant pathway discovery:
              </Typography>

              <Stack spacing={1.5} sx={{ mt: 2 }}>
                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#FFF8E1' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                    1. Semantic Scoring (+30% Boost)
                  </Typography>
                  <Typography variant="body2" fontSize="0.875rem">
                    Pathways with disease context terms receive priority scoring.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#E8F5E9' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                    2. Strict Cardiac Name Filter
                  </Typography>
                  <Typography variant="body2" fontSize="0.875rem">
                    ALL pathways must have explicit cardiac/cardiovascular/heart terminology in names. 
                    Generic metabolic/inflammatory pathways are filtered out.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#E3F2FD' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                    3. Cardiac Disease Score (0-1)
                  </Typography>
                  <Typography variant="body2" fontSize="0.875rem">
                    Quantitative scoring based on 200+ curated cardiovascular disease genes.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#FCE4EC' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                    4. Literature Validation
                  </Typography>
                  <Typography variant="body2" fontSize="0.875rem">
                    PubMed queries for cardiovascular disease literature evidence.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#F3E5F5' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontWeight: 600 }}>
                    5. Cardiac Tissue Expression
                  </Typography>
                  <Typography variant="body2" fontSize="0.875rem">
                    GTEx cardiac tissue specificity ratios prioritize heart-specific genes.
                  </Typography>
                </Paper>
              </Stack>

              <Typography variant="body2" sx={{ mt: 2, p: 2, bgcolor: '#FFF3E0', borderRadius: 1, fontStyle: 'italic' }}>
                <strong>Result:</strong> The combination of these 5 cardiac-focused filters ensures that final pathway results 
                are highly specific to cardiovascular disease and directly relevant to your research context.
              </Typography>
            </CardContent>
          </Card>

          {/* Databases and APIs */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Storage color="primary" />
                Databases Cross-Referenced
              </Typography>
              
              <Stack spacing={2} sx={{ mt: 2 }}>
                <Box>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    Pathway Databases
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip label="Reactome" color="primary" variant="outlined" />
                    <Chip label="KEGG" color="primary" variant="outlined" />
                    <Chip label="WikiPathways" color="primary" variant="outlined" />
                    <Chip label="Gene Ontology (GO:BP)" color="primary" variant="outlined" />
                    <Chip label="Gene Ontology (GO:MF)" color="primary" variant="outlined" />
                    <Chip label="Gene Ontology (GO:CC)" color="primary" variant="outlined" />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    Comprehensive pathway enrichment across 6 major databases covering signaling, metabolic, disease, and functional pathways.
                  </Typography>
                </Box>

                <Divider />

                <Box>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    Protein-Protein Interaction
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip label="STRING Database" color="secondary" variant="outlined" />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    High-confidence protein interactions (score &gt; 0.4) for functional neighborhood expansion.
                  </Typography>
                </Box>

                <Divider />

                <Box>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    Tissue Expression
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip label="GTEx (Genotype-Tissue Expression)" color="error" variant="outlined" />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    Cardiac tissue-specific gene expression data (TPM values) for heart tissue specificity scoring.
                  </Typography>
                </Box>

                <Divider />

                <Box>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    Druggability & Clinical
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip label="FDA Approved Genes" color="success" variant="outlined" />
                    <Chip label="Clinical Trial Genes" color="warning" variant="outlined" />
                    <Chip label="Druggable Gene Families" color="info" variant="outlined" />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    Curated databases of therapeutic targets for druggability classification.
                  </Typography>
                </Box>

                <Divider />

                <Box>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    Cardiovascular Disease Genes
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                    <Chip label="200+ Curated CVD Genes" color="error" variant="outlined" />
                  </Stack>
                  <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                    Manually curated database of cardiovascular disease-associated genes with cardiac disease scores (0-1 scale).
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>

          {/* APIs Used */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Cloud color="primary" />
                External APIs Queried
              </Typography>
              
              <Stack spacing={2} sx={{ mt: 2 }}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    g:Profiler API
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Purpose:</strong> Gene Set Enrichment Analysis (GSEA) for pathway enrichment<br />
                    <strong>Endpoint:</strong> https://biit.cs.ut.ee/gprofiler/api/<br />
                    <strong>Usage:</strong> Primary and secondary pathway enrichment with multiple databases
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    STRING API
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Purpose:</strong> Protein-protein interaction network data<br />
                    <strong>Endpoint:</strong> https://string-db.org/api/<br />
                    <strong>Usage:</strong> Functional neighborhood expansion with confidence threshold &gt; 0.4
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="subtitle1" color="primary" gutterBottom sx={{ fontWeight: 600 }}>
                    PubMed E-utilities API
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Purpose:</strong> Literature mining and citation validation<br />
                    <strong>Endpoint:</strong> https://eutils.ncbi.nlm.nih.gov/entrez/eutils/<br />
                    <strong>Usage:</strong> Query cardiovascular disease literature for gene-pathway associations
                  </Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>

          {/* Algorithm Workflow */}
          <Card elevation={1}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                NETS Algorithm Workflow
              </Typography>
              
              <Stack spacing={2} sx={{ mt: 2 }}>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 1: Seed Gene Validation
                  </Typography>
                  <Typography variant="body2">
                    Input genes are validated against gene databases and converted to standard symbols.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 2: Functional Neighborhood (STRING PPI)
                  </Typography>
                  <Typography variant="body2">
                    Expands seed genes using STRING protein-protein interactions (confidence &gt; 0.4) to build a functional neighborhood.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 3: Primary Pathway Enrichment
                  </Typography>
                  <Typography variant="body2">
                    Performs GSEA on functional neighborhood genes against 6 pathway databases (Reactome, KEGG, WikiPathways, GO).
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 4: Secondary Pathway Discovery
                  </Typography>
                  <Typography variant="body2">
                    Extracts genes from primary pathways and performs second-level enrichment to discover related pathways.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 5: Pathway Aggregation & Lineage Tracking
                  </Typography>
                  <Typography variant="body2">
                    Aggregates pathways across databases, tracks complete lineage (Seed → Primary → Secondary → Final), and calculates support scores.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 6: Semantic Filtering (Cardiac Context)
                  </Typography>
                  <Typography variant="body2">
                    Applies strict cardiac term filtering using 700+ curated cardiovascular terms. Only pathways with explicit cardiac terminology pass.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 7: NES Scoring
                  </Typography>
                  <Typography variant="body2">
                    Calculates Normalized Enrichment Scores combining statistical significance, evidence strength, and cardiac relevance.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 8: Enhanced Validation
                  </Typography>
                  <Typography variant="body2">
                    Integrates GTEx tissue expression, druggability analysis, and seed gene tracing for comprehensive validation.
                  </Typography>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA' }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    Stage 9: Literature Mining (PubMed)
                  </Typography>
                  <Typography variant="body2">
                    Queries PubMed for cardiovascular disease literature linking seed genes to discovered pathways.
                  </Typography>
                </Paper>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Performance Metrics */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
                Performance
              </Typography>
              
              <Stack spacing={2}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Analysis Time
                  </Typography>
                  <Typography variant="h6" color="primary">
                    2-4 minutes
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Optimized pipeline without network topology analysis
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Pathway Coverage
                  </Typography>
                  <Typography variant="h6" color="primary">
                    1000+ Total
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Filtered to cardiac-relevant pathways only
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Databases
                  </Typography>
                  <Typography variant="h6" color="primary">
                    6 Integrated
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Reactome, KEGG, WikiPathways, GO (BP/MF/CC)
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>

          {/* Key Metrics */}
          <Card elevation={1}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="primary" sx={{ fontWeight: 600 }}>
                <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                Key Metrics Explained
              </Typography>
              
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    NES Score
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Normalized Enrichment Score combining statistical significance, evidence count, and cardiac relevance
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    Clinical Impact
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Multi-factor score: literature validation + druggability + tissue specificity
                  </Typography>
                </Box>
                
                <Box>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    GTEx Cardiac Specificity
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ratio of cardiac tissue expression vs. other tissues (higher = more heart-specific)
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="primary" gutterBottom>
                    Literature Reported
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Number of PubMed citations linking genes to pathways in cardiovascular context
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
