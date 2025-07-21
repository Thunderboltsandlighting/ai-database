/**
 * API Service
 * 
 * Provides a central service for interacting with the backend API.
 */
import axios from 'axios';

// Create axios instance with API base URL
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 30000 // Increased timeout for AI operations
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  config => {
    // You can add authentication headers here if needed
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor for API calls
apiClient.interceptors.response.use(
  response => {
    return response;
  },
  async error => {
    const originalRequest = error.config;
    
    // Handle specific error codes
    if (error.response) {
      // Handle unauthorized errors (401)
      if (error.response.status === 401 && !originalRequest._retry) {
        // Handle token refresh or redirect to login
      }
      
      // Handle server errors (500)
      if (error.response.status >= 500) {
        console.error('Server error:', error.response.data);
      }
    }
    
    return Promise.reject(error);
  }
);

// Database API
const databaseApi = {
  /**
   * Get list of database tables
   */
  getTables() {
    return apiClient.get('/database/tables');
  },
  
  /**
   * Get data from a specific table
   * @param {string} tableName - Table name
   * @param {object} params - Query parameters (limit, offset, etc.)
   */
  getTableData(tableName, params = {}) {
    return apiClient.get(`/database/tables/${tableName}`, { params });
  },
  
  /**
   * Execute a SQL query
   * @param {string} query - SQL query
   * @param {Array} params - Query parameters
   */
  executeQuery(query, params = []) {
    return apiClient.post('/database/query', { query, params });
  },
  
  /**
   * Get database statistics
   */
  getStats() {
    return apiClient.get('/database/stats');
  }
};

// AI API
const aiApi = {
  /**
   * Chat with the AI assistant
   * @param {string} message - User message
   * @param {Array} history - Chat history
   */
  chat(message, history = []) {
    return apiClient.post('/ai/chat', { message, history });
  },
  
  /**
   * Send a query to the AI
   * @param {string} query - Query text
   */
  query(query) {
    return apiClient.post('/ai/query', { query });
  },
  
  /**
   * Get AI status
   */
  getStatus() {
    return apiClient.get('/ai/status');
  },
  
  /**
   * Get specialized analysis from AI
   * @param {string} analysisType - Type of analysis
   * @param {object} params - Analysis parameters
   */
  getAnalysis(analysisType, params = {}) {
    return apiClient.post('/ai/specialized', {
      analysis_type: analysisType,
      parameters: params
    });
  },
  
  /**
   * Get information about available data files and database content
   */
  getDataInfo() {
    return apiClient.get('/ai/data-info');
  }
};

// Files API
const filesApi = {
  /**
   * Upload a file
   * @param {File} file - File to upload
   * @param {object} options - Upload options
   */
  uploadFile(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add options to formData
    Object.keys(options).forEach(key => {
      formData.append(key, options[key]);
    });
    
    return apiClient.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * Detect format of a file
   * @param {File} file - File to detect format
   */
  detectFormat(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiClient.post('/files/detect-format', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  /**
   * Import a file to database
   * @param {string} fileId - File ID
   * @param {object} options - Import options
   */
  importFile(fileId, options = {}) {
    return apiClient.post('/files/import', {
      file_id: fileId,
      ...options
    });
  },
  
  /**
   * Get file preview
   * @param {string} fileId - File ID
   */
  getFilePreview(fileId) {
    return apiClient.get(`/files/preview/${fileId}`);
  }
};

// Analysis API
const analysisApi = {
  /**
   * Get revenue analysis
   * @param {object} params - Analysis parameters
   */
  getRevenueAnalysis(params = {}) {
    return apiClient.get('/analysis/revenue', { params });
  },
  
  /**
   * Get provider performance analysis
   * @param {object} params - Analysis parameters
   */
  getPerformanceAnalysis(params = {}) {
    return apiClient.get('/analysis/performance', { params });
  },
  
  /**
   * Get monthly trends
   * @param {object} params - Analysis parameters
   */
  getMonthlyTrends(params = {}) {
    return apiClient.get('/analysis/monthly-trends', { params });
  },
  
  /**
   * Get data quality issues
   * @param {object} params - Analysis parameters
   */
  getDataQualityIssues(params = {}) {
    return apiClient.get('/analysis/data-quality', { params });
  },

  /**
   * Get any provider's overhead coverage analysis
   * @param {string} providerName - Name of the provider to analyze
   */
  getProviderOverheadAnalysis(providerName) {
    return apiClient.get(`/analytics/provider-overhead-analysis/${encodeURIComponent(providerName)}`);
  },

  /**
   * Get universal analysis for any question
   * @param {string} question - The question to analyze
   */
  getUniversalAnalysis(question) {
    return apiClient.post('/analytics/universal-analysis', { question });
  }
};

// Settings API
const settingsApi = {
  /**
   * Get all settings
   */
  getSettings() {
    return apiClient.get('/settings');
  },
  
  /**
   * Save application settings
   * @param {object} settings - Application settings
   */
  saveAppSettings(settings) {
    return apiClient.post('/settings/application', settings);
  },
  
  /**
   * Save database settings
   * @param {object} settings - Database settings
   */
  saveDbSettings(settings) {
    return apiClient.post('/settings/database', settings);
  },
  
  /**
   * Save AI settings
   * @param {object} settings - AI settings
   */
  saveAiSettings(settings) {
    return apiClient.post('/settings/ai', settings);
  },
  
  /**
   * Save import/export settings
   * @param {object} settings - Import/export settings
   */
  saveImportSettings(settings) {
    return apiClient.post('/settings/import', settings);
  },
  
  /**
   * Save system settings
   * @param {object} settings - System settings
   */
  saveSystemSettings(settings) {
    return apiClient.post('/settings/system', settings);
  }
};

// Export all API services
export {
  apiClient,
  databaseApi,
  aiApi,
  filesApi,
  analysisApi,
  settingsApi
};