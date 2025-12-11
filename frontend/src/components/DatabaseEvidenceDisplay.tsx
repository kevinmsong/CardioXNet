import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
  IconButton,
  Tooltip,
  LinearProgress,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  ExpandMore,
  Storage,
  Science,
  Hub,
  Link as LinkIcon,
  OpenInNew,
  Assessment,
  Verified,
} from '@mui/icons-material';
import { useState } from 'react';

interface DatabaseEvidenceProps {
  hypothesis: any;
  functionalNeighborhood: any;
}

export default function DatabaseEvidenceDisplay({ 
  hypothesis, 
  functionalNeighborhood 
}: DatabaseEvidenceProps) {
  const [selectedTab, setSelectedTab] = useState(0);
  
  const pathway = hypothesis?.aggregated_pathway?.pathway;
  const evidenceGenes = pathway?.evidence_genes || [];
  const interactions = functionalNeighborhood?.interactions || [];
  
  // Group interactions by database source
  const interactionsByDatabase = interactions.reduce((acc: Record<string, any[]>, interaction: any) => {
    const source = interaction.source || 'Unknown';
    if (!acc[source]) acc[source] = [];
    acc[source].push(interaction);
    return acc;
  }, {});

  // Filter interactions involving pathway evidence genes
  const pathwayInteractions = interactions.filter((interaction: any) => 
    evidenceGenes.includes(interaction.gene1) || evidenceGenes.includes(interaction.gene2)
  );

  // Calculate database statistics
  const databaseStats = Object.entries(interactionsByDatabase).map(([database, interactions]) => {
    const dbInteractions = interactions as any[];
    const pathwaySpecific = dbInteractions.filter((interaction: any) => 
      evidenceGenes.includes(interaction.gene1) || evidenceGenes.includes(interaction.gene2)
    );
    
    const avgScore = dbInteractions
      .filter((i: any) => i.score !== undefined)
      .reduce((sum: number, i: any) => sum + (i.score || 0), 0) / dbInteractions.length || 0;

    return {
      database,
      totalInteractions: dbInteractions.length,
      pathwayInteractions: pathwaySpecific.length,
      averageScore: avgScore,
      coverageRatio: pathwaySpecific.length / dbInteractions.length,
      interactions: dbInteractions
    };
  }).sort((a, b) => b.pathwayInteractions - a.pathwayInteractions);

  // Pathway database info
  const pathwayDatabase = {
    name: pathway?.source_db || 'Unknown',
    pathway_id: pathway?.pathway_id || 'N/A',
    pathway_name: pathway?.pathway_name || 'Unknown',
    p_value: pathway?.p_value || 0,
    p_adj: pathway?.p_adj || 0,
    evidence_count: evidenceGenes.length,
    total_genes: pathway?.total_genes || evidenceGenes.length
  };

  const getDatabaseIcon = (database: string) => {
    switch (database.toLowerCase()) {
      case 'string': return <Hub color="primary" />;
      case 'biogrid': return <Science color="secondary" />;
      case 'intact': return <Assessment color="success" />;
      case 'reactome': return <Verified color="warning" />;
      default: return <Storage color="action" />;
    }
  };

  const getDatabaseColor = (database: string) => {
    switch (database.toLowerCase()) {
      case 'string': return 'primary';
      case 'biogrid': return 'secondary';
      case 'intact': return 'success';
      case 'reactome': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Card elevation={2} sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Storage color="primary" />
          <Typography variant="h6" fontWeight={600}>
            Database Evidence & Sources
          </Typography>
        </Box>

        <Tabs 
          value={selectedTab} 
          onChange={(_, newValue) => setSelectedTab(newValue)} 
          sx={{ mb: 3 }}
        >
          <Tab label="Interaction Databases" />
          <Tab label="Pathway Database" />
          <Tab label="Evidence Summary" />
        </Tabs>

        {selectedTab === 0 && (
          <Box>
            {/* Database Statistics Overview */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              {databaseStats.slice(0, 4).map((stat) => (
                <Grid item xs={12} sm={6} md={3} key={stat.database}>
                  <Card variant="outlined" sx={{ textAlign: 'center' }}>
                    <CardContent sx={{ py: 2 }}>
                      <Avatar 
                        sx={{ 
                          bgcolor: `${getDatabaseColor(stat.database)}.main`, 
                          mx: 'auto', 
                          mb: 1,
                          width: 40,
                          height: 40
                        }}
                      >
                        {getDatabaseIcon(stat.database)}
                      </Avatar>
                      <Typography variant="h6" fontWeight={600} color="primary">
                        {stat.database}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {stat.totalInteractions} total interactions
                      </Typography>
                      <Typography variant="body2" fontWeight={600} color="success.main">
                        {stat.pathwayInteractions} pathway-relevant
                      </Typography>
                      {stat.averageScore > 0 && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            Avg Score: {stat.averageScore.toFixed(2)}
                          </Typography>
                          <LinearProgress 
                            variant="determinate" 
                            value={Math.min(stat.averageScore * 100, 100)} 
                            sx={{ mt: 0.5 }}
                          />
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {/* Detailed Database Breakdown */}
            {databaseStats.map((stat) => (
              <Accordion key={stat.database} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Avatar sx={{ bgcolor: `${getDatabaseColor(stat.database)}.main`, width: 32, height: 32 }}>
                      {getDatabaseIcon(stat.database)}
                    </Avatar>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6" fontWeight={600}>
                        {stat.database}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {stat.pathwayInteractions} pathway interactions • {stat.totalInteractions} total
                      </Typography>
                    </Box>
                    <Chip 
                      label={`${((stat.pathwayInteractions / stat.totalInteractions) * 100).toFixed(1)}% relevant`}
                      size="small"
                      color={getDatabaseColor(stat.database) as any}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>Gene 1</strong></TableCell>
                          <TableCell><strong>Gene 2</strong></TableCell>
                          {(stat.interactions as any[])?.some((i: any) => i.score !== undefined) && (
                            <TableCell><strong>Score</strong></TableCell>
                          )}
                          <TableCell><strong>Evidence</strong></TableCell>
                          <TableCell><strong>Actions</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(stat.interactions as any[])
                          ?.filter((interaction: any) => 
                            evidenceGenes.includes(interaction.gene1) || 
                            evidenceGenes.includes(interaction.gene2)
                          )
                          ?.slice(0, 10)
                          ?.map((interaction: any, idx: number) => (
                            <TableRow 
                              key={idx} 
                              sx={{ 
                                bgcolor: (evidenceGenes.includes(interaction.gene1) && evidenceGenes.includes(interaction.gene2)) 
                                  ? 'success.50' 
                                  : 'grey.50' 
                              }}
                            >
                              <TableCell>
                                <Chip 
                                  label={interaction.gene1} 
                                  size="small" 
                                  color={evidenceGenes.includes(interaction.gene1) ? 'primary' : 'default'}
                                />
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={interaction.gene2} 
                                  size="small"
                                  color={evidenceGenes.includes(interaction.gene2) ? 'primary' : 'default'}
                                />
                              </TableCell>
                              {(stat.interactions as any[])?.some((i: any) => i.score !== undefined) && (
                                <TableCell>
                                  {interaction.score !== undefined ? (
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                        {interaction.score.toFixed(3)}
                                      </Typography>
                                      <LinearProgress 
                                        variant="determinate" 
                                        value={Math.min(interaction.score * 100, 100)} 
                                        sx={{ width: 50, height: 4 }}
                                      />
                                    </Box>
                                  ) : 'N/A'}
                                </TableCell>
                              )}
                              <TableCell>
                                <Typography variant="caption">
                                  {interaction.evidence_types?.join(', ') || 'PPI'}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Tooltip title={`View in ${stat.database}`} arrow>
                                  <IconButton 
                                    size="small" 
                                    onClick={() => {
                                      // Open external database link (placeholder)
                                      const url = `https://${stat.database.toLowerCase()}.org/search/${interaction.gene1}+${interaction.gene2}`;
                                      window.open(url, '_blank');
                                    }}
                                  >
                                    <OpenInNew fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          ))
                        }
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {(stat.interactions as any[]).filter((interaction: any) => 
                    evidenceGenes.includes(interaction.gene1) || evidenceGenes.includes(interaction.gene2)
                  ).length > 10 && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Showing top 10 of {(stat.interactions as any[]).filter((interaction: any) => 
                        evidenceGenes.includes(interaction.gene1) || evidenceGenes.includes(interaction.gene2)
                      ).length} pathway-relevant interactions
                    </Typography>
                  )}
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        )}

        {selectedTab === 1 && (
          <Box>
            {/* Pathway Database Information */}
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'success.main' }}>
                    <Science />
                  </Avatar>
                  <Box>
                    <Typography variant="h6" fontWeight={600}>
                      {pathwayDatabase.name} Database
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Source of pathway annotation
                    </Typography>
                  </Box>
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Pathway Information
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <LinkIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary="Pathway ID"
                          secondary={pathwayDatabase.pathway_id}
                          secondaryTypographyProps={{ fontFamily: 'monospace' }}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Pathway Name"
                          secondary={pathwayDatabase.pathway_name}
                        />
                      </ListItem>
                    </List>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Statistical Evidence
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="P-value"
                          secondary={pathwayDatabase.p_value.toExponential(3)}
                          secondaryTypographyProps={{ fontFamily: 'monospace' }}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Adjusted P-value"
                          secondary={pathwayDatabase.p_adj.toExponential(3)}
                          secondaryTypographyProps={{ fontFamily: 'monospace' }}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Evidence Genes"
                          secondary={`${pathwayDatabase.evidence_count} genes`}
                        />
                      </ListItem>
                    </List>
                  </Grid>
                </Grid>

                <Box sx={{ mt: 2 }}>
                  <Tooltip title={`View pathway in ${pathwayDatabase.name}`} arrow>
                    <IconButton
                      size="small"
                      onClick={() => {
                        const baseUrls: Record<string, string> = {
                          'REAC': 'https://reactome.org/content/detail/',
                          'KEGG': 'https://www.genome.jp/kegg-bin/show_pathway?',
                          'GO:BP': 'http://amigo.geneontology.org/amigo/term/',
                          'WP': 'https://www.wikipathways.org/index.php/Pathway:'
                        };
                        const baseUrl = baseUrls[pathwayDatabase.name] || '#';
                        window.open(`${baseUrl}${pathwayDatabase.pathway_id}`, '_blank');
                      }}
                      sx={{
                        bgcolor: 'primary.main',
                        color: 'white',
                        '&:hover': { bgcolor: 'primary.dark' }
                      }}
                    >
                      <OpenInNew />
                    </IconButton>
                  </Tooltip>
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}

        {selectedTab === 2 && (
          <Box>
            {/* Evidence Summary */}
            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      Network Evidence
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Total Interactions"
                          secondary={interactions.length}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Pathway-Relevant"
                          secondary={pathwayInteractions.length}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Database Sources"
                          secondary={Object.keys(interactionsByDatabase).length}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Evidence Coverage"
                          secondary={`${((pathwayInteractions.length / interactions.length) * 100).toFixed(1)}%`}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      Pathway Evidence
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Source Database"
                          secondary={pathwayDatabase.name}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Statistical Significance"
                          secondary={pathwayDatabase.p_adj < 0.001 ? 'Highly Significant' : 'Significant'}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Evidence Strength"
                          secondary={`${pathwayDatabase.evidence_count} genes`}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Database Quality"
                          secondary={pathwayDatabase.name === 'REAC' ? 'Curated' : 'High Quality'}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      Cardiac Tissue Validation (GTEx)
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Validation Method"
                          secondary="GTEx Portal Tissue Expression"
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Target Tissues"
                          secondary="Heart Atrial Appendage, Left Ventricle"
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Cardiac-Validated Genes"
                          secondary={`${evidenceGenes.filter((g: any) => g.cardiac_validated).length}/${evidenceGenes.length}`}
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Validation Status"
                          secondary={evidenceGenes.some((g: any) => g.cardiac_validated) ? 'Cardiac-Specific' : 'Pending Validation'}
                        />
                      </ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}