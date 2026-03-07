import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { AccountTree, BiotechOutlined, MenuBook, Science } from '@mui/icons-material';

const dataSources = ['Reactome', 'KEGG', 'WikiPathways', 'GO:BP', 'STRING', 'GTEx', 'PubMed', 'Cardiac gene set', 'Druggability annotations'];

export default function DocumentationPageSimplified() {
  return (
    <Box sx={{ py: 2 }}>
      <Paper
        elevation={0}
        sx={{
          p: 4,
          mb: 3,
          borderRadius: 3,
          border: '1px solid #D8E8E2',
          background: 'linear-gradient(180deg, #FFFFFF 0%, #F4FAF7 100%)',
        }}
      >
        <Stack spacing={1.25}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <MenuBook sx={{ color: '#1F5A46' }} />
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              Documentation
            </Typography>
          </Stack>
          <Typography variant="body1" color="text.secondary">
            CardioXNet is a funnel-and-filter workflow for seed-gene driven pathway discovery. It
            broadens the search early, then ranks candidates with statistical, semantic, and
            literature-based evidence.
          </Typography>
        </Stack>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Stack spacing={3}>
            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <AccountTree sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      How the Pipeline Works
                    </Typography>
                  </Stack>
                  <Stack spacing={1.5}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        1. Seed genes and disease context
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Input genes are validated and interpreted in the chosen cardiovascular
                        context.
                      </Typography>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        2. Broad primary funnel
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        STRING neighbors and primary enrichment create a wider candidate space than
                        the seed list alone.
                      </Typography>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        3. Secondary discovery
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Genes from leading primary pathways are re-enriched to expose related
                        secondary pathways and replicated signals.
                      </Typography>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        4. Final prioritization
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Cardiac relevance, support count, pathway statistics, and PubMed query hits
                        are combined into the final ranking.
                      </Typography>
                    </Paper>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Science sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Interpreting Results
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    Treat the output as prioritized pathway hypotheses, not proof of novelty. A
                    missing PubMed query hit is evidence of limited retrieval, not confirmation that
                    a pathway is unreported.
                  </Typography>
                  <Stack spacing={1}>
                    <Typography variant="body2">
                      <strong>NES score:</strong> Combined prioritization score using enrichment,
                      support, and weighting factors.
                    </Typography>
                    <Typography variant="body2">
                      <strong>PubMed query hits:</strong> Rapid literature screen for pathway and
                      disease context terms.
                    </Typography>
                    <Typography variant="body2">
                      <strong>Important genes:</strong> Genes recurring across high-ranked pathways.
                    </Typography>
                    <Typography variant="body2">
                      <strong>Novelty language:</strong> Candidate or lower-overlap pathways are
                      leads for review, not validated discoveries.
                    </Typography>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={2}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <BiotechOutlined sx={{ color: '#1F5A46' }} />
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      Data Sources
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {dataSources.map((source) => (
                      <Chip key={source} label={source} variant="outlined" />
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        <Grid item xs={12} md={4}>
          <Stack spacing={3}>
            <Card elevation={0} sx={{ border: '1px solid #D8E8E2', borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack spacing={1.5}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Practical Guidance
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Start with the balanced preset. Move to exploratory mode when the seed list is
                    sparse or highly specific, and use deep evidence mode only when you need a more
                    thorough literature pass.
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Favor lower seed-overlap candidates when you want more pathway expansion away
                    from the original seed genes.
                  </Typography>
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
