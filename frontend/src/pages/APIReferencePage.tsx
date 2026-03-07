import { Box, Chip, Container, Divider, Paper, Stack, Typography } from '@mui/material';
import { Api, Code, Lan } from '@mui/icons-material';
import { getApiBaseUrl, getWebSocketUrl } from '../api/client';

const restEndpoints = [
  ['GET', '/api/v1/health'],
  ['POST', '/api/v1/genes/validate'],
  ['POST', '/api/v1/analysis/run'],
  ['GET', '/api/v1/analysis/{analysis_id}/status'],
  ['GET', '/api/v1/analysis/{analysis_id}/results'],
  ['GET', '/api/v1/analysis/{analysis_id}/detailed-results'],
  ['GET', '/api/v1/analysis/{analysis_id}/report/{format}'],
];

export default function APIReferencePage() {
  const apiBaseUrl = getApiBaseUrl();
  const websocketExample = getWebSocketUrl('/api/v1/analysis/{analysis_id}/progress');

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Stack spacing={3}>
        <Paper
          elevation={0}
          sx={{
            p: 4,
            borderRadius: 3,
            border: '1px solid #D8E8E2',
            background: 'linear-gradient(180deg, #FFFFFF 0%, #F4FAF7 100%)',
          }}
        >
          <Stack spacing={1.25}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Api sx={{ color: '#1F5A46' }} />
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                API Reference
              </Typography>
            </Stack>
            <Typography variant="body1" color="text.secondary">
              The frontend talks to the same versioned API used by the smoke tests. Use these
              endpoints for scripted analyses or for external integrations.
            </Typography>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                Base URL
              </Typography>
              <Typography sx={{ fontFamily: 'monospace', color: '#1F5A46', fontWeight: 700 }}>
                {apiBaseUrl}
              </Typography>
            </Box>
          </Stack>
        </Paper>

        <Paper elevation={0} sx={{ p: 3, border: '1px solid #D8E8E2', borderRadius: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            REST Endpoints
          </Typography>
          <Stack spacing={1.25}>
            {restEndpoints.map(([method, path]) => (
              <Stack key={path} direction="row" spacing={1.5} alignItems="center">
                <Chip
                  label={method}
                  size="small"
                  color={method === 'POST' ? 'success' : 'primary'}
                  sx={{ minWidth: 56 }}
                />
                <Typography sx={{ fontFamily: 'monospace' }}>{path}</Typography>
              </Stack>
            ))}
          </Stack>
        </Paper>

        <Paper elevation={0} sx={{ p: 3, border: '1px solid #D8E8E2', borderRadius: 3 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Code sx={{ color: '#1F5A46' }} />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Example Request
              </Typography>
            </Stack>
            <Divider />
            <Box
              component="pre"
              sx={{
                m: 0,
                p: 2,
                overflow: 'auto',
                fontSize: '0.85rem',
                borderRadius: 2,
                bgcolor: '#F6F8F7',
                fontFamily: 'monospace',
              }}
            >
{`curl -X POST "${apiBaseUrl}/api/v1/analysis/run" \\
  -H "Content-Type: application/json" \\
  -d '{
    "seed_genes": ["PIK3R1", "ITGB1", "SRC"],
    "disease_context": "cardiomyopathy",
    "config_overrides": {
      "string_neighbor_count": 80,
      "primary_pathways_to_expand": 30
    }
  }'`}
            </Box>
            <Typography variant="body2" color="text.secondary">
              The analysis endpoint is asynchronous. Poll the status endpoint or subscribe to the
              WebSocket progress channel until the run completes.
            </Typography>
          </Stack>
        </Paper>

        <Paper elevation={0} sx={{ p: 3, border: '1px solid #D8E8E2', borderRadius: 3 }}>
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={1.5} alignItems="center">
              <Lan sx={{ color: '#1F5A46' }} />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                WebSocket Progress Channel
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Subscribe here for live stage, progress, and completion updates:
            </Typography>
            <Typography sx={{ fontFamily: 'monospace', color: '#1F5A46', fontWeight: 700 }}>
              {websocketExample}
            </Typography>
          </Stack>
        </Paper>
      </Stack>
    </Container>
  );
}
