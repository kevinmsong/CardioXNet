import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import ProgressPage from './pages/ProgressPage';
import ResultsPage from './pages/ResultsPageClean';
import UltraDetailPage from './pages/UltraDetailPage';
import DocumentationPage from './pages/DocumentationPageSimplified';
import APIReferencePage from './pages/APIReferencePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// UAB Green branded theme with professional scientific look
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1E6B52', // UAB Green
      light: '#4A9B7F',
      dark: '#0D4A35',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#FFB81C', // UAB Gold accent
      light: '#FFD166',
      dark: '#CC9316',
      contrastText: '#000000',
    },
    background: {
      default: '#FFFFFF', // Pure white background
      paper: '#FAFAFA', // Subtle off-white for cards
    },
    text: {
      primary: '#1A1A1A',
      secondary: '#4A4A4A',
    },
    success: {
      main: '#1E6B52', // UAB Green for success states
    },
    info: {
      main: '#0066CC', // Professional blue for info
    },
    grey: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#EEEEEE',
      300: '#E0E0E0',
      400: '#BDBDBD',
      500: '#9E9E9E',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.25rem',
      fontWeight: 600,
      letterSpacing: '-0.01562em',
      color: '#1A1A1A',
    },
    h2: {
      fontSize: '1.8rem',
      fontWeight: 600,
      letterSpacing: '-0.00833em',
      color: '#1A1A1A',
    },
    h3: {
      fontSize: '1.575rem',
      fontWeight: 600,
      letterSpacing: '0em',
      color: '#1A1A1A',
    },
    h4: {
      fontSize: '1.35rem',
      fontWeight: 600,
      letterSpacing: '0.00735em',
      color: '#1A1A1A',
    },
    h5: {
      fontSize: '1.125rem',
      fontWeight: 600,
      letterSpacing: '0em',
      color: '#1A1A1A',
    },
    h6: {
      fontSize: '1.0rem',
      fontWeight: 600,
      letterSpacing: '0.0075em',
      color: '#1A1A1A',
    },
    subtitle1: {
      fontSize: '0.9rem',
      fontWeight: 500,
      letterSpacing: '0.00938em',
      color: '#4A4A4A',
    },
    body1: {
      fontSize: '0.9rem',
      letterSpacing: '0.00938em',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.8rem',
      letterSpacing: '0.01071em',
      lineHeight: 1.5,
    },
    button: {
      textTransform: 'none', // More professional, less shouty
      fontWeight: 500,
      fontSize: '0.875rem',
    },
  },
  shape: {
    borderRadius: 7, // Slightly rounded for modern look
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0,0,0,0.05)',
    '0px 4px 8px rgba(0,0,0,0.08)',
    '0px 6px 12px rgba(0,0,0,0.1)',
    '0px 8px 16px rgba(0,0,0,0.12)',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
    'none',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#FFFFFF',
          scrollbarColor: '#BDBDBD #F5F5F5',
          '&::-webkit-scrollbar, & *::-webkit-scrollbar': {
            width: 8,
            height: 8,
          },
          '&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb': {
            borderRadius: 8,
            backgroundColor: '#BDBDBD',
            minHeight: 24,
          },
          '&::-webkit-scrollbar-track, & *::-webkit-scrollbar-track': {
            backgroundColor: '#F5F5F5',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 5,
          padding: '7px 18px',
          fontSize: '0.875rem',
          fontWeight: 500,
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0,0,0,0.1)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          border: '1px solid #E0E0E0',
        },
      },
    },
  },
});

function App() {
  // Clear any previous analysis data on app startup
  useEffect(() => {
    console.log('[APP] Clearing previous analysis data on startup');
    localStorage.removeItem('currentAnalysisId');
    localStorage.removeItem('analysisResults');
    sessionStorage.removeItem('currentAnalysisId');
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/documentation" element={<DocumentationPage />} />
              <Route path="/api-reference" element={<APIReferencePage />} />
              <Route path="/progress/:analysisId" element={<ProgressPage />} />
              <Route path="/results/:analysisId" element={<ResultsPage />} />
              <Route path="/detail/:analysisId/:pathwayId" element={<UltraDetailPage />} />
            </Routes>
          </Layout>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
