import { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  AppBar,
  Box,
  Button,
  Container,
  Divider,
  Stack,
  Toolbar,
  Typography,
} from '@mui/material';
import { Api, Home, BiotechOutlined, MenuBook } from '@mui/icons-material';
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
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: '#F4F8F6' }}>
      {/* API Status Notification */}
      <ApiStatusNotification />
      
      <AppBar 
        position="sticky"
        elevation={0}
        sx={{ 
          background: '#163C30',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 10px 24px rgba(15, 43, 34, 0.14)',
        }}
      >
        <Toolbar sx={{ py: 1.25 }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ flexGrow: 1 }}>
            <Box
              sx={{
                background: 'rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                p: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <BiotechOutlined sx={{ fontSize: 24, color: '#B9E3D3' }} />
            </Box>
            <Typography 
              variant="h6" 
              component="div" 
              onClick={handleHomeClick}
              sx={{ 
                fontWeight: 700,
                color: '#FFFFFF',
                letterSpacing: '-0.2px',
                cursor: 'pointer',
                '&:hover': {
                  color: '#D7EFE6',
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
                color: location.pathname === '/' ? '#163C30' : '#FFFFFF',
                fontWeight: location.pathname === '/' ? 700 : 600,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/' ? '#D7EFE6' : 'transparent',
                cursor: location.pathname === '/' ? 'default' : 'pointer',
                '&:hover': {
                  bgcolor: location.pathname === '/' ? '#D7EFE6' : 'rgba(255,255,255,0.08)',
                },
              }}
            >
              Home
            </Button>
            <Button
              color="inherit"
              startIcon={<MenuBook />}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (location.pathname !== '/documentation') {
                  navigate('/documentation');
                }
              }}
              sx={{
                color: location.pathname === '/documentation' ? '#163C30' : '#FFFFFF',
                fontWeight: location.pathname === '/documentation' ? 700 : 600,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/documentation' ? '#D7EFE6' : 'transparent',
                cursor: location.pathname === '/documentation' ? 'default' : 'pointer',
                pointerEvents: 'auto',
                '&:hover': {
                  bgcolor: location.pathname === '/documentation' ? '#D7EFE6' : 'rgba(255,255,255,0.08)',
                },
              }}
            >
              Documentation
            </Button>
            <Button
              color="inherit"
              startIcon={<Api />}
              onClick={() => {
                if (location.pathname !== '/api-reference') {
                  navigate('/api-reference');
                }
              }}
              sx={{
                color: location.pathname === '/api-reference' ? '#163C30' : '#FFFFFF',
                fontWeight: location.pathname === '/api-reference' ? 700 : 600,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/api-reference' ? '#D7EFE6' : 'transparent',
                '&:hover': {
                  bgcolor: location.pathname === '/api-reference' ? '#D7EFE6' : 'rgba(255,255,255,0.08)',
                },
              }}
            >
              API
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>

      <Container 
        maxWidth={false}
        sx={{ 
          mt: 2, 
          mb: 3, 
          flexGrow: 1,
          px: { xs: 1.5, sm: 2, md: 3 },
          maxWidth: '1320px',
        }}
      >
        {children}
      </Container>

      <Box
        component="footer"
        sx={{
          py: 2.5,
          px: 2,
          mt: 'auto',
          bgcolor: '#EEF5F1',
          borderTop: '1px solid #D8E8E2',
        }}
      >
        <Container maxWidth="lg">
          <Stack spacing={2}>
            <Stack 
              direction={{ xs: 'column', sm: 'row' }} 
              spacing={3}
              justifyContent="space-between"
              alignItems="center"
            >
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    background: '#163C30',
                    borderRadius: '12px',
                    p: 0.8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <BiotechOutlined sx={{ color: '#D7EFE6', fontSize: 22 }} />
                </Box>
                <Box>
                  <Typography variant="body1" sx={{ color: '#163C30', fontWeight: 700 }}>
                    CardioXNet
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Cardiovascular pathway discovery and review
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
                CardioXNet for cardiovascular pathway discovery and review.
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
