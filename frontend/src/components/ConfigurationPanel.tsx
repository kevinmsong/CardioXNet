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
  Stack,
  Chip,
} from '@mui/material';
import { ExpandMore, Settings, Info, Bolt, Balance, Science } from '@mui/icons-material';

interface ConfigurationPanelProps {
  config: Record<string, any>;
  onConfigChange: (config: Record<string, any>) => void;
}

const PRESETS = {
  fast: {
    label: 'Fast',
    icon: <Bolt sx={{ fontSize: 16 }} />,
    color: '#E65100',
    desc: '~5 min',
    values: {
      string_neighbor_count: 50,
      string_score_threshold: 0.65,
      fdr_threshold: 0.05,
      top_hypotheses_count: 10,
      n_permutations: 10,
      pubmed_max_results: 10,
      semantic_max_results: 75,
      semantic_max_hypotheses_for_literature: 10,
      min_cardiac_expression_ratio: 0.50,
      redundancy_jaccard_threshold: 0.85,
      seed_overlap_threshold: 0.5,
      min_support_threshold: 1,
      semantic_relevance_threshold: 0.01,
      semantic_disease_boost: 1.8,
      literature_relevance_threshold: 0.3,
      aggregation_strategy: 'frequency',
    },
  },
  balanced: {
    label: 'Balanced',
    icon: <Balance sx={{ fontSize: 16 }} />,
    color: '#1E6B52',
    desc: '~10 min (default)',
    values: {
      string_neighbor_count: 75,
      string_score_threshold: 0.60,
      fdr_threshold: 0.05,
      top_hypotheses_count: 15,
      n_permutations: 25,
      pubmed_max_results: 20,
      semantic_max_results: 100,
      semantic_max_hypotheses_for_literature: 15,
      min_cardiac_expression_ratio: 0.50,
      redundancy_jaccard_threshold: 0.85,
      seed_overlap_threshold: 0.5,
      min_support_threshold: 1,
      semantic_relevance_threshold: 0.01,
      semantic_disease_boost: 1.8,
      literature_relevance_threshold: 0.3,
      aggregation_strategy: 'frequency',
    },
  },
  comprehensive: {
    label: 'Comprehensive',
    icon: <Science sx={{ fontSize: 16 }} />,
    color: '#1565C0',
    desc: '~20 min',
    values: {
      string_neighbor_count: 100,
      string_score_threshold: 0.55,
      fdr_threshold: 0.05,
      top_hypotheses_count: 25,
      n_permutations: 50,
      pubmed_max_results: 30,
      semantic_max_results: 150,
      semantic_max_hypotheses_for_literature: 25,
      min_cardiac_expression_ratio: 0.40,
      redundancy_jaccard_threshold: 0.85,
      seed_overlap_threshold: 0.5,
      min_support_threshold: 1,
      semantic_relevance_threshold: 0.01,
      semantic_disease_boost: 1.8,
      literature_relevance_threshold: 0.3,
      aggregation_strategy: 'frequency',
    },
  },
} as const;

type PresetKey = keyof typeof PRESETS;

const DEFAULTS = PRESETS.balanced.values;

export default function ConfigurationPanel({ config, onConfigChange }: ConfigurationPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [activePreset, setActivePreset] = useState<PresetKey | null>('balanced');

  const get = (key: string, fallback: any) => config[key] ?? fallback;

  const handleChange = (key: string, value: any) => {
    setActivePreset(null);
    onConfigChange({ ...config, [key]: value });
  };

  const applyPreset = (preset: PresetKey) => {
    setActivePreset(preset);
    onConfigChange({ ...config, ...PRESETS[preset].values });
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1, mr: 1 }}>
          <Settings sx={{ color: '#1E6B52', flexShrink: 0 }} />
          <Box sx={{ flex: 1 }}>
            <Typography fontWeight={600}>Advanced Configuration</Typography>
            <Typography variant="caption" color="text.secondary">
              Fine-tune NETS algorithm parameters
            </Typography>
          </Box>
          {/* Preset badges shown in summary when collapsed */}
          {!expanded && (
            <Stack direction="row" spacing={0.75} onClick={(e) => e.stopPropagation()}>
              {(Object.keys(PRESETS) as PresetKey[]).map((key) => {
                const p = PRESETS[key];
                const isActive = activePreset === key;
                return (
                  <Chip
                    key={key}
                    icon={p.icon}
                    label={p.label}
                    size="small"
                    onClick={(e) => { e.stopPropagation(); applyPreset(key); }}
                    sx={{
                      height: 26,
                      fontWeight: isActive ? 700 : 500,
                      bgcolor: isActive ? `${p.color}18` : 'transparent',
                      color: isActive ? p.color : '#757575',
                      border: `1px solid ${isActive ? p.color : '#E0E0E0'}`,
                      borderRadius: 1.5,
                      cursor: 'pointer',
                      '& .MuiChip-icon': { color: isActive ? p.color : '#9E9E9E' },
                      '&:hover': { bgcolor: `${p.color}12`, borderColor: p.color, color: p.color },
                    }}
                  />
                );
              })}
            </Stack>
          )}
        </Box>
      </AccordionSummary>

      <AccordionDetails sx={{ p: 3 }}>
        {/* Preset Selector */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5, color: '#1E6B52' }}>
            Configuration Preset
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            {(Object.keys(PRESETS) as PresetKey[]).map((key) => {
              const p = PRESETS[key];
              const isActive = activePreset === key;
              return (
                <Box
                  key={key}
                  onClick={() => applyPreset(key)}
                  sx={{
                    flex: 1, p: 1.5, borderRadius: 2, cursor: 'pointer',
                    border: `2px solid ${isActive ? p.color : '#E0E0E0'}`,
                    bgcolor: isActive ? `${p.color}10` : '#FAFAFA',
                    transition: 'all 0.15s ease',
                    '&:hover': { border: `2px solid ${p.color}`, bgcolor: `${p.color}08` },
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                    <Box sx={{ color: isActive ? p.color : '#9E9E9E' }}>{p.icon}</Box>
                    <Typography variant="body2" fontWeight={700} sx={{ color: isActive ? p.color : '#333' }}>
                      {p.label}
                    </Typography>
                    {isActive && (
                      <Chip label="Active" size="small"
                        sx={{ height: 18, fontSize: '0.65rem', bgcolor: p.color, color: '#fff', fontWeight: 700 }} />
                    )}
                  </Stack>
                  <Typography variant="caption" color="text.secondary">{p.desc}</Typography>
                </Box>
              );
            })}
          </Stack>
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Grid container spacing={3}>
          {/* Stage 1: Functional Neighborhood */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pb: 1, borderBottom: '2px solid #1E6B52' }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 1: Functional Neighborhood
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Expand seed genes using STRING protein-protein interaction network
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Number of functionally related genes to retrieve per seed gene from STRING. Higher = broader network." arrow placement="top">
              <TextField fullWidth label="STRING Neighbor Count" type="number"
                value={get('string_neighbor_count', DEFAULTS.string_neighbor_count)}
                onChange={(e) => handleChange('string_neighbor_count', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 250 }}
                helperText={`Range: 10–250 (default: ${DEFAULTS.string_neighbor_count})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Minimum STRING combined confidence score. 0.60 = moderate confidence." arrow placement="top">
              <TextField fullWidth label="STRING Confidence Score" type="number"
                value={get('string_score_threshold', DEFAULTS.string_score_threshold)}
                onChange={(e) => handleChange('string_score_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.4, max: 0.95 }}
                helperText={`Range: 0.4–0.95 (default: ${DEFAULTS.string_score_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}><Divider sx={{ my: 1 }} /></Grid>

          {/* Stage 2: Pathway Enrichment */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pb: 1, borderBottom: '2px solid #1E6B52' }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 2: Pathway Enrichment & Discovery
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Statistical thresholds and filters for pathway discovery
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="False Discovery Rate threshold. 0.05 = standard (5% expected false discoveries)." arrow placement="top">
              <TextField fullWidth label="FDR Threshold" type="number"
                value={get('fdr_threshold', DEFAULTS.fdr_threshold)}
                onChange={(e) => handleChange('fdr_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.005, min: 0.001, max: 0.2 }}
                helperText={`Range: 0.001–0.2 (default: ${DEFAULTS.fdr_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Maximum seed gene overlap in pathway evidence. Pathways with >50% seed genes are filtered as non-novel." arrow placement="top">
              <TextField fullWidth label="Seed Overlap Threshold" type="number"
                value={get('seed_overlap_threshold', DEFAULTS.seed_overlap_threshold)}
                onChange={(e) => handleChange('seed_overlap_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.2, max: 0.8 }}
                helperText={`Range: 0.2–0.8 (default: ${DEFAULTS.seed_overlap_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Minimum number of independent primary pathways that must support a secondary pathway." arrow placement="top">
              <TextField fullWidth label="Min Support (Replication)" type="number"
                value={get('min_support_threshold', DEFAULTS.min_support_threshold)}
                onChange={(e) => handleChange('min_support_threshold', parseInt(e.target.value))}
                inputProps={{ min: 1, max: 10 }}
                helperText={`Range: 1–10 (default: ${DEFAULTS.min_support_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Minimum cardiac relevance score for semantic filtering." arrow placement="top">
              <TextField fullWidth label="Semantic Cardiac Threshold" type="number"
                value={get('semantic_relevance_threshold', DEFAULTS.semantic_relevance_threshold)}
                onChange={(e) => handleChange('semantic_relevance_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.005, min: 0.001, max: 0.7 }}
                helperText={`Range: 0.001–0.7 (default: ${DEFAULTS.semantic_relevance_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Boost multiplier for disease-specific pathways in semantic scoring." arrow placement="top">
              <TextField fullWidth label="Disease Pathway Boost" type="number"
                value={get('semantic_disease_boost', DEFAULTS.semantic_disease_boost)}
                onChange={(e) => handleChange('semantic_disease_boost', parseFloat(e.target.value))}
                inputProps={{ step: 0.1, min: 1.0, max: 5.0 }}
                helperText={`Range: 1.0–5.0 (default: ${DEFAULTS.semantic_disease_boost})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Maximum number of final pathway results to return after scoring and filtering." arrow placement="top">
              <TextField fullWidth label="Max Pathway Results" type="number"
                value={get('semantic_max_results', DEFAULTS.semantic_max_results)}
                onChange={(e) => handleChange('semantic_max_results', parseInt(e.target.value))}
                inputProps={{ min: 25, max: 500 }}
                helperText={`Range: 25–500 (default: ${DEFAULTS.semantic_max_results})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Minimum relevance score for genes discovered through literature mining." arrow placement="top">
              <TextField fullWidth label="Literature Relevance" type="number"
                value={get('literature_relevance_threshold', DEFAULTS.literature_relevance_threshold)}
                onChange={(e) => handleChange('literature_relevance_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.1, max: 0.6 }}
                helperText={`Range: 0.1–0.6 (default: ${DEFAULTS.literature_relevance_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Maximum PubMed results per gene for literature mining." arrow placement="top">
              <TextField fullWidth label="PubMed Max Results" type="number"
                value={get('pubmed_max_results', DEFAULTS.pubmed_max_results)}
                onChange={(e) => handleChange('pubmed_max_results', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 500 }}
                helperText={`Range: 10–500 (default: ${DEFAULTS.pubmed_max_results})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12}><Divider sx={{ my: 1 }} /></Grid>

          {/* Stage 3-4: Scoring & Validation */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pb: 1, borderBottom: '2px solid #1E6B52' }}>
              <Typography variant="subtitle1" fontWeight={700} color="primary">
                Stage 3–4: Scoring & Validation
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              NES calculation and multi-evidence validation parameters
            </Typography>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Number of top-ranked hypotheses to validate with tissue expression and permutation testing." arrow placement="top">
              <TextField fullWidth label="Top Hypotheses to Validate" type="number"
                value={get('top_hypotheses_count', DEFAULTS.top_hypotheses_count)}
                onChange={(e) => handleChange('top_hypotheses_count', parseInt(e.target.value))}
                inputProps={{ min: 5, max: 200 }}
                helperText={`Range: 5–200 (default: ${DEFAULTS.top_hypotheses_count})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Frequency: count primaries supporting each pathway (recommended). Intersection: only pathways found by all primaries." arrow placement="top">
              <FormControl fullWidth>
                <InputLabel>Aggregation Strategy</InputLabel>
                <Select
                  value={get('aggregation_strategy', DEFAULTS.aggregation_strategy)}
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
            <Tooltip title="Minimum ratio of pathway genes expressed in cardiac tissue (GTEx validation)." arrow placement="top">
              <TextField fullWidth label="Cardiac Expression Ratio" type="number"
                value={get('min_cardiac_expression_ratio', DEFAULTS.min_cardiac_expression_ratio)}
                onChange={(e) => handleChange('min_cardiac_expression_ratio', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.1, max: 0.9 }}
                helperText={`Range: 0.1–0.9 (default: ${DEFAULTS.min_cardiac_expression_ratio})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Jaccard similarity threshold for pathway redundancy detection." arrow placement="top">
              <TextField fullWidth label="Redundancy Threshold" type="number"
                value={get('redundancy_jaccard_threshold', DEFAULTS.redundancy_jaccard_threshold)}
                onChange={(e) => handleChange('redundancy_jaccard_threshold', parseFloat(e.target.value))}
                inputProps={{ step: 0.05, min: 0.5, max: 0.95 }}
                helperText={`Range: 0.5–0.95 (default: ${DEFAULTS.redundancy_jaccard_threshold})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Number of top pathways to mine for literature evidence." arrow placement="top">
              <TextField fullWidth label="Literature Mining Count" type="number"
                value={get('semantic_max_hypotheses_for_literature', DEFAULTS.semantic_max_hypotheses_for_literature)}
                onChange={(e) => handleChange('semantic_max_hypotheses_for_literature', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 150 }}
                helperText={`Range: 10–150 (default: ${DEFAULTS.semantic_max_hypotheses_for_literature})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Tooltip title="Number of degree-preserving permutations for empirical p-value calculation. Higher = more robust but slower." arrow placement="top">
              <TextField fullWidth label="Permutation Count" type="number"
                value={get('n_permutations', DEFAULTS.n_permutations)}
                onChange={(e) => handleChange('n_permutations', parseInt(e.target.value))}
                inputProps={{ min: 10, max: 1000 }}
                helperText={`Range: 10–1000 (default: ${DEFAULTS.n_permutations})`}
                InputProps={{ endAdornment: <Info sx={{ fontSize: 18, color: 'text.secondary' }} /> }}
              />
            </Tooltip>
          </Grid>

        </Grid>
      </AccordionDetails>
    </Accordion>
  );
}
