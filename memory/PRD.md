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
- **Real-time**: WebSocket (exponential backoff)
- **Evidence Integrity**: SHA-256 hashing + Simulated Blockchain
- **Decentralized Storage**: IPFS via Pinata (when configured)
- **Maps**: Leaflet + OpenStreetMap

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
- Authentication, Cases, Evidence, Messaging, Transparency

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

## MOCKED Features
- **Blockchain**: Simulated (production: Ethereum/Polygon)
- **SOS SMS**: Logged (production: Twilio)
- **Emergency Contacts**: Logged (production: SMS/Email)

## LIVE Features
- **IPFS Storage**: ✅ ACTIVE with Pinata JWT (configured Jan 22, 2026)

## Prioritized Backlog

### P0 - COMPLETED
- [x] ✅ Enable IPFS with user's Pinata JWT - DONE Jan 22, 2026

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
- Email: encounter_test@example.com
- Password: password123
