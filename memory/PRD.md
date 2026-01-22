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

## Implemented Features (v5.1) - Jan 21, 2026

### Phase 1-3 (Core Platform) ✅
- User auth, Dashboard, Case Management, Evidence Library
- AI Attorney, Emergency SOS, Attorney Directory
- PWA, Transparency Portal, Incident Heat Map
- Mobile Navigation, Case Timeline, PDF Reports

### Phase 4 (Encounter Mode) ✅
- "I'm Being Pulled Over" emergency button
- Audio recording + real-time Whisper transcription
- AI violation detection, Rights reminders
- Officer info capture, Broadcast modes

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
