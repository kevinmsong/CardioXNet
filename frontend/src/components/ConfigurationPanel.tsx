import { useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Grid,
  Tooltip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material';
import { ExpandMore, Settings, Info } from '@mui/icons-material';

interface ConfigurationPanelProps {
  config: Record<string, any>;
  onConfigChange: (config: Record<string, any>) => void;
}

export default function ConfigurationPanel({ config, onConfigChange }: ConfigurationPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const handleChange = (key: string, value: any) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <Accordion 
      expanded={expanded} 
      onChange={() => setExpanded(!expanded)}
      sx={{
        border: '1px solid #E0E0E0',
        borderRadius: '8px !important',
        '&:before': { display: 'none' },
        boxShadow: 'none',
      }}
    >
      <AccordionSummary 
        expandIcon={<ExpandMore />}
        sx={{
          bgcolor: '#FAFAFA',
          borderRadius: expanded ? '8px 8px 0 0' : '8px',
          '&:hover': { bgcolor: '#F5F5F5' },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Settings sx={{ color: '#1E6B52' }} />
          <Box>
            <Typography fontWeight={600}>Advanced Configuration</Typography>
            <Typography variant="caption" color="text.secondary">
              Fine-tune NETS algorithm parameters
            </Typography>
          </Box>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 3 }}>
        <Grid container spacing={3}>
          {/* Stage 1: Functional Neighborhood */}
          <Grid item xs={12}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              mb: 1,
              pb: 1,
              borderBottom: '2px solid #1E6B52'
            }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 1: Functional Neighborhood
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Expand seed genes using STRING protein-protein interaction network
            </Typography>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Number of functionally related genes to retrieve per seed gene from STRING database. Higher values enable broader network exploration and pathway discovery." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="STRING Neighbor Count"
                type="number"
                defaultValue={100}
                onChange={(e) => handleChange('string_neighbor_count', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 250 }}
                helperText="Range: 10-250 (default: 100)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Minimum STRING combined confidence score (0-1). Controls interaction quality threshold. 0.60 = moderate confidence, balances discovery with reliability." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="STRING Confidence Score"
                type="number"
                defaultValue={0.6}
                onChange={(e) => handleChange('string_score_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.4, max: 0.95 }}
                helperText="Range: 0.4-0.95 (default: 0.6)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Stage 2: Pathway Enrichment */}
          <Grid item xs={12}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              mb: 1,
              pb: 1,
              borderBottom: '2px solid #1E6B52'
            }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 2: Pathway Enrichment & Discovery
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Statistical thresholds and filters for pathway discovery
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="False Discovery Rate threshold for statistical significance. Lower = stricter (fewer false positives). 0.05 = 5% expected false discoveries (standard threshold). Recommended: 0.01-0.05." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="FDR Threshold"
                type="number"
                defaultValue={0.05}
                onChange={(e) => handleChange('fdr_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.005, min: 0.001, max: 0.2 }}
                helperText="Range: 0.001-0.2 (default: 0.05, standard)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Maximum seed gene overlap allowed in pathway evidence. Pathways with >50% seed genes are filtered as non-novel. Lower = stricter novelty requirement." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Seed Overlap Threshold"
                type="number"
                defaultValue={0.5}
                onChange={(e) => handleChange('seed_overlap_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.2, max: 0.8 }}
                helperText="Range: 0.2-0.8 (default: 0.5 = 50%)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Minimum support count - number of independent primary pathways that must discover a secondary pathway for validation." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Min Support (Replication)"
                type="number"
                defaultValue={1}
                onChange={(e) => handleChange('min_support_threshold', parseInt(e.target.value))}
                inputProps={{ min: 1, max: 10 }}
                helperText="Range: 1-10 (default: 1)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Minimum cardiac relevance score for semantic filtering. Controls pathway specificity to cardiovascular context through multi-category scoring." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Semantic Cardiac Threshold"
                type="number"
                defaultValue={0.01}
                onChange={(e) => handleChange('semantic_relevance_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.005, min: 0.001, max: 0.7 }}
                helperText="Range: 0.001-0.7 (default: 0.01)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip
              title="Boost multiplier for disease-specific pathways. Enhances scoring of pathways with cardiovascular disease terminology."
              arrow
              placement="top"
            >
              <TextField
                fullWidth
                label="Disease Pathway Boost"
                type="number"
                defaultValue={1.8}
                onChange={(e) => handleChange('semantic_disease_boost', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 1.0, max: 5.0 }}
                helperText="Range: 1.0-5.0 (default: 1.8)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip
              title="Maximum number of final pathway results to return after scoring and filtering."
              arrow
              placement="top"
            >
              <TextField
                fullWidth
                label="Max Pathway Results"
                type="number"
                defaultValue={150}
                onChange={(e) => handleChange('semantic_max_results', parseInt(e.target.value))}
                inputProps={{ min: 25, max: 500 }}
                helperText="Range: 25-500 (default: 150)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Minimum relevance score for genes discovered through literature mining based on cardiovascular keyword matching." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Literature Relevance"
                type="number"
                defaultValue={0.3}
                onChange={(e) => handleChange('literature_relevance_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.1, max: 0.6 }}
                helperText="Range: 0.1-0.6 (default: 0.3)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Maximum PubMed results to retrieve per gene for literature mining and evidence gathering." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="PubMed Max Results"
                type="number"
                defaultValue={30}
                onChange={(e) => handleChange('pubmed_max_results', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 500 }}
                helperText="Range: 10-500 (default: 30)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Stage 3: Scoring & Validation */}
          <Grid item xs={12}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              mb: 1,
              pb: 1,
              borderBottom: '2px solid #1E6B52'
            }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 3-4: Scoring & Validation
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              NES calculation and multi-evidence validation parameters
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Number of top-ranked hypotheses to validate with network topology and literature analysis." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Top Hypotheses to Validate"
                type="number"
                defaultValue={150}
                onChange={(e) => handleChange('top_hypotheses_count', parseInt(e.target.value))}
                inputProps={{ min: 5, max: 200 }}
                helperText="Range: 5-200 (default: 150)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Frequency: Count primaries supporting each pathway (recommended). Intersection: Only pathways found by ALL primaries (very strict). Weighted: Experimental." 
              arrow 
              placement="top"
            >
              <FormControl fullWidth>
                <InputLabel>Aggregation Strategy</InputLabel>
                <Select
                  defaultValue="frequency"
                  onChange={(e) => handleChange('aggregation_strategy', e.target.value)}
                  label="Aggregation Strategy"
                  endAdornment={<Info sx={{ fontSize: 18, color: 'text.secondary', mr: 3 }} />}
                >
                  <MenuItem value="frequency">Frequency (Recommended)</MenuItem>
                  <MenuItem value="intersection">Intersection (Strict)</MenuItem>
                  <MenuItem value="weighted">Weighted (Experimental)</MenuItem>
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, ml: 1.5 }}>
                  How to combine pathways across primaries
                </Typography>
              </FormControl>
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Minimum ratio of pathway genes that must be expressed in cardiac tissue (GTEx validation)." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Cardiac Expression Ratio"
                type="number"
                defaultValue={0.5}
                onChange={(e) => handleChange('min_cardiac_expression_ratio', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.1, max: 0.9 }}
                helperText="Range: 0.1-0.9 (default: 0.5)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Jaccard similarity threshold for pathway redundancy detection. Higher values retain more pathways with overlapping genes." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Redundancy Threshold"
                type="number"
                defaultValue={0.85}
                onChange={(e) => handleChange('redundancy_jaccard_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.5, max: 0.95 }}
                helperText="Range: 0.5-0.95 (default: 0.85)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Number of top pathways to mine for literature evidence and citation analysis." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Literature Mining Count"
                type="number"
                defaultValue={100}
                onChange={(e) => handleChange('semantic_max_hypotheses_for_literature', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 150 }}
                helperText="Range: 10-150 (default: 100)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip 
              title="Number of permutation tests for empirical p-value calculation. Higher = more robust statistics but slower." 
              arrow 
              placement="top"
            >
              <TextField
                fullWidth
                label="Permutation Count"
                type="number"
                defaultValue={100}
                onChange={(e) => handleChange('n_permutations', parseInt(e.target.value))}
                inputProps={{ min: 50, max: 1000 }}
                helperText="Range: 50-1000 (default: 100)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
          </Grid>

          {/* Database Weights */}
          <Grid item xs={12}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1, 
              mb: 1,
              pb: 1,
              borderBottom: '2px solid #1E6B52'
            }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Database Quality Weights
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Adjust NES score multipliers based on database curation quality
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Tooltip title="Reactome: Expert-curated pathways with detailed mechanisms. Higher weight = higher priority in NES scoring." arrow placement="top">
              <TextField
                fullWidth
                label="Reactome"
                type="number"
                defaultValue={1.5}
                onChange={(e) => handleChange('db_weight_reactome', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 0.5, max: 3 }}
                helperText="Expert-curated (default: 1.5)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Tooltip title="KEGG: Reference pathways with metabolic and signaling focus. Well-established database." arrow placement="top">
              <TextField
                fullWidth
                label="KEGG"
                type="number"
                defaultValue={1.5}
                onChange={(e) => handleChange('db_weight_kegg', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 0.5, max: 3 }}
                helperText="Reference (default: 1.5)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Tooltip title="WikiPathways: Community-contributed pathways. Good coverage but variable curation quality." arrow placement="top">
              <TextField
                fullWidth
                label="WikiPathways"
                type="number"
                defaultValue={1.2}
                onChange={(e) => handleChange('db_weight_wikipathways', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 0.5, max: 3 }}
                helperText="Community (default: 1.2)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Tooltip title="GO:BP: Gene Ontology Biological Process terms. Broad coverage, baseline weight." arrow placement="top">
              <TextField
                fullWidth
                label="GO:BP"
                type="number"
                defaultValue={1.0}
                onChange={(e) => handleChange('db_weight_gobp', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 0.5, max: 3 }}
                helperText="Baseline (default: 1.0)"
                InputProps={{
                  endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} />,
                }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}>
            <Box 
              sx={{ 
                mt: 2, 
                p: 2.5, 
                bgcolor: '#F0F7F4', 
                borderRadius: 2,
                border: '1px solid #C8E6C9',
              }}
            >
              <Typography variant="body2" fontWeight={600} color="primary.main" gutterBottom>
                NES Score Formula
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', mb: 1.5 }}>
                NES = -log₁₀(P_adj) × evidence_count × db_weight
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip label="Higher weight = Higher NES" size="small" color="primary" variant="outlined" />
                <Chip label="Reactome & KEGG: Most trusted" size="small" />
                <Chip label="WikiPathways: Good coverage" size="small" />
                <Chip label="GO:BP: Broad context" size="small" />
              </Box>
            </Box>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}
