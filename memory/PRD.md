# JUSTICE Platform - Product Requirements Document

## Overview
JUSTICE is a revolutionary **Civil Rights Defense System** - a comprehensive police accountability and constitutional rights protection platform empowering citizens to protect their constitutional rights during police encounters.

## Core Mission
Provide AI-powered real-time assistance, **immutable blockchain-verified evidence**, community-driven evidence aggregation, and **policy impact reporting** for systemic change.

## Architecture
- **Frontend**: React 18 + Tailwind CSS + shadcn/ui components + PWA
- **Backend**: FastAPI (Python) + MongoDB
- **AI**: GPT-5.2 via Emergent LLM key (text analysis, violation detection)
- **Speech-to-Text**: OpenAI Whisper via emergentintegrations
- **Auth**: JWT + Emergent Google OAuth
- **Real-time**: WebSocket (exponential backoff reconnection)
- **Storage**: Local file storage (S3-ready)
- **Evidence Integrity**: SHA-256 cryptographic hashing + simulated blockchain
- **Maps**: Leaflet with OpenStreetMap tiles

## Implemented Features (v5.0) - Updated Jan 21, 2026

### Phase 1-3 (Core Platform) ✅
- User authentication, Dashboard, Case Management, Evidence Library
- AI Attorney (GPT-5.2), Emergency SOS, Attorney Directory
- PWA support, Transparency Portal, Incident Heat Map
- Mobile Navigation, Case Timeline, PDF Reports

### Phase 4 (Encounter Mode) ✅
- "I'm Being Pulled Over" emergency button
- Audio recording + real-time Whisper transcription
- AI violation detection, Rights reminders
- Officer info capture, Broadcast modes

### Phase 5 (AI Legal Analyst) ✅
- Document Analysis for police reports, body cam transcripts
- Violation and bias detection
- Rights Coach, Similar Cases Search

### Phase 6 (Community Evidence Vault) ✅
- Anonymized incident submissions
- Department & Officer tracking rankings
- Public browsing, Upvoting system

### Phase 7 (Blockchain Evidence + Policy Impact) ✅ - NEW
- **Immutable Evidence System**:
  - SHA-256 cryptographic hashing (file + metadata + timestamp)
  - Chain of custody tracking (every access recorded with signatures)
  - Court-admissible verification certificates
  - Simulated blockchain with proof-of-work
  
- **Policy Impact Dashboard**:
  - Report generation for 4 audiences: City Council, Media, Civil Rights Orgs, Legislators
  - 4 report types: Department Accountability, Officer Patterns, State Analysis, Violation Trends
  - Key findings with severity ratings
  - AI-generated recommendations for policy reform

## Backend APIs (v5.0)

### Blockchain Evidence (NEW)
- `POST /api/evidence/secure-upload` - Upload with SHA-256 hash + chain of custody
- `GET /api/evidence/{id}/verify` - Verify integrity (is_valid, chain_intact, court_admissible)
- `GET /api/evidence/{id}/certificate` - Generate court-ready certificate
- `GET /api/blockchain/status` - Blockchain status (blocks, hashes, validity)

### Policy Impact (NEW)
- `GET /api/policy/dashboard-data` - Aggregated data for dashboard
- `POST /api/policy/generate-report` - Generate advocacy report
- `GET /api/policy/reports` - List generated reports
- `GET /api/policy/report/{id}` - Get specific report

### All Other Endpoints
- Authentication: `/api/auth/*`
- Encounter Mode: `/api/encounters/*`
- Document Analysis: `/api/analyze/*`
- Community Vault: `/api/community/*`
- Cases, Evidence, Messaging, Transparency, Incidents, Settings

## Frontend Pages
- `/` - Landing page
- `/dashboard` - User dashboard
- `/encounter` - Encounter Mode (real-time recording)
- `/analyze` - Document Analysis
- `/community` - Community Evidence Vault
- `/policy` - **Policy Impact Dashboard (NEW)**
- `/cases/*` - Case management
- `/evidence` - Evidence library (blockchain-verified)
- `/ai-attorney` - AI chat
- `/sos` - Emergency SOS
- All other pages from Phases 1-6

## Technical Implementation Details

### Blockchain Evidence System
```
1. Upload → SHA-256(file_content) = file_hash
2. Upload → SHA-256(metadata_json) = metadata_hash
3. Upload → SHA-256(file_hash + metadata_hash + timestamp) = combined_hash
4. Chain of Custody → Sign(action + actor + timestamp) = signature
5. Verification → Compare current_hash vs original_hash
6. Certificate → Include all hashes + custody chain + legal notice
```

### Evidence Verification Response
```json
{
  "is_valid": true,
  "chain_intact": true,
  "court_admissible": true,
  "custody_entries": 4,
  "hash_algorithm": "SHA-256",
  "original_hash": "abc123...",
  "current_hash": "abc123...",
  "chain_of_custody": [...]
}
```

### Court Certificate Structure
```json
{
  "certificate_type": "DIGITAL EVIDENCE AUTHENTICITY CERTIFICATE",
  "cryptographic_verification": {
    "algorithm": "SHA-256",
    "file_hash": "...",
    "metadata_hash": "...",
    "combined_hash": "..."
  },
  "chain_of_custody": {...},
  "integrity_statement": "...",
  "legal_notice": "..."
}
```

## Test Reports
- /app/test_reports/iteration_1.json - Phase 1
- /app/test_reports/iteration_2.json - Phase 2
- /app/test_reports/iteration_3.json - Phase 3
- /app/test_reports/iteration_4.json - Phase 4 & 5
- /app/test_reports/iteration_5.json - Phase 6 Community Vault
- /app/test_reports/iteration_6.json - Phase 7 (31/31 tests passed)

## MOCKED Features
- **Blockchain**: Simulated (not real distributed ledger) - for production, integrate with Ethereum/IPFS
- **SOS SMS**: Notifications logged but not sent (needs Twilio)
- **Emergency Contacts**: Notifications logged (needs SMS/email integration)
- **File Storage**: Local (needs AWS S3 for production)

## Prioritized Backlog

### P0 (Ready for Implementation)
- [ ] Real blockchain integration (IPFS/Ethereum for evidence anchoring)
- [ ] Twilio SMS for real SOS alerts
- [ ] AWS S3 for scalable file storage
- [ ] Emergency Contacts UI in Settings

### P1 (Next Phase)
- [ ] Video recording in Encounter Mode
- [ ] OCR for officer badge capture
- [ ] Live streaming (YouTube/Twitch)
- [ ] Attorney hotline integration

### P2 (Future)
- [ ] Smart glasses SDK
- [ ] Dash cam integration
- [ ] 3D scene reconstruction
- [ ] Settlement tracking

## Test Credentials
- Email: encounter_test@example.com
- Password: password123
