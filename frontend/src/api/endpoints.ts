import apiClient from './client';
import type {
  ValidationResult,
  AnalysisRequest,
  AnalysisResponse,
  AnalysisStatus,
  AnalysisResults,
  StageResult,
  ConfigDefaults,
} from './types';

export const api = {
  // Gene validation
  validateGenes: async (geneIds: string[]): Promise<ValidationResult> => {
    const response = await apiClient.post('/api/v1/genes/validate', {
      gene_ids: geneIds,
    });
    return response.data.result;
  },

  // Analysis
  startAnalysis: async (request: AnalysisRequest): Promise<AnalysisResponse> => {
    const response = await apiClient.post('/api/v1/analysis/run', request);
    return response.data;
  },

  getAnalysisStatus: async (analysisId: string): Promise<AnalysisStatus> => {
    const response = await apiClient.get(`/api/v1/analysis/${analysisId}/status`);
    return response.data;
  },

  getAnalysisResults: async (analysisId: string): Promise<AnalysisResults> => {
    const response = await apiClient.get(`/api/v1/analysis/${analysisId}/results`);
    return response.data;
  },

  getDetailedAnalysisResults: async (analysisId: string): Promise<any> => {
    const response = await apiClient.get(`/api/v1/analysis/${analysisId}/detailed-results`);
    return response.data;
  },

  getStageResults: async (analysisId: string, stageId: string): Promise<StageResult> => {
    const response = await apiClient.get(`/api/v1/analysis/${analysisId}/stage/${stageId}`);
    return response.data;
  },

  // Configuration
  getConfigDefaults: async (): Promise<ConfigDefaults> => {
    const response = await apiClient.get('/api/v1/config/defaults');
    return response.data;
  },

  // WebSocket connection
  connectWebSocket: (analysisId: string): WebSocket => {
    const wsUrl = `ws://localhost:8000/api/v1/analysis/${analysisId}/progress`;
    return new WebSocket(wsUrl);
  },
};

export default api;
