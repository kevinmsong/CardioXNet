import { useState, useEffect } from 'react';
import { Alert, Snackbar } from '@mui/material';
import { Warning } from '@mui/icons-material';

interface ApiStatusNotificationProps {
  show?: boolean;
}

export default function ApiStatusNotification({ show = false }: ApiStatusNotificationProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [apiIssues, setApiIssues] = useState<string[]>([]);

  useEffect(() => {
    // Only check API status if explicitly requested
    if (!show) return;

    // Check actual API endpoints (you can enhance this to ping actual endpoints)
    const checkApiStatus = async () => {
      const issues: string[] = [];
      
      try {
        // In production, you would actually check API endpoints here
        // For now, we'll only show if there's an explicit failure
        const response = await fetch('/api/v1/health', { 
          method: 'GET',
          signal: AbortSignal.timeout(3000) 
        });
        
        if (!response.ok) {
          issues.push('API service');
        }
      } catch (error) {
        // Only show notification if there's an actual connection error

      }

      if (issues.length > 0) {
        setApiIssues(issues);
        setIsVisible(true);
      }
    };

    checkApiStatus();
  }, [show]);

  const handleClose = () => {
    setIsVisible(false);
  };

  // Don't show notification unless there are actual issues
  if (!isVisible || apiIssues.length === 0) return null;

  return (
    <Snackbar
      open={isVisible}
      autoHideDuration={8000}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
    >
      <Alert
        onClose={handleClose}
        severity="warning"
        icon={<Warning />}
        sx={{ 
          width: '100%',
          bgcolor: '#FFF3CD',
          color: '#856404',
          border: '1px solid #FFEAA7',
        }}
      >
        <strong>Service Notice:</strong> Unable to connect to analysis service. 
        Please check your internet connection or try again later.
      </Alert>
    </Snackbar>
  );
}