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
      // No analysis ID provided, redirect to home
      navigate('/');
      return;
    }

    let ws: WebSocket | null = null;
    let mounted = true;
    let pollInterval: NodeJS.Timeout | null = null;

    // Fallback polling in case WebSocket fails
    const startPolling = () => {
      pollInterval = setInterval(async () => {
        try {
          const status = await api.getAnalysisStatus(analysisId);
          
          if (status.progress_percentage !== undefined) setProgress(status.progress_percentage);
          if (status.current_stage) setCurrentStage(status.current_stage);
          if (status.message) setMessage(status.message);
          if (status.status) setStatus(status.status);
          
          if (status.status === 'completed') {
            if (pollInterval) clearInterval(pollInterval);
            setTimeout(() => navigate(`/results/${analysisId}`), 2000);
          } else if (status.status === 'failed') {
            if (pollInterval) clearInterval(pollInterval);
          }
        } catch (error: any) {
          // Only redirect if we're still on the progress page
          // Don't interfere with navigation to other pages
          if (pollInterval) clearInterval(pollInterval);
          if (mounted && window.location.pathname.includes('/progress/')) {
            navigate('/');
          }
        }
      }, 2000); // Poll every 2 seconds
    };

    // Small delay to ensure analysis is created
    const connectWebSocket = () => {
      if (!mounted) return;

      ws = api.connectWebSocket(analysisId);

      ws.onopen = () => {};

      ws.onmessage = (event) => {
        if (!mounted) return;
        
        const data: ProgressMessage = JSON.parse(event.data);
        setProgress(data.progress || 0);
        setCurrentStage(data.current_stage || '');
        setMessage(data.message || '');
        setStatus(data.status);

        if (data.type === 'complete') {
          if (data.status === 'completed') {
            setTimeout(() => navigate(`/results/${analysisId}`), 2000);
          }
        }
      };

      ws.onerror = (error) => {
        startPolling();
      };

      ws.onclose = () => {
        // Start polling as fallback if WebSocket closes unexpectedly
        if (status !== 'completed' && status !== 'failed') {
          startPolling();
        }
      };
    };

    // Connect after a small delay
    const timer = setTimeout(connectWebSocket, 100);

    return () => {
      mounted = false;
      clearTimeout(timer);
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (ws) {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
        ws = null;
      }
    };
  }, [analysisId, navigate, status]);

  const stages = [
    'Stage 1: Seed Gene Validation',
    'Stage 2: Functional Neighborhood',
    'Stage 3: Primary Pathway Enrichment',
    'Stage 4: Secondary Pathway Discovery',
    'Stage 5: Pathway Aggregation',
    'Stage 6: Semantic Filtering',
    'Stage 7: NES Scoring',
    'Stage 8: Enhanced Validation',
    'Stage 9: Literature Mining',
  ];

  const stageDescriptions: { [key: string]: string } = {
    'Stage 1': 'Validating input genes and checking API connectivity',
    'Stage 2': 'Building protein interaction networks (STRING database)',
    'Stage 3': 'Primary pathway enrichment (g:Profiler: GO, KEGG, Reactome, WikiPathways)',
    'Stage 4': 'Secondary pathway discovery through network expansion',
    'Stage 5': 'Aggregating pathways and tracking complete lineage',
    'Stage 6': 'Filtering pathways by strict cardiac term matching',
    'Stage 7': 'Computing NETS (Neighborhood Enrichment Triage and Scoring) scores',
    'Stage 8': 'Enhanced validation (GTEx cardiac expression, druggability, therapeutic targets)',
    'Stage 9': 'Mining PubMed for cardiovascular disease literature evidence',
  };

  // Get the index of the current stage
  const getCurrentStageIndex = (stage: string) => {
    const stageMap: { [key: string]: number } = {
      // Backend sends "Stage 1", "Stage 2", etc.
      'Stage 1': 0,
      'Stage 2': 1,
      'Stage 3': 2,
      'Stage 4': 3,
      'Stage 5': 4,
      'Stage 6': 5,
      'Stage 7': 6,
      'Stage 8': 7,
      'Stage 9': 8,
      'Stage 10': 8,  // Old stage 10 maps to stage 9
      'Stage 11': 8,  // Old stage 11 maps to stage 9
      'Stage 12': 8,  // Old stage 12 maps to stage 9
      'Complete': 9,
      'complete': 9,
      'Error': -1,
      'error': -1,
    };
    return stageMap[stage] ?? -1;
  };

  const currentStageIndex = getCurrentStageIndex(currentStage);

  const estimatedTimeRemaining = Math.max(0, Math.round((100 - progress) / 100 * 5)); // ~5 min total

  return (
    <Box>
      {/* Enhanced Header */}
      <Paper
        elevation={3}
        sx={{
          p: 3,
          mb: 3,
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          borderRadius: 3,
          border: '2px solid #FFB81C',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ position: 'relative' }} spacing={3}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h4" sx={{ color: 'white', fontWeight: 700, mb: 1 }}>
              Analysis in Progress
            </Typography>
            <Typography variant="h6" sx={{ color: '#FFB81C', fontWeight: 600, mb: 1 }}>
              {currentStage || 'Initializing pipeline...'}
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.85)', lineHeight: 1.6, mb: 1 }}>
              {stageDescriptions[currentStage.split(':')[0]] || 'Running analysis...'}
            </Typography>
            {currentStage.includes('Stage 2') && (
              <Typography variant="caption" sx={{ color: '#FFB81C', fontStyle: 'italic', display: 'block', mt: 0.5 }}>
                ⚠️ g:Profiler may be slow or temporarily unavailable. Retrying automatically...
              </Typography>
            )}
          </Box>
          <Box sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
            <Typography variant="h3" sx={{ color: '#FFB81C', fontWeight: 700 }}>
              {progress}%
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)', display: 'block' }}>
              Est. {estimatedTimeRemaining} min remaining
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Progress Visualization */}
      <Paper 
        elevation={2}
        sx={{ 
          p: 3, 
          mb: 3,
          borderRadius: 3,
          border: '2px solid #E8F5E9',
        }}
      >
        <LinearProgress 
          variant="determinate" 
          value={progress} 
          sx={{ 
            mb: 2,
            height: 12,
            borderRadius: 6,
            bgcolor: '#E0E0E0',
            '& .MuiLinearProgress-bar': {
              bgcolor: '#1E6B52',
              borderRadius: 6,
              transition: 'transform 0.4s ease-in-out',
            }
          }} 
        />
        <Stack spacing={1}>
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{ 
              textAlign: 'center',
              fontStyle: 'italic',
              minHeight: '20px',
            }}
          >
            {message || 'Processing your analysis...'}
          </Typography>
          {currentStage.includes('Stage 2') && (
            <Box sx={{ 
              p: 1.5, 
              bgcolor: '#FFF3E0', 
              borderRadius: 2, 
              border: '1px solid #FFB74D',
              textAlign: 'center'
            }}>
              <Typography variant="caption" sx={{ color: '#E65100', fontWeight: 600 }}>
                ℹ️ Pathway enrichment may take 1-2 minutes. If g:Profiler is unavailable, the system will retry automatically.
              </Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* Pipeline Stages */}
      <Paper 
        elevation={2}
        sx={{ 
          p: 3, 
          mb: 3,
          borderRadius: 3,
          border: '2px solid #E3F2FD',
        }}
      >
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: '#1E6B52', mb: 3 }}>
          Pipeline Stages
        </Typography>
        <List sx={{ p: 0 }}>
          {stages.map((stage, index) => {
            const isCompleted = index < currentStageIndex;
            const isCurrent = index === currentStageIndex;
            
            let icon;
            if (isCompleted) {
              icon = <CheckCircle sx={{ fontSize: 28, color: '#4CAF50' }} />;
            } else if (isCurrent) {
              icon = (
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <CircularProgress size={28} thickness={4} sx={{ color: '#1E6B52' }} />
                </Box>
              );
            } else {
              icon = <RadioButtonUnchecked sx={{ fontSize: 28, color: '#BDBDBD' }} />;
            }
            
            return (
              <ListItem 
                key={index}
                sx={{
                  py: 1.5,
                  px: 2,
                  mb: 1,
                  borderRadius: 2,
                  bgcolor: isCurrent ? 'rgba(30, 107, 82, 0.05)' : 'transparent',
                  border: isCurrent ? '2px solid #E8F5E9' : '2px solid transparent',
                  transition: 'all 0.3s ease-in-out',
                  transform: isCurrent ? 'scale(1.02)' : 'scale(1)',
                }}
              >
                <Box sx={{ mr: 2 }}>{icon}</Box>
                <ListItemText 
                  primary={stage}
                  sx={{
                    '& .MuiListItemText-primary': {
                      fontWeight: isCurrent ? 600 : isCompleted ? 500 : 'normal',
                      color: isCurrent ? '#1E6B52' : isCompleted ? '#4CAF50' : '#9E9E9E',
                      fontSize: isCurrent ? '1.05rem' : '1rem',
                    }
                  }}
                />
                {isCompleted && (
                  <Chip 
                    label="Completed" 
                    size="small" 
                    sx={{ 
                      bgcolor: '#E8F5E9', 
                      color: '#4CAF50',
                      fontWeight: 600,
                    }} 
                  />
                )}
                {isCurrent && (
                  <Chip 
                    label="In Progress" 
                    size="small" 
                    sx={{ 
                      bgcolor: '#E8F5E9', 
                      color: '#1E6B52',
                      fontWeight: 600,
                    }} 
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
          fullWidth
          sx={{ mt: 2 }}
          onClick={() => navigate(`/results/${analysisId}`)}
        >
          View Results
        </Button>
      )}
    </Box>
  );
}
