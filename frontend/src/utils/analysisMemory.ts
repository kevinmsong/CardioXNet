import { QueryClient } from '@tanstack/react-query';

/**
 * Utility function to clear all analysis-related memory and cache
 * This includes localStorage, sessionStorage, and React Query cache
 */
export const clearAnalysisMemory = (queryClient?: QueryClient) => {
  console.log('[ANALYSIS MEMORY] Clearing all analysis-related data...');
  
  // Clear localStorage analysis data
  const localStorageKeysToRemove = [
    'currentAnalysisId',
    'analysisResults',
    'previousAnalysisId',
  ];
  
  localStorageKeysToRemove.forEach(key => {
    localStorage.removeItem(key);
  });
  
  // Clear additional localStorage keys that contain analysis-related data
  const additionalLocalKeys = Object.keys(localStorage).filter(key => 
    key.includes('analysis') || 
    key.includes('progress') || 
    key.includes('pathway') ||
    key.includes('results')
  );
  additionalLocalKeys.forEach(key => localStorage.removeItem(key));
  
  // Clear sessionStorage analysis data
  const sessionStorageKeysToRemove = [
    'currentAnalysisId',
    'analysisResults',
    'progressData',
  ];
  
  sessionStorageKeysToRemove.forEach(key => {
    sessionStorage.removeItem(key);
  });
  
  // Clear additional sessionStorage keys that contain analysis-related data
  const additionalSessionKeys = Object.keys(sessionStorage).filter(key => 
    key.includes('analysis') || 
    key.includes('progress') || 
    key.includes('pathway') ||
    key.includes('results')
  );
  additionalSessionKeys.forEach(key => sessionStorage.removeItem(key));
  
  // Clear React Query cache if queryClient is provided
  if (queryClient) {
    queryClient.removeQueries({ 
      predicate: (query) => {
        const queryKey = query.queryKey[0];
        if (typeof queryKey === 'string') {
          return (
            queryKey.includes('analysis') || 
            queryKey.includes('progress') || 
            queryKey.includes('pathway') ||
            queryKey.includes('results')
          );
        }
        return false;
      }
    });
    
    // Also clear any potential mutations
    queryClient.getMutationCache().clear();
  }
  
  console.log('[ANALYSIS MEMORY] Analysis memory cleared successfully');
  console.log('[ANALYSIS MEMORY] Cleared localStorage keys:', localStorageKeysToRemove.length + additionalLocalKeys.length);
  console.log('[ANALYSIS MEMORY] Cleared sessionStorage keys:', sessionStorageKeysToRemove.length + additionalSessionKeys.length);
  console.log('[ANALYSIS MEMORY] React Query cache cleared:', !!queryClient);
};

/**
 * Lightweight version that only clears basic analysis identifiers
 * Useful for quick cleanup without affecting cached data
 */
export const clearCurrentAnalysis = () => {
  console.log('[ANALYSIS MEMORY] Clearing current analysis identifiers...');
  
  localStorage.removeItem('currentAnalysisId');
  sessionStorage.removeItem('currentAnalysisId');
  
  console.log('[ANALYSIS MEMORY] Current analysis identifiers cleared');
};