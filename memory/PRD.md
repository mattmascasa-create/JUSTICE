# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a revolutionary **Civil Rights Defense System** - a comprehensive police accountability and constitutional rights protection platform empowering citizens to protect their constitutional rights during police encounters.

## Core Mission
Provide AI-powered real-time assistance, evidence management, legal support connectivity, accountability tracking, real-time encounter protection, and **community-driven evidence aggregation** for citizens facing police encounters.

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
3. **Researchers/Public** - Transparency portal and community vault access
4. **Advocates** - Using aggregated data for policy change

## Implemented Features (v4.1) - Updated Jan 21, 2026

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

### Phase 4 (Encounter Mode) ✅
- [x] "I'm Being Pulled Over" emergency button
- [x] GPS location pinning
- [x] Audio recording + real-time transcription
- [x] AI violation detection during encounters
- [x] Rights reminders on screen
- [x] Officer information capture
- [x] Broadcast modes (save, share, livestream)
- [x] Auto-generated encounter reports

### Phase 5 (AI Legal Analyst) ✅
- [x] Document Analysis for police reports, body cam transcripts
- [x] Violation detection in documents
- [x] Bias detection (racial profiling, discrimination)
- [x] Rights Coach for real-time guidance
- [x] Similar Cases Search with landmark precedents
- [x] Emergency Contacts API

### Phase 6 (Community Evidence Vault) ✅ - NEW
- [x] **Anonymized Submissions** - Report encounters without exposing identity
- [x] **Department Rankings** - Track departments by incident count
- [x] **Officer Tracking** - Monitor officers with multiple complaints
- [x] **Aggregated Statistics** - Top violations, state distribution, severity breakdown
- [x] **Public Access** - Browse submissions without login
- [x] **Upvoting System** - Community validation of reports
- [x] **Officer Profiles** - Complete history for individual officers
- [x] **Department Profiles** - Stats, submissions, and officers by department
- [x] **Filtering & Search** - By state, department, violation type, severity

## Backend APIs (v4.1)

### Community Evidence Vault (NEW - Public endpoints)
- `GET /api/community/stats` - Overall statistics (total submissions, departments, officers, top violations)
- `GET /api/community/submissions` - Browse submissions with filters (state, department, violation, severity)
- `GET /api/community/departments` - Department rankings by incidents
- `GET /api/community/officers` - Officer rankings by incidents
- `GET /api/community/officer/{badge}/{department}` - Officer profile with all submissions
- `GET /api/community/department/{department}` - Department profile with stats and officers

### Community Evidence Vault (Auth Required)
- `POST /api/community/submit` - Submit anonymized encounter report
- `POST /api/community/upvote/{id}` - Upvote a submission (prevents duplicates)

### All Other Endpoints
- Authentication: `/api/auth/*`
- Encounter Mode: `/api/encounters/*`
- Document Analysis: `/api/analyze/*`
- Rights Coach: `/api/rights-coach`
- Cases: `/api/cases/*`
- Evidence: `/api/evidence/*`, `/api/upload`
- Messaging: `/api/messages/*`
- Transparency: `/api/departments/*`
- Incidents: `/api/incidents/*`
- Settings: `/api/settings/*`

## Frontend Pages
- `/` - Landing page (public)
- `/login`, `/register` - Authentication
- `/dashboard` - User dashboard
- `/encounter` - Encounter Mode
- `/analyze` - Document Analysis
- `/community` - **Community Evidence Vault (NEW)**
- `/cases/*` - Case management
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
- Community Vault: **Privacy-first** - No user_id stored with submissions
- Audio transcription: OpenAI Whisper via emergentintegrations
- AI Analysis: GPT-5.2 via Emergent LLM key

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
- /app/test_reports/iteration_4.json - Phase 4 & 5 tests
- /app/test_reports/iteration_5.json - Phase 6 Community Vault tests (28/28 passed)

## Test Credentials
- Email: encounter_test@example.com
- Password: password123
