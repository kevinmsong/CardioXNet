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
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Button,
} from '@mui/material';
import {
  MenuBook,
  OpenInNew,
  Star,
  StarBorder,
  Science,
  ExpandMore,
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

export default function LiteratureEvidenceDisplay({ 
  hypothesis, 
  allResults = {},
  citations = []
}: LiteratureEvidenceProps) {
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null);

  const literatureAssociations = hypothesis?.literature_associations || {};
  const tracedSeedGenes = hypothesis?.traced_seed_genes || [];
  const pathway = hypothesis?.aggregated_pathway?.pathway;

  // Extract literature data from results
  const literatureResults = allResults?.stage_4_literature || {};
  let hypothesisCitations: Citation[] = citations; // Start with prop citations
  
  // Try multiple locations for citations
  // First try: allResults.stage_4_literature[pathway_id].top_citations (CORRECT LOCATION)
  if (allResults?.stage_4_literature?.[pathway?.pathway_id]?.top_citations) {
    // Map 'relevance' field to 'relevance_score' for compatibility
    hypothesisCitations = allResults.stage_4_literature[pathway.pathway_id].top_citations.map((cit: any) => ({
      ...cit,
      relevance_score: cit.relevance_score || cit.relevance || 0,
      authors: cit.authors || 'Unknown'
    }));
  }
  // Fallback: old structure for backwards compatibility
  else if (allResults?.stage_4_literature?.hypothesis_citations?.[pathway?.pathway_id]) {
    hypothesisCitations = allResults.stage_4_literature.hypothesis_citations[pathway.pathway_id];
  } else if (allResults?.literature?.hypothesis_citations?.[pathway?.pathway_id]) {
    hypothesisCitations = allResults.literature.hypothesis_citations[pathway.pathway_id];
  } else if (hypothesis?.literature_evidence?.citations) {
    // Mock data structure
    hypothesisCitations = hypothesis.literature_evidence.citations;
  }



  // Sort citations by relevance score
  const sortedCitations = [...hypothesisCitations].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));

  // Group citations by relevance tiers
  const highRelevance = sortedCitations.filter(c => (c.relevance_score || 0) >= 0.7);
  const mediumRelevance = sortedCitations.filter(c => (c.relevance_score || 0) >= 0.4 && (c.relevance_score || 0) < 0.7);
  const lowRelevance = sortedCitations.filter(c => (c.relevance_score || 0) < 0.4);

  // Handle literature support from multiple sources
  const hasLiteratureSupport = literatureAssociations?.has_literature_support || 
                              (hypothesis?.literature_evidence?.total_citations > 0) || 
                              (sortedCitations.length > 0);
  const totalCitations = literatureAssociations?.total_citations || 
                        hypothesis?.literature_evidence?.total_citations || 
                        sortedCitations.length || 0;

  const getRelevanceColor = (score: number) => {
    if (score >= 0.7) return 'success';
    if (score >= 0.4) return 'warning';
    return 'default';
  };

  const getRelevanceLabel = (score: number) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
  };

  const formatAuthors = (authors: string) => {
    const authorList = authors.split(',').map(a => a.trim());
    if (authorList.length <= 2) return authors;
    return `${authorList[0]} et al.`;
  };

  return (
    <Card elevation={2} sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <MenuBook color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Literature Evidence & Citations
          </Typography>
        </Box>

        {/* Literature Support Status */}
        <Card 
          variant="outlined" 
          sx={{ 
            mb: 3, 
            borderColor: hasLiteratureSupport ? 'success.main' : 'warning.main',
            bgcolor: hasLiteratureSupport ? 'success.50' : 'warning.50'
          }}
        >
          <CardContent sx={{ py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar 
                sx={{ 
                  bgcolor: hasLiteratureSupport ? 'success.main' : 'warning.main',
                  width: 40,
                  height: 40
                }}
              >
                {hasLiteratureSupport ? <VerifiedUser /> : <Warning />}
              </Avatar>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" fontWeight={600}>
                  {hasLiteratureSupport ? 'Literature Support Found' : 'Novel Finding - No Prior Literature'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {hasLiteratureSupport 
                    ? `Found ${totalCitations} publications linking this pathway to ${tracedSeedGenes.length} seed gene(s)`
                    : 'No existing literature evidence found for this pathway-seed gene association. This may represent a novel discovery.'
                  }
                </Typography>
              </Box>
              <Chip 
                label={hasLiteratureSupport ? 'Reported' : 'Not Reported'}
                color={hasLiteratureSupport ? 'success' : 'warning'}
                sx={{ fontWeight: 600 }}
              />
            </Box>
          </CardContent>
        </Card>

        {/* Contributing Seed Genes for Literature Search */}
        {tracedSeedGenes && tracedSeedGenes.length > 0 && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Science color="primary" fontSize="small" />
                <Typography variant="subtitle1" fontWeight={600}>
                  Contributing Seed Genes for Literature Search
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Literature search focused on the {tracedSeedGenes.length} seed gene(s) that specifically contributed to discovering this pathway:
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {tracedSeedGenes.map((gene: string, index: number) => (
                  <Chip
                    key={index}
                    label={gene}
                    size="small"
                    color="primary"
                    variant="outlined"
                    icon={<Science />}
                    sx={{ fontWeight: 600 }}
                  />
                ))}
              </Box>
              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>Targeted Literature Mining:</strong> Citations below were found by searching for publications 
                  that discuss "{hypothesis?.aggregated_pathway?.pathway?.pathway_name}" in combination with these specific 
                  contributing seed genes, providing more relevant evidence than generic pathway literature.
                </Typography>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* Citation Statistics */}
        {totalCitations > 0 && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={3}>
              <Card variant="outlined" sx={{ textAlign: 'center' }}>
                <CardContent sx={{ py: 2 }}>
                  <Typography variant="h4" color="primary" fontWeight={600}>
                    {totalCitations}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Citations
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card variant="outlined" sx={{ textAlign: 'center' }}>
                <CardContent sx={{ py: 2 }}>
                  <Typography variant="h4" color="success.main" fontWeight={600}>
                    {highRelevance.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    High Relevance
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card variant="outlined" sx={{ textAlign: 'center' }}>
                <CardContent sx={{ py: 2 }}>
                  <Typography variant="h4" color="warning.main" fontWeight={600}>
                    {mediumRelevance.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Medium Relevance
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card variant="outlined" sx={{ textAlign: 'center' }}>
                <CardContent sx={{ py: 2 }}>
                  <Typography variant="h4" color="text.secondary" fontWeight={600}>
                    {lowRelevance.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Lower Relevance
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Citations List */}
        {sortedCitations.length > 0 ? (
          <Box>
            <Typography variant="h6" fontWeight={600} gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Article color="primary" />
              Supporting Publications
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Publications ranked by relevance to the pathway-seed gene association
            </Typography>

            {[
              { citations: highRelevance, title: 'High Relevance (≥0.7)', color: 'success' },
              { citations: mediumRelevance, title: 'Medium Relevance (0.4-0.7)', color: 'warning' },
              { citations: lowRelevance, title: 'Lower Relevance (<0.4)', color: 'default' }
            ].filter(group => group.citations.length > 0).map((group, groupIdx) => (
              <Accordion key={groupIdx} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip 
                      label={group.citations.length} 
                      size="small" 
                      color={group.color as any}
                    />
                    <Typography variant="subtitle1" fontWeight={600}>
                      {group.title}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <List>
                    {group.citations.map((citation, _idx) => (
                      <ListItem 
                        key={citation.pmid} 
                        sx={{ 
                          border: '1px solid #E0E0E0',
                          borderRadius: 1,
                          mb: 1,
                          bgcolor: 'grey.50'
                        }}
                      >
                        <Box sx={{ width: '100%' }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Box sx={{ flexGrow: 1, pr: 2 }}>
                              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                                {citation.title}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {formatAuthors(citation.authors)} • {citation.year} • {citation.journal || 'Unknown Journal'}
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Chip 
                                label={`${(citation.relevance_score * 100).toFixed(0)}%`}
                                size="small"
                                color={getRelevanceColor(citation.relevance_score) as any}
                              />
                              <Badge 
                                badgeContent={getRelevanceLabel(citation.relevance_score)}
                                color={getRelevanceColor(citation.relevance_score) as any}
                                sx={{ '& .MuiBadge-badge': { fontSize: '0.7rem' } }}
                              >
                                <Box sx={{ display: 'flex' }}>
                                  {[...Array(5)].map((_, starIdx) => (
                                    starIdx < Math.round(citation.relevance_score * 5) 
                                      ? <Star key={starIdx} sx={{ fontSize: 16, color: 'gold' }} />
                                      : <StarBorder key={starIdx} sx={{ fontSize: 16, color: 'grey.400' }} />
                                  ))}
                                </Box>
                              </Badge>
                            </Box>
                          </Box>
                          
                          {citation.abstract && (
                            <Box sx={{ mb: 1 }}>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontSize: '0.875rem',
                                  lineHeight: 1.4,
                                  color: 'text.secondary',
                                  display: expandedCitation === citation.pmid ? 'block' : '-webkit-box',
                                  WebkitLineClamp: expandedCitation === citation.pmid ? 'none' : 2,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden'
                                }}
                              >
                                {citation.abstract}
                              </Typography>
                              <Button
                                size="small"
                                onClick={() => setExpandedCitation(
                                  expandedCitation === citation.pmid ? null : citation.pmid
                                )}
                                sx={{ mt: 0.5, p: 0, minWidth: 'auto', textTransform: 'none' }}
                              >
                                {expandedCitation === citation.pmid ? 'Show less' : 'Show more'}
                              </Button>
                            </Box>
                          )}

                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              <Chip 
                                label={`PMID: ${citation.pmid}`} 
                                size="small" 
                                variant="outlined"
                                sx={{ fontSize: '0.75rem', fontFamily: 'monospace' }}
                              />
                              {citation.mesh_terms && citation.mesh_terms.slice(0, 2).map((term: any, termIdx: number) => (
                                <Chip 
                                  key={termIdx}
                                  label={term} 
                                  size="small" 
                                  variant="outlined"
                                  sx={{ fontSize: '0.75rem' }}
                                />
                              ))}
                            </Box>
                            <Box>
                              <Tooltip title="View on PubMed" arrow>
                                <IconButton
                                  size="small"
                                  onClick={() => window.open(`https://pubmed.ncbi.nlm.nih.gov/${citation.pmid}`, '_blank')}
                                  sx={{
                                    bgcolor: 'primary.main',
                                    color: 'white',
                                    '&:hover': { bgcolor: 'primary.dark' }
                                  }}
                                >
                                  <OpenInNew fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </Box>
                        </Box>
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        ) : (
          <Alert 
            severity={hasLiteratureSupport ? "info" : "warning"}
            sx={{ mt: 2 }}
          >
            <Typography variant="body2">
              {hasLiteratureSupport 
                ? "Literature evidence was found but detailed citations are not available in this view."
                : "This pathway-seed gene association has no prior literature evidence, suggesting it may be a novel finding worthy of further investigation."
              }
            </Typography>
          </Alert>
        )}

        {/* Literature Mining Stats */}
        {literatureResults && Object.keys(literatureResults).length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Literature Mining Statistics
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="primary">
                    {literatureResults.hypotheses_with_literature || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Pathways with Literature
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="success.main">
                    {literatureResults.total_citations || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total Citations Found
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="warning.main">
                    {literatureResults.avg_relevance_score?.toFixed(2) || 'N/A'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Avg Relevance Score
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="text.secondary">
                    {literatureResults.unique_journals || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Unique Journals
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}