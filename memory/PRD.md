# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a comprehensive police accountability and constitutional rights protection platform empowering citizens to protect their constitutional rights during police encounters.

## Core Mission
Provide AI-powered real-time assistance, evidence management, legal support connectivity, and accountability tracking for citizens facing police encounters.

## Architecture
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui components
- **Backend**: FastAPI (Python) + MongoDB
- **AI**: GPT-5.2 via Emergent LLM key
- **Auth**: JWT + Emergent Google OAuth
- **Real-time**: WebSocket (native)

## User Personas
1. **Citizens** - Primary users seeking rights protection
2. **Attorneys** - Civil rights legal professionals
3. **Administrators** - Platform managers

## Core Requirements (MVP - Implemented)
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

## What's Been Implemented (January 2026)

### Backend APIs
- `/api/auth/*` - Authentication (register, login, logout, session, me)
- `/api/cases/*` - Case management (CRUD)
- `/api/evidence/*` - Evidence management with blockchain hashing
- `/api/attorneys` - Attorney directory
- `/api/sos/*` - Emergency SOS alerts
- `/api/ai/chat` - AI Attorney chat (GPT-5.2)
- `/api/messages` - Secure messaging
- `/api/analytics/*` - Dashboard statistics
- `/api/rights` - Know Your Rights content

### Frontend Pages
- Landing Page with hero, features, stats, testimonials
- Login/Register pages with Google OAuth
- Dashboard with metrics and quick actions
- Cases list and detail pages
- New case form
- Evidence library
- AI Attorney chat interface
- Emergency SOS page
- Attorney directory
- Know Your Rights guide
- Settings page

## Prioritized Backlog

### P0 (Critical)
- [x] Core authentication flow
- [x] Case management
- [x] AI Attorney integration

### P1 (High Priority - Next Phase)
- [ ] Twilio SMS integration for real SOS alerts
- [ ] Real-time notifications (WebSocket)
- [ ] File upload for evidence (S3)
- [ ] Attorney messaging system
- [ ] Case timeline view

### P2 (Medium Priority)
- [ ] Multi-camera video analysis
- [ ] 3D scene reconstruction
- [ ] Department transparency portal
- [ ] Settlement tracking
- [ ] Insurance integration

### P3 (Future)
- [ ] Mobile app (PWA)
- [ ] Government dashboard
- [ ] Research partner portal
- [ ] Community forum

## Technical Notes
- SMS notifications are MOCKED (Twilio not integrated)
- Evidence URLs are external links (no S3 upload yet)
- Session management uses httpOnly cookies
- CORS configured for production URL

## Next Action Items
1. Integrate Twilio for real SMS alerts
2. Add S3 file upload for evidence
3. Implement WebSocket for real-time updates
4. Add attorney-client messaging
5. Create mobile-optimized PWA
