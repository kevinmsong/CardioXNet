import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { AccountTree, BiotechOutlined, MenuBook, Science } from '@mui/icons-material';

const pipelineSteps = [
  {
    title: '1. Input normalization',
    body:
      'Seed genes are validated, normalized, and interpreted in the selected cardiovascular disease context before downstream enrichment begins.',
  },
  {
    title: '2. Functional neighborhood',
    body:
      'STRING interaction expansion builds the local functional neighborhood that seeds the first enrichment pass.',
  },
  {
    title: '3. Primary pathway enrichment',
    body:
      'g:Profiler enrichment across Reactome, KEGG, WikiPathways, and GO:BP creates the first broad candidate set.',
  },
  {
    title: '4. Secondary pathway discovery',
    body:
      'Genes from leading primary pathways are re-enriched, with bounded literature expansion, to recover replicated or less obvious downstream pathways.',
  },
  {
    title: '5. Aggregation and NES scoring',
    body:
      'Pathways are aggregated across supporting primaries, deduplicated, and ranked with NES-based scoring before later filters are applied.',
  },
  {
    title: '6. Semantic filtering and validation',
    body:
      'Semantic cardiac relevance, redundancy reduction, GTEx support, degree-preserving permutation testing when enabled, and curated plus bounded live Open Targets evidence refine the ranked set.',
  },
  {
    title: '7. Literature and final filter',
    body:
      'PubMed pathway-level review and seed tracing annotate the ranked candidates, then a final strict cardiac-name filter retains the displayed final pathways and refreshes literature evidence on that set.',
  },
  {
    title: '8. Important genes and reports',
    body:
      'Important genes are generated from top ranked pathways with DisGeNET and therapeutic evidence, and the analysis is exported through the results page and downloadable reports.',
  },
];

const interpretationItems = [
  {
    label: 'NES score',
    value:
      'Combined prioritization score reflecting enrichment strength, support, pathway-level weighting, and ranking features.',
  },
  {
    label: 'Support count',
    value:
      'Number of upstream primary pathways supporting the final aggregated pathway. Higher support implies stronger replication across the funnel.',
  },
  {
    label: 'GTEx cardiac specificity',
    value:
      'Tissue-expression evidence indicating whether pathway genes show cardiac expression support consistent with the disease setting.',
  },
  {
    label: 'PubMed query hits',
    value:
      'Rapid literature screen for pathway and disease-context terms. Zero hits indicate limited retrieval, not proof that a pathway is unreported.',
  },
  {
    label: 'Therapeutic target evidence',
    value:
      'Target-evidence layer summarizing approved, clinical, or tractable pathway genes and representative drug examples when available.',
  },
  {
    label: 'Important genes',
    value:
      'Genes recurring across higher-ranked pathways with weighting for pathway quality, recurrence, and translational relevance.',
  },
];

const scopeItems = [
  {
    title: 'Strength',
    body:
      'The workflow combines network expansion, replicated pathway support, tissue context, therapeutic tractability, and literature review in one ranked output.',
  },
  {
    title: 'Limitation',
    body:
      'Novelty is inferred indirectly from filtering and literature retrieval gaps. It is not established by exhaustive negative evidence across all pathway synonyms and corpora.',
  },
  {
    title: 'Best use',
    body:
      'Use CardioXNet to prioritize pathways for expert review, downstream mechanistic follow-up, and experimental validation rather than as a final proof engine.',
  },
];

const sourceGroups = [
  {
    title: 'Pathway Databases',
    sources: ['Reactome', 'KEGG', 'WikiPathways', 'GO:BP'],
  },
  {
    title: 'Network and Validation',
    sources: ['STRING', 'GTEx', 'Open Targets'],
  },
  {
    title: 'Literature and Curated Evidence',
    sources: ['PubMed', 'Curated cardiac gene sets', 'Curated druggability annotations'],
  },
];

const reviewSteps = [
  'Start with a balanced run unless the seed list is unusually sparse or unusually specific.',
  'Review high-support pathways first, then inspect lower-overlap candidates for potentially less obvious biology.',
  'For stronger translational confidence, favor pathways where GTEx, permutation support, and therapeutic evidence point in the same direction.',
  'Before claiming novelty, manually review pathway synonyms, related disease terms, and primary literature.',
];

export default function DocumentationPageSimplified() {
  return (
    <Box sx={{ py: 2 }}>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 4 },
          mb: 3,
          borderRadius: 3,
          border: '1px solid #D8E8E2',
          background: 'linear-gradient(180deg, #FFFFFF 0%, #F4FAF7 100%)',
        }}
      >
        <Stack spacing={2} sx={{ maxWidth: '900px' }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <MenuBook sx={{ color: '#1F5A46' }} />
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              Documentation
            </Typography>
          </Stack>
          <Typography variant="body1" color="text.secondary">
            CardioXNet is a seed-gene driven cardiovascular pathway prioritization workflow. It
            expands from validated seed genes into interaction neighborhoods and enrichment results,
            then progressively filters candidates with replication, cardiac relevance, tissue
            evidence, therapeutic tractability, and literature review.
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label="Seed-gene driven" variant="outlined" />
            <Chip label="Funnel and filter workflow" variant="outlined" />
            <Chip label="Multi-layer validation" variant="outlined" />
            <Chip label="Hypothesis prioritization, not proof of novelty" variant="outlined" />
          </Stack>
        </Stack>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Stack spacing={3}>
            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2.5}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <AccountTree sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Pipeline Overview
                    </Typography>
                  </Stack>
                  <Stack spacing={1.5}>
                    {pipelineSteps.map((step) => (
                      <Paper
                        key={step.title}
                        variant="outlined"
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          borderColor: '#D8E8E2',
                          backgroundColor: '#FCFEFD',
                        }}
                      >
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                          {step.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {step.body}
                        </Typography>
                      </Paper>
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2.5}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Science sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Reading the Output
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    Interpret the output as ranked pathway hypotheses for review. The workflow is
                    designed to prioritize plausible candidates, not to certify that a pathway is
                    absent from prior literature.
                  </Typography>
                  <Divider />
                  <Stack spacing={1.75}>
                    {interpretationItems.map((item) => (
                      <Box key={item.label}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.4 }}>
                          {item.label}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {item.value}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2.5}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Science sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Scientific Scope
                    </Typography>
                  </Stack>
                  <Stack spacing={1.5}>
                    {scopeItems.map((item) => (
                      <Paper key={item.title} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                          {item.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {item.body}
                        </Typography>
                      </Paper>
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2.5}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <BiotechOutlined sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Data Sources
                    </Typography>
                  </Stack>
                  <Grid container spacing={2}>
                    {sourceGroups.map((group) => (
                      <Grid item xs={12} md={4} key={group.title}>
                        <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: '100%' }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                            {group.title}
                          </Typography>
                          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                            {group.sources.map((source) => (
                              <Chip key={source} label={source} size="small" variant="outlined" />
                            ))}
                          </Stack>
                        </Paper>
                      </Grid>
                    ))}
                  </Grid>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Stack spacing={3}>
            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={1.5}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    At a Glance
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    The workflow broadens early, then becomes stricter later. Final pathways are
                    therefore meant to be both discoverable and reviewable rather than merely
                    abundant.
                  </Typography>
                  <Stack spacing={1}>
                    <Typography variant="body2" color="text.secondary">
                      Seed genes define the starting biological context.
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Primary and secondary enrichment expand beyond direct seed overlap.
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Validation layers add tissue, permutation, and therapeutic evidence.
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Literature review remains necessary before making strong novelty claims.
                    </Typography>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={1.5}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Recommended Review Workflow
                  </Typography>
                  <Stack spacing={1.25}>
                    {reviewSteps.map((step, index) => (
                      <Stack key={step} direction="row" spacing={1.25} alignItems="flex-start">
                        <Chip
                          label={index + 1}
                          size="small"
                          sx={{
                            bgcolor: '#1F5A46',
                            color: '#FFFFFF',
                            fontWeight: 700,
                            minWidth: 28,
                          }}
                        />
                        <Typography variant="body2" color="text.secondary" sx={{ pt: 0.2 }}>
                          {step}
                        </Typography>
                      </Stack>
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Alert severity="warning">
              Final pathway review should still include manual literature reading, synonym checks,
              and domain judgement before claiming a pathway is genuinely unreported.
            </Alert>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
