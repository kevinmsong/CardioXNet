import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { AutoAwesome, Science, Settings } from '@mui/icons-material';
import api from '../api/endpoints';

interface ConfigurationPanelProps {
  config: Record<string, any>;
  onConfigChange: (config: Record<string, any>) => void;
}

type AnalysisProfile = 'focused' | 'balanced' | 'exploratory';
type EvidenceDepth = 'fast' | 'standard' | 'deep';

const FALLBACK_DEFAULTS = {
  string_neighbor_count: 80,
  fdr_threshold: 0.05,
  top_hypotheses_count: 20,
  primary_pathways_to_expand: 30,
  min_support_threshold: 2,
  semantic_relevance_threshold: 0.15,
  semantic_max_results: 60,
  semantic_max_hypotheses_for_literature: 15,
  pubmed_max_results: 25,
  permutation_test_enabled: true,
  n_permutations: 50,
  gtex_top_pathways: 6,
  external_druggability_enabled: true,
  external_druggability_top_pathways: 4,
  permutation_top_pathways: 8,
  seed_overlap_threshold: 0.45,
};

const OVERRIDABLE_KEYS = [
  'string_neighbor_count',
  'fdr_threshold',
  'top_hypotheses_count',
  'primary_pathways_to_expand',
  'min_support_threshold',
  'semantic_relevance_threshold',
  'semantic_max_results',
  'semantic_max_hypotheses_for_literature',
  'pubmed_max_results',
  'permutation_test_enabled',
  'n_permutations',
  'gtex_top_pathways',
  'external_druggability_enabled',
  'external_druggability_top_pathways',
  'permutation_top_pathways',
  'seed_overlap_threshold',
] as const;

export default function ConfigurationPanel({ onConfigChange }: ConfigurationPanelProps) {
  const [analysisProfile, setAnalysisProfile] = useState<AnalysisProfile>('balanced');
  const [evidenceDepth, setEvidenceDepth] = useState<EvidenceDepth>('standard');
  const [strictNovelty, setStrictNovelty] = useState(true);

  const { data } = useQuery({
    queryKey: ['config-defaults'],
    queryFn: api.getConfigDefaults,
  });

  const defaults = useMemo(() => {
    const apiDefaults = data?.config ?? {};
    return {
      ...FALLBACK_DEFAULTS,
      ...apiDefaults,
    };
  }, [data]);

  const mergedConfig = useMemo(() => {
    const profileOverrides: Record<AnalysisProfile, Record<string, any>> = {
      focused: {
        string_neighbor_count: 60,
        primary_pathways_to_expand: 20,
        fdr_threshold: 0.03,
        semantic_relevance_threshold: 0.18,
        semantic_max_results: 40,
        min_support_threshold: 2,
      },
      balanced: {},
      exploratory: {
        string_neighbor_count: 110,
        primary_pathways_to_expand: 45,
        fdr_threshold: 0.08,
        semantic_relevance_threshold: 0.11,
        semantic_max_results: 100,
        min_support_threshold: 2,
      },
    };

    const evidenceOverrides: Record<EvidenceDepth, Record<string, any>> = {
      fast: {
        top_hypotheses_count: 10,
        semantic_max_hypotheses_for_literature: 6,
        pubmed_max_results: 10,
        permutation_test_enabled: false,
        n_permutations: 25,
        gtex_top_pathways: 3,
        permutation_top_pathways: 0,
        external_druggability_enabled: false,
        external_druggability_top_pathways: 0,
      },
      standard: {
        top_hypotheses_count: 16,
        permutation_test_enabled: true,
        n_permutations: 50,
        gtex_top_pathways: 6,
      },
      deep: {
        top_hypotheses_count: 20,
        semantic_max_hypotheses_for_literature: 30,
        pubmed_max_results: 40,
        permutation_test_enabled: true,
        n_permutations: 100,
        gtex_top_pathways: 10,
        external_druggability_top_pathways: 6,
        permutation_top_pathways: 10,
      },
    };

    return {
      ...defaults,
      ...profileOverrides[analysisProfile],
      ...evidenceOverrides[evidenceDepth],
      seed_overlap_threshold: strictNovelty ? 0.35 : defaults.seed_overlap_threshold,
    };
  }, [analysisProfile, defaults, evidenceDepth, strictNovelty]);

  const overrideConfig = useMemo(
    () =>
      Object.fromEntries(
        OVERRIDABLE_KEYS.map((key) => [key, mergedConfig[key]])
      ),
    [mergedConfig]
  );

  useEffect(() => {
    onConfigChange(overrideConfig);
  }, [onConfigChange, overrideConfig]);

  return (
    <Card
      elevation={0}
      sx={{
        border: '1px solid #D8E8E2',
        borderRadius: 3,
        background: 'linear-gradient(180deg, #FFFFFF 0%, #F7FBF9 100%)',
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Settings sx={{ color: '#1F5A46' }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Analysis Presets
                </Typography>
              </Box>
            </Stack>
          </Stack>

          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.25, fontWeight: 700 }}>
              Discovery profile
            </Typography>
            <ToggleButtonGroup
              exclusive
              fullWidth
              color="primary"
              value={analysisProfile}
              onChange={(_, value: AnalysisProfile | null) => {
                if (value) {
                  setAnalysisProfile(value);
                }
              }}
            >
              <ToggleButton value="focused">Focused</ToggleButton>
              <ToggleButton value="balanced">Balanced</ToggleButton>
              <ToggleButton value="exploratory">Exploratory</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <FormControl fullWidth>
            <InputLabel id="evidence-depth-label">Evidence depth</InputLabel>
            <Select
              labelId="evidence-depth-label"
              label="Evidence depth"
              value={evidenceDepth}
              onChange={(event) => setEvidenceDepth(event.target.value as EvidenceDepth)}
            >
              <MenuItem value="fast">Fast screening</MenuItem>
              <MenuItem value="standard">Standard review</MenuItem>
              <MenuItem value="deep">Deep evidence pass</MenuItem>
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Switch
                checked={strictNovelty}
                onChange={(event) => setStrictNovelty(event.target.checked)}
              />
            }
            label="Favor lower seed-overlap candidates"
          />

          <Alert severity="info" icon={<Science />}>
            CardioXNet now keeps a broader primary funnel, expands more secondary pathways, and
            then prioritizes by replication, semantic cardiac relevance, and literature review.
          </Alert>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              icon={<AutoAwesome />}
              label={`${overrideConfig.string_neighbor_count} STRING neighbors`}
              variant="outlined"
            />
            <Chip
              label={`${overrideConfig.primary_pathways_to_expand} primary pathways expanded`}
              variant="outlined"
            />
            <Chip
              label={`FDR ${overrideConfig.fdr_threshold}`}
              variant="outlined"
            />
            <Chip
              label={`Semantic cutoff ${overrideConfig.semantic_relevance_threshold}`}
              variant="outlined"
            />
            <Chip
              label={`${overrideConfig.semantic_max_hypotheses_for_literature} pathways checked in PubMed`}
              variant="outlined"
            />
            <Chip
              label={
                overrideConfig.permutation_test_enabled
                  ? `${overrideConfig.n_permutations} permutations`
                  : 'No permutations'
              }
              variant="outlined"
            />
            <Chip
              label={
                overrideConfig.external_druggability_enabled
                  ? 'Live target evidence on'
                  : 'Curated target review only'
              }
              variant="outlined"
            />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
