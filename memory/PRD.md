# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a revolutionary **Civil Rights Defense System** - a comprehensive police accountability and constitutional rights protection platform empowering citizens to protect their constitutional rights during police encounters.

## Core Mission
Provide AI-powered real-time assistance, evidence management, legal support connectivity, accountability tracking, and now **real-time encounter protection** for citizens facing police encounters.

## Architecture
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui components + PWA
- **Backend**: FastAPI (Python) + MongoDB
- **AI**: GPT-5.2 via Emergent LLM key (text analysis, violation detection)
- **Speech-to-Text**: OpenAI Whisper via emergentintegrations
- **Auth**: JWT + Emergent Google OAuth
- **Real-time**: WebSocket (native implementation with exponential backoff)
- **Storage**: Local file storage (S3-ready)
- **Maps**: Leaflet with OpenStreetMap tiles
- **PDF Generation**: jspdf + jspdf-autotable

## User Personas
1. **Citizens** - Primary users seeking rights protection during encounters
2. **Attorneys** - Civil rights legal professionals
3. **Researchers/Public** - Transparency portal access

## Implemented Features (v4.0) - Updated Jan 21, 2026

### Phase 1 (Core MVP) ✅
- [x] User authentication (Email/Password + Google OAuth)
- [x] Dashboard with analytics and quick actions
- [x] Case Management (CRUD operations)
- [x] Evidence Library with blockchain-verified timestamps
- [x] AI Attorney powered by GPT-5.2
- [x] Emergency SOS system (SMS MOCKED)
- [x] Attorney Directory with search/filter
- [x] Know Your Rights educational content
- [x] Dark/Light theme toggle
- [x] Responsive design

### Phase 2 (Core Features) ✅
- [x] Local file storage for evidence (S3-ready)
- [x] WebSocket real-time notifications
- [x] Attorney-client secure messaging
- [x] PWA support (manifest, service worker, offline page)
- [x] Department Transparency Portal with risk scores

### Phase 3 (Advanced Features) ✅
- [x] Incident Heat Map (Leaflet + OpenStreetMap)
- [x] Mobile Navigation (bottom nav bar for mobile)
- [x] Case Timeline with event tracking and notes
- [x] PDF Report generation for cases
- [x] Push Notification subscription/unsubscription
- [x] WebSocket exponential backoff reconnection

### Phase 4 (Encounter Mode) ✅ - NEW
- [x] **"I'm Being Pulled Over" emergency button** - One-tap to start recording
- [x] **GPS location pinning** - Automatic location capture at encounter start
- [x] **Audio recording** - Continuous audio capture during encounters
- [x] **Real-time transcription** - Whisper-powered speech-to-text
- [x] **AI violation detection** - Real-time analysis for civil rights violations
- [x] **Rights reminders** - Rotating prompts about your rights
- [x] **Officer information capture** - Record badge, name, department
- [x] **Broadcast modes** - Save only, share with contacts, attorney, or livestream
- [x] **Encounter reports** - AI-generated comprehensive reports after encounter ends

### Phase 5 (AI Legal Analyst) ✅ - NEW
- [x] **Document Analysis** - Upload police reports, body cam transcripts, discovery docs
- [x] **Violation detection** - AI identifies constitutional violations in documents
- [x] **Bias detection** - Identifies racial profiling and discrimination indicators
- [x] **Inconsistency analysis** - Finds contradictions and timeline issues
- [x] **Rights Coach** - Real-time guidance on what to say/do during encounters
- [x] **Similar Cases Search** - Find landmark cases and precedents
- [x] **Emergency Contacts** - Configure contacts for automatic notification

## Backend APIs (v4.0)

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/session` - Google OAuth session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Encounter Mode (NEW)
- `POST /api/encounters/start` - Start new encounter with location
- `POST /api/encounters/{id}/audio` - Upload audio chunk for transcription
- `POST /api/encounters/{id}/officer` - Add officer information
- `POST /api/encounters/{id}/end` - End encounter and generate report
- `GET /api/encounters` - List user encounters
- `GET /api/encounters/{id}` - Get encounter with transcriptions and report

### Document Analysis (NEW)
- `POST /api/analyze/document` - Upload and analyze document
- `GET /api/analyze/documents` - List user's analyses
- `GET /api/analyze/document/{id}` - Get specific analysis

### Rights & Legal (NEW)
- `POST /api/rights-coach` - Get real-time rights guidance
- `GET /api/cases/similar` - Search similar cases and precedents

### Settings (NEW)
- `POST /api/settings/emergency-contacts` - Update emergency contacts
- `GET /api/settings/emergency-contacts` - Get emergency contacts

### Cases
- `GET/POST /api/cases` - List/Create cases
- `GET /api/cases/similar` - Search similar cases
- `GET/PATCH/DELETE /api/cases/{id}` - Case operations
- `GET /api/cases/{id}/timeline` - Get case timeline events
- `POST /api/cases/{id}/events` - Add event to timeline
- `GET /api/cases/{id}/report` - Get PDF report data

### Evidence
- `GET/POST /api/evidence` - List/Create evidence
- `POST /api/upload` - File upload (local storage)
- `GET /api/files/{filename}` - Serve files

### Other
- `GET /api/departments` - Transparency portal departments
- `GET /api/incidents/map` - Incident map data
- `GET /api/attorneys` - Attorney directory
- `POST /api/sos` - Emergency SOS
- `POST /api/ai/chat` - AI Attorney chat
- `WS /api/ws/{token}` - WebSocket real-time

## Frontend Pages
- `/` - Landing page (public)
- `/login`, `/register` - Authentication
- `/dashboard` - User dashboard
- `/encounter` - **Encounter Mode (NEW)**
- `/analyze` - **Document Analysis (NEW)**
- `/cases`, `/cases/new`, `/cases/:id` - Case management
- `/evidence` - Evidence library
- `/ai-attorney` - AI chat
- `/sos` - Emergency SOS
- `/attorneys` - Attorney directory
- `/messages` - Secure messaging
- `/incident-map` - Incident heat map
- `/rights` - Know Your Rights
- `/transparency` - Department transparency
- `/settings` - User settings

## Technical Notes
- SMS notifications: **MOCKED** (Twilio not integrated)
- Emergency contact notifications: **MOCKED** (logged but not sent)
- File storage: Local `/app/backend/uploads/` (S3-ready)
- Audio transcription: OpenAI Whisper via emergentintegrations
- AI Analysis: GPT-5.2 via Emergent LLM key
- Rights Coach has fallback responses when AI unavailable

## Prioritized Backlog

### P0 (Ready for Implementation)
- [ ] Add Emergency Contacts UI to Settings page (API exists)
- [ ] Integrate Twilio for real SMS alerts
- [ ] Integrate AWS S3 for scalable file storage

### P1 (Next Phase)
- [ ] Video recording in Encounter Mode
- [ ] OCR for officer badge/name capture from video
- [ ] Live streaming to YouTube/Twitch
- [ ] Attorney hotline integration
- [ ] Admin/Legal Professional Dashboard

### P2 (Future)
- [ ] Smart glasses SDK for AR overlay
- [ ] Dash cam API integration
- [ ] 3D scene reconstruction for trials
- [ ] Settlement tracking
- [ ] Community Forum
- [ ] Two-factor authentication (2FA)

## Test Reports
- /app/test_reports/iteration_1.json - Phase 1 tests
- /app/test_reports/iteration_2.json - Phase 2 tests
- /app/test_reports/iteration_3.json - Phase 3 tests
- /app/test_reports/iteration_4.json - Phase 4 & 5 tests (100% backend, 95% frontend)

## Test Credentials
- Email: encounter_test@example.com
- Password: password123
