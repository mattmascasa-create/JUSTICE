"""
Pydantic models for JUSTICE application
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, ConfigDict


# ============== USER MODELS ==============

class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    role: str = "citizen"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    phone: Optional[str] = None
    role: str
    picture: Optional[str] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============== CASE MODELS ==============

class CaseCreate(BaseModel):
    title: str
    description: str
    incident_date: datetime
    location: str
    department: Optional[str] = None
    officer_name: Optional[str] = None
    officer_badge: Optional[str] = None
    violation_type: str
    severity: str = "medium"

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    violation_type: Optional[str] = None
    severity: Optional[str] = None
    assigned_attorney_id: Optional[str] = None

class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    user_id: str
    title: str
    description: str
    status: str
    incident_date: datetime
    location: str
    department: Optional[str] = None
    officer_name: Optional[str] = None
    officer_badge: Optional[str] = None
    violation_type: str
    severity: str
    evidence_count: int = 0
    assigned_attorney_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CaseEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str
    case_id: str
    event_type: str
    description: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by: str


# ============== EVIDENCE MODELS ==============

class EvidenceCreate(BaseModel):
    case_id: str
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    description: Optional[str] = None

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    evidence_id: str
    case_id: str
    user_id: str
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    description: Optional[str] = None
    blockchain_hash: Optional[str] = None
    uploaded_at: datetime


# ============== ATTORNEY MODELS ==============

class AttorneyProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    attorney_id: str
    user_id: str
    name: str
    email: str
    bar_number: str
    state: str
    specializations: List[str]
    rating: float = 0.0
    success_rate: float = 0.0
    cases_won: int = 0
    total_cases: int = 0
    years_experience: int = 0
    hourly_rate: Optional[float] = None
    bio: Optional[str] = None
    verified: bool = False
    available_for_emergency: bool = False
    picture: Optional[str] = None


# ============== SOS ALERT MODELS ==============

class SOSAlertCreate(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

class SOSAlertResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    alert_id: str
    user_id: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


# ============== MESSAGING MODELS ==============

class MessageCreate(BaseModel):
    recipient_id: str
    case_id: Optional[str] = None
    content: str
    attachments: Optional[List[str]] = None

class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str
    conversation_id: str
    sender_id: str
    recipient_id: str
    case_id: Optional[str] = None
    content: str
    attachments: Optional[List[str]] = None
    read: bool = False
    created_at: datetime

class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    conversation_id: str
    participants: List[str]
    case_id: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime


# ============== ENCOUNTER MODELS ==============

class EncounterStart(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    encounter_type: str = "traffic_stop"
    broadcast_mode: str = "save"

class EncounterUpdate(BaseModel):
    status: Optional[str] = None
    broadcast_mode: Optional[str] = None
    notes: Optional[str] = None

class EncounterResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    encounter_id: str
    user_id: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    encounter_type: str
    status: str
    broadcast_mode: str
    stream_key: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0

class TranscriptionSegment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    segment_id: str
    encounter_id: str
    text: str
    speaker: str = "unknown"
    start_time: float
    end_time: float
    confidence: float = 0.0
    violations_detected: List[str] = []
    created_at: datetime

class ViolationAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    analysis_id: str
    encounter_id: str
    violation_type: str
    severity: str
    description: str
    legal_citation: str
    timestamp_in_recording: float
    evidence_segment_ids: List[str] = []
    similar_cases: List[Dict[str, Any]] = []
    recommended_actions: List[str] = []
    created_at: datetime

class OfficerProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    officer_id: str
    encounter_id: str
    name: Optional[str] = None
    badge_number: Optional[str] = None
    department: Optional[str] = None
    rank: Optional[str] = None
    prior_incidents: int = 0
    complaints_count: int = 0
    use_of_force_count: int = 0
    captured_from: str = "manual"
    confidence: float = 0.0
    created_at: datetime

class EncounterReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    report_id: str
    encounter_id: str
    user_id: str
    summary: str
    violations: List[ViolationAnalysis] = []
    officers: List[OfficerProfile] = []
    transcript_text: str
    recommendations: List[str] = []
    legal_resources: List[Dict[str, str]] = []
    similar_cases: List[Dict[str, Any]] = []
    created_at: datetime


# ============== AI CHAT MODELS ==============

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    violation_detected: bool = False
    violation_type: Optional[str] = None
    rights_reminder: Optional[str] = None


# ============== DOCUMENT ANALYSIS MODELS ==============

class DocumentAnalysisRequest(BaseModel):
    document_type: str
    analysis_focus: Optional[str] = None

class DocumentAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    analysis_id: str
    document_id: str
    document_type: str
    summary: str
    violations_found: List[Dict[str, Any]] = []
    bias_indicators: List[Dict[str, Any]] = []
    inconsistencies: List[Dict[str, Any]] = []


# ============== COMMUNITY VAULT MODELS ==============

class CommunitySubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    submission_id: str
    encounter_type: str
    location_city: str
    location_state: str
    incident_date: datetime
    violations: List[str] = []
    department: Optional[str] = None
    officer_badge: Optional[str] = None
    severity: str
    outcome: Optional[str] = None
    summary: str
    verified: bool = False
    upvotes: int = 0
    created_at: datetime

class CommunitySubmitRequest(BaseModel):
    encounter_id: Optional[str] = None
    encounter_type: str
    location_city: str
    location_state: str
    incident_date: datetime
    violations: List[str]
    department: Optional[str] = None
    officer_badge: Optional[str] = None
    severity: str
    outcome: Optional[str] = None
    summary: str

class OfficerStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    badge_number: str
    department: str
    total_incidents: int = 0
    violations_by_type: Dict[str, int] = {}
    severity_distribution: Dict[str, int] = {}
    first_incident: Optional[datetime] = None
    last_incident: Optional[datetime] = None

class DepartmentStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    department: str
    state: str
    total_incidents: int = 0
    officers_with_incidents: int = 0
    violations_by_type: Dict[str, int] = {}
    severity_distribution: Dict[str, int] = {}
    trend: str = "stable"


# ============== BLOCKCHAIN MODELS ==============

class EvidenceHash(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hash_id: str
    evidence_id: str
    file_hash: str
    metadata_hash: str
    combined_hash: str
    algorithm: str = "SHA-256"
    timestamp: datetime
    block_number: Optional[int] = None
    previous_hash: Optional[str] = None
    merkle_root: Optional[str] = None
    verified: bool = False

class ChainOfCustody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    custody_id: str
    evidence_id: str
    action: str
    actor_id: str
    actor_type: str
    timestamp: datetime
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    signature: str
    previous_custody_hash: Optional[str] = None

class EvidenceVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    verification_id: str
    evidence_id: str
    original_hash: str
    current_hash: str
    is_valid: bool
    chain_intact: bool
    custody_entries: int
    verification_timestamp: datetime
    verifier_signature: str

class BlockchainRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    block_number: int
    timestamp: datetime
    evidence_hashes: List[str]
    previous_block_hash: str
    nonce: int
    block_hash: str


# ============== POLICY & REPORTS ==============

class PolicyReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    report_id: str
    report_type: str
    target_audience: str
    title: str
    executive_summary: str
    key_findings: List[Dict[str, Any]]
    data_sources: List[str]
    recommendations: List[str]
    charts_data: Dict[str, Any]
    generated_at: datetime

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    department_id: str
    name: str
    city: str
    state: str
    chief_name: Optional[str] = None
    officer_count: int = 0
    budget: Optional[float] = None
    risk_score: float = 0.0
    complaint_rate: float = 0.0
    use_of_force_rate: float = 0.0
    body_cam_adoption: float = 0.0
    transparency_score: float = 0.0
    total_incidents: int = 0
    resolved_incidents: int = 0


# ============== MISC ==============

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]

class IncidentLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    latitude: float
    longitude: float
    title: str
    violation_type: str
    severity: str
    status: str
    incident_date: datetime
    department: Optional[str] = None
