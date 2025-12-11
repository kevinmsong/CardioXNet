import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
} from '@mui/material';
import { History } from '@mui/icons-material';

export default function RecentAnalyses() {
  const navigate = useNavigate();
  
  // Mock data - would come from localStorage or API
  const recentAnalyses = [
    { id: 'analysis_001', genes: ['NKX2-5', 'GATA4'], status: 'completed', date: '2024-01-15' },
    { id: 'analysis_002', genes: ['MEF2C', 'TBX5'], status: 'running', date: '2024-01-16' },
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <History />
        <Typography variant="h6">Recent Analyses</Typography>
      </Box>
      <List>
        {recentAnalyses.map((analysis) => (
          <ListItem key={analysis.id} disablePadding>
            <ListItemButton onClick={() => navigate(`/results/${analysis.id}`)}>
              <ListItemText
                primary={analysis.genes.join(', ')}
                secondary={analysis.date}
              />
              <Chip
                label={analysis.status}
                size="small"
                color={analysis.status === 'completed' ? 'success' : 'primary'}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
