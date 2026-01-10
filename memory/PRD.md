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
- **Real-time**: WebSocket (native implementation)
- **Storage**: Local file storage (S3-ready)

## User Personas
1. **Citizens** - Primary users seeking rights protection
2. **Attorneys** - Civil rights legal professionals
3. **Researchers/Public** - Transparency portal access

## Implemented Features (v2.0)

### Phase 1 (Core MVP)
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

### Phase 2 (Current)
- [x] Local file storage for evidence (S3-ready)
- [x] WebSocket real-time notifications
- [x] Attorney-client secure messaging
- [x] PWA support (manifest, service worker, offline page)
- [x] Department Transparency Portal with risk scores
- [x] Enhanced navigation (Messages, Transparency pages)

## Backend APIs (v2.0)

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/session` - Google OAuth session
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Cases
- `GET/POST /api/cases` - List/Create cases
- `GET/PATCH/DELETE /api/cases/{id}` - Case operations

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
- `/cases/:id` - Case detail
- `/evidence` - Evidence library (with file upload)
- `/ai-attorney` - AI chat
- `/sos` - Emergency SOS
- `/attorneys` - Attorney directory
- `/messages` - Secure messaging
- `/rights` - Know Your Rights
- `/transparency` - Department transparency (public)
- `/settings` - User settings

## Technical Notes
- SMS notifications: **MOCKED** (Twilio not integrated)
- File storage: Local `/app/backend/uploads/` (S3-ready)
- PWA: Service worker for offline support
- WebSocket: Native implementation for real-time updates

## Prioritized Backlog

### P1 (Next Phase)
- [ ] Integrate Twilio for real SMS alerts
- [ ] Integrate S3 for scalable file storage
- [ ] Push notifications via service worker
- [ ] Incident heat map visualization
- [ ] Mobile-optimized experience improvements

### P2 (Future)
- [ ] Multi-camera video analysis
- [ ] 3D scene reconstruction
- [ ] Settlement tracking
- [ ] Insurance integration
- [ ] Government dashboard

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
