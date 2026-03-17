import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Button,
  Stack,
  CircularProgress,
  Chip,
} from '@mui/material';
import { CheckCircle, RadioButtonUnchecked } from '@mui/icons-material';
import api from '../api/endpoints';
import type { ProgressMessage } from '../api/types';

export default function ProgressPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('running');

  useEffect(() => {
    if (!analysisId) {
      navigate('/');
      return;
    }

    let ws: WebSocket | null = null;
    let mounted = true;
    let pollInterval: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const statusData = await api.getAnalysisStatus(analysisId);
          if (statusData.progress_percentage !== undefined) setProgress(statusData.progress_percentage);
          if (statusData.current_stage) setCurrentStage(statusData.current_stage);
          if (statusData.message) setMessage(statusData.message);
          if (statusData.status) setStatus(statusData.status);

          if (statusData.status === 'completed') {
            if (pollInterval) clearInterval(pollInterval);
            setTimeout(() => navigate(`/results/${analysisId}`), 2000);
          } else if (statusData.status === 'failed') {
            if (pollInterval) clearInterval(pollInterval);
          }
        } catch {
          if (pollInterval) clearInterval(pollInterval);
          if (mounted && window.location.pathname.includes('/progress/')) {
            navigate('/');
          }
        }
      }, 2000);
    };

    const connectWebSocket = () => {
      if (!mounted) return;

      ws = api.connectWebSocket(analysisId);

      ws.onmessage = (event) => {
        if (!mounted) return;
        const data: ProgressMessage = JSON.parse(event.data);
        setProgress(data.progress || 0);
        setCurrentStage(data.current_stage || '');
        setMessage(data.message || '');
        setStatus(data.status);

        if (data.type === 'complete' && data.status === 'completed') {
          setTimeout(() => navigate(`/results/${analysisId}`), 2000);
        }
      };

      ws.onerror = () => startPolling();

      ws.onclose = () => {
        if (status !== 'completed' && status !== 'failed') {
          startPolling();
        }
      };
    };

    const timer = setTimeout(connectWebSocket, 100);

    return () => {
      mounted = false;
      clearTimeout(timer);
      if (pollInterval) clearInterval(pollInterval);
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
  }, [analysisId, navigate, status]);

  const stages = [
    'Stage 1: Input Validation',
    'Stage 2: Functional Neighborhood',
    'Stage 3: Primary Pathway Enrichment',
    'Stage 4: Secondary Pathway Discovery',
    'Stage 5: Pathway Aggregation',
    'Stage 6: NES Scoring',
    'Stage 7: Semantic Filtering',
    'Stage 8: Enhanced Validation',
    'Stage 9: Literature Mining',
    'Stage 10: Network Topology Analysis',
    'Stage 11: Therapeutic Targets',
    'Stage 12: Report Generation',
  ];

  const stageDescriptions: { [key: string]: string } = {
    'Stage 1': 'Validating input genes and normalizing identifiers',
    'Stage 2': 'Building protein interaction networks via STRING (75 neighbors, confidence ≥ 0.60)',
    'Stage 3': 'Primary pathway enrichment using g:Profiler (GO:BP, KEGG, Reactome, WikiPathways)',
    'Stage 4': 'Secondary pathway discovery through network expansion and aggregation',
    'Stage 5': 'Aggregating pathways and removing redundant entries (Jaccard ≥ 0.85)',
    'Stage 6': 'Computing NES scores with √(gene_count) normalization and database quality weighting',
    'Stage 7': 'Cardiac disease context filtering (3-tier thresholds, 700+ cardiovascular terms)',
    'Stage 8': 'Biological validation: GTEx tissue expression, permutation testing, druggability',
    'Stage 9': 'Mining PubMed abstracts for pathway-gene literature evidence (20/gene)',
    'Stage 10': 'Network topology analysis: PageRank, betweenness, closeness centrality',
    'Stage 11': 'Identifying druggable therapeutic targets (FDA approved, clinical trials, research)',
    'Stage 12': 'Generating analysis reports (JSON, PDF)',
  };

  const getCurrentStageIndex = (stage: string) => {
    const stageMap: { [key: string]: number } = {
      'input_validation': 0,
      'functional_neighborhood': 1,
      'primary_pathway': 2,
      'secondary_pathway': 3,
      'pathway_aggregation': 4,
      'nes_scoring': 5,
      'semantic_filtering': 6,
      'enhanced_validation': 7,
      'literature_mining': 8,
      'topology_analysis': 9,
      'therapeutic_targets': 10,
      'report_generation': 11,
      'complete': 12,
    };
    return stageMap[stage] ?? -1;
  };

  const currentStageIndex = getCurrentStageIndex(currentStage);

  const getEstimatedTimeRemaining = () => {
    if (progress >= 100) return 0;
    const stageDurations: { [key: number]: number } = {
      0: 0.2, 1: 1.2, 2: 2.0, 3: 2.5, 4: 0.5,
      5: 0.4, 6: 1.0, 7: 2.5, 8: 1.5, 9: 1.0, 10: 0.4, 11: 0.3,
    };
    let remaining = 0;
    for (let i = currentStageIndex + 1; i < 12; i++) {
      remaining += stageDurations[i] || 0.5;
    }
    remaining += (stageDurations[currentStageIndex] || 1) * 0.5;
    return Math.max(0.5, Math.round(remaining));
  };

  const estimatedTimeRemaining = getEstimatedTimeRemaining();

  return (
    <Box>
      {/* Header */}
      <Paper
        elevation={3}
        sx={{
          p: 4,
          mb: 3,
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          borderRadius: 3,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={3}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h4" sx={{ color: 'white', fontWeight: 700, mb: 1 }}>
              Analysis in Progress
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.9)', mb: 2 }}>
              ID: <Box component="span" sx={{ fontFamily: 'monospace', color: '#FFB81C' }}>{analysisId}</Box>
            </Typography>
            <Typography variant="h6" sx={{ color: '#FFB81C', fontWeight: 600 }}>
              {currentStage || 'Initializing...'}
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography variant="h2" sx={{ color: '#FFB81C', fontWeight: 700, mb: 0.5 }}>
              {progress}%
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.9)' }}>
              ~{estimatedTimeRemaining} min remaining
            </Typography>
          </Box>
        </Stack>

        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            mt: 3,
            height: 10,
            borderRadius: 5,
            bgcolor: 'rgba(255,255,255,0.2)',
            '& .MuiLinearProgress-bar': {
              bgcolor: '#FFB81C',
              borderRadius: 5,
              transition: 'transform 0.4s ease-in-out',
            },
          }}
        />
      </Paper>

      {/* Current Status */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2, border: '1px solid #E0E0E0' }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1E6B52', mb: 2 }}>
          Current Status
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.primary', mb: 2, minHeight: '24px' }}>
          {message || 'Processing your analysis...'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {stageDescriptions[currentStage.split(':')[0]] || 'Running CardioXNet pathway discovery pipeline...'}
        </Typography>
      </Paper>

      {/* Pipeline Stages */}
      <Paper elevation={2} sx={{ p: 3, borderRadius: 2, border: '1px solid #E0E0E0' }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1E6B52', mb: 2 }}>
          Pipeline Stages
        </Typography>
        <List sx={{ p: 0 }}>
          {stages.map((stage, index) => {
            const isCompleted = index < currentStageIndex;
            const isCurrent = index === currentStageIndex;

            let icon;
            if (isCompleted) {
              icon = <CheckCircle sx={{ fontSize: 24, color: '#4CAF50' }} />;
            } else if (isCurrent) {
              icon = (
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <CircularProgress size={24} thickness={5} sx={{ color: '#1E6B52' }} />
                </Box>
              );
            } else {
              icon = <RadioButtonUnchecked sx={{ fontSize: 24, color: '#BDBDBD' }} />;
            }

            return (
              <ListItem
                key={index}
                sx={{
                  py: 1.5,
                  px: 2,
                  mb: 0.5,
                  borderRadius: 1,
                  bgcolor: isCurrent ? 'rgba(30, 107, 82, 0.04)' : 'transparent',
                  borderLeft: isCurrent ? '3px solid #1E6B52' : '3px solid transparent',
                  transition: 'all 0.2s ease',
                }}
              >
                <Box sx={{ mr: 2, display: 'flex', alignItems: 'center' }}>{icon}</Box>
                <ListItemText
                  primary={stage}
                  sx={{
                    '& .MuiListItemText-primary': {
                      fontWeight: isCurrent ? 600 : isCompleted ? 500 : 400,
                      color: isCurrent ? '#1E6B52' : isCompleted ? '#4CAF50' : '#757575',
                      fontSize: '0.95rem',
                    },
                  }}
                />
                {isCompleted && (
                  <Chip
                    label="✓"
                    size="small"
                    sx={{ bgcolor: '#E8F5E9', color: '#4CAF50', fontWeight: 600, fontSize: '0.75rem', height: '24px', minWidth: '32px' }}
                  />
                )}
                {isCurrent && (
                  <Chip
                    label="Running"
                    size="small"
                    sx={{ bgcolor: '#E8F5E9', color: '#1E6B52', fontWeight: 600, fontSize: '0.75rem', height: '24px' }}
                  />
                )}
              </ListItem>
            );
          })}
        </List>
      </Paper>

      {status === 'completed' && (
        <Button
          variant="contained"
          size="large"
          fullWidth
          sx={{
            mt: 3, py: 1.5,
            bgcolor: '#1E6B52',
            '&:hover': { bgcolor: '#145A43' },
            fontSize: '1.1rem',
            fontWeight: 600,
          }}
          onClick={() => navigate(`/results/${analysisId}`)}
        >
          View Results
        </Button>
      )}
    </Box>
  );
}
