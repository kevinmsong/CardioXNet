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
          CardioXNet REST API Documentation
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
      </Paper>

      {/* Main Analysis Endpoint */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="POST" color="success" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/fast-analysis</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Run the complete 9-stage CardioXNet NETS pipeline for cardiovascular pathway discovery.
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Request Body
        </Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem', mb: 2 }}>
          <pre style={{ margin: 0 }}>
{`{
  "seed_genes": ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"],
  "disease_context": "cardiomyopathy",
  "output_format": "all"
}`}
          </pre>
        </Box>

        <Typography variant="subtitle2" fontWeight={600} gutterBottom sx={{ mt: 2 }}>
          Parameters
        </Typography>
        <Stack spacing={1.5} sx={{ ml: 2 }}>
          <Box>
            <Typography variant="body2" fontWeight={600}>seed_genes <Chip label="required" size="small" color="error" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">Array of gene symbols (1-50 genes recommended)</Typography>
          </Box>
          <Box>
            <Typography variant="body2" fontWeight={600}>disease_context <Chip label="optional" size="small" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">
              Disease context for semantic filtering. Options: <code>heart_failure</code>, <code>cardiomyopathy</code>, <code>coronary_artery_disease</code>, 
              <code>myocardial_infarction</code>, <code>arrhythmia</code>, <code>atrial_fibrillation</code>, <code>hypertension</code>, 
              <code>stroke</code>, <code>valvular_disease</code>, <code>cardiovascular</code> (default)
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2" fontWeight={600}>output_format <Chip label="optional" size="small" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">Output format: <code>all</code> (HTML + JSON + MD), <code>json</code>, <code>html</code>, <code>markdown</code>. Default: <code>all</code></Typography>
          </Box>
        </Stack>

        <Typography variant="subtitle1" fontWeight={600} gutterBottom sx={{ mt: 3 }}>
          Response (202 Accepted)
        </Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>
{`{
  "analysis_id": "fast_analysis_20251017_061521",
  "status": "processing",
  "message": "Analysis started successfully"
}`}
          </pre>
        </Box>

        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            This is an asynchronous endpoint. Use the <code>analysis_id</code> to poll the progress endpoint.
          </Typography>
        </Alert>
      </Paper>

      {/* Progress Endpoint */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/analysis/{'<analysis_id>'}/progress</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Get real-time progress updates for a running analysis.
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Response (200 OK)
        </Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>
{`{
  "analysis_id": "fast_analysis_20251017_061521",
  "status": "processing",
  "progress": 85.0,
  "stage": "topology",
  "stage_name": "Topology analysis",
  "message": "Analyzing network topology..."
}`}
          </pre>
        </Box>

        <Typography variant="subtitle2" fontWeight={600} gutterBottom sx={{ mt: 2 }}>
          Status Values
        </Typography>
        <Stack spacing={1} sx={{ ml: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CheckCircle fontSize="small" color="success" />
            <Typography variant="body2"><code>complete</code> - Analysis finished successfully</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Code fontSize="small" color="primary" />
            <Typography variant="body2"><code>processing</code> - Analysis in progress</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Error fontSize="small" color="error" />
            <Typography variant="body2"><code>failed</code> - Analysis encountered an error</Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Results Endpoint */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/analysis/{'<analysis_id>'}/results</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Retrieve complete analysis results including pathways, topology data, and validation metrics.
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Response (200 OK)
        </Typography>
        <Box sx={{ bgcolor: '#F5F5F5', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.9rem' }}>
          <pre style={{ margin: 0 }}>
{`{
  "analysis_id": "fast_analysis_20251017_061521",
  "status": "complete",
  "seed_genes": ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"],
  "disease_context": "cardiomyopathy",
  "pathways": [
    {
      "pathway_id": "GO:0006936",
      "name": "Muscle Contraction",
      "nes_score": 245.8,
      "p_adj": 1.2e-15,
      "evidence_count": 42,
      "database": "GO:BP",
      "cardiac_relevance": 0.95,
      "druggability_tier": "FDA Approved",
      "tissue_expression_ratio": 0.88
    }
  ],
  "top_genes": [...],
  "summary_statistics": {...}
}`}
          </pre>
        </Box>
      </Paper>

      {/* Report Download Endpoint */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Chip label="GET" color="primary" size="small" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>/api/analysis/{'<analysis_id>'}/report</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" paragraph>
          Download comprehensive analysis report in HTML, JSON, or Markdown format.
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
          Query Parameters
        </Typography>
        <Stack spacing={1} sx={{ ml: 2 }}>
          <Box>
            <Typography variant="body2" fontWeight={600}>format <Chip label="optional" size="small" sx={{ ml: 1, height: 18 }} /></Typography>
            <Typography variant="body2" color="text.secondary">Report format: <code>html</code>, <code>json</code>, <code>markdown</code>. Default: <code>html</code></Typography>
          </Box>
        </Stack>

        <Typography variant="subtitle1" fontWeight={600} gutterBottom sx={{ mt: 2 }}>
          Response (200 OK)
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Returns the report file with appropriate Content-Type header.
        </Typography>
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
            <Typography variant="body2" color="text.secondary">Invalid request parameters (e.g., empty seed_genes array)</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>404 Not Found</Typography>
            <Typography variant="body2" color="text.secondary">Analysis ID not found</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>500 Internal Server Error</Typography>
            <Typography variant="body2" color="text.secondary">Server error during analysis processing</Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Example Usage */}
      <Paper sx={{ p: 3, bgcolor: '#E3F2FD', border: '1px solid #2196F3' }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Code color="primary" />
          Example Usage (Python)
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Box sx={{ bgcolor: 'white', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.85rem' }}>
          <pre style={{ margin: 0, overflow: 'auto' }}>
{`import requests
import time

# Start analysis
response = requests.post(
    "http://localhost:8000/api/fast-analysis",
    json={
        "seed_genes": ["TTN", "MYH7", "MYBPC3", "TNNT2", "LMNA"],
        "disease_context": "cardiomyopathy",
        "output_format": "all"
    }
)
analysis_id = response.json()["analysis_id"]

# Poll progress
while True:
    progress = requests.get(
        f"http://localhost:8000/api/analysis/{analysis_id}/progress"
    ).json()
    
    print(f"Progress: {progress['progress']}% - {progress['stage_name']}")
    
    if progress["status"] == "complete":
        break
    elif progress["status"] == "failed":
        raise Exception("Analysis failed")
    
    time.sleep(2)

# Get results
results = requests.get(
    f"http://localhost:8000/api/analysis/{analysis_id}/results"
).json()

print(f"Found {len(results['pathways'])} pathways")
print(f"Top pathway: {results['pathways'][0]['name']}")
print(f"NES Score: {results['pathways'][0]['nes_score']}")`}
          </pre>
        </Box>
      </Paper>
    </Container>
  );
}
