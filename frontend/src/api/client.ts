import axios from 'axios';

const getBrowserHostname = () => {
  if (typeof window === 'undefined') {
    return '127.0.0.1';
  }

  return window.location.hostname || '127.0.0.1';
};

export const getApiBaseUrl = () =>
  import.meta.env.VITE_API_URL || `http://${getBrowserHostname()}:8000`;

export const getApiPath = (path: string) => `${getApiBaseUrl()}${path}`;

export const getWebSocketUrl = (path: string) => {
  if (import.meta.env.VITE_WS_URL) {
    const explicit = import.meta.env.VITE_WS_URL;
    if (explicit.startsWith('ws://') || explicit.startsWith('wss://')) {
      return `${explicit}${path}`;
    }

    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${protocol}://${explicit}${path}`;
  }

  const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${getBrowserHostname()}:8000${path}`;
};

const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default apiClient;
