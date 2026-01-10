import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Create axios instance with defaults
const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('justice-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('justice-token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  processSession: (sessionId) => api.post('/auth/session', { session_id: sessionId }),
};

// Cases API
export const casesAPI = {
  list: () => api.get('/cases'),
  get: (id) => api.get(`/cases/${id}`),
  create: (data) => api.post('/cases', data),
  update: (id, data) => api.patch(`/cases/${id}`, data),
  delete: (id) => api.delete(`/cases/${id}`),
};

// Evidence API
export const evidenceAPI = {
  list: () => api.get('/evidence'),
  getByCase: (caseId) => api.get(`/evidence/case/${caseId}`),
  create: (data) => api.post('/evidence', data),
  delete: (id) => api.delete(`/evidence/${id}`),
  upload: (file, caseId, description) => {
    const formData = new FormData();
    formData.append('file', file);
    if (caseId) formData.append('case_id', caseId);
    if (description) formData.append('description', description);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

// Attorneys API
export const attorneysAPI = {
  list: (params) => api.get('/attorneys', { params }),
  get: (id) => api.get(`/attorneys/${id}`),
};

// SOS API
export const sosAPI = {
  create: (data) => api.post('/sos', data),
  getActive: () => api.get('/sos/active'),
  resolve: (id) => api.post(`/sos/${id}/resolve`),
};

// AI Chat API
export const aiAPI = {
  chat: (message, sessionId) => api.post('/ai/chat', { message, session_id: sessionId }),
  getHistory: (sessionId) => api.get(`/ai/history/${sessionId}`),
};

// Messages API
export const messagesAPI = {
  getConversations: () => api.get('/messages/conversations'),
  getMessages: (conversationId) => api.get(`/messages/conversation/${conversationId}`),
  send: (data) => api.post('/messages', data),
  markRead: (id) => api.post(`/messages/${id}/read`),
};

// Departments API (Transparency Portal)
export const departmentsAPI = {
  list: (params) => api.get('/departments', { params }),
  get: (id) => api.get(`/departments/${id}`),
  getIncidents: (id, limit) => api.get(`/departments/${id}/incidents`, { params: { limit } }),
};

// Analytics API
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getPublic: () => api.get('/analytics/public'),
};

// Rights API
export const rightsAPI = {
  getAll: () => api.get('/rights'),
};

export default api;
