import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Stack,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableRow,
  LinearProgress,
} from '@mui/material';
import {
  Science,
  TrendingUp,
  AccountTree,
  Timeline,
  Speed,
  BiotechOutlined,
  CheckCircleOutline,
  LibraryBooks,
  Hub,
  Biotech,
  BarChart,
  FilterAlt,
  VerifiedUser,
  Article,
  Share,
  FavoriteBorder,
  FileDownload,
  ManageSearch,
} from '@mui/icons-material';

const GREEN = '#1E6B52';
const DARK_GREEN = '#145A43';
const GOLD = '#FFB81C';

interface PipelineStage {
  num: string;
  title: string;
  subtitle: string;
  desc: string;
  pct: number;
  phase: 'input' | 'enrichment' | 'scoring' | 'validation' | 'output';
  icon: React.ReactNode;
  details?: string[];
}

const PHASE_COLORS = {
  input: { bg: '#E8F5E9', border: '#1E6B52', text: '#1E6B52', label: 'Input' },
  enrichment: { bg: '#FFF3E0', border: '#E65100', text: '#E65100', label: 'Enrichment' },
  scoring: { bg: '#E3F2FD', border: '#1565C0', text: '#1565C0', label: 'Scoring' },
  validation: { bg: '#EDE7F6', border: '#512DA8', text: '#512DA8', label: 'Validation' },
  output: { bg: '#FFF8E1', border: '#F57F17', text: '#F57F17', label: 'Output' },
};

const PIPELINE_STAGES: PipelineStage[] = [
  {
    num: '01', title: 'Input Validation', subtitle: 'Gene normalization', pct: 5, phase: 'input',
    icon: <ManageSearch sx={{ fontSize: 20 }} />,
    desc: 'HGNC gene symbol normalization, invalid identifier filtering, duplicate removal.',
    details: ['Accepts HGNC symbols (e.g., MYH7, TTN)', 'Removes unrecognized or duplicate entries', '5–50 genes per analysis'],
  },
  {
    num: '02', title: 'Functional Neighborhood', subtitle: 'STRING PPI expansion', pct: 15, phase: 'input',
    icon: <Hub sx={{ fontSize: 20 }} />,
    desc: 'STRING v11.5 PPI expansion — 75 neighbors per seed gene at confidence ≥ 0.60.',
    details: ['STRING v11.5 API, 75 neighbors/gene', 'Combined score threshold ≥ 0.60', 'Builds functional interaction context'],
  },
  {
    num: '03', title: 'Primary Pathway Enrichment', subtitle: 'g:Profiler', pct: 25, phase: 'enrichment',
    icon: <Biotech sx={{ fontSize: 20 }} />,
    desc: 'g:Profiler enrichment across GO:BP, KEGG, Reactome, WikiPathways with BH FDR ≤ 0.05.',
    details: ['4 databases: GO:BP, KEGG, Reactome, WikiPathways', 'BH FDR correction, threshold ≤ 0.05', 'Fold-enrichment ≥ 2.0 required'],
  },
  {
    num: '04', title: 'Secondary Pathway Discovery', subtitle: 'Re-enrichment', pct: 40, phase: 'enrichment',
    icon: <AccountTree sx={{ fontSize: 20 }} />,
    desc: 'Per-neighbor network re-expansion and re-enrichment guided by PubMed cardiovascular context.',
    details: ['Re-enriches each neighbor subnetwork', 'PubMed disease context guidance', 'Captures non-primary pathway associations'],
  },
  {
    num: '05', title: 'Pathway Aggregation', subtitle: 'Deduplication', pct: 55, phase: 'enrichment',
    icon: <FilterAlt sx={{ fontSize: 20 }} />,
    desc: 'Frequency-based pathway aggregation. Jaccard ≥ 0.85 redundancy filtering removes highly overlapping terms.',
    details: ['Frequency-based aggregation strategy', 'Jaccard similarity ≥ 0.85 removes redundancy', 'Pathway support count tracking'],
  },
  {
    num: '06', title: 'NES Scoring', subtitle: 'Composite enrichment score', pct: 65, phase: 'scoring',
    icon: <BarChart sx={{ fontSize: 20 }} />,
    desc: 'NES = –log₁₀(p_adj) × √gene_count × db_weight. Weights: Reactome 1.5×, KEGG 1.5×, WikiPathways 1.2×, GO:BP 1.0×.',
    details: ['√gene_count normalization (GSEA standard)', 'Database quality weighting', 'Final: log₁₀(|NES_raw| + 1)'],
  },
  {
    num: '07', title: 'Semantic Cardiac Filtering', subtitle: '700+ cardiovascular terms', pct: 75, phase: 'scoring',
    icon: <Science sx={{ fontSize: 20 }} />,
    desc: '700+ curated cardiovascular terms, 3-tier disease thresholds. Strict name filter enforces cardiac relevance in all final results.',
    details: ['6 term categories: anatomy, processes, pathology, context, names, negatives', '3-tier thresholds: high/medium/low cardiac', 'Mandatory strict name filter on final output'],
  },
  {
    num: '08', title: 'Enhanced Validation', subtitle: 'GTEx + Permutations + Druggability', pct: 83, phase: 'validation',
    icon: <VerifiedUser sx={{ fontSize: 20 }} />,
    desc: 'GTEx v8 cardiac tissue expression (left ventricle + atrial appendage), 25 degree-preserving permutations, curated druggability scoring.',
    details: ['GTEx v8 live API — cardiac ratio >= 0.50', 'Degree-preserving permutations x 25 (empirical p)', 'Curated DrugBank + live ChEMBL druggability'],
  },
  {
    num: '09', title: 'Literature Mining', subtitle: 'PubMed evidence', pct: 88, phase: 'validation',
    icon: <Article sx={{ fontSize: 20 }} />,
    desc: 'PubMed abstract screening — 50 results per seed gene. Traceability linking genes to discovered pathways.',
    details: ['50 PubMed abstracts per seed gene', 'Gene-to-pathway citation traceability', 'Disease context-guided queries'],
  },
  {
    num: '10', title: 'Network Topology Analysis', subtitle: 'Hub gene identification', pct: 93, phase: 'validation',
    icon: <Share sx={{ fontSize: 20 }} />,
    desc: 'PageRank, betweenness, closeness, and degree centrality on unified PPI network from top pathways.',
    details: ['PageRank, betweenness, closeness, degree', 'Unified PPI network from top pathways', 'Hub gene scores feed therapeutic target ranking'],
  },
  {
    num: '11', title: 'Therapeutic Targets', subtitle: 'Druggable hub genes', pct: 95, phase: 'output',
    icon: <FavoriteBorder sx={{ fontSize: 20 }} />,
    desc: 'Importance = Frequency^1.2 × Avg NES × (1 + Cardiac Score). Druggability tier annotation.',
    details: ['Multi-factor importance scoring', 'FDA-approved, clinical trial, druggable tiers', 'Top 20 genes ranked with evidence'],
  },
  {
    num: '12', title: 'Report Generation', subtitle: 'JSON + PDF export', pct: 100, phase: 'output',
    icon: <FileDownload sx={{ fontSize: 20 }} />,
    desc: 'JSON and PDF output. Ranked hypotheses, hub genes, therapeutic targets with full provenance chain.',
    details: ['JSON + PDF output formats', 'Ranked pathway hypotheses', 'Full provenance and evidence chain'],
  },
];

function PipelineStageCard({ stage }: { stage: PipelineStage }) {
  const phase = PHASE_COLORS[stage.phase];
  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      {/* Left: number + connector */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <Box
          sx={{
            width: 40, height: 40, borderRadius: '50%',
            bgcolor: phase.bg, border: `2px solid ${phase.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: phase.text, flexShrink: 0,
          }}
        >
          {stage.icon}
        </Box>
        {/* Connector line */}
        <Box sx={{ width: 2, flex: 1, bgcolor: '#E0E0E0', minHeight: 12, mt: 0.5 }} />
      </Box>

      {/* Right: content */}
      <Box sx={{ flex: 1, pb: 2.5 }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
          <Typography variant="caption" sx={{ color: '#9E9E9E', fontWeight: 600, fontSize: '0.68rem', fontFamily: 'monospace' }}>
            STAGE {stage.num}
          </Typography>
          <Chip
            label={phase.label}
            size="small"
            sx={{ height: 18, fontSize: '0.65rem', fontWeight: 700, bgcolor: phase.bg, color: phase.text, borderRadius: 1 }}
          />
          <Typography variant="caption" sx={{ color: '#BDBDBD', ml: 'auto', fontWeight: 600 }}>
            {stage.pct}%
          </Typography>
        </Stack>

        <Typography variant="body2" fontWeight={700} sx={{ color: '#1A1A1A', mb: 0.25 }}>
          {stage.title}
        </Typography>
        <Typography variant="caption" sx={{ color: phase.text, fontWeight: 600, mb: 0.75, display: 'block' }}>
          {stage.subtitle}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.6, mb: 0.75, display: 'block' }}>
          {stage.desc}
        </Typography>

        {/* Progress bar */}
        <LinearProgress
          variant="determinate"
          value={stage.pct}
          sx={{
            height: 3, borderRadius: 2, bgcolor: '#F0F0F0',
            '& .MuiLinearProgress-bar': { bgcolor: phase.border, borderRadius: 2 },
          }}
        />

        {/* Detail bullets */}
        {stage.details && (
          <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
            {stage.details.map((d) => (
              <Chip
                key={d}
                label={d}
                size="small"
                variant="outlined"
                sx={{ height: 20, fontSize: '0.65rem', borderColor: '#E0E0E0', color: '#757575', borderRadius: 1 }}
              />
            ))}
          </Stack>
        )}
      </Box>
    </Box>
  );
}

export default function DocumentationPageSimplified() {
  return (
    <Box sx={{ py: 2 }}>
      {/* Professional Header */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, md: 4 }, mb: 3,
          background: `linear-gradient(135deg, ${GREEN} 0%, ${DARK_GREEN} 100%)`,
          color: 'white', borderRadius: 3,
          border: `2px solid ${GOLD}`,
        }}
      >
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems={{ xs: 'flex-start', sm: 'center' }}>
          <Box sx={{ p: 1.5, bgcolor: 'rgba(255,184,28,0.2)', border: `2px solid ${GOLD}`, borderRadius: 2, display: 'flex', flexShrink: 0 }}>
            <Science sx={{ fontSize: 40, color: GOLD }} />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#fff', mb: 0.5, letterSpacing: '-0.5px' }}>
              CardioXNet Documentation
            </Typography>
            <Typography variant="subtitle1" sx={{ color: 'rgba(255,255,255,0.85)', fontWeight: 400, mb: 1.5 }}>
              Network-Enhanced Tissue-Specific Pathway Analysis for Cardiovascular Disease
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {['STRING v11.5', 'g:Profiler', 'GTEx v8', 'PubMed', 'DrugBank v5.1'].map((db) => (
                <Chip key={db} label={db} size="small"
                  sx={{ bgcolor: 'rgba(255,184,28,0.2)', color: GOLD, fontWeight: 600, fontSize: '0.72rem' }} />
              ))}
            </Stack>
          </Box>
          <Box sx={{ textAlign: { xs: 'left', sm: 'right' }, flexShrink: 0 }}>
            <Typography variant="h5" sx={{ color: GOLD, fontWeight: 700 }}>12 Stages</Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.75)' }}>8–12 min · 5–50 genes</Typography>
          </Box>
        </Stack>
      </Paper>

      <Grid container spacing={3}>
        {/* Left column */}
        <Grid item xs={12} lg={8}>

          {/* Quick Start */}
          <Card elevation={1} sx={{ mb: 3, border: `1px solid ${GOLD}50` }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2.5 }}>
                <Speed sx={{ color: GREEN, fontSize: 26 }} />
                <Typography variant="h5" sx={{ fontWeight: 700, color: GREEN }}>Quick Start</Typography>
              </Stack>
              <Grid container spacing={2}>
                {[
                  { step: '1', title: 'Enter Genes', body: 'Paste 5–50 cardiovascular gene symbols (e.g., MYH7, MYBPC3, TTN, SCN5A). One per line or comma-separated.' },
                  { step: '2', title: 'Configure (Optional)', body: 'Adjust neighbor count, FDR threshold, or pathway limit. Defaults are optimized for most analyses.' },
                  { step: '3', title: 'Monitor Progress', body: 'Watch real-time progress through all 12 pipeline stages on the progress page.' },
                  { step: '4', title: 'Explore Results', body: 'Review ranked pathways with NES scores, p-values, tissue expression, and therapeutic targets. Export as CSV or PDF.' },
                ].map(({ step, title, body }) => (
                  <Grid item xs={12} sm={6} key={step}>
                    <Box sx={{ display: 'flex', gap: 1.5 }}>
                      <Chip label={step} size="small"
                        sx={{ bgcolor: GREEN, color: '#fff', fontWeight: 700, minWidth: 28, height: 28, borderRadius: '50%', flexShrink: 0 }} />
                      <Box>
                        <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>{title}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.5 }}>{body}</Typography>
                      </Box>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>

          {/* Pipeline Stages Figure */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                <Timeline sx={{ color: GREEN, fontSize: 26 }} />
                <Typography variant="h5" sx={{ fontWeight: 700, color: GREEN }}>12-Stage Analysis Pipeline</Typography>
              </Stack>

              {/* Phase legend */}
              <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 0.75 }}>
                {Object.entries(PHASE_COLORS).map(([key, val]) => (
                  <Chip key={key} label={val.label} size="small"
                    sx={{ bgcolor: val.bg, color: val.text, fontWeight: 700, fontSize: '0.7rem', border: `1px solid ${val.border}40`, borderRadius: 1 }} />
                ))}
              </Stack>

              <Box>
                {PIPELINE_STAGES.map((stage) => (
                  <PipelineStageCard key={stage.num} stage={stage} />
                ))}
              </Box>

              {/* Footer summary */}
              <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8FAF9', borderColor: '#C8E6C9', borderRadius: 2, mt: 1 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-around">
                  {[
                    { label: 'Total Stages', value: '12' },
                    { label: 'External APIs', value: '4 live' },
                    { label: 'Runtime', value: '8–12 min' },
                    { label: 'Max Pathways Out', value: '100' },
                  ].map(({ label, value }) => (
                    <Box key={label} sx={{ textAlign: 'center' }}>
                      <Typography variant="h6" sx={{ color: GREEN, fontWeight: 700, lineHeight: 1 }}>{value}</Typography>
                      <Typography variant="caption" color="text.secondary">{label}</Typography>
                    </Box>
                  ))}
                </Stack>
              </Paper>
            </CardContent>
          </Card>

          {/* Algorithm Details */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2.5 }}>
                <BiotechOutlined sx={{ color: GREEN, fontSize: 26 }} />
                <Typography variant="h5" sx={{ fontWeight: 700, color: GREEN }}>Algorithm Details</Typography>
              </Stack>

              {/* NES */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>NES Score Formula</Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA', borderRadius: 2, mb: 1 }}>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '0.88rem', color: GREEN, fontWeight: 600 }}>
                    NES_raw = –log₁₀(p_adj) × √(gene_count) × db_weight
                  </Typography>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '0.88rem', color: GREEN, fontWeight: 600, mt: 0.5 }}>
                    NES = log₁₀(|NES_raw| + 1)
                  </Typography>
                </Paper>
                <Typography variant="body2" color="text.secondary">
                  Square-root normalization (GSEA standard) prevents large pathway bias. A 400-gene pathway scores 2× a 100-gene pathway,
                  not 4×. Final log₁₀ compression stabilizes the range for downstream comparison.
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Permutation Testing */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>Degree-Preserving Permutation Testing</Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Genes are permuted while preserving degree-quintile stratification, maintaining network topology in the null distribution.
                  Applied per-pathway during Stage 8.
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#F8F9FA', borderRadius: 2, mb: 1 }}>
                  <Typography sx={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#333' }}>
                    empirical_p = (n_more_extreme + 1) / (n_permutations + 1)
                  </Typography>
                </Paper>
                <Typography variant="body2" color="text.secondary">
                  +1 correction (Phipson &amp; Smyth 2010) prevents zero p-values. 5 degree quintile bins.
                  Default: 25 permutations per pathway.
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Druggability */}
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>Druggability Classification</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Primary: curated gene lists from DrugBank v5.1.10 (Nov 2023) and TTD 2023.
                  Secondary: live ChEMBL REST API for genes not in the curated set — real-time max_phase and drug activity lookup.
                </Typography>
                <Stack spacing={1}>
                  {[
                    { tier: 'FDA Approved', desc: 'Beta-blockers (ADRB1/2), ACE inhibitors (ACE, AGTR1), statins (HMGCR), antiarrhythmics (SCN5A, KCNH2)', color: '#2E7D32' },
                    { tier: 'Clinical Trial', desc: 'PCSK9 inhibitors, SGLT2 inhibitors (SLC5A2), novel anticoagulants (F11, F12)', color: '#1565C0' },
                    { tier: 'Druggable', desc: 'GPCRs, kinases, ion channels, nuclear receptors (Hopkins & Groom 2002)', color: '#6A1B9A' },
                  ].map(({ tier, desc, color }) => (
                    <Box key={tier} sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                      <Chip label={tier} size="small"
                        sx={{ bgcolor: `${color}15`, color, fontWeight: 700, fontSize: '0.7rem', flexShrink: 0, height: 22 }} />
                      <Typography variant="caption" color="text.secondary" sx={{ pt: 0.25 }}>{desc}</Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Right sidebar */}
        <Grid item xs={12} lg={4}>

          {/* Output Metrics */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <TrendingUp sx={{ color: GREEN, fontSize: 22 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color: GREEN }}>Output Metrics</Typography>
              </Stack>
              <Stack spacing={1.5} divider={<Divider />}>
                {[
                  { label: 'NES Score', desc: 'Composite enrichment score with √normalization, database quality weights, and network centrality.' },
                  { label: 'FDR-Adjusted P-value', desc: 'Benjamini-Hochberg correction from g:Profiler. Threshold ≤ 0.05.' },
                  { label: 'Empirical P-value', desc: '25 degree-preserving permutations. Topology-preserving null distribution.' },
                  { label: 'Fold-Enrichment', desc: 'Observed/expected gene overlap ratio. Minimum 2.0× required.' },
                  { label: 'Cardiac Disease Score', desc: 'Association score (0–1) from curated cardiovascular gene sets and pathway membership.' },
                  { label: 'Druggability Tier', desc: 'FDA approved → clinical trial → druggable, from curated DrugBank/TTD/ChEMBL data.' },
                ].map(({ label, desc }) => (
                  <Box key={label}>
                    <Typography variant="body2" fontWeight={700} sx={{ color: '#1A1A1A', mb: 0.25 }}>{label}</Typography>
                    <Typography variant="caption" color="text.secondary">{desc}</Typography>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>

          {/* Statistical Rigor */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <Science sx={{ color: GREEN, fontSize: 22 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color: GREEN }}>Statistical Rigor</Typography>
              </Stack>
              <Stack spacing={1.25}>
                {[
                  { label: 'FDR Correction', detail: 'Benjamini-Hochberg via g:Profiler on all enrichment results' },
                  { label: 'Permutation Testing', detail: '25 degree-preserving permutations, empirical p-values per pathway' },
                  { label: 'Topology Preservation', detail: 'Stratified sampling by degree quintile (5 bins)' },
                  { label: 'Gene Set Normalization', detail: '√(gene_count) — GSEA standard' },
                  { label: 'Effect Size Filter', detail: 'Fold-enrichment ≥ 2.0 required' },
                  { label: 'Redundancy Removal', detail: 'Jaccard similarity ≥ 0.85 threshold' },
                ].map(({ label, detail }) => (
                  <Box key={label} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                    <CheckCircleOutline sx={{ fontSize: 16, color: GREEN, mt: 0.25, flexShrink: 0 }} />
                    <Box>
                      <Typography variant="caption" fontWeight={700} sx={{ color: '#1A1A1A' }}>{label}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">{detail}</Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>

          {/* Data Sources */}
          <Card elevation={1} sx={{ mb: 3 }}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <AccountTree sx={{ color: GREEN, fontSize: 22 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color: GREEN }}>Data Sources</Typography>
              </Stack>
              <Table size="small">
                <TableBody>
                  {[
                    { src: 'STRING v11.5', use: 'PPI networks, 75 neighbors/gene' },
                    { src: 'g:Profiler', use: 'GO:BP, KEGG, Reactome, WikiPathways' },
                    { src: 'GTEx v8', use: 'Cardiac tissue expression (live API)' },
                    { src: 'PubMed/NCBI', use: 'Literature mining, 50 abstracts/gene' },
                    { src: 'DrugBank v5.1.10', use: 'Druggability curated gene lists (Nov 2023)' },
                    { src: 'ChEMBL REST API', use: 'Live drug phase & activity lookup (EBI)' },
                  ].map(({ src, use }) => (
                    <TableRow key={src} sx={{ '&:last-child td': { border: 0 } }}>
                      <TableCell sx={{ py: 0.75, px: 0, fontWeight: 600, fontSize: '0.75rem', color: GREEN, whiteSpace: 'nowrap', verticalAlign: 'top', pr: 1.5 }}>
                        {src}
                      </TableCell>
                      <TableCell sx={{ py: 0.75, px: 0, fontSize: '0.72rem', color: '#666' }}>
                        {use}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Default Parameters */}
          <Card elevation={1}>
            <CardContent sx={{ p: 2.5 }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
                <LibraryBooks sx={{ color: GREEN, fontSize: 22 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, color: GREEN }}>Default Parameters</Typography>
              </Stack>
              <Table size="small">
                <TableBody>
                  {[
                    { param: 'STRING neighbors', value: '75' },
                    { param: 'Confidence threshold', value: '≥ 0.60' },
                    { param: 'FDR threshold', value: '≤ 0.05' },
                    { param: 'Permutations', value: '25' },
                    { param: 'Top hypotheses', value: '15' },
                    { param: 'PubMed per gene', value: '50' },
                    { param: 'Jaccard threshold', value: '≥ 0.85' },
                    { param: 'Min fold-enrichment', value: '2.0×' },
                  ].map(({ param, value }) => (
                    <TableRow key={param} sx={{ '&:last-child td': { border: 0 } }}>
                      <TableCell sx={{ py: 0.75, px: 0, fontSize: '0.75rem', color: '#555', pr: 1 }}>{param}</TableCell>
                      <TableCell sx={{ py: 0.75, px: 0, fontSize: '0.75rem', fontWeight: 700, color: '#1A1A1A', textAlign: 'right' }}>{value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
