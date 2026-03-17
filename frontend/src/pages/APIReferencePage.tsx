import { Box, Typography, Container, Paper, Divider, Stack, Chip, Alert } from '@mui/material';
import { Code, Api, CheckCircle, Error } from '@mui/icons-material';

export default function APIReferencePage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 700, color: '#1E6B52' }}>
          API Reference
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          CardioXNet REST API — v1
        </Typography>
      </Box>

      {/* Base URL */}
      <Paper sx={{ p: 3, mb: 3, bgcolor: '#F5F5F5' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Api color="primary" />
          Base URL
        </Typography>
        <Typography variant="body1" sx={{ fontFamily: 'monospace', color: '#1E6B52', fontWeight: 600 }}>
          http://localhost:8000
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Interactive docs: <code>http://localhost:8000/docs</code> (Swagger UI)
        </Typography>
      </Paper>

      {/* Gene Validation */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="POST" color="success" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/genes/validate</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Validate and normalize gene identifiers against HGNC before running an analysis.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Request Body</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem', mb: 2 }}>
          <pre style={{ margin: 0 }}>{`{ "gene_ids": ["TTN", "MYH7", "MYBPC3"] }`}</pre>
        </Box>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Response (200 OK)</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>{`{ "result": { "valid": ["TTN", "MYH7", "MYBPC3"], "invalid": [] } }`}</pre>
        </Box>
      </Paper>

      {/* Start Analysis */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="POST" color="success" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/analysis/run</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Start the 12-stage CardioXNet NETS pipeline. Returns an <code>analysis_id</code> immediately;
          use the status endpoint to poll progress.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Request Body</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem', mb: 2 }}>
          <pre style={{ margin: 0 }}>{`{
  "seed_genes": ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"],
  "disease_context": "cardiomyopathy",
  "config_overrides": {
    "string_neighbor_count": 75,
    "fdr_threshold": 0.05
  }
}`}</pre>
        </Box>
        <Typography variant="subtitle2" fontWeight={600} gutterBottom>Parameters</Typography>
        <Stack spacing={1.5} sx={{ ml: 2, mb: 2 }}>
          <Box>
            <Typography variant="body2" fontWeight={600}>seed_genes <Chip label="required" size="small" color="error" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">Array of HGNC gene symbols (1–50 genes recommended)</Typography>
          </Box>
          <Box>
            <Typography variant="body2" fontWeight={600}>disease_context <Chip label="optional" size="small" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">
              Focuses semantic filtering and literature mining. Options: <code>heart_failure</code>, <code>cardiomyopathy</code>,{' '}
              <code>myocardial_infarction</code>, <code>arrhythmia</code>, <code>diabetic_cardiomyopathy</code>. Default: general cardiovascular.
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" fontWeight={600}>config_overrides <Chip label="optional" size="small" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">Override pipeline parameters (see Configuration panel for available keys)</Typography>
          </Box>
        </Stack>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Response (200 OK)</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>{`{
  "analysis_id": "nets_20260316_143021_a1b2c3",
  "status": "started",
  "message": "Analysis started successfully"
}`}</pre>
        </Box>
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Asynchronous endpoint. Poll <code>/api/v1/analysis/{'<id>'}/status</code> every 2–3 seconds to track progress.
          </Typography>
        </Alert>
      </Paper>

      {/* Status */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/analysis/{'<analysis_id>'}/status</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Poll real-time progress for a running analysis.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Response (200 OK)</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem', mb: 2 }}>
          <pre style={{ margin: 0 }}>{`{
  "analysis_id": "nets_20260316_143021_a1b2c3",
  "status": "running",
  "current_stage": "semantic_filtering",
  "progress_percentage": 72.0,
  "message": "Applying cardiac disease context filters..."
}`}</pre>
        </Box>
        <Typography variant="subtitle2" fontWeight={600} gutterBottom>Status Values</Typography>
        <Stack spacing={1} sx={{ ml: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Code fontSize="small" color="primary" />
            <Typography variant="body2"><code>started</code> / <code>running</code> — Analysis in progress</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircle fontSize="small" color="success" />
            <Typography variant="body2"><code>completed</code> — Analysis finished; results ready</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Error fontSize="small" color="error" />
            <Typography variant="body2"><code>failed</code> — Analysis encountered an error</Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Results */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/analysis/{'<analysis_id>'}/results</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Retrieve complete analysis results including ranked pathways, seed genes, topology data, and top therapeutic target genes.
          Only available when status is <code>completed</code>.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Response (200 OK)</Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>{`{
  "analysis_id": "nets_20260316_143021_a1b2c3",
  "status": "completed",
  "seed_genes": [{ "symbol": "TTN", "entrez_id": "7273", ... }],
  "hypotheses": {
    "total_count": 87,
    "hypotheses": [
      {
        "pathway_id": "REAC:R-HSA-397014",
        "pathway_name": "Muscle contraction",
        "nes_score": 4.21,
        "p_adj": 1.2e-15,
        "evidence_count": 42,
        "score_components": { "cardiac_relevance": 0.94, ... }
      }
    ]
  },
  "top_genes": [{ "gene": "MYH7", "importance_score": 3.8, "pathway_count": 12 }],
  "topology": { "hub_genes": [...], "network_metrics": { ... } }
}`}</pre>
        </Box>
      </Paper>

      {/* Report Download */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/analysis/{'<analysis_id>'}/report/{'<format>'}</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Download the analysis report. Supported formats: <code>pdf</code>, <code>json</code>, <code>html</code>.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Returns the report file with the appropriate <code>Content-Type</code> header and a suggested filename.
          If the report has not yet been generated, it is created on demand.
        </Typography>
      </Paper>

      {/* Config Defaults */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/v1/config/defaults</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Returns current pipeline default parameters.
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>{`{
  "config": {
    "string_neighbor_count": 75,
    "string_score_threshold": 0.60,
    "fdr_threshold": 0.05,
    "top_hypotheses_count": 15,
    "aggregation_strategy": "frequency",
    "min_support_threshold": 1
  }
}`}</pre>
        </Box>
      </Paper>

      {/* Error Responses */}
      <Paper sx={{ p: 3, mb: 3, bgcolor: '#FFF3E0', border: '1px solid #FF9800' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Error color="warning" />
          Error Responses
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Stack spacing={2}>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>400 Bad Request</Typography>
            <Typography variant="body2" color="text.secondary">Invalid parameters or analysis not yet completed</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>404 Not Found</Typography>
            <Typography variant="body2" color="text.secondary">Analysis ID does not exist</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>500 Internal Server Error</Typography>
            <Typography variant="body2" color="text.secondary">Pipeline error — check backend logs for details</Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Python Example */}
      <Paper sx={{ p: 3, bgcolor: '#E3F2FD', border: '1px solid #2196F3' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Code color="primary" />
          Example Usage (Python)
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Box sx={{ bgcolor: 'white', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.85rem' }}>
          <pre style={{ margin: 0, overflow: 'auto' }}>{`import requests, time

BASE = "http://localhost:8000"

# Start analysis
r = requests.post(f"{BASE}/api/v1/analysis/run", json={
    "seed_genes": ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"],
    "disease_context": "cardiomyopathy",
})
analysis_id = r.json()["analysis_id"]
print(f"Started: {analysis_id}")

# Poll status
while True:
    status = requests.get(f"{BASE}/api/v1/analysis/{analysis_id}/status").json()
    print(f"{status['progress_percentage']:.0f}% — {status.get('message', '')}")
    if status["status"] == "completed":
        break
    elif status["status"] == "failed":
        raise RuntimeError("Analysis failed")
    time.sleep(3)

# Fetch results
results = requests.get(f"{BASE}/api/v1/analysis/{analysis_id}/results").json()
pathways = results["hypotheses"]["hypotheses"]
print(f"Found {len(pathways)} pathways")
print(f"Top: {pathways[0]['pathway_name']} (NES={pathways[0]['nes_score']:.2f})")

# Download PDF report
pdf = requests.get(f"{BASE}/api/v1/analysis/{analysis_id}/report/pdf")
with open("report.pdf", "wb") as f:
    f.write(pdf.content)
`}</pre>
        </Box>
      </Paper>
    </Container>
  );
}
