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

// Incidents Map API
export const incidentsAPI = {
  getForMap: (params) => api.get('/incidents/map', { params }),
  getStats: () => api.get('/incidents/stats'),
};

// Case Timeline API
export const timelineAPI = {
  get: (caseId) => api.get(`/cases/${caseId}/timeline`),
  addEvent: (caseId, data) => api.post(`/cases/${caseId}/events`, null, { params: data }),
};

// Report API
export const reportAPI = {
  getData: (caseId) => api.get(`/cases/${caseId}/report`),
};

// Push Notifications API
export const pushAPI = {
  subscribe: (subscription) => api.post('/push/subscribe', subscription),
  unsubscribe: () => api.delete('/push/unsubscribe'),
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

// Encounter Mode API
export const encounterAPI = {
  start: (data) => api.post('/encounters/start', data),
  end: (encounterId) => api.post(`/encounters/${encounterId}/end`),
  get: (encounterId) => api.get(`/encounters/${encounterId}`),
  list: (status) => api.get('/encounters', { params: { status } }),
  uploadAudio: (encounterId, audioBlob, chunkIndex) => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `chunk_${chunkIndex}.webm`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  addOfficer: (encounterId, officerInfo) => {
    const formData = new FormData();
    if (officerInfo.name) formData.append('name', officerInfo.name);
    if (officerInfo.badge) formData.append('badge_number', officerInfo.badge);
    if (officerInfo.department) formData.append('department', officerInfo.department);
    return api.post(`/encounters/${encounterId}/officer`, formData);
  }
};

// Document Analysis API
export const analysisAPI = {
  analyzeDocument: (file, documentType, analysisFocus) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    formData.append('analysis_focus', analysisFocus);
    return api.post('/analyze/document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  list: () => api.get('/analyze/documents'),
  get: (analysisId) => api.get(`/analyze/document/${analysisId}`)
};

// Rights Coach API
export const rightsCoachAPI = {
  getGuidance: (situation, encounterId) => {
    const formData = new FormData();
    formData.append('situation', situation);
    if (encounterId) formData.append('encounter_id', encounterId);
    return api.post('/rights-coach', formData);
  }
};

// Similar Cases API
export const similarCasesAPI = {
  search: (violationType, department, state) => api.get('/cases/similar', {
    params: { violation_type: violationType, department, state }
  })
};

// Emergency Contacts API
export const emergencyContactsAPI = {
  get: () => api.get('/settings/emergency-contacts'),
  update: (contacts) => api.post('/settings/emergency-contacts', contacts)
};

export default api;
