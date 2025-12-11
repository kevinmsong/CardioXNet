import { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  Button,
  Container,
  Divider,
  Stack,
} from '@mui/material';
import { Home, BiotechOutlined, AccountTreeOutlined } from '@mui/icons-material';
import { clearAnalysisMemory } from '../utils/analysisMemory';
import ApiStatusNotification from './ApiStatusNotification';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const handleHomeClick = () => {

    clearAnalysisMemory(queryClient);
    navigate('/');
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: '#FFFFFF' }}>
      {/* API Status Notification */}
      <ApiStatusNotification />
      
      {/* Professional Header with UAB Green */}
      <AppBar 
        position="sticky"
        elevation={3}
        sx={{ 
          background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
          borderBottom: '3px solid #FFB81C',
          boxShadow: '0 4px 16px rgba(30, 107, 82, 0.2)',
        }}
      >
        <Toolbar sx={{ py: 1.5 }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ flexGrow: 1 }}>
            <Box
              sx={{
                background: 'rgba(255, 184, 28, 0.2)',
                borderRadius: '10px',
                p: 0.8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '2px solid #FFB81C',
              }}
            >
              <BiotechOutlined sx={{ fontSize: 28, color: '#FFB81C' }} />
            </Box>
            <Typography 
              variant="h5" 
              component="div" 
              onClick={handleHomeClick}
              sx={{ 
                fontWeight: 700,
                color: '#FFFFFF',
                letterSpacing: '-0.5px',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  color: '#FFB81C',
                  transform: 'scale(1.02)',
                },
              }}
            >
              CardioXNet
            </Typography>
          </Stack>
          
          <Stack direction="row" spacing={1}>
            <Button
              color="inherit"
              startIcon={<Home />}
              onClick={() => {
                if (location.pathname !== '/') {
                  handleHomeClick();
                }
              }}
              sx={{
                color: location.pathname === '/' ? '#FFB81C' : '#FFFFFF',
                fontWeight: location.pathname === '/' ? 700 : 600,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/' ? 'rgba(255,184,28,0.15)' : 'transparent',
                cursor: location.pathname === '/' ? 'default' : 'pointer',
                '&:hover': {
                  bgcolor: location.pathname === '/' ? 'rgba(255,184,28,0.15)' : 'rgba(255,184,28,0.2)',
                  borderColor: '#FFB81C',
                  border: '1px solid',
                },
              }}
            >
              Home
            </Button>
            <Button
              color="inherit"
              startIcon={<AccountTreeOutlined />}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (location.pathname !== '/documentation') {
                  navigate('/documentation');
                }
              }}
              sx={{
                color: location.pathname === '/documentation' ? '#FFB81C' : '#FFFFFF',
                fontWeight: location.pathname === '/documentation' ? 700 : 600,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/documentation' ? 'rgba(255,184,28,0.15)' : 'transparent',
                cursor: location.pathname === '/documentation' ? 'default' : 'pointer',
                pointerEvents: 'auto',
                '&:hover': {
                  bgcolor: location.pathname === '/documentation' ? 'rgba(255,184,28,0.15)' : 'rgba(255,184,28,0.2)',
                  borderColor: '#FFB81C',
                  border: '1px solid',
                },
              }}
            >
              Documentation
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>

      {/* Main Content Area - Wider layout with 30% narrower margins */}
      <Container 
        maxWidth="xl" 
        sx={{ 
          mt: 1.5, 
          mb: 2, 
          flexGrow: 1,
          px: { xs: 0.7, sm: 1, md: 1.4 },  // 30% narrower margins (was 1, 1.5, 2)
          maxWidth: '1800px !important',  // Wider max width (was 1400px)
        }}
      >
        {children}
      </Container>

      {/* Enhanced Footer */}
      <Box
        component="footer"
        sx={{
          py: 3,
          px: 2,
          mt: 'auto',
          bgcolor: '#F5F5F5',
          borderTop: '3px solid #1E6B52',
        }}
      >
        <Container maxWidth="lg">
          <Stack spacing={2.5}>
            <Stack 
              direction={{ xs: 'column', sm: 'row' }} 
              spacing={3}
              justifyContent="space-between"
              alignItems="center"
            >
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    background: 'linear-gradient(135deg, #1E6B52 0%, #145A43 100%)',
                    borderRadius: '10px',
                    p: 0.8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '2px solid #FFB81C',
                  }}
                >
                  <BiotechOutlined sx={{ color: '#FFB81C', fontSize: 24 }} />
                </Box>
                <Box>
                  <Typography variant="body1" sx={{ color: '#1E6B52', fontWeight: 700 }}>
                    CardioXNet
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    NETS (Neighborhood Enrichment Triage and Scoring) Algorithm Platform
                  </Typography>
                </Box>
              </Stack>
              
              <Stack spacing={0.5} alignItems={{ xs: 'center', sm: 'flex-end' }}>
                <Typography variant="body2" color="text.secondary" fontWeight={600}>
                  Cardiovascular Disease Pathway Discovery
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Advanced Computational Biology • Literature-Validated Results
                </Typography>
              </Stack>
            </Stack>
            
            <Divider sx={{ bgcolor: '#E0E0E0' }} />
            
            <Stack 
              direction={{ xs: 'column', sm: 'row' }} 
              spacing={2}
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography variant="caption" color="text.secondary">
                © Yajing Wang & Jay Zhang Labs • The University of Alabama at Birmingham • All rights reserved.
              </Typography>
              <Stack direction="row" spacing={2}>
                <Typography 
                  variant="caption" 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (location.pathname !== '/documentation') {
                      navigate('/documentation');
                    }
                  }}
                  sx={{ 
                    color: location.pathname === '/documentation' ? '#145A43' : '#1E6B52', 
                    fontWeight: location.pathname === '/documentation' ? 700 : 600, 
                    cursor: location.pathname === '/documentation' ? 'default' : 'pointer', 
                    '&:hover': { textDecoration: location.pathname === '/documentation' ? 'none' : 'underline' } 
                  }}
                >
                  Documentation
                </Typography>
                <Typography 
                  variant="caption" 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (location.pathname !== '/api-reference') {
                      navigate('/api-reference');
                    }
                  }}
                  sx={{ 
                    color: location.pathname === '/api-reference' ? '#145A43' : '#1E6B52', 
                    fontWeight: location.pathname === '/api-reference' ? 700 : 600, 
                    cursor: location.pathname === '/api-reference' ? 'default' : 'pointer', 
                    '&:hover': { textDecoration: location.pathname === '/api-reference' ? 'none' : 'underline' } 
                  }}
                >
                  API Reference
                </Typography>
                <Typography 
                  variant="caption"
                  component="a"
                  href="mailto:kmsong@uab.edu"
                  sx={{ 
                    color: '#1E6B52', 
                    fontWeight: 600, 
                    textDecoration: 'none',
                    '&:hover': { textDecoration: 'underline' } 
                  }}
                >
                  Contact
                </Typography>
              </Stack>
            </Stack>
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}
