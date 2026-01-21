# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a comprehensive police accountability and constitutional rights protection platform empowering citizens to protect their constitutional rights during police encounters.

## Core Mission
Provide AI-powered real-time assistance, evidence management, legal support connectivity, and accountability tracking for citizens facing police encounters.

## Architecture
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui components + PWA
- **Backend**: FastAPI (Python) + MongoDB
- **AI**: GPT-5.2 via Emergent LLM key
- **Auth**: JWT + Emergent Google OAuth
- **Real-time**: WebSocket (native implementation with exponential backoff)
- **Storage**: Local file storage (S3-ready)
- **Maps**: Leaflet with OpenStreetMap tiles
- **PDF Generation**: jspdf + jspdf-autotable

## User Personas
1. **Citizens** - Primary users seeking rights protection
2. **Attorneys** - Civil rights legal professionals
3. **Researchers/Public** - Transparency portal access

## Implemented Features (v3.0)

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

### Phase 3 (Advanced Features) ✅ - Completed Jan 21, 2026
- [x] Incident Heat Map (Leaflet + OpenStreetMap)
- [x] Mobile Navigation (bottom nav bar for mobile)
- [x] Case Timeline with event tracking and notes
- [x] PDF Report generation for cases
- [x] Push Notification subscription/unsubscription
- [x] WebSocket exponential backoff reconnection

## Backend APIs (v3.0)

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/session` - Google OAuth session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Cases
- `GET/POST /api/cases` - List/Create cases
- `GET/PATCH/DELETE /api/cases/{id}` - Case operations
- `GET /api/cases/{id}/timeline` - Get case timeline events
- `POST /api/cases/{id}/events` - Add event to timeline
- `GET /api/cases/{id}/report` - Get PDF report data

### Evidence
- `GET/POST /api/evidence` - List/Create evidence
- `GET /api/evidence/case/{id}` - Case evidence
- `DELETE /api/evidence/{id}` - Delete evidence
- `POST /api/upload` - File upload (local storage)
- `GET /api/files/{filename}` - Serve files

### Messaging
- `GET /api/messages/conversations` - List conversations
- `GET /api/messages/conversation/{id}` - Get messages
- `POST /api/messages` - Send message

### Transparency Portal
- `GET /api/departments` - List departments with risk scores
- `GET /api/departments/{id}` - Department details
- `GET /api/departments/{id}/incidents` - Department incidents

### Incident Map
- `GET /api/incidents/map` - Get incidents for map visualization
- `GET /api/incidents/stats` - Get incident statistics

### Push Notifications
- `POST /api/push/subscribe` - Subscribe to push notifications
- `DELETE /api/push/unsubscribe` - Unsubscribe from push

### Others
- `GET /api/attorneys` - Attorney directory
- `POST /api/sos` - Create SOS alert
- `POST /api/ai/chat` - AI Attorney chat
- `GET /api/analytics/public` - Public stats
- `WS /api/ws/{token}` - WebSocket real-time

## Frontend Pages
- `/` - Landing page (public)
- `/login` - Login
- `/register` - Registration
- `/dashboard` - User dashboard
- `/cases` - Case management
- `/cases/new` - Create case
- `/cases/:id` - Case detail (with Timeline tab)
- `/evidence` - Evidence library (with file upload)
- `/ai-attorney` - AI chat
- `/sos` - Emergency SOS
- `/attorneys` - Attorney directory
- `/messages` - Secure messaging
- `/incident-map` - Incident heat map
- `/rights` - Know Your Rights
- `/transparency` - Department transparency (public)
- `/settings` - User settings

## Technical Notes
- SMS notifications: **MOCKED** (Twilio not integrated)
- File storage: Local `/app/backend/uploads/` (S3-ready)
- PWA: Service worker for offline support + push notifications
- WebSocket: Native implementation with exponential backoff (max 10 attempts)
- Maps: Leaflet with OpenStreetMap tiles (no API key required)
- PDF: jspdf + jspdf-autotable for case report generation

## Prioritized Backlog

### P0 (Ready for Implementation)
- [ ] Integrate Twilio for real SMS alerts
- [ ] Integrate AWS S3 for scalable file storage (user needs credentials)

### P1 (Next Phase)
- [ ] Admin/Legal Professional Dashboard
- [ ] Community Forum
- [ ] Multi-camera video analysis

### P2 (Future)
- [ ] 3D scene reconstruction
- [ ] Settlement tracking
- [ ] Insurance integration
- [ ] Government dashboard
- [ ] Automated Legal Document Generation
- [ ] Gamification elements
- [ ] Two-factor authentication (2FA)

## S3 Migration Guide
When ready to switch from local to S3:
1. Get AWS credentials (see setup guide in conversation)
2. Add to backend/.env:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - S3_BUCKET_NAME
   - AWS_REGION
3. Install boto3: `pip install boto3`
4. Update upload endpoint to use S3
5. Update file URLs to S3 presigned URLs

## Test Reports
- /app/test_reports/iteration_1.json - Phase 1 tests
- /app/test_reports/iteration_2.json - Phase 2 tests
- /app/test_reports/iteration_3.json - Phase 3 tests (100% backend, 95% frontend)

## Test Credentials
- Email: test_ui_9410619d@example.com
- Password: password123
