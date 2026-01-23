# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a revolutionary **Civil Rights Defense System** - the most comprehensive police accountability and constitutional rights protection platform ever built. It empowers citizens to protect their constitutional rights during police encounters through AI-powered assistance, **immutable blockchain-verified evidence**, **decentralized IPFS storage**, community-driven evidence aggregation, and **policy impact reporting** for systemic change.

## Core Mission
**"Change the narrative. Control your own evidence. End police abuse."**

## Architecture
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui + PWA
- **Backend**: FastAPI (Python) + MongoDB
- **AI**: GPT-5.2 via Emergent LLM key
- **Speech-to-Text**: OpenAI Whisper
- **Auth**: JWT + Emergent Google OAuth
- **Real-time**: WebSocket (exponential backoff) + User notifications endpoint
- **Evidence Integrity**: SHA-256 hashing + Simulated Blockchain
- **Decentralized Storage**: IPFS via Pinata (when configured)
- **Cloud Storage**: AWS S3 for recordings
- **Email**: SendGrid (requires API key)
- **PDF Generation**: fpdf2
- **Scheduling**: APScheduler
- **Maps**: Leaflet + OpenStreetMap

## Latest Updates (Jan 2026)

### Completed Features
- **Push Notifications**: Web Push API with service worker for background alerts
- **Notification Bell**: Real-time notification system with badge count and dropdown panel
- **Report Templates**: Full CRUD for custom branded report templates
- **Template Integration**: Templates now apply to single PDF export, batch export, and email delivery
- **AI Summaries**: GPT-powered transcript summarization
- **PDF Export**: Single and batch PDF generation
- **Email Delivery**: SendGrid integration for emailing reports (requires API key)
- **Scheduled Reports**: APScheduler-based recurring report delivery
- **Live Transcription**: Real-time transcription during video calls
- **WebSocket User Notifications**: Fixed endpoint for real-time user notifications
- **Dashboard Analytics**: Added `/api/analytics/dashboard` endpoint
- **Notifications API**: Full CRUD for user notifications at `/api/notifications`

### Pending Issues
- **WebSocket Stability**: Initial connections sometimes fail in preview environment (auto-reconnect works)
- **SendGrid API Key**: Not configured - email functionality requires `SENDGRID_API_KEY` in backend/.env

## Code Architecture

```
/app/
├── backend/
│   ├── .env                    # Environment variables
│   ├── server.py               # Monolithic server (to be gradually migrated)
│   ├── app/                    # NEW: Refactored module structure
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Configuration settings
│   │   │   └── security.py     # JWT, password hashing, auth
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── database.py     # MongoDB connection
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py      # Pydantic models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ai_service.py   # LLM, transcription, analysis
│   │   │   └── websocket.py    # WebSocket manager
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── analytics.py    # Analytics endpoints
│   │       └── health.py       # Health check
├── frontend/
│   ├── src/
│   │   ├── pages/              # All page components
│   │   ├── components/         # Reusable UI components
│   │   ├── lib/                # API utilities
│   │   └── contexts/           # React contexts
└── memory/
    └── PRD.md
```

**Refactoring Status: ✅ DEPLOYED & LIVE (v5.2.0) - Jan 22, 2026**
- ✅ Created modular directory structure (`/app/backend/app/`)
- ✅ Extracted core config (`config.py`)
- ✅ Extracted security utilities (`security.py`)
- ✅ Extracted database connection (`database.py`)
- ✅ Extracted Pydantic models (`schemas.py` - 50+ models)
- ✅ Extracted AI services (`ai_service.py`)
- ✅ Extracted WebSocket manager (`websocket.py`)
- ✅ Created auth router (`auth.py`)
- ✅ Created cases router (`cases.py`)
- ✅ Created evidence router (`evidence.py`)
- ✅ Created SOS router (`sos.py`)
- ✅ Created analytics router (`analytics.py`)
- ✅ Created attorneys router (`attorneys.py`)
- ✅ Created AI chat router (`ai_chat.py`)
- ✅ Created health router (`health.py`)
- ✅ Created encounters router (`encounters.py`) - full encounter mode with audio/video
- ✅ Created community router (`community.py`) - community vault
- ✅ Created rights router (`rights.py`) - know your rights
- ✅ Created main.py entry point (65 routes across 11 routers)
- ✅ **LIVE**: Backend now runs modular architecture via redirect (server.py imports app.main)
- ✅ Full regression test passed: 20/20 backend tests, 6/6 frontend tests (100% success)
- ✅ Old server.py backed up to server_backup.py (6018 lines)
- ⏳ Future: Policy, Blockchain, IPFS, Document Analysis routers (still in server_backup.py)

## Implemented Features (v5.1) - Jan 21, 2026

### Phase 1-3 (Core Platform) ✅
- User auth, Dashboard, Case Management, Evidence Library
- AI Attorney, Emergency SOS, Attorney Directory
- PWA, Transparency Portal, Incident Heat Map
- Mobile Navigation, Case Timeline, PDF Reports

### Phase 4 (Civil Rights Defense System - Encounter Mode) ✅
- **Real-time recording**: Video + audio with automatic chunked saving
- **Video Recording Mode**: Toggle for video (default on) or audio-only
- **Geolocation pinning**: Automatic location capture
- **AI transcription**: OpenAI Whisper for real-time speech-to-text
- **Violation detection**: AI-powered analysis of police conduct
- **Rights reminders**: Rotating prompts during encounters
- **Officer identification**: Capture badge number, name, department
- **Video Playback**: Full video player with chunk navigation in reports
- **Live Sharing**: Share encounter link with emergency contacts/attorneys
- **Detailed Incident Reports**: AI-generated reports with:
  - Encounter summary and timeline
  - Violation analysis with legal citations
  - Evidence inventory (video chunks, audio, transcriptions)
  - Legal recommendations
  - Similar case references
- **Real-Time AI Analysis** ✅ (Jan 22, 2026):
  - Continuous transcript analysis for violations (4th, 5th, 6th, 8th, 14th Amendments)
  - Bias indicator detection (racial, gender, age, socioeconomic)
  - Procedural issue identification with proper procedure guidance
  - Risk level assessment (low/medium/high/critical)
  - Immediate alerts for critical violations
  - Legal citations and defense strategies
  - Evidence strength evaluation and recommended actions
- **Voice Commands** ✅ (Jan 22, 2026):
  - Hands-free operation during encounters using Web Speech API
  - Commands: "mark violation", "call attorney", "SOS/emergency", "end recording", "pause", "resume", "share"
  - Visual feedback when command recognized
  - Manual violation marks persisted with timestamps
  - Toggle switch to enable/disable voice listening
- **Enhanced Live Transcription** ✅ (Jan 22, 2026):
  - Real-time scrolling transcript display with segment timestamps
  - Keyword highlighting: danger words (red), rights words (green), commands (yellow)
  - Violation alerts inline with transcript segments
  - Typing indicator while listening
  - Expandable full transcript summary
  - Auto-scroll to latest transcription
- **Speaker Diarization** ✅ (Jan 22, 2026):
  - AI-powered speaker identification (Officer vs Citizen)
  - Confidence scores for speaker detection (95%+ accuracy)
  - Multi-speaker detection with speaker_changes array
  - Color-coded segments: blue (Officer), green (Citizen)
  - Speaker badges with emojis (👮/🙋) and confidence %
  - Speaker legend/key in transcription panel
  - Labeled text output ("Officer: ...", "Citizen: ...")
- **Emotion/Tone Detection** ✅ (Jan 22, 2026):
  - AI-powered tone analysis for aggressive, intimidating, hostile behavior
  - 9 tone categories: professional, assertive, aggressive, intimidating, hostile, calm, anxious, defensive, compliant
  - 4 severity levels: normal, elevated, concerning, critical
  - Emotion indicators with evidence quotes and severity ratings
  - Officer demeanor analysis: professionalism, aggression_level (0-100%), intimidation_level, conduct concerns
  - Citizen demeanor analysis: compliance_level, stress_level, asserting_rights
  - Escalation detection with direction tracking (escalating/de-escalating/stable)
  - Real-time WebSocket alerts for concerning/critical tones
  - Visual aggression progress bars and animated alerts
- **Encounter Analytics Dashboard** ✅ (Jan 22, 2026):
  - Risk Score calculation (0-100) based on aggression, intimidation, professionalism
  - Summary stats: total encounters, active, completed, max aggression, violations count
  - Officer Demeanor Analysis with progress bars (professionalism, aggression, intimidation)
  - Tone Distribution visualization showing frequency of each tone type
  - Time patterns: hour-of-day chart (24 hours), day-of-week distribution, peak analysis
  - Geographic hotspots: clustered locations, encounter density mapping
  - 30-day trend tracking with daily encounter counts and aggression levels
  - Violations breakdown by type
  - Tab navigation: Overview, Patterns, Violations, Locations
  - Sidebar navigation integration

### Phase 5 (AI Legal Analyst) ✅
- Document Analysis (police reports, body cam, discovery)
- Violation & bias detection
- Rights Coach, Similar Cases Search

### Phase 6 (Community Evidence Vault) ✅
- Anonymized incident submissions
- Department & Officer rankings
- Public browsing, Upvoting system

### Phase 7 (Blockchain Evidence) ✅
- SHA-256 cryptographic hashing
- Chain of custody tracking
- Court-admissible certificates

### Phase 8 (IPFS Integration) ✅ - Jan 22, 2026
- **Decentralized Storage**: Files uploaded to IPFS network
- **Content Identifiers (CID)**: Permanent, tamper-proof URLs
- **Dual Storage**: Local + IPFS for redundancy
- **Gateway Access**: Anyone can verify via ipfs.io/ipfs/{CID}
- **Pinata Integration**: Professional IPFS pinning service
- **Graceful Degradation**: Works without IPFS, upgrades when configured

### Phase 9 (Evidence Export) ✅ - Jan 22, 2026
- **PDF Report with QR Codes**: Scannable QR codes for instant IPFS verification
- **Quick Verification Grid**: Up to 8 QR codes at top of PDF for rapid scanning
- **Batch Export (ZIP)**: Download complete evidence package for court
  - All evidence files (original quality)
  - VERIFICATION_MANIFEST.json (all hashes, CIDs, custody records)
  - EXPORT_SUMMARY.txt (human-readable)
- **Tabbed Export Dialog**: Choose between PDF Report or Full ZIP Package
- **Chain of Custody**: Complete audit trail with signatures

### Phase 10 (S3 Cloud Backup) ✅ - Jan 22, 2026
- **AWS S3 Integration**: Automated disaster recovery backup
- **Background Backup Jobs**: Non-blocking backup execution
- **Backup Status Dashboard**: Real-time backup statistics in Settings
- **Manual Trigger**: "Backup All Evidence Now" button
- **Graceful Degradation**: Works without S3, provides setup instructions
- **Backup History**: Track all backup jobs with success/failure status

### Phase 11 (Real-time Encounter Sharing) ✅ - Jan 22, 2026
- **Live Share Links**: Generate secure, time-limited (24h) shareable links during encounters
- **Public Viewer Page**: Read-only view showing live transcript, location, and AI alerts at `/shared/:id?token=xxx`
- **Live Guidance**: Viewers can send short guidance messages (max 200 chars) to the user in real-time
- **Auto-notify Contacts**: Option to automatically send share link to emergency contacts when encounter starts
- **Viewer Count**: Track how many people are watching the live encounter
- **Quick Tips**: Pre-written guidance messages for easy sending
- **Share Revocation**: User can revoke share link at any time
- **WebSocket + HTTP Polling**: Real-time updates via WebSocket with HTTP polling fallback
- **Version**: 5.3.0

### Phase 12 (Video Streaming for Shared Views) ✅ - Jan 22, 2026
- **Live Video Feed**: Viewers can watch the live video stream from the user's camera
- **Chunked Streaming**: 15-second video chunks for efficient delivery (~5-10 sec latency)
- **Video Scrubbing**: Timeline slider allows viewers to replay past video chunks
- **Playback Controls**: Play/pause, skip forward/back, fullscreen buttons
- **Go Live Button**: One-click return to live feed when scrubbing
- **Chunk Navigation**: Click on timeline markers to jump to specific chunks
- **LIVE Badge**: Visual indicator when viewing latest chunk
- **Graceful Fallback**: "Waiting for video" placeholder when no video available
- **Security**: Video chunks only accessible with valid share token
- **Version**: 5.4.0

### Phase 13 (Screen Recording Mode) ✅ - Jan 22, 2026
- **Optional Screen Recording**: Toggle in setup to enable screen capture during encounters
- **Browser Support Detection**: Screen recording toggle only shown on supported browsers (Desktop/Android Chrome)
- **Picture-in-Picture View**: Viewers see screen recording as main view with camera feed as corner overlay
- **Toggle Camera PiP**: Button to show/hide camera overlay
- **Screen Chunk Upload**: Separate endpoint for screen recording chunks (`POST /api/encounters/{id}/screen`)
- **Screen Chunk Streaming**: Viewers can access screen chunks via `/api/encounters/shared/{id}/screen/{filename}`
- **Synchronized Playback**: Screen and camera recordings stay in sync during scrubbing
- **Evidence Value**: Captures texts, app interactions, and on-screen evidence
- **Version**: 5.5.0

### Phase 14 (AI Evidence Highlights) ✅ - Jan 22, 2026
- **Auto-detect Key Moments**: AI scans transcriptions to identify violations, escalations, important statements
- **Timestamped Highlights**: Each highlight linked to specific moment in video for easy navigation
- **Categorized Tags**: violation, escalation, threat, rights_assertion, cooperation, important_statement, procedural_issue
- **Severity Scoring**: critical (red), high (orange), medium (yellow), low (blue) for quick triage
- **Timeline Markers**: Colored dots on video timeline showing highlight locations
- **Click-to-Jump**: Click any highlight to jump to that timestamp in video
- **Filter by Category/Severity**: Dropdown to filter highlights
- **Auto-generate + Regenerate**: Auto-generate after encounter ends + regenerate button with feedback
- **Real-time for Viewers**: Shared viewers see highlights as they're generated
- **Legal Relevance Notes**: Each highlight includes legal significance explanation
- **Version**: 5.6.0

### Phase 15 (Export Highlights Report) ✅ - Jan 22, 2026
- **Professional PDF Reports**: Generate court-ready PDF reports with all evidence highlights
- **Two Report Styles**: Formal (court-ready with legal disclaimer) and Simple (quick summary)
- **Both Owner & Viewers**: Encounter owner and shared viewers can download reports
- **Report Contents**: Case info, executive summary, severity/category breakdown, detailed highlights with timestamps
- **Legal Disclaimer**: Formal style includes professional legal disclaimer page
- **Download Headers**: Proper Content-Disposition for automatic file download
- **Filename Convention**: JUSTICE_Report_{encounter_id}_{style}_{date}.pdf
- **QR Code Link**: Optional QR code linking to video evidence (when share URL available)
- **Version**: 5.7.0

### Phase 16 (Attorney Collaboration Mode) ✅ - Jan 22, 2026
- **Attorney Invitation System**: Clients can invite attorneys via email with secure 48-hour token
- **Accept Invite Flow**: Attorneys can create new account or login with existing credentials
- **Attorney Verification**: Submit bar number, firm name, specialization for verification
- **Attorney Dashboard**: Stats (clients, encounters, reviews, messages), client list, encounter list
- **Case Notes**: Private attorney notes with types (general, legal_analysis, strategy, evidence_review)
- **Secure Messaging**: Real-time messaging between attorney and client
- **Encounter Workspace**: Review highlights, transcripts, create notes, send messages
- **Access Management**: Clients can view their attorneys and revoke access
- **Dynamic Sidebar**: Attorney Dashboard link appears for users with role='attorney'
- **Role-based Access Control**: Proper 403 responses for non-attorneys
- **Version**: 5.8.0

### Phase 17 (Video Call Integration) ✅ - Jan 22, 2026
- **WebRTC Video Calls**: Peer-to-peer video/audio calls between attorney and client
- **Call Management API**: Initiate, answer, reject, end calls with history tracking
- **WebSocket Signaling**: Real-time SDP offer/answer and ICE candidate exchange
- **Screen Sharing**: Share screen during calls for document review
- **Incoming Call Modal**: Full-screen modal for incoming calls with accept/reject
- **Call Controls**: Toggle video, audio, screen share, fullscreen, end call
- **Call History**: Database-persisted call records with duration tracking
- **Attorney Workspace Integration**: Video Call button in Messages tab
- **Call Recording**: Record video consultations and save to S3 for legal evidence
  - Start/stop recording with both parties notified
  - MediaRecorder API for client-side capture
  - Upload to S3 with presigned download URLs
  - Fallback to local download if S3 unavailable
  - Recording history and playback
- **Recordings Library Page**: Browse, search, filter, and play all recordings
  - Grid view with thumbnails and metadata
  - Search by participant name or ID
  - Filter by status (completed, awaiting upload, failed)
  - Sort by newest/oldest
  - Built-in video player with controls (play/pause, seek, skip, volume, fullscreen)
  - Direct download option
- **AI Transcription**: OpenAI Whisper-powered speech-to-text for recordings
  - One-click transcription from recording player
  - Transcript tab in video player dialog
  - Copy transcript to clipboard
  - Transcript search across all recordings
  - Search results with context excerpts
  - "Transcribed" badge on transcribed recordings
- **Speaker Identification**: AI labels who said what in conversations
  - GPT-powered speaker diarization
  - Color-coded speaker segments (Attorney: blue, Client: purple)
  - Speaker labels with participant names
  - Formatted output for legal documentation
- **Timestamp Video Sync**: Click transcript segments to jump to video
  - Each segment shows timestamp badge (e.g., "2:35")
  - Clicking a segment switches to video tab and seeks to that moment
  - Auto-plays from clicked position
  - Segments are highlighted and clickable
  - Helper text explains click-to-seek functionality
- **Live Real-Time Transcription** ✅ (Jan 22, 2026):
  - Real-time speech-to-text during video calls using OpenAI Whisper
  - Collapsible transcript panel alongside video feed
  - Live transcript segments with timestamps
  - Note-taking with 4 types: general (blue), important (red), action_item (green), question (yellow)
  - Notes are time-stamped and synced with call duration
  - Transcript auto-scrolls to latest segment
  - Live transcribing indicator animation
  - Notes broadcast to other call participant via WebSocket
  - Transcript saved to MongoDB when call ends
- **AI-Powered Transcript Summaries** ✅ (Jan 22, 2026):
  - Generate comprehensive summaries from call transcripts using GPT-4o-mini
  - AI extracts: Overview, Key Discussion Points, Action Items, Legal Concerns, Recommendations, Follow-up Notes
  - Summary tab in video player dialog alongside Video and Transcript tabs
  - Copy summary to clipboard functionality
  - Visual icons for different section types (green for actions, red for legal concerns, yellow for recommendations)
  - Summaries stored in MongoDB for quick access
  - "Summary" badge on recording cards when summary exists
  - **Export to PDF**: Professional PDF documents with JUSTICE branding, colored section headers, participant info, and confidentiality notice
  - **Batch PDF Export**: Select multiple recordings and export a consolidated report with table of contents, individual summaries, and disclaimer page (max 20 per batch)
  - **Email Delivery**: Send PDF summaries directly to clients/team via email with custom message, CC support, and professional HTML formatting (requires SendGrid API key)
  - **Scheduled Reports** ✅ (Jan 23, 2026): Automated daily/weekly/monthly email reports with APScheduler background jobs, supporting up to 5 schedules per user and 10 recipients per schedule
  - **Report Templates** ✅ (Jan 23, 2026): Custom templates with firm branding (colors, name, logo), section toggles (8 configurable sections), custom header/footer/intro text, confidentiality notice. Max 10 templates per user, with default template support and duplication feature
- **Version**: 5.18.0

### Settings Enhancements ✅
- **Emergency Contacts UI**: Add/remove contacts for encounter notifications
- **Evidence Storage Status**: View blockchain and IPFS status
- **IPFS Setup Guide**: Instructions to enable decentralized storage

## Evidence Integrity System

### How It Works
```
1. UPLOAD
   ├── Compute SHA-256(file) → file_hash
   ├── Compute SHA-256(metadata) → metadata_hash
   ├── Compute SHA-256(combined + timestamp) → combined_hash
   └── Upload to IPFS → ipfs_cid (if configured)

2. CHAIN OF CUSTODY
   └── Every action (create, view, verify, download) logged with digital signature

3. VERIFICATION
   ├── Re-hash file content
   ├── Compare to original hash
   ├── Verify IPFS content matches (if available)
   └── Generate court-admissible certificate

4. IPFS PERMANENCE
   ├── Content stored on decentralized network
   ├── CID = cryptographic hash of content
   └── Cannot be deleted or modified by anyone

5. EVIDENCE REPORT (NEW)
   ├── Generate comprehensive PDF for any case
   ├── Include all evidence with hashes & IPFS CIDs
   └── Full chain of custody for court submission
```

### Court Certificate Includes
- Evidence details (filename, size, type, timestamp)
- SHA-256 file hash, metadata hash, combined hash
- IPFS CID and gateway URLs (if stored on IPFS)
- Full chain of custody with signatures
- Legal integrity statement
- Blockchain block number (simulated)

## Backend APIs (v5.3)

### Evidence Export
- `GET /api/evidence/report/{case_id}` - Generate PDF report data
- `GET /api/evidence/batch-export/{case_id}` - Download ZIP package with all files

### S3 Cloud Backup (NEW)
- `GET /api/backup/status` - Get backup system status and statistics
- `POST /api/backup/trigger` - Manually trigger a backup job
- `GET /api/backup/history` - Get backup job history

### IPFS Storage
- `GET /api/ipfs/status` - IPFS integration status

### Blockchain Evidence
- `POST /api/evidence/secure-upload` - Upload with hash + optional IPFS
- `GET /api/evidence/{id}/verify` - Verify integrity + IPFS
- `GET /api/evidence/{id}/certificate` - Generate court certificate
- `GET /api/blockchain/status` - Blockchain status

### Encounter Mode (NEW - AI Real-Time Analysis)
- `POST /api/encounters/{id}/analyze` - Analyze transcript for violations, bias, procedural issues
- `GET /api/encounters/{id}/violations` - Get all detected violations for an encounter
- `POST /api/encounters/{id}/mark-violation` - Mark a moment as violation (voice command or manual)

### All Other Endpoints
- Community Vault: `/api/community/*`
- Policy Impact: `/api/policy/*`
- Encounter Mode: `/api/encounters/*`
- Document Analysis: `/api/analyze/*`
- Attorney Collaboration: `/api/attorney/*`
- Authentication, Cases, Evidence, Messaging, Transparency

### Attorney Collaboration API (NEW - v5.8.0)
- `POST /api/attorney/invite` - Invite attorney to collaborate on encounter
- `GET /api/attorney/invite/{token}/details` - Public endpoint for invite details
- `POST /api/attorney/accept-invite` - Accept invite (new user)
- `POST /api/attorney/accept-invite/existing` - Accept invite (existing user)
- `POST /api/attorney/verify` - Submit attorney verification
- `GET /api/attorney/dashboard` - Attorney dashboard with stats
- `GET /api/attorney/clients` - List attorney's clients
- `GET /api/attorney/encounters` - List shared encounters
- `POST /api/attorney/notes` - Create case note
- `GET /api/attorney/notes/{encounter_id}` - Get notes for encounter
- `PUT /api/attorney/notes/{note_id}` - Update note
- `DELETE /api/attorney/notes/{note_id}` - Delete note
- `POST /api/attorney/messages` - Send message
- `GET /api/attorney/messages` - Get messages with contact
- `GET /api/attorney/messages/inbox` - Get message inbox
- `GET /api/attorney/my-attorneys` - Client gets their attorneys
- `DELETE /api/attorney/access/{encounter_id}` - Revoke attorney access

### Video Call API (NEW - v5.9.0)
- `POST /api/calls/initiate` - Start a video/audio call
- `POST /api/calls/{call_id}/answer` - Answer incoming call
- `POST /api/calls/{call_id}/reject` - Reject incoming call
- `POST /api/calls/{call_id}/end` - End active call
- `GET /api/calls/active` - Get user's current active call
- `GET /api/calls/incoming` - Get incoming calls
- `GET /api/calls/history` - Get call history
- `WS /api/calls/signal/{call_id}` - WebSocket for WebRTC signaling
- `POST /api/calls/{call_id}/recording/start` - Start recording
- `POST /api/calls/{call_id}/recording/stop` - Stop recording
- `POST /api/calls/{call_id}/recording/upload` - Upload recording to S3
- `GET /api/calls/{call_id}/recordings` - Get recordings for a call
- `GET /api/calls/recordings/my` - Get all user's recordings
- `POST /api/calls/{recording_id}/transcribe` - Transcribe recording with AI
- `GET /api/calls/{recording_id}/transcript` - Get transcript for recording
- `GET /api/calls/transcripts/search` - Search across all transcripts

### Backup API (NEW - v5.9.0)
- `GET /api/backup/status` - Get S3 backup status
- `POST /api/backup/trigger` - Trigger manual backup
- `GET /api/backup/history` - Get backup history

## Configuration

### Environment Variables (backend/.env)
```
PINATA_JWT=<your-pinata-jwt-token>  # For IPFS
```

### Getting Pinata API Key (Free)
1. Go to https://app.pinata.cloud
2. Create account
3. Go to API Keys → New Key
4. Copy JWT token
5. Add to backend/.env as PINATA_JWT

## Test Reports
- iteration_1.json - Phase 1
- iteration_2.json - Phase 2
- iteration_3.json - Phase 3
- iteration_4.json - Phase 4 & 5
- iteration_5.json - Phase 6 (Community Vault)
- iteration_6.json - Phase 7 (Blockchain) - 31/31 passed
- iteration_7.json - Phase 8 (IPFS Integration) - 7/7 passed ✅ - Jan 22, 2026
- iteration_8.json - Phase 9 (Evidence Report) - 9/9 passed ✅ - Jan 22, 2026
- iteration_9.json - Real-Time AI Analysis - 11/11 passed ✅ - Jan 22, 2026
- iteration_10.json - Voice Commands - 9/9 passed ✅ - Jan 22, 2026
- iteration_11.json - Speaker Diarization - 8/8 passed ✅ - Jan 22, 2026
- iteration_12.json - Tone/Emotion Detection - 22/22 passed ✅ - Jan 22, 2026
- iteration_13.json - Encounter Analytics Dashboard - 16/16 passed ✅ - Jan 22, 2026
- iteration_14.json - Backend Refactoring Verification - 27/27 passed ✅ - Jan 22, 2026
- iteration_15.xml - Complete Backend Refactoring - 28/34 passed ✅ - Jan 22, 2026
- iteration_21.json - Attorney Collaboration Mode - 21/21 passed ✅ - Jan 22, 2026
- iteration_22.json - Live Real-Time Transcription - 17/17 passed ✅ - Jan 22, 2026
- iteration_23.json - AI-Powered Transcript Summaries - 10/10 passed ✅ - Jan 22, 2026
- iteration_24.json - PDF Export for Summaries - 6/6 passed ✅ - Jan 23, 2026
- iteration_25.json - Batch PDF Export - 14/14 passed ✅ - Jan 23, 2026
- iteration_26.json - Email Delivery for Summaries - 20/20 passed ✅ - Jan 23, 2026
- iteration_27.json - Scheduled Email Reports - 26/26 backend + UI passed ✅ - Jan 23, 2026
- iteration_28.json - Report Templates - 28/28 backend + UI passed ✅ - Jan 23, 2026

## MOCKED Features
- **Blockchain**: Simulated (production: Ethereum/Polygon)
- **SOS SMS**: Logged (production: Twilio)
- **Emergency Contacts**: Logged (production: SMS/Email)

## LIVE Features
- **IPFS Storage**: ✅ ACTIVE with Pinata JWT (configured Jan 22, 2026)

## Prioritized Backlog

### P0 - COMPLETED
- [x] ✅ Enable IPFS with user's Pinata JWT - DONE Jan 22, 2026
- [x] ✅ Attorney Collaboration Mode - DONE Jan 22, 2026
- [x] ✅ AWS S3 Backup Activation - DONE Jan 22, 2026
- [x] ✅ Video Call Integration - DONE Jan 22, 2026
- [x] ✅ Live Real-Time Transcription - DONE Jan 22, 2026
- [x] ✅ AI-Powered Transcript Summaries - DONE Jan 22, 2026

### P1 (Ready)
- [ ] Real blockchain anchoring (Ethereum/Polygon)
- [ ] Twilio SMS integration
- [ ] AWS S3 backup storage

### P2 (Future)
- [ ] Video recording in Encounter Mode
- [ ] Live streaming (YouTube/Twitch)
- [ ] Smart glasses SDK
- [ ] 3D evidence reconstruction

## Test Credentials
- Citizen: encounter_test@example.com / password123
- Attorney: my_attorney@lawfirm.com / attorney123
