import axios from 'axios';

export const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_URL,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('justice-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors - improved to avoid redirect loops
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only handle 401 errors, not 403 (which might be permission-based)
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      // Don't redirect if already on login/register/public pages
      const publicPaths = ['/', '/login', '/register', '/transparency', '/incident-map', '/accountability'];
      const isPublicPath = publicPaths.some(path => currentPath === path || currentPath.startsWith('/live/') || currentPath.startsWith('/shared/'));
      
      if (!isPublicPath) {
        console.log('[API] 401 error - clearing token and redirecting to login');
        localStorage.removeItem('justice-token');
        // Use replace to avoid back button issues
        window.location.replace('/login');
      }
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
  getMyAttorneys: () => api.get('/attorney/my-attorneys'),
};

// SOS API
export const sosAPI = {
  create: (data) => api.post('/sos', data),
  createEncounterSOS: (data) => api.post('/sos/encounter', data),
  quickAlert: (data) => api.post('/sos/quick-alert', data),
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
    // Use the blob's actual type to determine extension
    const ext = audioBlob.type?.includes('mp4') ? '.m4a' : 
                audioBlob.type?.includes('aac') ? '.aac' : 
                audioBlob.type?.includes('wav') ? '.wav' : '.webm';
    formData.append('audio', audioBlob, `chunk_${chunkIndex}${ext}`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/audio`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  uploadVideo: (encounterId, videoBlob, chunkIndex) => {
    const formData = new FormData();
    // Use the blob's actual type to determine extension
    const ext = videoBlob.type?.includes('mp4') ? '.mp4' : 
                videoBlob.type?.includes('quicktime') ? '.mov' : '.webm';
    formData.append('video', videoBlob, `video_chunk_${chunkIndex}${ext}`);
    formData.append('chunk_index', chunkIndex);
    return api.post(`/encounters/${encounterId}/video`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  uploadScreen: (encounterId, screenBlob, chunkIndex) => {
    const formData = new FormData();
    const ext = screenBlob.type?.includes('mp4') ? '.mp4' : '.webm';
    formData.append('screen', screenBlob, `screen_chunk_${chunkIndex}${ext}`);
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
  getAll: () => api.get('/emergency-contacts'),
  create: (contact) => api.post('/emergency-contacts', contact),
  update: (contactId, data) => api.put(`/emergency-contacts/${contactId}`, data),
  delete: (contactId) => api.delete(`/emergency-contacts/${contactId}`),
  test: (contactId) => api.post(`/emergency-contacts/${contactId}/test`),
  reorder: (contactIds) => api.post('/emergency-contacts/reorder', contactIds)
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
  
  // Transcription
  transcribeRecording: (recordingId) => api.post(`/calls/${recordingId}/transcribe`, null, { timeout: 300000 }), // 5 min timeout
  getTranscript: (recordingId) => api.get(`/calls/${recordingId}/transcript`),
  searchTranscripts: (query, limit = 20) => api.get('/calls/transcripts/search', { params: { query, limit } }),
  
  // Live Transcription
  sendAudioChunk: (callId, audioBlob, chunkIndex) => {
    const formData = new FormData();
    formData.append('audio_chunk', audioBlob, 'chunk.webm');
    formData.append('chunk_index', chunkIndex);
    return api.post(`/calls/${callId}/live-transcribe`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000
    });
  },
  getLiveTranscript: (callId) => api.get(`/calls/${callId}/live-transcript`),
  addLiveNote: (callId, content, timestamp, noteType = 'general') => {
    const formData = new FormData();
    formData.append('content', content);
    formData.append('timestamp', timestamp);
    formData.append('note_type', noteType);
    return api.post(`/calls/${callId}/live-note`, formData);
  },
  saveLiveTranscript: (callId) => api.post(`/calls/${callId}/save-live-transcript`),
  
  // AI Summary
  generateSummary: (recordingId) => api.post(`/calls/${recordingId}/summarize`, null, { timeout: 120000 }),
  getSummary: (recordingId) => api.get(`/calls/${recordingId}/summary`),
  downloadSummaryPDF: (recordingId, templateId = null) => api.get(`/calls/${recordingId}/summary/pdf`, { 
    params: templateId ? { template_id: templateId } : {},
    responseType: 'blob' 
  }),
  downloadBatchSummaryPDF: (recordingIds, templateId = null) => api.post('/calls/batch-summary/pdf', { 
    recording_ids: recordingIds,
    template_id: templateId 
  }, { responseType: 'blob', timeout: 120000 }),
  emailSummary: (recordingIds, recipientEmails, ccEmails = null, customMessage = null, recipientName = null, templateId = null) => 
    api.post('/calls/email-summary', { 
      recording_ids: recordingIds, 
      recipient_emails: recipientEmails,
      cc_emails: ccEmails,
      custom_message: customMessage,
      recipient_name: recipientName,
      template_id: templateId
    }, { timeout: 60000 }),
};

// Scheduled Reports API
export const schedulesAPI = {
  getMySchedules: () => api.get('/schedules/my'),
  createSchedule: (data) => api.post('/schedules/create', data),
  getSchedule: (scheduleId) => api.get(`/schedules/${scheduleId}`),
  updateSchedule: (scheduleId, data) => api.put(`/schedules/${scheduleId}`, data),
  deleteSchedule: (scheduleId) => api.delete(`/schedules/${scheduleId}`),
  toggleSchedule: (scheduleId) => api.post(`/schedules/${scheduleId}/toggle`),
  testSchedule: (scheduleId) => api.post(`/schedules/${scheduleId}/test`, null, { timeout: 60000 }),
};

// Report Templates API
export const templatesAPI = {
  getMyTemplates: () => api.get('/templates/my'),
  getDefaultTemplate: () => api.get('/templates/default'),
  createTemplate: (data) => api.post('/templates/create', data),
  getTemplate: (templateId) => api.get(`/templates/${templateId}`),
  updateTemplate: (templateId, data) => api.put(`/templates/${templateId}`, data),
  deleteTemplate: (templateId) => api.delete(`/templates/${templateId}`),
  setDefault: (templateId) => api.post(`/templates/${templateId}/set-default`),
  duplicateTemplate: (templateId) => api.post(`/templates/${templateId}/duplicate`),
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

// Violation Detection API
export const violationAPI = {
  analyze: (encounterId, transcript, encounterType = 'general') => 
    api.post('/advanced/violations/analyze', { 
      encounter_id: encounterId, 
      transcript, 
      encounter_type: encounterType 
    }),
  quickScan: (transcript) => 
    api.post('/advanced/violations/quick-scan', null, { params: { transcript } }),
  getReport: (encounterId) => 
    api.get(`/advanced/violations/report/${encounterId}`),
  getStats: () => 
    api.get('/advanced/violations/stats')
};

// Legal Precedent API
export const legalPrecedentAPI = {
  searchPrecedents: (encounterId, violations, transcript, encounterType = 'general') =>
    api.post('/advanced/legal/precedents', {
      encounter_id: encounterId,
      violations,
      transcript,
      encounter_type: encounterType
    }),
  getCasesByAmendment: (amendment) => 
    api.get(`/advanced/legal/cases/${amendment}`),
  searchCases: (keywords) => 
    api.post('/advanced/legal/search', keywords),
  estimateValue: (violations, hasInjury = false, hasArrest = false, hasVideo = true) =>
    api.post('/advanced/legal/estimate-value', {
      violations,
      has_injury: hasInjury,
      has_arrest: hasArrest,
      has_video: hasVideo
    })
};

// FOIA Automation API
export const foiaAPI = {
  generate: (encounterId, departmentCode = null, customDepartment = null) =>
    api.post('/advanced/foia/generate', {
      encounter_id: encounterId,
      department_code: departmentCode,
      custom_department: customDepartment
    }),
  submit: (requestId, submissionMethod = 'email') =>
    api.post(`/advanced/foia/submit/${requestId}`, null, { params: { submission_method: submissionMethod } }),
  updateStatus: (requestId, status, responseNotes = null, documentsReceived = null) =>
    api.put(`/advanced/foia/status/${requestId}`, {
      status,
      response_notes: responseNotes,
      documents_received: documentsReceived
    }),
  getMyRequests: () => 
    api.get('/advanced/foia/my-requests'),
  generateAppeal: (requestId, denialReason) =>
    api.post(`/advanced/foia/appeal/${requestId}`, null, { params: { denial_reason: denialReason } }),
  getStats: () => 
    api.get('/advanced/foia/stats')
};

// Hardware Integration API
export const hardwareAPI = {
  // Device Management
  getDevices: () => api.get('/hardware/devices'),
  registerDevice: (deviceType, deviceName, connectionInfo = null) =>
    api.post('/hardware/devices', { device_type: deviceType, device_name: deviceName, connection_info: connectionInfo }),
  getDevice: (deviceId) => api.get(`/hardware/devices/${deviceId}`),
  updateDeviceSettings: (deviceId, settings) =>
    api.put(`/hardware/devices/${deviceId}/settings`, { settings }),
  deleteDevice: (deviceId) => api.delete(`/hardware/devices/${deviceId}`),
  updateDeviceStatus: (deviceId, status) =>
    api.put(`/hardware/devices/${deviceId}/status`, null, { params: { status } }),
  
  // GoPro
  getGoProConfig: (deviceId) => api.get(`/hardware/gopro/${deviceId}/config`),
  getGoProPairingGuide: () => api.get('/hardware/gopro/pairing-guide'),
  
  // RTSP Camera
  validateRtspUrl: (rtspUrl) => api.post('/hardware/rtsp/validate', { rtsp_url: rtspUrl }),
  getRtspSetupGuide: () => api.get('/hardware/rtsp/setup-guide'),
  
  // Dash Cam
  getDashcamSetupGuide: () => api.get('/hardware/dashcam/setup-guide'),
  
  // Stealth Recording
  getStealthSettings: () => api.get('/hardware/stealth/settings'),
  updateStealthSettings: (settings) => api.put('/hardware/stealth/settings', settings),
  
  // Multi-Camera
  getMultiCameraLayout: () => api.get('/hardware/multi-camera/layout')
};

// Two-Factor Authentication API
export const twoFactorAPI = {
  // Status
  getStatus: () => api.get('/2fa/status'),
  
  // TOTP (Authenticator App)
  setupTOTP: () => api.post('/2fa/totp/setup'),
  verifyTOTP: (code) => api.post('/2fa/totp/verify', { code }),
  
  // SMS
  setupSMS: (phone) => api.post('/2fa/sms/setup', { phone }),
  verifySMS: (code) => api.post('/2fa/sms/verify', { code }),
  
  // Email
  setupEmail: () => api.post('/2fa/email/setup'),
  verifyEmail: (code) => api.post('/2fa/email/verify', { code }),
  
  // Management
  disable: (password) => api.post('/2fa/disable', { password }),
  regenerateBackupCodes: () => api.post('/2fa/backup-codes/regenerate'),
  setPrimaryMethod: (method) => api.put('/2fa/primary-method', { method }),
  
  // Login
  sendCode: (method = null) => api.post('/2fa/send-code', null, { params: { method } }),
  verifyLogin: (code, method = null) => api.post('/2fa/verify-login', { code }, { params: { method } })
};

// Rights Training API
export const trainingAPI = {
  getCategories: () => api.get('/training/categories'),
  getScenarios: (category = null) => api.get('/training/scenarios', { params: { category } }),
  getScenario: (scenarioId) => api.get(`/training/scenarios/${scenarioId}`),
  getProgress: () => api.get('/training/progress'),
  submitAnswer: (scenarioId, answerId) => api.post('/training/submit', { scenario_id: scenarioId, answer_id: answerId }),
  getBadges: () => api.get('/training/badges'),
  getLeaderboard: (limit = 10) => api.get('/training/leaderboard', { params: { limit } })
};

// Legal Documents API
export const documentsAPI = {
  getTypes: () => api.get('/documents/types'),
  generate: (encounterId, documentType, additionalInfo = {}) => 
    api.post('/documents/generate', { 
      encounter_id: encounterId, 
      document_type: documentType,
      ...additionalInfo
    }),
  getMyDocuments: () => api.get('/documents/my-documents'),
  getDocument: (documentId) => api.get(`/documents/${documentId}`),
  deleteDocument: (documentId) => api.delete(`/documents/${documentId}`),
  // Document Sharing
  shareDocument: (documentId, recipientId, message) => 
    api.post(`/documents/${documentId}/share`, { recipient_id: recipientId, message }),
  getReceivedShares: () => api.get('/documents/shared/received'),
  getSentShares: () => api.get('/documents/shared/sent'),
  getSharedDocument: (shareId) => api.get(`/documents/shared/${shareId}`)
};

// Court-Grade Evidence Integrity API
export const evidenceIntegrityAPI = {
  // Register evidence with cryptographic verification
  register: (evidenceId, metadata, fileHash, blockchainTier = 'local') =>
    api.post('/evidence-integrity/register', {
      ...metadata,
      evidence_id: evidenceId,
      blockchain_tier: blockchainTier
    }, { params: { file_hash: fileHash } }),
  
  // Verify evidence integrity
  verify: (evidenceId) => api.get(`/evidence-integrity/${evidenceId}/verify`),
  
  // Get chain of custody
  getCustodyChain: (evidenceId) => api.get(`/evidence-integrity/${evidenceId}/custody-chain`),
  
  // Log custody event
  logCustodyEvent: (evidenceId, action, details = {}) =>
    api.post(`/evidence-integrity/${evidenceId}/custody-event`, { 
      evidence_id: evidenceId,
      action, 
      details 
    }),
  
  // Generate court package
  getCourtPackage: (evidenceId) => api.get(`/evidence-integrity/${evidenceId}/court-package`),
  
  // Get forensic metadata
  getMetadata: (evidenceId) => api.get(`/evidence-integrity/${evidenceId}/metadata`),
  
  // Get integrity stats
  getStats: () => api.get('/evidence-integrity/stats')
};

// Police Accountability Portal API
export const accountabilityAPI = {
  // Public endpoints (no auth required)
  getPublicStats: () => api.get('/accountability/public/stats'),
  getPublicDepartments: (state = null, sortBy = 'accountability_score', limit = 50, offset = 0) => 
    api.get('/accountability/public/departments', { 
      params: { state, sort_by: sortBy, limit, offset } 
    }),
  getPublicDepartment: (departmentId) => api.get(`/accountability/public/departments/${departmentId}`),
  getPublicOfficers: (query = null, departmentId = null, minViolations = null, maxScore = null, limit = 50) =>
    api.get('/accountability/public/officers', {
      params: { query, department_id: departmentId, min_violations: minViolations, max_score: maxScore, limit }
    }),
  getPublicOfficer: (officerId) => api.get(`/accountability/public/officers/${officerId}`),
  getOfficerByBadge: (badgeNumber, departmentId) =>
    api.get(`/accountability/public/officers/badge/${badgeNumber}`, { params: { department_id: departmentId } }),
  getLeaderboard: (state = null, limit = 20) =>
    api.get('/accountability/public/leaderboard', { params: { state, limit } }),
  getViolationTypes: () => api.get('/accountability/public/violation-types'),
  
  // Quick lookup - for citizens during encounters
  quickLookup: (badge, state = null) =>
    api.get('/accountability/public/officers/quick-lookup', { params: { badge, state } }),
  
  // Authenticated endpoints
  reportViolation: (violationData) => api.post('/accountability/violations/report', violationData),
  createOfficer: (officerData) => api.post('/accountability/officers', officerData),
  createDepartment: (departmentData) => api.post('/accountability/departments', departmentData),
  updateViolationOutcome: (violationId, outcome, disciplinaryAction = null, settlementAmount = null) =>
    api.patch(`/accountability/violations/${violationId}/outcome`, {
      outcome,
      disciplinary_action: disciplinaryAction,
      settlement_amount: settlementAmount
    }),
  getMyReports: (limit = 50) => api.get('/accountability/my-reports', { params: { limit } }),
  linkOfficerToEncounter: (encounterId, badgeNumber, departmentName, departmentState) =>
    api.post(`/accountability/encounters/${encounterId}/link-officer`, null, {
      params: { badge_number: badgeNumber, department_name: departmentName, department_state: departmentState }
    })
};

// Court-Grade AI API - Enhanced legal analysis with guardrails and confidence scoring
export const courtGradeAPI = {
  // Analyze encounter with court-grade standards
  analyze: (encounterId, transcript, encounterType = 'general', useExistingAnalysis = true) =>
    api.post('/court-grade/analyze', {
      encounter_id: encounterId,
      transcript,
      encounter_type: encounterType,
      use_existing_analysis: useExistingAnalysis
    }),
  
  // Get specific analysis
  getAnalysis: (analysisId) => api.get(`/court-grade/analysis/${analysisId}`),
  
  // Get all analyses for an encounter
  getEncounterAnalyses: (encounterId) => api.get(`/court-grade/encounter/${encounterId}/analyses`),
  
  // Knowledge base access
  getViolationDefinition: (violationType) => api.get(`/court-grade/knowledge-base/violation/${violationType}`),
  getAmendmentInfo: (amendment) => api.get(`/court-grade/knowledge-base/amendment/${amendment}`),
  listAmendments: () => api.get('/court-grade/knowledge-base/amendments'),
  
  // Guardrails
  rerunGuardrails: (analysisId) => api.get(`/court-grade/guardrails/check/${analysisId}`),
  
  // Confidence explanations
  explainConfidence: () => api.get('/court-grade/confidence/explain'),
  
  // Batch processing
  batchAnalyzeQueue: (encounterIds) => api.post('/court-grade/batch-analyze', encounterIds),
  batchAnalyzeRun: (encounterIds) => api.post('/court-grade/batch-analyze/run', encounterIds),
  getBatchStatus: (jobId) => api.get(`/court-grade/batch/${jobId}`)
};

// Premium Analytics API - Predictive analytics and trend analysis
export const premiumAnalyticsAPI = {
  // Risk prediction for a department
  getRiskPrediction: (departmentId) => api.get(`/premium-analytics/risk-prediction/${departmentId}`),
  
  // Violation trends analysis
  getTrends: (departmentId = null, state = null, months = 12) =>
    api.get('/premium-analytics/trends', {
      params: { department_id: departmentId, state, months }
    }),
  
  // Generate audit report
  generateAuditReport: (departmentId = null, state = null, includeOfficers = true, includeSettlements = true) =>
    api.get('/premium-analytics/audit-report', {
      params: { 
        department_id: departmentId, 
        state, 
        include_officers: includeOfficers,
        include_settlements: includeSettlements 
      }
    }),
  
  // Download audit report as PDF
  downloadAuditReportPDF: (departmentId = null, state = null, includeOfficers = true, includeSettlements = true) =>
    api.get('/premium-analytics/audit-report/pdf', {
      params: { 
        department_id: departmentId, 
        state, 
        include_officers: includeOfficers,
        include_settlements: includeSettlements 
      },
      responseType: 'blob'
    }),
  
  // Compare multiple departments
  compareDepartments: (departmentIds) => api.post('/premium-analytics/compare-departments', { department_ids: departmentIds }),
  
  // State overview
  getStateOverview: (state) => api.get(`/premium-analytics/state-overview/${state}`),
  
  // Violation hotspots
  getHotspots: (limit = 10) => api.get('/premium-analytics/hotspots', { params: { limit } })
};

// Officer Detection API - Automatic extraction of officer info from audio/text
export const officerDetectionAPI = {
  // Detect from transcript text
  detectFromText: (transcript, encounterId = null) =>
    api.post('/officer-detection/from-text', { transcript, encounter_id: encounterId }),
  
  // Detect from audio file
  detectFromAudio: (audioFile, encounterId = null) => {
    const formData = new FormData();
    formData.append('audio', audioFile);
    if (encounterId) formData.append('encounter_id', encounterId);
    return api.post('/officer-detection/from-audio', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  // Get detections for an encounter
  getEncounterDetections: (encounterId) => api.get(`/officer-detection/encounter/${encounterId}`),
  
  // Re-run detection on existing encounter
  redetectEncounter: (encounterId) => api.post(`/officer-detection/encounter/${encounterId}/redetect`),
  
  // Get detection stats
  getStats: () => api.get('/officer-detection/stats')
};

// Real-Time Violation Alerts API - Attorney notification system
export const realtimeAlertsAPI = {
  // Analyze transcript chunk for violations (called during live transcription)
  analyzeChunk: (encounterId, transcriptChunk, timestamp = null) =>
    api.post('/realtime-alerts/analyze-chunk', {
      encounter_id: encounterId,
      transcript_chunk: transcriptChunk,
      timestamp
    }),
  
  // Manually trigger alert to attorney
  triggerManualAlert: (encounterId, message, severity = 'high') =>
    api.post('/realtime-alerts/manual-alert', {
      encounter_id: encounterId,
      message,
      severity
    }),
  
  // Get alerts for an encounter
  getEncounterAlerts: (encounterId) => api.get(`/realtime-alerts/encounter/${encounterId}`),
  
  // Get my alerts (for citizens or attorneys)
  getMyAlerts: (limit = 50, unacknowledgedOnly = false) =>
    api.get('/realtime-alerts/my-alerts', {
      params: { limit, unacknowledged_only: unacknowledgedOnly }
    }),
  
  // Acknowledge an alert
  acknowledgeAlert: (alertId) => api.post('/realtime-alerts/acknowledge', { alert_id: alertId }),
  
  // Acknowledge all alerts
  acknowledgeAll: (encounterId = null) =>
    api.post('/realtime-alerts/acknowledge-all', null, {
      params: encounterId ? { encounter_id: encounterId } : {}
    }),
  
  // Get alert statistics
  getStats: (days = 30) => api.get('/realtime-alerts/stats', { params: { days } }),
  
  // Get keywords that trigger alerts
  getKeywords: () => api.get('/realtime-alerts/keywords')
};

// Voice Commands API - Hands-free encounter control
export const voiceCommandsAPI = {
  // Process a voice command
  processCommand: (text, encounterId = null) =>
    api.post('/voice-commands/process', { text, encounter_id: encounterId }),
  
  // Get rights information for encounter type
  getRights: (encounterType, topic = 'default') =>
    api.get(`/voice-commands/rights/${encounterType}`, { params: { topic } }),
  
  // List available commands
  listCommands: () => api.get('/voice-commands/commands'),
  
  // Get voice command stats
  getStats: (days = 30) => api.get('/voice-commands/stats', { params: { days } }),
  
  // Test command parsing (no auth required)
  testCommand: (text) => api.post('/voice-commands/test', { text })
};

// Encounter Coaching API - Real-time AI guidance during encounters
export const encounterCoachAPI = {
  // Analyze transcript chunk for coaching (during live encounter)
  analyze: (transcriptChunk, encounterType = 'general', encounterId = null) =>
    api.post('/encounter-coach/analyze', {
      transcript_chunk: transcriptChunk,
      encounter_type: encounterType,
      encounter_id: encounterId
    }),
  
  // Ask the AI coach a specific question
  askCoach: (question, transcriptContext = '', encounterType = 'general') =>
    api.post('/encounter-coach/ask', {
      question,
      transcript_context: transcriptContext,
      encounter_type: encounterType
    }),
  
  // Get quick response script for a scenario
  getQuickResponse: (scenario) => api.get(`/encounter-coach/quick-response/${scenario}`),
  
  // List all quick response scenarios
  listQuickResponses: () => api.get('/encounter-coach/quick-responses'),
  
  // Get situation-specific coaching
  getSituationCoaching: (encounterType, situation) =>
    api.get(`/encounter-coach/situation/${encounterType}/${situation}`),
  
  // Get list of encounter types
  getEncounterTypes: () => api.get('/encounter-coach/encounter-types'),
  
  // Get list of trigger keywords (debugging/info)
  getTriggers: () => api.get('/encounter-coach/triggers'),
  
  // End coaching session
  endSession: (encounterId) => api.post(`/encounter-coach/end-session/${encounterId}`),
  
  // Get coaching statistics
  getStats: (days = 30) => api.get('/encounter-coach/stats', { params: { days } })
};

// Location Alerts API - Proactive coaching based on proximity to problematic precincts
export const locationAlertsAPI = {
  // Check for alerts at a location
  check: (lat, lon) => api.get('/location-alerts/check', { params: { lat, lon } }),
  
  // Get user's alert history
  getHistory: (limit = 20) => api.get('/location-alerts/history', { params: { limit } }),
  
  // Get monitored precincts
  getPrecincts: () => api.get('/location-alerts/precincts')
};

// Legal Services API - FOIA, Legal Briefs, Miranda Detection
export const legalServicesAPI = {
  // FOIA Request Generation
  generateFOIA: (data) => api.post('/legal/foia/generate', data),
  getFOIALaws: () => api.get('/legal/foia/laws'),
  getMyFOIARequests: () => api.get('/legal/foia/my-requests'),
  
  // Miranda Rights Detection
  analyzeMiranda: (transcript, encounterType, encounterId = null) =>
    api.post('/legal/miranda/analyze', {
      transcript,
      encounter_type: encounterType,
      encounter_id: encounterId
    }),
  analyzeEncounterMiranda: (encounterId) =>
    api.post(`/legal/miranda/analyze-encounter/${encounterId}`),
  
  // Legal Brief Generation
  generateBrief: (data) => api.post('/legal/brief/generate', data),
  generateBriefFromEncounter: (encounterId, plaintiffName) =>
    api.post(`/legal/brief/from-encounter/${encounterId}`, null, {
      params: { plaintiff_name: plaintiffName }
    }),
  getMyBriefs: () => api.get('/legal/brief/my-briefs'),
  
  // Legal Hotlines
  getHotlines: () => api.get('/legal/hotline/numbers'),
  getStateResources: (state) => api.get(`/legal/hotline/by-state/${state}`)
};

export default api;
