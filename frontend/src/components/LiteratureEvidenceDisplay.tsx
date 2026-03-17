import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  List,
  ListItem,
  Avatar,
  IconButton,
  Tooltip,
  Divider,
  Alert,
  Button,
} from '@mui/material';
import {
  MenuBook,
  OpenInNew,
  Science,
  Article,
  VerifiedUser,
  Warning,
} from '@mui/icons-material';
import { useState } from 'react';

interface Citation {
  pmid: string;
  title: string;
  authors: string;
  year: number;
  relevance_score: number;
  journal?: string;
  abstract?: string;
  mesh_terms?: string[];
}

interface LiteratureEvidenceProps {
  hypothesis: any;
  allResults?: any;
  citations?: Citation[];
}

const PUBMED_URL = (pmid: string) => `https://pubmed.ncbi.nlm.nih.gov/${pmid}`;

function formatAuthors(authors: string) {
  if (!authors) return '';
  const list = authors.split(',').map(a => a.trim());
  return list.length <= 2 ? authors : `${list[0]} et al.`;
}

export default function LiteratureEvidenceDisplay({
  hypothesis,
  allResults = {},
  citations = [],
}: LiteratureEvidenceProps) {
  const [expandedPmid, setExpandedPmid] = useState<string | null>(null);

  const pathway = hypothesis?.aggregated_pathway?.pathway;
  const pathwayId = pathway?.pathway_id;
  const tracedSeedGenes = hypothesis?.traced_seed_genes || [];
  const literatureAssociations = hypothesis?.literature_associations || {};

  // ── Step 1: collect all citations from every possible source ──────────────
  const citationMap = new Map<string, Citation>();

  // Priority 1: structured top_citations with full metadata (stage_4_literature)
  const topCitations: any[] =
    allResults?.stage_4_literature?.[pathwayId]?.top_citations ||
    allResults?.stage_4_literature?.hypothesis_citations?.[pathwayId] ||
    allResults?.literature?.hypothesis_citations?.[pathwayId] ||
    hypothesis?.literature_evidence?.citations ||
    citations;

  for (const c of topCitations) {
    const pmid = String(c.pmid || '');
    if (!pmid) continue;
    citationMap.set(pmid, {
      pmid,
      title: c.title || '',
      authors: c.authors || '',
      year: c.year || 0,
      relevance_score: c.relevance_score ?? c.relevance ?? 0,
      journal: c.journal || '',
      abstract: c.abstract || '',
      mesh_terms: c.mesh_terms || [],
    });
  }

  // Priority 2: per-gene association arrays — add any PMIDs not yet seen
  const associations: any[] = literatureAssociations?.associations || [];
  for (const assoc of associations) {
    // flat pmids array
    for (const pmid of (assoc.pmids || [])) {
      const key = String(pmid);
      if (!citationMap.has(key)) {
        citationMap.set(key, {
          pmid: key,
          title: assoc.title || '',       // assoc-level title if present
          authors: assoc.authors || '',
          year: assoc.year || 0,
          relevance_score: assoc.relevance_score || 0,
          journal: assoc.journal || '',
        });
      }
    }
    // nested citations array
    for (const cit of (assoc.citations || [])) {
      const key = String(cit.pmid || '');
      if (!key) continue;
      if (!citationMap.has(key)) {
        citationMap.set(key, {
          pmid: key,
          title: cit.title || '',
          authors: cit.authors || '',
          year: cit.year || 0,
          relevance_score: cit.relevance_score ?? cit.relevance ?? 0,
          journal: cit.journal || '',
          abstract: cit.abstract || '',
        });
      }
    }
  }

  // Sort: by relevance_score desc, then by year desc
  const allCitations = [...citationMap.values()].sort((a, b) => {
    const rDiff = (b.relevance_score || 0) - (a.relevance_score || 0);
    if (Math.abs(rDiff) > 0.001) return rDiff;
    return (b.year || 0) - (a.year || 0);
  });

  const hasSupport =
    literatureAssociations?.has_literature_support ||
    (hypothesis?.literature_evidence?.total_citations ?? 0) > 0 ||
    allCitations.length > 0;

  const totalCount =
    literatureAssociations?.total_citations ||
    hypothesis?.literature_evidence?.total_citations ||
    allCitations.length ||
    0;

  return (
    <Card elevation={2} sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <MenuBook color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Literature Evidence &amp; Citations
          </Typography>
          {allCitations.length > 0 && (
            <Chip
              label={`${allCitations.length} citation${allCitations.length !== 1 ? 's' : ''}`}
              size="small"
              color="primary"
              sx={{ ml: 1, fontWeight: 700 }}
            />
          )}
        </Box>

        {/* Support status banner */}
        <Card
          variant="outlined"
          sx={{
            mb: 3,
            borderColor: hasSupport ? 'success.main' : 'warning.main',
            bgcolor: hasSupport ? '#F1F8E9' : '#FFF8E1',
          }}
        >
          <CardContent sx={{ py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar sx={{ bgcolor: hasSupport ? 'success.main' : 'warning.main', width: 40, height: 40 }}>
                {hasSupport ? <VerifiedUser /> : <Warning />}
              </Avatar>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" fontWeight={600}>
                  {hasSupport ? 'Literature Support Found' : 'Novel Finding — No Prior Literature'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {hasSupport
                    ? `${totalCount} publication${totalCount !== 1 ? 's' : ''} link this pathway to ${tracedSeedGenes.length} seed gene${tracedSeedGenes.length !== 1 ? 's' : ''}`
                    : 'No existing literature evidence found. This may represent a novel discovery.'}
                </Typography>
              </Box>
              <Chip
                label={hasSupport ? 'Reported' : 'Not Reported'}
                color={hasSupport ? 'success' : 'warning'}
                sx={{ fontWeight: 600 }}
              />
            </Box>
          </CardContent>
        </Card>

        {/* Contributing genes */}
        {tracedSeedGenes.length > 0 && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Science color="primary" fontSize="small" />
                <Typography variant="subtitle1" fontWeight={600}>
                  Contributing Seed Genes ({tracedSeedGenes.length})
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {tracedSeedGenes.map((gene: string, i: number) => (
                  <Chip key={i} label={gene} size="small" color="primary" variant="outlined" sx={{ fontWeight: 600 }} />
                ))}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Citation stats */}
        {allCitations.length > 0 && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            {[
              { label: 'Total Citations', value: allCitations.length, color: 'primary.main' },
              { label: 'High Relevance (≥70%)', value: allCitations.filter(c => c.relevance_score >= 0.7).length, color: 'success.main' },
              { label: 'With Title', value: allCitations.filter(c => c.title).length, color: 'info.main' },
              { label: 'Recent (≥2020)', value: allCitations.filter(c => c.year >= 2020).length, color: 'warning.main' },
            ].map(({ label, value, color }) => (
              <Grid item xs={6} sm={3} key={label}>
                <Card variant="outlined" sx={{ textAlign: 'center' }}>
                  <CardContent sx={{ py: 2 }}>
                    <Typography variant="h4" sx={{ color }} fontWeight={600}>{value}</Typography>
                    <Typography variant="body2" color="text.secondary">{label}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {/* ── All citations flat list ────────────────────────────────────── */}
        {allCitations.length > 0 ? (
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
              <Article color="primary" />
              <Typography variant="h6" fontWeight={600}>
                Supporting Publications — All {allCitations.length}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Sorted by relevance score. Click the title or PMID chip to open in PubMed.
            </Typography>

            <List disablePadding>
              {allCitations.map((citation, idx) => {
                const relevancePct = Math.round((citation.relevance_score || 0) * 100);
                const relevanceColor =
                  relevancePct >= 70 ? '#2E7D32' : relevancePct >= 40 ? '#E65100' : '#757575';

                return (
                  <ListItem
                    key={citation.pmid}
                    disablePadding
                    sx={{
                      mb: 1.5,
                      border: '1px solid #E0E0E0',
                      borderLeft: `4px solid ${relevanceColor}`,
                      borderRadius: 1,
                      bgcolor: idx % 2 === 0 ? '#FAFAFA' : 'white',
                      p: 2,
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                    }}
                  >
                    {/* Top row: title + score */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', width: '100%', mb: 0.5 }}>
                      <Box sx={{ flex: 1, pr: 2 }}>
                        {citation.title ? (
                          <Typography
                            variant="subtitle2"
                            fontWeight={600}
                            sx={{
                              cursor: 'pointer',
                              color: 'primary.main',
                              '&:hover': { textDecoration: 'underline' },
                              lineHeight: 1.4,
                            }}
                            onClick={() => window.open(PUBMED_URL(citation.pmid), '_blank')}
                          >
                            {citation.title}
                          </Typography>
                        ) : (
                          <Typography
                            variant="subtitle2"
                            fontWeight={600}
                            sx={{ cursor: 'pointer', color: 'primary.main', '&:hover': { textDecoration: 'underline' }, fontFamily: 'monospace' }}
                            onClick={() => window.open(PUBMED_URL(citation.pmid), '_blank')}
                          >
                            PMID {citation.pmid}
                          </Typography>
                        )}
                      </Box>
                      <Chip
                        label={`${relevancePct}%`}
                        size="small"
                        sx={{ bgcolor: relevanceColor, color: 'white', fontWeight: 700, flexShrink: 0 }}
                      />
                    </Box>

                    {/* Authors / year / journal */}
                    {(citation.authors || citation.year || citation.journal) && (
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                        {[
                          citation.authors ? formatAuthors(citation.authors) : null,
                          citation.year || null,
                          citation.journal || null,
                        ].filter(Boolean).join(' • ')}
                      </Typography>
                    )}

                    {/* Abstract (collapsible) */}
                    {citation.abstract && (
                      <Box sx={{ width: '100%', mt: 0.5 }}>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            fontSize: '0.82rem',
                            lineHeight: 1.5,
                            display: expandedPmid === citation.pmid ? 'block' : '-webkit-box',
                            WebkitLineClamp: expandedPmid === citation.pmid ? undefined : 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {citation.abstract}
                        </Typography>
                        <Button
                          size="small"
                          onClick={() => setExpandedPmid(expandedPmid === citation.pmid ? null : citation.pmid)}
                          sx={{ mt: 0.25, p: 0, minWidth: 'auto', textTransform: 'none', fontSize: '0.75rem' }}
                        >
                          {expandedPmid === citation.pmid ? 'Collapse' : 'Expand abstract'}
                        </Button>
                      </Box>
                    )}

                    {/* Footer: PMID chip + open button */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                      <Chip
                        label={`PMID: ${citation.pmid}`}
                        size="small"
                        variant="outlined"
                        clickable
                        onClick={() => window.open(PUBMED_URL(citation.pmid), '_blank')}
                        sx={{ fontFamily: 'monospace', fontSize: '0.72rem', cursor: 'pointer', '&:hover': { bgcolor: '#E3F2FD' } }}
                      />
                      {citation.mesh_terms?.slice(0, 2).map((term, i) => (
                        <Chip key={i} label={term} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                      ))}
                      <Tooltip title="Open in PubMed" arrow>
                        <IconButton
                          size="small"
                          onClick={() => window.open(PUBMED_URL(citation.pmid), '_blank')}
                          sx={{ ml: 'auto', bgcolor: 'primary.main', color: 'white', '&:hover': { bgcolor: 'primary.dark' } }}
                        >
                          <OpenInNew sx={{ fontSize: 14 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          </Box>
        ) : (
          <Alert severity={hasSupport ? 'info' : 'warning'} sx={{ mt: 2 }}>
            <Typography variant="body2">
              {hasSupport
                ? 'Literature support recorded but citation details not retrieved. Re-run with higher PubMed results setting.'
                : 'No prior literature evidence found. This may indicate a novel finding.'}
            </Typography>
          </Alert>
        )}

        {/* Literature mining stats */}
        {allResults?.stage_4_literature && Object.keys(allResults.stage_4_literature).length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>Literature Mining Statistics</Typography>
            <Grid container spacing={2}>
              {[
                { label: 'Pathways with Literature', value: allResults.stage_4_literature.hypotheses_with_literature ?? 0, color: 'primary' },
                { label: 'Total Citations Found', value: allResults.stage_4_literature.total_citations ?? 0, color: 'success.main' },
                { label: 'Avg Relevance Score', value: allResults.stage_4_literature.avg_relevance_score?.toFixed(2) ?? 'N/A', color: 'warning.main' },
                { label: 'Unique Journals', value: allResults.stage_4_literature.unique_journals ?? 0, color: 'text.secondary' },
              ].map(({ label, value, color }) => (
                <Grid item xs={6} sm={3} key={label}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" sx={{ color }}>{value}</Typography>
                    <Typography variant="caption" color="text.secondary">{label}</Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
