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
          background: 'linear-gradient(180deg, #1E6B52 0%, #174B3B 100%)',
          borderBottom: '3px solid #FFB81C',
          boxShadow: '0 10px 24px rgba(15, 43, 34, 0.14)',
        }}
      >
        <Toolbar sx={{ py: 1.25 }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ flexGrow: 1 }}>
            <Box
              sx={{
                background: 'rgba(255, 184, 28, 0.14)',
                borderRadius: '12px',
                p: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(255, 184, 28, 0.4)',
              }}
            >
              <BiotechOutlined sx={{ fontSize: 24, color: '#FFB81C' }} />
            </Box>
            <Typography 
              variant="h6" 
              component="div" 
              onClick={handleHomeClick}
              sx={{ 
                fontWeight: 600,
                color: '#FFFFFF',
                letterSpacing: '0',
                cursor: 'pointer',
                '&:hover': {
                  color: '#FFDD87',
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
                fontWeight: location.pathname === '/' ? 600 : 500,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/' ? '#FFB81C' : 'transparent',
                cursor: location.pathname === '/' ? 'default' : 'pointer',
                '&:hover': {
                  bgcolor: location.pathname === '/' ? '#FFB81C' : 'rgba(255,184,28,0.16)',
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
                fontWeight: location.pathname === '/documentation' ? 600 : 500,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/documentation' ? '#FFB81C' : 'transparent',
                cursor: location.pathname === '/documentation' ? 'default' : 'pointer',
                pointerEvents: 'auto',
                '&:hover': {
                  bgcolor: location.pathname === '/documentation' ? '#FFB81C' : 'rgba(255,184,28,0.16)',
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
                fontWeight: location.pathname === '/api-reference' ? 600 : 500,
                px: 2,
                borderRadius: 2,
                bgcolor: location.pathname === '/api-reference' ? '#FFB81C' : 'transparent',
                '&:hover': {
                  bgcolor: location.pathname === '/api-reference' ? '#FFB81C' : 'rgba(255,184,28,0.16)',
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
          bgcolor: '#F5F8F6',
          borderTop: '3px solid #1E6B52',
          boxShadow: 'inset 0 1px 0 rgba(255, 184, 28, 0.45)',
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
                    background: 'linear-gradient(180deg, #1E6B52 0%, #174B3B 100%)',
                    borderRadius: '12px',
                    p: 0.8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid rgba(255, 184, 28, 0.45)',
                  }}
                >
                  <BiotechOutlined sx={{ color: '#FFB81C', fontSize: 22 }} />
                </Box>
                <Box>
                  <Typography variant="body1" sx={{ color: '#163C30', fontWeight: 600 }}>
                    CardioXNet
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Cardiovascular pathway discovery and review
                  </Typography>
                </Box>
              </Stack>
              
              <Stack spacing={0.5} alignItems={{ xs: 'center', sm: 'flex-end' }}>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
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
              alignItems={{ xs: 'flex-start', sm: 'center' }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'left' }}>
                Copyright © 2026 Yajing Wang and Jay Zhang Labs, The University of Alabama at Birmingham. All rights reserved.
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
                    color: location.pathname === '/documentation' ? '#A66C00' : '#1E6B52', 
                    fontWeight: location.pathname === '/documentation' ? 600 : 500, 
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
                    color: location.pathname === '/api-reference' ? '#A66C00' : '#1E6B52', 
                    fontWeight: location.pathname === '/api-reference' ? 600 : 500, 
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
                    fontWeight: 500, 
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
