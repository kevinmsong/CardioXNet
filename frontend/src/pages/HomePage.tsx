import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Stack,
} from '@mui/material';
// Icons removed - none currently used in HomePage
import GeneInputPanel from '../components/GeneInputPanel';
import ConfigurationPanel from '../components/ConfigurationPanel';
import { clearAnalysisMemory } from '../utils/analysisMemory';

export default function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedGenes, setSelectedGenes] = useState<string[]>([]);
  const [config, setConfig] = useState<Record<string, any>>({});

  // Clear analysis memory when navigating to home page
  useEffect(() => {
    clearAnalysisMemory(queryClient);
  }, [queryClient]);

  const handleAnalysisStart = (analysisId: string) => {
    navigate(`/progress/${analysisId}`);
  };

  return (
    <Box>
      {/* Professional Hero Section */}
      <Paper
        elevation={4}
        sx={{
          mb: 4,
          p: { xs: 3, md: 5 },
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          borderRadius: 3,
          boxShadow: '0 12px 48px rgba(30, 107, 82, 0.2)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Typography
            variant="h2"
            sx={{
              fontWeight: 800,
              color: '#FFFFFF',
              mb: 0.5,
              fontSize: { xs: '2rem', md: '2.8rem' },
              letterSpacing: '-0.5px',
            }}
          >
            CardioXNet
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: '#FFB81C',
              fontWeight: 600,
              mb: 2.5,
              fontSize: { xs: '0.95rem', md: '1.1rem' },
              letterSpacing: '0.5px',
            }}
          >
            AI-Powered Cardiovascular Pathway Discovery Platform
          </Typography>

          <Stack spacing={1.2} sx={{ mb: 2.5 }}>
            <Typography
              variant="body1"
              sx={{
                color: 'rgba(255,255,255,0.95)',
                lineHeight: 1.7,
                fontSize: '0.95rem',
              }}
            >
              Discover novel cardiovascular disease pathways through the NETS (Neighborhood Enrichment Triage and Scoring) algorithm. 
              Integrates multiple pathway databases, literature validation, and tissue expression analysis for comprehensive cardiac pathway discovery.
            </Typography>
          </Stack>


        </Box>
      </Paper>

      {/* Main Content Grid */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          {/* Gene Input Section */}
          <Paper
            elevation={2}
            sx={{
              p: 3,
              mb: 3,
              border: '2px solid #E8F5E9',
              borderRadius: 3,
              bgcolor: '#FFFFFF',
            }}
          >
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 600,
                  color: '#1E6B52',
                  mb: 0.5,
                }}
              >
                Gene Input
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Enter or paste your cardiovascular gene list to begin analysis
              </Typography>
            </Box>
            <GeneInputPanel
              selectedGenes={selectedGenes}
              onGenesChange={setSelectedGenes}
              config={config}
              onAnalysisStart={handleAnalysisStart}
            />
          </Paper>

          {/* Configuration Section */}
          <Paper
            elevation={2}
            sx={{
              p: 3,
              border: '2px solid #E3F2FD',
              borderRadius: 3,
              bgcolor: '#FFFFFF',
            }}
          >
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 600,
                  color: '#1E6B52',
                  mb: 0.5,
                }}
              >
                Analysis Configuration
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Customize pipeline parameters for optimal results
              </Typography>
            </Box>
            <ConfigurationPanel
              config={config}
              onConfigChange={setConfig}
            />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
