import axios from 'axios';

export const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_URL,
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
  getReport: (encounterId) => api.get(`/encounters/${encounterId}/report`),
  getMediaUrl: (encounterId, filename) => `${API_URL}/encounters/${encounterId}/media/${filename}`,
  getStreamToken: (encounterId) => api.get(`/encounters/${encounterId}/stream-token`),
  verifyStreamAccess: (encounterId, token) => api.get(`/live/${encounterId}/verify`, { params: { token } }),
  analyzeRealtime: (encounterId, text, analysisType = 'full') => {
    const formData = new FormData();
    formData.append('text', text);
    formData.append('analysis_type', analysisType);
    return api.post(`/encounters/${encounterId}/analyze`, formData);
  },
  getViolations: (encounterId) => api.get(`/encounters/${encounterId}/violations`),
  markViolation: (encounterId, timestamp, note = 'Manual violation mark') => {
    const formData = new FormData();
    formData.append('timestamp', timestamp);
    formData.append('note', note);
    return api.post(`/encounters/${encounterId}/mark-violation`, formData);
  },
  list: (status) => api.get('/encounters', { params: { status } }),
  uploadAudio: (encounterId, audioBlob, chunkIndex) => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `chunk_${chunkIndex}.webm`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  uploadVideo: (encounterId, videoBlob, chunkIndex) => {
    const formData = new FormData();
    formData.append('video_file', videoBlob, `video_chunk_${chunkIndex}.webm`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/video`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  uploadScreen: (encounterId, screenBlob, chunkIndex) => {
    const formData = new FormData();
    formData.append('screen', screenBlob, `screen_chunk_${chunkIndex}.webm`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/screen`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  addOfficer: (encounterId, officerInfo) => {
    const formData = new FormData();
    if (officerInfo.name) formData.append('name', officerInfo.name);
    if (officerInfo.badge) formData.append('badge_number', officerInfo.badge);
    if (officerInfo.department) formData.append('department', officerInfo.department);
    return api.post(`/encounters/${encounterId}/officer`, formData);
  },
  // Real-time sharing
  createShare: (encounterId, autoNotify = false) => 
    api.post(`/encounters/${encounterId}/share?auto_notify=${autoNotify}`),
  revokeShare: (encounterId) => 
    api.delete(`/encounters/${encounterId}/share`),
  getShared: (encounterId, token) => 
    api.get(`/encounters/shared/${encounterId}?token=${token}`),
  sendGuidance: (encounterId, token, message, senderName) =>
    api.post(`/encounters/shared/${encounterId}/message?token=${token}&message=${encodeURIComponent(message)}&sender_name=${encodeURIComponent(senderName)}`),
  // AI Evidence Highlights
  generateHighlights: (encounterId) =>
    api.post(`/encounters/${encounterId}/highlights/generate`),
  regenerateHighlights: (encounterId, feedback) => {
    const formData = new FormData();
    formData.append('feedback', feedback);
    return api.post(`/encounters/${encounterId}/highlights/regenerate`, formData);
  },
  getHighlights: (encounterId) =>
    api.get(`/encounters/${encounterId}/highlights`),
  getSharedHighlights: (encounterId, token) =>
    api.get(`/encounters/shared/${encounterId}/highlights?token=${token}`),
  // Export Highlights Report
  exportReport: (encounterId, style = 'formal') =>
    `${API_URL}/encounters/${encounterId}/highlights/export?style=${style}`,
  exportSharedReport: (encounterId, token, style = 'formal') =>
    `${API_URL}/encounters/shared/${encounterId}/highlights/export?token=${token}&style=${style}`
};

// Helper to get the API URL for direct media access
export const getMediaStreamUrl = (encounterId, filename, token) => {
  return `${API_URL}/live/${encounterId}/media/${filename}?token=${token}`;
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

// Community Evidence Vault API
export const communityAPI = {
  submit: (data) => api.post('/community/submit', data),
  getSubmissions: (params) => api.get('/community/submissions', { params }),
  getDepartments: (state) => api.get('/community/departments', { params: { state } }),
  getOfficers: (department, minIncidents) => api.get('/community/officers', { 
    params: { department, min_incidents: minIncidents } 
  }),
  getStats: () => api.get('/community/stats'),
  upvote: (submissionId) => api.post(`/community/upvote/${submissionId}`),
  getOfficerProfile: (badge, department) => api.get(`/community/officer/${badge}/${encodeURIComponent(department)}`),
  getDepartmentProfile: (department, state) => api.get(`/community/department/${encodeURIComponent(department)}`, { params: { state } })
};

// Blockchain Evidence API
export const blockchainAPI = {
  secureUpload: (file, caseId, encounterId, description, evidenceType) => {
    const formData = new FormData();
    formData.append('file', file);
    if (caseId) formData.append('case_id', caseId);
    if (encounterId) formData.append('encounter_id', encounterId);
    formData.append('description', description || '');
    formData.append('evidence_type', evidenceType || 'document');
    return api.post('/evidence/secure-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  verifyEvidence: (evidenceId) => api.get(`/evidence/${evidenceId}/verify`),
  getCertificate: (evidenceId) => api.get(`/evidence/${evidenceId}/certificate`),
  getBlockchainStatus: () => api.get('/blockchain/status'),
  getIPFSStatus: () => api.get('/ipfs/status'),
  getEvidenceReport: (caseId) => api.get(`/evidence/report/${caseId}`),
  batchExport: (caseId) => api.get(`/evidence/batch-export/${caseId}`, { responseType: 'blob' })
};

// S3 Backup API
export const backupAPI = {
  getStatus: () => api.get('/backup/status'),
  triggerBackup: () => api.post('/backup/trigger'),
  getHistory: (limit = 10) => api.get('/backup/history', { params: { limit } })
};

// Attorney Collaboration API
export const attorneyCollabAPI = {
  // Invitation management
  inviteAttorney: (email, encounterId, message) => {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('encounter_id', encounterId);
    if (message) formData.append('message', message);
    return api.post('/attorney/invite', formData);
  },
  getInviteDetails: (token) => api.get(`/attorney/invite/${token}/details`),
  acceptInvite: (inviteToken, name, password) => {
    const formData = new FormData();
    formData.append('invite_token', inviteToken);
    formData.append('name', name);
    formData.append('password', password);
    return api.post('/attorney/accept-invite', formData);
  },
  acceptInviteExisting: (inviteToken, email, password) => {
    const formData = new FormData();
    formData.append('invite_token', inviteToken);
    formData.append('email', email);
    formData.append('password', password);
    return api.post('/attorney/accept-invite/existing', formData);
  },
  
  // Attorney verification
  verify: (barNumber, firmName, specialization) => {
    const formData = new FormData();
    formData.append('bar_number', barNumber);
    if (firmName) formData.append('firm_name', firmName);
    if (specialization) formData.append('specialization', specialization);
    return api.post('/attorney/verify', formData);
  },
  
  // Dashboard & data
  getDashboard: () => api.get('/attorney/dashboard'),
  getClients: () => api.get('/attorney/clients'),
  getEncounters: () => api.get('/attorney/encounters'),
  
  // Case notes
  createNote: (encounterId, content, noteType = 'general') => {
    const formData = new FormData();
    formData.append('encounter_id', encounterId);
    formData.append('content', content);
    formData.append('note_type', noteType);
    return api.post('/attorney/notes', formData);
  },
  getNotes: (encounterId) => api.get(`/attorney/notes/${encounterId}`),
  updateNote: (noteId, content, noteType) => {
    const formData = new FormData();
    formData.append('content', content);
    if (noteType) formData.append('note_type', noteType);
    return api.put(`/attorney/notes/${noteId}`, formData);
  },
  deleteNote: (noteId) => api.delete(`/attorney/notes/${noteId}`),
  
  // Messaging
  sendMessage: (recipientId, content, encounterId, messageType = 'text') => {
    const formData = new FormData();
    formData.append('recipient_id', recipientId);
    formData.append('content', content);
    if (encounterId) formData.append('encounter_id', encounterId);
    formData.append('message_type', messageType);
    return api.post('/attorney/messages', formData);
  },
  getMessages: (contactId, encounterId) => api.get('/attorney/messages', { 
    params: { contact_id: contactId, encounter_id: encounterId } 
  }),
  getInbox: () => api.get('/attorney/messages/inbox'),
  markMessageRead: (messageId) => api.put(`/attorney/messages/${messageId}/read`),
  markAllRead: (contactId) => api.put('/attorney/messages/read-all', null, { 
    params: { contact_id: contactId } 
  }),
  
  // Access management (for clients)
  getMyAttorneys: () => api.get('/attorney/my-attorneys'),
  revokeAccess: (encounterId) => api.delete(`/attorney/access/${encounterId}`),
};

// Video Call API
export const callsAPI = {
  // Call management
  initiateCall: (recipientId, callType = 'video', encounterId = null) => {
    const formData = new FormData();
    formData.append('recipient_id', recipientId);
    formData.append('call_type', callType);
    if (encounterId) formData.append('encounter_id', encounterId);
    return api.post('/calls/initiate', formData);
  },
  answerCall: (callId) => api.post(`/calls/${callId}/answer`),
  rejectCall: (callId) => api.post(`/calls/${callId}/reject`),
  endCall: (callId) => api.post(`/calls/${callId}/end`),
  getActiveCall: () => api.get('/calls/active'),
  getIncomingCalls: () => api.get('/calls/incoming'),
  getCallHistory: (limit = 20, contactId = null) => api.get('/calls/history', {
    params: { limit, contact_id: contactId }
  }),
  
  // Recording management
  startRecording: (callId) => api.post(`/calls/${callId}/recording/start`),
  stopRecording: (callId) => api.post(`/calls/${callId}/recording/stop`),
  uploadRecording: (callId, recordingId, blob) => {
    const formData = new FormData();
    formData.append('recording_id', recordingId);
    formData.append('file', blob, 'recording.webm');
    return api.post(`/calls/${callId}/recording/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000 // 2 min timeout for large files
    });
  },
  getCallRecordings: (callId) => api.get(`/calls/${callId}/recordings`),
  getMyRecordings: (limit = 20) => api.get('/calls/recordings/my', { params: { limit } }),
};

// Policy Impact Dashboard API
export const policyAPI = {
  getDashboardData: () => api.get('/policy/dashboard-data'),
  generateReport: (reportType, targetAudience, department, state, violationType) => {
    const formData = new FormData();
    formData.append('report_type', reportType);
    formData.append('target_audience', targetAudience);
    if (department) formData.append('department', department);
    if (state) formData.append('state', state);
    if (violationType) formData.append('violation_type', violationType);
    return api.post('/policy/generate-report', formData);
  },
  getReports: (reportType, targetAudience) => api.get('/policy/reports', { 
    params: { report_type: reportType, target_audience: targetAudience } 
  }),
  getReport: (reportId) => api.get(`/policy/report/${reportId}`)
};

export default api;
