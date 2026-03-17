import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Box,
  TextField,
  Chip,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { PlayArrow, CheckCircle, Error, Info } from '@mui/icons-material';
import api from '../api/endpoints';

interface GeneInputPanelProps {
  selectedGenes: string[];
  onGenesChange: (genes: string[]) => void;
  config: Record<string, any>;
  onAnalysisStart: (analysisId: string) => void;
}

const DISEASE_OPTIONS = [
  {
    value: 'general',
    label: 'General Cardiovascular Discovery',
    description: 'Broad cardiac pathway prioritization without narrowing to a single disease'
  },
  {
    value: 'cardiomyopathy',
    label: 'Cardiomyopathy',
    description: 'Inherited or acquired myocardial dysfunction and remodeling'
  },
  {
    value: 'heart_failure',
    label: 'Heart Failure',
    description: 'Pump dysfunction, remodeling, stress response, and maladaptive signaling'
  },
  {
    value: 'diabetic_cardiomyopathy',
    label: 'Diabetic Cardiomyopathy',
    description: 'Heart dysfunction related to diabetes and metabolic dysfunction'
  },
  {
    value: 'myocardial_infarction',
    label: 'Myocardial Infarction',
    description: 'Ischemic injury, repair signaling, and post-infarct remodeling'
  },
  {
    value: 'arrhythmia',
    label: 'Arrhythmia',
    description: 'Conduction, ion channel, and rhythm-associated pathway focus'
  }
];

export default function GeneInputPanel({
  selectedGenes,
  onGenesChange,
  config,
  onAnalysisStart,
}: GeneInputPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [selectedDisease, setSelectedDisease] = useState<string>('');

  const validateMutation = useMutation({
    mutationFn: (genes: string[]) => api.validateGenes(genes),
  });

  const startAnalysisMutation = useMutation({
    mutationFn: (genes: string[]) => api.startAnalysis({ 
      seed_genes: genes,
      ...(selectedDisease && { disease_context: selectedDisease }),
      config_overrides: config
    }),
    onSuccess: (data) => {
      onAnalysisStart(data.analysis_id);
    },
  });

  // Parse gene list from various formats (space, comma, newline separated)
  const parseGeneList = (text: string): string[] => {
    return text
      .split(/[\s,\n\r]+/) // Split by spaces, commas, or newlines
      .map(gene => gene.trim())
      .filter(gene => gene.length > 0); // Remove empty strings
  };

  const parsedInputCount = useMemo(
    () => inputValue.split(/[\s,\n\r,]+/).filter((gene) => gene.length > 0).length,
    [inputValue]
  );

  const handleAddGenes = () => {
    if (inputValue.trim()) {
      const parsedGenes = parseGeneList(inputValue);
      const uniqueGenes = [...new Set([...selectedGenes, ...parsedGenes])]; // Remove duplicates
      onGenesChange(uniqueGenes);
      setInputValue('');
      validateMutation.mutate(uniqueGenes);
    }
  };

  const handleClearAll = () => {
    onGenesChange([]);
    setInputValue('');
  };

  const handleStartAnalysis = () => {
    if (selectedGenes.length > 0) {
      startAnalysisMutation.mutate(selectedGenes);
    }
  };

  return (
    <Box>
      <Stack spacing={2}>
        {/* Disease Context Selection */}
        <FormControl fullWidth>
          <InputLabel>Disease Context</InputLabel>
          <Select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            label="Disease Context"
          >
            {DISEASE_OPTIONS.map((disease) => (
              <MenuItem key={disease.value} value={disease.value}>
                <Box>
                  <Typography variant="body2" fontWeight={600}>
                    {disease.label}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {disease.description}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {selectedDisease && (
          <Alert severity="info" icon={<Info />}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              Disease Context: {DISEASE_OPTIONS.find(d => d.value === selectedDisease)?.label}
            </Typography>
            <Typography variant="caption" display="block" gutterBottom>
              {DISEASE_OPTIONS.find(d => d.value === selectedDisease)?.description}
            </Typography>
            <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'rgba(25, 118, 210, 0.08)', borderRadius: 1, borderLeft: '3px solid #1976d2' }}>
              <Typography variant="caption" fontWeight={600} display="block" sx={{ mb: 0.5 }}>
                What this changes:
              </Typography>
              <Typography variant="caption" component="div" sx={{ fontSize: '0.75rem', lineHeight: 1.6 }}>
                <strong>• Funnel control:</strong> Prioritizes pathway branches relevant to this disease<br/>
                <strong>• Semantic focus:</strong> Raises the score of disease-matched pathway language<br/>
                <strong>• Literature focus:</strong> Centers PubMed queries on the selected context<br/>
                <strong>• Interpretability:</strong> Makes final rankings easier to review in one disease frame
              </Typography>
            </Box>
          </Alert>
        )}

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Enter or Paste Gene Symbols"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleAddGenes();
            }
          }}
          placeholder="Example: PIK3R1 ITGB1 SRC"
          helperText={`${parsedInputCount} gene symbol${parsedInputCount === 1 ? '' : 's'} detected`}
          disabled={validateMutation.isPending}
          sx={{
            '& .MuiInputBase-root': {
              fontFamily: 'monospace',
              fontSize: '0.95rem',
            }
          }}
        />
        
        <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
          <Button 
            variant="contained" 
            onClick={handleAddGenes}
            disabled={!inputValue.trim() || validateMutation.isPending}
            sx={{ flexGrow: 1 }}
            startIcon={validateMutation.isPending ? <CircularProgress size={20} color="inherit" /> : undefined}
          >
            {validateMutation.isPending ? 'Validating...' : 'Add Genes'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => {
              const exampleGenes = ['PIK3R1', 'ITGB1', 'SRC'];
              const mergedGenes = [...new Set([...selectedGenes, ...exampleGenes])];
              onGenesChange(mergedGenes);
              validateMutation.mutate(mergedGenes);
            }}
            disabled={validateMutation.isPending}
          >
            Add Examples
          </Button>
          {selectedGenes.length > 0 && (
            <Button 
              variant="outlined" 
              color="error"
              onClick={handleClearAll}
              disabled={validateMutation.isPending}
            >
              Clear
            </Button>
          )}
        </Stack>

        {selectedGenes.length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {selectedGenes.map((gene) => (
              <Chip
                key={gene}
                label={gene}
                onDelete={() => {
                  const newGenes = selectedGenes.filter((g) => g !== gene);
                  onGenesChange(newGenes);
                }}
                color="primary"
              />
            ))}
          </Box>
        )}

        {validateMutation.isPending && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1.5 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">Validating genes...</Typography>
        </Box>
        )}

        {validateMutation.isSuccess && validateMutation.data?.invalid_genes.length === 0 && (
          <Alert severity="success" icon={<CheckCircle />} sx={{ mt: 1.5 }}>
            <Typography variant="body2" fontWeight={600}>
              ✓ All {selectedGenes.length} gene{selectedGenes.length !== 1 ? 's' : ''} validated successfully
            </Typography>
          </Alert>
        )}

        {validateMutation.isSuccess && validateMutation.data?.invalid_genes.length > 0 && (
          <Alert severity="warning" icon={<Error />} sx={{ mt: 1.5 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              ⚠ {validateMutation.data.invalid_genes.length} gene{validateMutation.data.invalid_genes.length !== 1 ? 's' : ''} not found:
            </Typography>
            <Typography variant="caption" display="block" sx={{ mt: 0.5, fontFamily: 'monospace' }}>
              {validateMutation.data.invalid_genes.join(', ')}
            </Typography>
            <Typography variant="caption" display="block" sx={{ mt: 1, fontStyle: 'italic' }}>
              Note: These genes will be skipped. You can still analyze valid genes or add different ones.
            </Typography>
          </Alert>
        )}

        <Button
          variant="contained"
          size="large"
          startIcon={startAnalysisMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
          onClick={handleStartAnalysis}
          disabled={selectedGenes.length === 0 || startAnalysisMutation.isPending || validateMutation.isPending}
          fullWidth
          sx={{ mt: 2, py: 1.2, fontSize: '1rem', fontWeight: 600 }}
        >
          {startAnalysisMutation.isPending ? 'Starting Analysis...' : `Start Analysis (${selectedGenes.length} gene${selectedGenes.length !== 1 ? 's' : ''})`}
        </Button>

        {startAnalysisMutation.isError && (
          <Alert severity="error" sx={{ mt: 1.5 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              Failed to start analysis
            </Typography>
            <Typography variant="caption" display="block">
              {startAnalysisMutation.error && typeof startAnalysisMutation.error === 'object' && 'message' in startAnalysisMutation.error
                ? (startAnalysisMutation.error as any).message 
                : 'An unknown error occurred. Please try again or check your internet connection.'}
            </Typography>
          </Alert>
        )}
      </Stack>
    </Box>
  );
}
