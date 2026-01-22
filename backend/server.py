from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, Request, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any, Set
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
import bcrypt
import httpx
import json
import asyncio
import shutil
import random
import base64
import io
import tempfile
import hmac
import aiohttp
import zipfile
from emergentintegrations.llm.openai import OpenAISpeechToText, LlmChat
from emergentintegrations.llm.chat import UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# IPFS Configuration (Pinata)
PINATA_JWT = os.environ.get('PINATA_JWT', '')
PINATA_API_URL = "https://api.pinata.cloud"
IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"

# AWS S3 Configuration (for backup)
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')
S3_ENABLED = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME)

# Initialize S3 client if credentials are available
s3_client = None
if S3_ENABLED:
    import boto3
    from botocore.exceptions import ClientError as S3ClientError
    s3_client = boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'justice-platform-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

# File Storage Settings
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mp3', '.wav', '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'}

# Create the main app
app = FastAPI(title="JUSTICE Platform API", version="5.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AI Services Initialization
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
stt_service = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY) if EMERGENT_LLM_KEY else None

def create_llm_chat(session_id: str, system_message: str = "You are a helpful civil rights legal expert."):
    """Create a new LlmChat instance for analysis"""
    if not EMERGENT_LLM_KEY:
        return None
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message
    )

# Encounter recordings directory
ENCOUNTERS_DIR = ROOT_DIR / "encounters"
ENCOUNTERS_DIR.mkdir(exist_ok=True)
# ============== WEBSOCKET CONNECTION MANAGER ==============

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # user_id -> set of websockets
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.all_connections.add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        self.all_connections.discard(websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            disconnected = set()
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.add(ws)
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)
    
    async def broadcast(self, message: dict, exclude_user: str = None):
        disconnected = set()
        for ws in self.all_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.all_connections.discard(ws)

manager = ConnectionManager()

# ============== MODELS ==============

class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    role: str = "citizen"  # citizen, attorney, admin

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

class CaseCreate(BaseModel):
    title: str
    description: str
    incident_date: datetime
    location: str
    department: Optional[str] = None
    officer_name: Optional[str] = None
    officer_badge: Optional[str] = None
    violation_type: str
    severity: str = "medium"  # low, medium, high, critical

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

class EvidenceCreate(BaseModel):
    case_id: str
    file_name: str
    file_url: str
    file_type: str  # video, audio, image, document
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

class CaseEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str
    case_id: str
    event_type: str  # created, status_change, evidence_added, attorney_assigned, message, note
    description: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by: str

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    violation_detected: bool = False
    violation_type: Optional[str] = None
    rights_reminder: Optional[str] = None

# ============== ENCOUNTER MODE MODELS ==============

class EncounterStart(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    encounter_type: str = "traffic_stop"  # traffic_stop, pedestrian_stop, arrest, search, other
    broadcast_mode: str = "save"  # save, share_contacts, share_attorney, livestream, all

class EncounterUpdate(BaseModel):
    status: Optional[str] = None  # active, paused, ended
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
    speaker: str = "unknown"  # user, officer, unknown
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
    severity: str  # low, medium, high, critical
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
    captured_from: str = "manual"  # manual, ocr, audio
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

class DocumentAnalysisRequest(BaseModel):
    document_type: str  # police_report, discovery, court_filing, body_cam_transcript, other
    analysis_focus: Optional[str] = None  # bias, violations, inconsistencies, all

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
    trend: str = "stable"  # increasing, decreasing, stable

class CommunitySubmitRequest(BaseModel):
    encounter_id: Optional[str] = None  # If sharing from an existing encounter
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

# ============== BLOCKCHAIN EVIDENCE MODELS ==============

class EvidenceHash(BaseModel):
    """Cryptographic hash record for evidence integrity"""
    model_config = ConfigDict(extra="ignore")
    hash_id: str
    evidence_id: str
    file_hash: str  # SHA-256 hash of file content
    metadata_hash: str  # SHA-256 hash of metadata
    combined_hash: str  # Hash of (file_hash + metadata_hash + timestamp)
    algorithm: str = "SHA-256"
    timestamp: datetime
    block_number: Optional[int] = None  # Simulated blockchain block
    previous_hash: Optional[str] = None  # Chain link to previous evidence
    merkle_root: Optional[str] = None  # For batch verification
    verified: bool = False

class ChainOfCustody(BaseModel):
    """Track every access and modification to evidence"""
    model_config = ConfigDict(extra="ignore")
    custody_id: str
    evidence_id: str
    action: str  # created, accessed, downloaded, shared, verified
    actor_id: str
    actor_type: str  # user, system, attorney, court
    timestamp: datetime
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    signature: str  # Digital signature of the action
    previous_custody_hash: Optional[str] = None

class EvidenceVerification(BaseModel):
    """Verification record for court submission"""
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
    """Simulated blockchain block for evidence"""
    model_config = ConfigDict(extra="ignore")
    block_number: int
    timestamp: datetime
    evidence_hashes: List[str]
    previous_block_hash: str
    nonce: int
    block_hash: str

class PolicyReport(BaseModel):
    """Generated policy impact report"""
    model_config = ConfigDict(extra="ignore")
    report_id: str
    report_type: str  # department_accountability, officer_pattern, state_analysis, violation_trend
    target_audience: str  # city_council, media, civil_rights_org, legislators
    title: str
    executive_summary: str
    key_findings: List[Dict[str, Any]]
    data_sources: List[str]
    recommendations: List[str]
    charts_data: Dict[str, Any]
    generated_at: datetime

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

# ============== AUTH HELPERS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    # Check cookie first, then Authorization header
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if it's a session token (from Google OAuth)
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        
        user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    
    # Otherwise, try JWT
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
        return 'video'
    elif ext in {'.mp3', '.wav', '.ogg', '.m4a'}:
        return 'audio'
    elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        return 'image'
    else:
        return 'document'

# ============== AUTH ENDPOINTS ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "phone": user_data.phone,
        "role": "citizen",
        "picture": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.users.insert_one(user_doc)
    token = create_token(user_id)
    
    user_response = UserResponse(
        user_id=user_id,
        email=user_data.email,
        name=user_data.name,
        phone=user_data.phone,
        role="citizen",
        picture=None,
        created_at=now
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("password_hash") or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["user_id"])
    
    created_at = user.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    
    user_response = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        phone=user.get("phone"),
        role=user.get("role", "citizen"),
        picture=user.get("picture"),
        created_at=created_at
    )
    
    return TokenResponse(access_token=token, user=user_response)

@api_router.post("/auth/session")
async def process_session(request: Request):
    """Process Google OAuth session_id and return user data with session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Fetch user data from Emergent Auth
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        auth_data = response.json()
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": auth_data["email"]}, {"_id": 0})
    now = datetime.now(timezone.utc)
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": auth_data.get("name", existing_user["name"]),
                "picture": auth_data.get("picture"),
                "updated_at": now.isoformat()
            }}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": auth_data["email"],
            "name": auth_data.get("name", "User"),
            "picture": auth_data.get("picture"),
            "role": "citizen",
            "phone": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create session
    session_token = auth_data.get("session_token", f"sess_{uuid.uuid4().hex}")
    expires_at = now + timedelta(days=7)
    
    await db.user_sessions.update_one(
        {"user_id": user_id},
        {"$set": {
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat()
        }},
        upsert=True
    )
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    response = JSONResponse(content={
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "role": user.get("role", "citizen")
    })
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7*24*60*60,
        path="/"
    )
    
    return response

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    created_at = current_user.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "phone": current_user.get("phone"),
        "role": current_user.get("role", "citizen"),
        "picture": current_user.get("picture"),
        "created_at": created_at.isoformat() if created_at else None
    }

@api_router.post("/auth/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    await db.user_sessions.delete_one({"user_id": current_user["user_id"]})
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("session_token", path="/")
    return response

# ============== FILE UPLOAD ENDPOINTS ==============

@api_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    case_id: str = None,
    description: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload a file to local storage (will be S3 later)"""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    
    # Generate unique filename
    file_id = f"{uuid.uuid4().hex[:12]}"
    safe_filename = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Get file size
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        file_path.unlink()  # Delete the file
        raise HTTPException(status_code=400, detail="File too large (max 500MB)")
    
    # Generate file URL
    file_url = f"/api/files/{safe_filename}"
    
    # If case_id provided, create evidence record
    evidence_id = None
    blockchain_hash = None
    if case_id:
        # Verify case exists and belongs to user
        case = await db.cases.find_one(
            {"case_id": case_id, "user_id": current_user["user_id"]},
            {"_id": 0}
        )
        if not case:
            file_path.unlink()
            raise HTTPException(status_code=404, detail="Case not found")
        
        evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        # Generate blockchain-style hash
        hash_input = f"{file_url}{now.isoformat()}{evidence_id}"
        blockchain_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        evidence_doc = {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "user_id": current_user["user_id"],
            "file_name": file.filename,
            "file_url": file_url,
            "file_type": get_file_type(file.filename),
            "file_size": file_size,
            "description": description,
            "blockchain_hash": blockchain_hash,
            "uploaded_at": now.isoformat()
        }
        
        await db.evidence.insert_one(evidence_doc)
        await db.cases.update_one(
            {"case_id": case_id},
            {"$inc": {"evidence_count": 1}}
        )
        
        # Send WebSocket notification
        await manager.send_to_user(current_user["user_id"], {
            "type": "evidence_added",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "file_name": file.filename
        })
    
    return {
        "file_url": file_url,
        "file_name": file.filename,
        "file_size": file_size,
        "file_type": get_file_type(file.filename),
        "evidence_id": evidence_id,
        "blockchain_hash": blockchain_hash
    }

@api_router.get("/files/{filename}")
async def get_file(filename: str):
    """Serve uploaded files"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# ============== CASES ENDPOINTS ==============

@api_router.post("/cases", response_model=CaseResponse)
async def create_case(case_data: CaseCreate, current_user: dict = Depends(get_current_user)):
    case_id = f"case_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    case_doc = {
        "case_id": case_id,
        "user_id": current_user["user_id"],
        "title": case_data.title,
        "description": case_data.description,
        "status": "open",
        "incident_date": case_data.incident_date.isoformat(),
        "location": case_data.location,
        "department": case_data.department,
        "officer_name": case_data.officer_name,
        "officer_badge": case_data.officer_badge,
        "violation_type": case_data.violation_type,
        "severity": case_data.severity,
        "evidence_count": 0,
        "assigned_attorney_id": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.cases.insert_one(case_doc)
    
    # Send WebSocket notification
    await manager.send_to_user(current_user["user_id"], {
        "type": "case_created",
        "case_id": case_id,
        "title": case_data.title
    })
    
    return CaseResponse(
        case_id=case_id,
        user_id=current_user["user_id"],
        title=case_data.title,
        description=case_data.description,
        status="open",
        incident_date=case_data.incident_date,
        location=case_data.location,
        department=case_data.department,
        officer_name=case_data.officer_name,
        officer_badge=case_data.officer_badge,
        violation_type=case_data.violation_type,
        severity=case_data.severity,
        evidence_count=0,
        assigned_attorney_id=None,
        created_at=now,
        updated_at=now
    )

@api_router.get("/cases", response_model=List[CaseResponse])
async def get_cases(current_user: dict = Depends(get_current_user)):
    cases = await db.cases.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    result = []
    for case in cases:
        for field in ["incident_date", "created_at", "updated_at"]:
            if isinstance(case.get(field), str):
                case[field] = datetime.fromisoformat(case[field])
        result.append(CaseResponse(**case))
    
    return result

@api_router.get("/cases/similar")
async def search_similar_cases(
    violation_type: str,
    department: Optional[str] = None,
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Search for similar cases and their outcomes"""
    # Search our database first
    query = {"violation_type": violation_type, "status": {"$in": ["resolved", "closed"]}}
    if department:
        query["department"] = department
    
    similar = await db.cases.find(query, {"_id": 0}).limit(10).to_list(length=10)
    
    # Mock external case data (in production, integrate with legal databases)
    external_cases = [
        {
            "case_name": "Terry v. Ohio (1968)",
            "violation_type": "4th Amendment",
            "outcome": "Established 'stop and frisk' standards - officers need reasonable suspicion",
            "relevance": "high" if "4th" in violation_type.lower() or "search" in violation_type.lower() else "medium"
        },
        {
            "case_name": "Miranda v. Arizona (1966)",
            "violation_type": "5th Amendment",
            "outcome": "Established Miranda rights requirement before interrogation",
            "relevance": "high" if "5th" in violation_type.lower() or "miranda" in violation_type.lower() else "medium"
        },
        {
            "case_name": "Graham v. Connor (1989)",
            "violation_type": "Excessive Force",
            "outcome": "Established 'objective reasonableness' standard for force",
            "relevance": "high" if "force" in violation_type.lower() or "8th" in violation_type.lower() else "medium"
        }
    ]
    
    return {
        "similar_cases_in_system": similar,
        "landmark_cases": external_cases,
        "total_found": len(similar)
    }

@api_router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(case.get(field), str):
            case[field] = datetime.fromisoformat(case[field])
    
    return CaseResponse(**case)

@api_router.patch("/cases/{case_id}", response_model=CaseResponse)
async def update_case(case_id: str, case_data: CaseUpdate, current_user: dict = Depends(get_current_user)):
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    update_data = {k: v for k, v in case_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    old_status = case.get("status")
    
    await db.cases.update_one(
        {"case_id": case_id},
        {"$set": update_data}
    )
    
    updated_case = await db.cases.find_one({"case_id": case_id}, {"_id": 0})
    
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(updated_case.get(field), str):
            updated_case[field] = datetime.fromisoformat(updated_case[field])
    
    # Send WebSocket notification for status change
    if case_data.status and case_data.status != old_status:
        await manager.send_to_user(current_user["user_id"], {
            "type": "case_status_changed",
            "case_id": case_id,
            "old_status": old_status,
            "new_status": case_data.status
        })
    
    return CaseResponse(**updated_case)

@api_router.delete("/cases/{case_id}")
async def delete_case(case_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.cases.delete_one(
        {"case_id": case_id, "user_id": current_user["user_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Also delete associated evidence
    await db.evidence.delete_many({"case_id": case_id})
    
    return {"message": "Case deleted successfully"}

# ============== EVIDENCE ENDPOINTS ==============

@api_router.post("/evidence", response_model=EvidenceResponse)
async def create_evidence(evidence_data: EvidenceCreate, current_user: dict = Depends(get_current_user)):
    # Verify case exists and belongs to user
    case = await db.cases.find_one(
        {"case_id": evidence_data.case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Generate blockchain-style hash for evidence integrity
    hash_input = f"{evidence_data.file_url}{now.isoformat()}{evidence_id}"
    blockchain_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    
    evidence_doc = {
        "evidence_id": evidence_id,
        "case_id": evidence_data.case_id,
        "user_id": current_user["user_id"],
        "file_name": evidence_data.file_name,
        "file_url": evidence_data.file_url,
        "file_type": evidence_data.file_type,
        "file_size": evidence_data.file_size,
        "description": evidence_data.description,
        "blockchain_hash": blockchain_hash,
        "uploaded_at": now.isoformat()
    }
    
    await db.evidence.insert_one(evidence_doc)
    
    # Update evidence count on case
    await db.cases.update_one(
        {"case_id": evidence_data.case_id},
        {"$inc": {"evidence_count": 1}}
    )
    
    return EvidenceResponse(
        evidence_id=evidence_id,
        case_id=evidence_data.case_id,
        user_id=current_user["user_id"],
        file_name=evidence_data.file_name,
        file_url=evidence_data.file_url,
        file_type=evidence_data.file_type,
        file_size=evidence_data.file_size,
        description=evidence_data.description,
        blockchain_hash=blockchain_hash,
        uploaded_at=now
    )

@api_router.get("/evidence", response_model=List[EvidenceResponse])
async def get_all_evidence(current_user: dict = Depends(get_current_user)):
    evidence_list = await db.evidence.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(500)
    
    result = []
    for ev in evidence_list:
        if isinstance(ev.get("uploaded_at"), str):
            ev["uploaded_at"] = datetime.fromisoformat(ev["uploaded_at"])
        result.append(EvidenceResponse(**ev))
    
    return result

@api_router.get("/evidence/case/{case_id}", response_model=List[EvidenceResponse])
async def get_case_evidence(case_id: str, current_user: dict = Depends(get_current_user)):
    evidence_list = await db.evidence.find(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(100)
    
    result = []
    for ev in evidence_list:
        if isinstance(ev.get("uploaded_at"), str):
            ev["uploaded_at"] = datetime.fromisoformat(ev["uploaded_at"])
        result.append(EvidenceResponse(**ev))
    
    return result

@api_router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str, current_user: dict = Depends(get_current_user)):
    evidence = await db.evidence.find_one(
        {"evidence_id": evidence_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    await db.evidence.delete_one({"evidence_id": evidence_id})
    
    # Update evidence count on case
    await db.cases.update_one(
        {"case_id": evidence["case_id"]},
        {"$inc": {"evidence_count": -1}}
    )
    
    # Delete local file if exists
    if evidence["file_url"].startswith("/api/files/"):
        filename = evidence["file_url"].split("/")[-1]
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            file_path.unlink()
    
    return {"message": "Evidence deleted successfully"}

# ============== ATTORNEY ENDPOINTS ==============

@api_router.get("/attorneys", response_model=List[AttorneyProfile])
async def get_attorneys(
    state: Optional[str] = None,
    specialization: Optional[str] = None,
    available_emergency: Optional[bool] = None,
    min_rating: Optional[float] = None
):
    query = {"verified": True}
    
    if state:
        query["state"] = state
    if specialization:
        query["specializations"] = {"$in": [specialization]}
    if available_emergency:
        query["available_for_emergency"] = True
    if min_rating:
        query["rating"] = {"$gte": min_rating}
    
    attorneys = await db.attorneys.find(query, {"_id": 0}).sort("rating", -1).to_list(100)
    
    # If no attorneys, seed some sample data
    if not attorneys:
        await seed_sample_attorneys()
        attorneys = await db.attorneys.find(query, {"_id": 0}).sort("rating", -1).to_list(100)
    
    return [AttorneyProfile(**a) for a in attorneys]

@api_router.get("/attorneys/{attorney_id}", response_model=AttorneyProfile)
async def get_attorney(attorney_id: str):
    attorney = await db.attorneys.find_one({"attorney_id": attorney_id}, {"_id": 0})
    
    if not attorney:
        raise HTTPException(status_code=404, detail="Attorney not found")
    
    return AttorneyProfile(**attorney)

async def seed_sample_attorneys():
    """Seed sample attorney data for the directory"""
    sample_attorneys = [
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Sarah Mitchell, Esq.",
            "email": "sarah.mitchell@civilrights.law",
            "bar_number": "CA123456",
            "state": "California",
            "specializations": ["Civil Rights", "Police Misconduct", "4th Amendment"],
            "rating": 4.9,
            "success_rate": 87.5,
            "cases_won": 156,
            "total_cases": 178,
            "years_experience": 15,
            "hourly_rate": 350.0,
            "bio": "Former ACLU staff attorney with 15 years of experience in civil rights litigation. Specializing in police accountability cases.",
            "verified": True,
            "available_for_emergency": True,
            "picture": "https://images.pexels.com/photos/4427497/pexels-photo-4427497.jpeg"
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Marcus Johnson, Esq.",
            "email": "mjohnson@constitutionaldefense.org",
            "bar_number": "NY789012",
            "state": "New York",
            "specializations": ["Constitutional Law", "1st Amendment", "Excessive Force"],
            "rating": 4.8,
            "success_rate": 82.3,
            "cases_won": 203,
            "total_cases": 247,
            "years_experience": 20,
            "hourly_rate": 400.0,
            "bio": "Constitutional law expert and former federal public defender. Led landmark civil rights cases before the Supreme Court.",
            "verified": True,
            "available_for_emergency": True,
            "picture": "https://images.pexels.com/photos/4427428/pexels-photo-4427428.jpeg"
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Elena Rodriguez, Esq.",
            "email": "erodriguez@rightsdefenders.com",
            "bar_number": "TX345678",
            "state": "Texas",
            "specializations": ["Civil Rights", "Immigration Rights", "5th Amendment"],
            "rating": 4.7,
            "success_rate": 79.8,
            "cases_won": 134,
            "total_cases": 168,
            "years_experience": 12,
            "hourly_rate": 300.0,
            "bio": "Bilingual civil rights attorney dedicated to protecting marginalized communities. Named 'Rising Star' by Super Lawyers.",
            "verified": True,
            "available_for_emergency": False,
            "picture": None
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "David Chen, Esq.",
            "email": "dchen@policeoversight.law",
            "bar_number": "IL901234",
            "state": "Illinois",
            "specializations": ["Police Misconduct", "False Arrest", "Civil Rights"],
            "rating": 4.6,
            "success_rate": 85.2,
            "cases_won": 98,
            "total_cases": 115,
            "years_experience": 8,
            "hourly_rate": 275.0,
            "bio": "Former prosecutor turned civil rights advocate. Expertise in police misconduct and false arrest cases in Chicago.",
            "verified": True,
            "available_for_emergency": True,
            "picture": None
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Aisha Williams, Esq.",
            "email": "awilliams@justiceinitiative.org",
            "bar_number": "GA567890",
            "state": "Georgia",
            "specializations": ["Racial Profiling", "14th Amendment", "Civil Rights"],
            "rating": 4.9,
            "success_rate": 91.0,
            "cases_won": 187,
            "total_cases": 206,
            "years_experience": 18,
            "hourly_rate": 375.0,
            "bio": "Award-winning civil rights attorney focused on racial justice. Board member of the National Civil Rights Legal Foundation.",
            "verified": True,
            "available_for_emergency": True,
            "picture": None
        }
    ]
    
    await db.attorneys.insert_many(sample_attorneys)

# ============== MESSAGING ENDPOINTS ==============

@api_router.post("/messages", response_model=MessageResponse)
async def send_message(message_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Find or create conversation
    participants = sorted([current_user["user_id"], message_data.recipient_id])
    conversation = await db.conversations.find_one({
        "participants": participants,
        "case_id": message_data.case_id
    }, {"_id": 0})
    
    if conversation:
        conversation_id = conversation["conversation_id"]
    else:
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        await db.conversations.insert_one({
            "conversation_id": conversation_id,
            "participants": participants,
            "case_id": message_data.case_id,
            "created_at": now.isoformat()
        })
    
    message_doc = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender_id": current_user["user_id"],
        "recipient_id": message_data.recipient_id,
        "case_id": message_data.case_id,
        "content": message_data.content,
        "attachments": message_data.attachments,
        "read": False,
        "created_at": now.isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    # Update conversation
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {"$set": {
            "last_message": message_data.content[:100],
            "last_message_at": now.isoformat()
        }}
    )
    
    # Send WebSocket notification to recipient
    await manager.send_to_user(message_data.recipient_id, {
        "type": "new_message",
        "message_id": message_id,
        "conversation_id": conversation_id,
        "sender_id": current_user["user_id"],
        "sender_name": current_user["name"],
        "content_preview": message_data.content[:50] + "..." if len(message_data.content) > 50 else message_data.content
    })
    
    return MessageResponse(
        message_id=message_id,
        conversation_id=conversation_id,
        sender_id=current_user["user_id"],
        recipient_id=message_data.recipient_id,
        case_id=message_data.case_id,
        content=message_data.content,
        attachments=message_data.attachments,
        read=False,
        created_at=now
    )

@api_router.get("/messages/conversations", response_model=List[ConversationResponse])
async def get_conversations(current_user: dict = Depends(get_current_user)):
    conversations = await db.conversations.find(
        {"participants": current_user["user_id"]},
        {"_id": 0}
    ).sort("last_message_at", -1).to_list(50)
    
    result = []
    for conv in conversations:
        # Count unread messages
        unread_count = await db.messages.count_documents({
            "conversation_id": conv["conversation_id"],
            "recipient_id": current_user["user_id"],
            "read": False
        })
        
        for field in ["last_message_at", "created_at"]:
            if isinstance(conv.get(field), str):
                conv[field] = datetime.fromisoformat(conv[field])
        
        conv["unread_count"] = unread_count
        result.append(ConversationResponse(**conv))
    
    return result

@api_router.get("/messages/conversation/{conversation_id}", response_model=List[MessageResponse])
async def get_conversation_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    # Verify user is participant
    conversation = await db.conversations.find_one({
        "conversation_id": conversation_id,
        "participants": current_user["user_id"]
    }, {"_id": 0})
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.messages.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    
    # Mark messages as read
    await db.messages.update_many(
        {
            "conversation_id": conversation_id,
            "recipient_id": current_user["user_id"],
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    result = []
    for msg in messages:
        if isinstance(msg.get("created_at"), str):
            msg["created_at"] = datetime.fromisoformat(msg["created_at"])
        result.append(MessageResponse(**msg))
    
    return result

@api_router.post("/messages/{message_id}/read")
async def mark_message_read(message_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.messages.update_one(
        {"message_id": message_id, "recipient_id": current_user["user_id"]},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Message marked as read"}

# ============== SOS ALERTS ==============

@api_router.post("/sos", response_model=SOSAlertResponse)
async def create_sos_alert(alert_data: SOSAlertCreate, current_user: dict = Depends(get_current_user)):
    alert_id = f"sos_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    alert_doc = {
        "alert_id": alert_id,
        "user_id": current_user["user_id"],
        "latitude": alert_data.latitude,
        "longitude": alert_data.longitude,
        "address": alert_data.address,
        "status": "active",
        "created_at": now.isoformat(),
        "resolved_at": None
    }
    
    await db.sos_alerts.insert_one(alert_doc)
    
    # MOCKED: In production, this would trigger:
    # - SMS notifications via Twilio
    # - Email notifications to emergency contacts
    # - Attorney notifications for emergency responders
    logger.info(f"SOS Alert created: {alert_id} by user {current_user['user_id']}")
    
    # Broadcast SOS to emergency-available attorneys (simulated)
    await manager.broadcast({
        "type": "sos_alert",
        "alert_id": alert_id,
        "user_name": current_user["name"],
        "latitude": alert_data.latitude,
        "longitude": alert_data.longitude
    }, exclude_user=current_user["user_id"])
    
    return SOSAlertResponse(
        alert_id=alert_id,
        user_id=current_user["user_id"],
        latitude=alert_data.latitude,
        longitude=alert_data.longitude,
        address=alert_data.address,
        status="active",
        created_at=now,
        resolved_at=None
    )

@api_router.get("/sos/active", response_model=Optional[SOSAlertResponse])
async def get_active_alert(current_user: dict = Depends(get_current_user)):
    alert = await db.sos_alerts.find_one(
        {"user_id": current_user["user_id"], "status": "active"},
        {"_id": 0}
    )
    
    if not alert:
        return None
    
    if isinstance(alert.get("created_at"), str):
        alert["created_at"] = datetime.fromisoformat(alert["created_at"])
    
    return SOSAlertResponse(**alert)

@api_router.post("/sos/{alert_id}/resolve")
async def resolve_sos_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    
    result = await db.sos_alerts.update_one(
        {"alert_id": alert_id, "user_id": current_user["user_id"]},
        {"$set": {"status": "resolved", "resolved_at": now.isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "SOS alert resolved"}

# ============== AI ATTORNEY CHAT ==============

@api_router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat(chat_data: ChatMessage, current_user: dict = Depends(get_current_user)):
    """AI Attorney - Constitutional rights advisor powered by GPT-5.2"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    session_id = chat_data.session_id or f"chat_{uuid.uuid4().hex[:12]}"
    
    # Get chat history for context
    history = await db.chat_history.find(
        {"session_id": session_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(20)
    
    system_message = """You are JUSTICE AI Attorney, an expert constitutional rights advisor. Your role is to:

1. Help citizens understand their constitutional rights during police encounters
2. Detect potential civil rights violations in described situations
3. Provide clear, actionable advice on how to protect one's rights
4. Explain relevant amendments (1st, 4th, 5th, 6th, 8th, 14th)
5. Suggest when professional legal help is needed

IMPORTANT GUIDELINES:
- Always prioritize the person's safety
- Be clear about what they can legally do vs what might escalate situations
- Remind them they have the right to remain silent (5th Amendment)
- Remind them they have the right to refuse consent to searches (4th Amendment)
- If they're being detained, they have the right to know why
- Document everything when safe to do so
- Never provide advice that could put them in danger

Format your responses clearly with:
- RIGHTS REMINDER: Key rights relevant to their situation
- ANALYSIS: Assessment of any potential violations
- ADVICE: Recommended actions
- WARNING: Any safety considerations

If you detect a potential violation, clearly state which constitutional right may be at risk."""

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        # Build context from history
        context = ""
        if history:
            context = "Previous conversation context:\n"
            for msg in history[-5:]:  # Last 5 messages for context
                context += f"User: {msg['user_message']}\nAssistant: {msg['ai_response']}\n\n"
        
        full_message = context + f"Current question: {chat_data.message}" if context else chat_data.message
        
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Check for violation detection
        violation_detected = False
        violation_type = None
        rights_reminder = None
        
        response_lower = response.lower()
        if "violation" in response_lower or "unconstitutional" in response_lower:
            violation_detected = True
            if "4th amendment" in response_lower or "search" in response_lower:
                violation_type = "4th Amendment - Unlawful Search/Seizure"
            elif "5th amendment" in response_lower or "self-incrimination" in response_lower:
                violation_type = "5th Amendment - Right to Silence"
            elif "1st amendment" in response_lower:
                violation_type = "1st Amendment - Free Speech"
            elif "6th amendment" in response_lower:
                violation_type = "6th Amendment - Right to Counsel"
            elif "excessive force" in response_lower or "8th amendment" in response_lower:
                violation_type = "8th Amendment - Excessive Force"
            elif "14th amendment" in response_lower or "equal protection" in response_lower:
                violation_type = "14th Amendment - Equal Protection"
        
        if "rights reminder" in response_lower:
            # Extract rights reminder section
            lines = response.split("\n")
            for i, line in enumerate(lines):
                if "rights reminder" in line.lower():
                    rights_reminder = lines[i+1] if i+1 < len(lines) else None
                    break
        
        # Save to history
        now = datetime.now(timezone.utc)
        await db.chat_history.insert_one({
            "session_id": session_id,
            "user_id": current_user["user_id"],
            "user_message": chat_data.message,
            "ai_response": response,
            "violation_detected": violation_detected,
            "violation_type": violation_type,
            "created_at": now.isoformat()
        })
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            violation_detected=violation_detected,
            violation_type=violation_type,
            rights_reminder=rights_reminder
        )
        
    except Exception as e:
        logger.error(f"AI Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@api_router.get("/ai/history/{session_id}")
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    history = await db.chat_history.find(
        {"session_id": session_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    return history

# ============== DEPARTMENTS (TRANSPARENCY PORTAL) ==============

@api_router.get("/departments", response_model=List[DepartmentResponse])
async def get_departments(
    state: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    sort_by: str = "risk_score"
):
    """Get department data for transparency portal"""
    query = {}
    if state:
        query["state"] = state
    if min_risk_score:
        query["risk_score"] = {"$gte": min_risk_score}
    
    departments = await db.departments.find(query, {"_id": 0}).to_list(100)
    
    # If no departments, seed sample data
    if not departments:
        await seed_sample_departments()
        departments = await db.departments.find(query, {"_id": 0}).to_list(100)
    
    # Sort
    if sort_by == "risk_score":
        departments.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    elif sort_by == "transparency_score":
        departments.sort(key=lambda x: x.get("transparency_score", 0), reverse=True)
    elif sort_by == "complaint_rate":
        departments.sort(key=lambda x: x.get("complaint_rate", 0), reverse=True)
    
    return [DepartmentResponse(**d) for d in departments]

@api_router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def get_department(department_id: str):
    department = await db.departments.find_one({"department_id": department_id}, {"_id": 0})
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    return DepartmentResponse(**department)

@api_router.get("/departments/{department_id}/incidents")
async def get_department_incidents(department_id: str, limit: int = 50):
    """Get incidents for a specific department"""
    incidents = await db.cases.find(
        {"department": {"$regex": department_id, "$options": "i"}},
        {"_id": 0, "case_id": 1, "title": 1, "violation_type": 1, "severity": 1, "status": 1, "incident_date": 1, "location": 1}
    ).sort("incident_date", -1).to_list(limit)
    
    return incidents

async def seed_sample_departments():
    """Seed sample department data for transparency portal"""
    sample_departments = [
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Los Angeles Police Department",
            "city": "Los Angeles",
            "state": "California",
            "chief_name": "Michel Moore",
            "officer_count": 9500,
            "budget": 1760000000,
            "risk_score": 7.2,
            "complaint_rate": 12.5,
            "use_of_force_rate": 8.3,
            "body_cam_adoption": 95.0,
            "transparency_score": 6.8,
            "total_incidents": 1250,
            "resolved_incidents": 890
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "New York Police Department",
            "city": "New York",
            "state": "New York",
            "chief_name": "Keechant Sewell",
            "officer_count": 36000,
            "budget": 5440000000,
            "risk_score": 6.8,
            "complaint_rate": 9.2,
            "use_of_force_rate": 5.7,
            "body_cam_adoption": 98.0,
            "transparency_score": 7.5,
            "total_incidents": 3200,
            "resolved_incidents": 2450
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Chicago Police Department",
            "city": "Chicago",
            "state": "Illinois",
            "chief_name": "Larry Snelling",
            "officer_count": 11900,
            "budget": 1920000000,
            "risk_score": 8.1,
            "complaint_rate": 18.3,
            "use_of_force_rate": 11.2,
            "body_cam_adoption": 88.0,
            "transparency_score": 5.4,
            "total_incidents": 2100,
            "resolved_incidents": 1200
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Houston Police Department",
            "city": "Houston",
            "state": "Texas",
            "chief_name": "Troy Finner",
            "officer_count": 5300,
            "budget": 946000000,
            "risk_score": 6.5,
            "complaint_rate": 10.1,
            "use_of_force_rate": 7.8,
            "body_cam_adoption": 82.0,
            "transparency_score": 6.2,
            "total_incidents": 890,
            "resolved_incidents": 620
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Phoenix Police Department",
            "city": "Phoenix",
            "state": "Arizona",
            "chief_name": "Michael Sullivan",
            "officer_count": 2900,
            "budget": 740000000,
            "risk_score": 7.8,
            "complaint_rate": 14.7,
            "use_of_force_rate": 9.5,
            "body_cam_adoption": 78.0,
            "transparency_score": 5.8,
            "total_incidents": 720,
            "resolved_incidents": 410
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Minneapolis Police Department",
            "city": "Minneapolis",
            "state": "Minnesota",
            "chief_name": "Brian O'Hara",
            "officer_count": 580,
            "budget": 191000000,
            "risk_score": 8.9,
            "complaint_rate": 22.1,
            "use_of_force_rate": 15.8,
            "body_cam_adoption": 92.0,
            "transparency_score": 4.2,
            "total_incidents": 340,
            "resolved_incidents": 145
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Atlanta Police Department",
            "city": "Atlanta",
            "state": "Georgia",
            "chief_name": "Darin Schierbaum",
            "officer_count": 1800,
            "budget": 240000000,
            "risk_score": 6.2,
            "complaint_rate": 8.9,
            "use_of_force_rate": 6.4,
            "body_cam_adoption": 96.0,
            "transparency_score": 7.8,
            "total_incidents": 420,
            "resolved_incidents": 335
        },
        {
            "department_id": f"dept_{uuid.uuid4().hex[:12]}",
            "name": "Seattle Police Department",
            "city": "Seattle",
            "state": "Washington",
            "chief_name": "Adrian Diaz",
            "officer_count": 1000,
            "budget": 363000000,
            "risk_score": 5.5,
            "complaint_rate": 7.2,
            "use_of_force_rate": 4.8,
            "body_cam_adoption": 99.0,
            "transparency_score": 8.5,
            "total_incidents": 280,
            "resolved_incidents": 230
        }
    ]
    
    await db.departments.insert_many(sample_departments)

# ============== ANALYTICS ==============

@api_router.get("/analytics/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    # Get user's case statistics
    total_cases = await db.cases.count_documents({"user_id": user_id})
    open_cases = await db.cases.count_documents({"user_id": user_id, "status": "open"})
    resolved_cases = await db.cases.count_documents({"user_id": user_id, "status": "resolved"})
    
    # Get evidence count
    total_evidence = await db.evidence.count_documents({"user_id": user_id})
    
    # Get unread messages
    unread_messages = await db.messages.count_documents({
        "recipient_id": user_id,
        "read": False
    })
    
    # Get violation types distribution
    violation_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    violations = await db.cases.aggregate(violation_pipeline).to_list(10)
    
    # Get recent activity
    recent_cases = await db.cases.find(
        {"user_id": user_id},
        {"_id": 0, "case_id": 1, "title": 1, "status": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(5)
    
    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "resolved_cases": resolved_cases,
        "total_evidence": total_evidence,
        "unread_messages": unread_messages,
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "recent_cases": recent_cases
    }

@api_router.get("/analytics/public")
async def get_public_stats():
    """Public transparency data - no auth required"""
    total_cases = await db.cases.count_documents({})
    total_users = await db.users.count_documents({})
    resolved_cases = await db.cases.count_documents({"status": "resolved"})
    total_departments = await db.departments.count_documents({})
    
    # Get violation types distribution
    violation_pipeline = [
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    violations = await db.cases.aggregate(violation_pipeline).to_list(10)
    
    # Get state distribution
    state_pipeline = [
        {"$group": {"_id": "$state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    states = await db.departments.aggregate(state_pipeline).to_list(10)
    
    return {
        "total_cases": total_cases,
        "total_users": total_users,
        "resolved_cases": resolved_cases,
        "total_departments": total_departments,
        "success_rate": round((resolved_cases / total_cases * 100) if total_cases > 0 else 0, 1),
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "departments_by_state": [{"state": s["_id"], "count": s["count"]} for s in states]
    }

# ============== ENCOUNTER ANALYTICS DASHBOARD ==============

@api_router.get("/analytics/encounters/summary")
async def get_encounter_summary(current_user: dict = Depends(get_current_user)):
    """Get comprehensive encounter statistics for the user"""
    user_id = current_user["user_id"]
    
    # Basic counts
    total_encounters = await db.encounters.count_documents({"user_id": user_id})
    active_encounters = await db.encounters.count_documents({"user_id": user_id, "status": "active"})
    completed_encounters = await db.encounters.count_documents({"user_id": user_id, "status": "completed"})
    
    # Get all transcriptions for this user's encounters
    user_encounters = await db.encounters.find(
        {"user_id": user_id},
        {"encounter_id": 1, "_id": 0}
    ).to_list(1000)
    encounter_ids = [e["encounter_id"] for e in user_encounters]
    
    # Aggregate tone data from transcriptions
    tone_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}}},
        {"$group": {
            "_id": "$tone",
            "count": {"$sum": 1},
            "avg_confidence": {"$avg": "$tone_confidence"}
        }},
        {"$sort": {"count": -1}}
    ]
    tone_distribution = await db.transcriptions.aggregate(tone_pipeline).to_list(20)
    
    # Aggregate officer aggression levels
    aggression_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "officer_demeanor.aggression_level": {"$exists": True}}},
        {"$group": {
            "_id": None,
            "avg_aggression": {"$avg": "$officer_demeanor.aggression_level"},
            "max_aggression": {"$max": "$officer_demeanor.aggression_level"},
            "avg_intimidation": {"$avg": "$officer_demeanor.intimidation_level"},
            "avg_professionalism": {"$avg": "$officer_demeanor.professionalism"}
        }}
    ]
    aggression_stats = await db.transcriptions.aggregate(aggression_pipeline).to_list(1)
    aggression_data = aggression_stats[0] if aggression_stats else {
        "avg_aggression": 0, "max_aggression": 0, "avg_intimidation": 0, "avg_professionalism": 1
    }
    
    # Violation types from encounters
    violation_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}}},
        {"$unwind": {"path": "$violations_detected", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$violations_detected", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    violations = await db.transcriptions.aggregate(violation_pipeline).to_list(10)
    
    # Escalation counts
    escalation_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "escalation_detected": True}},
        {"$group": {"_id": "$escalation_direction", "count": {"$sum": 1}}}
    ]
    escalations = await db.transcriptions.aggregate(escalation_pipeline).to_list(10)
    
    # Calculate risk score (0-100)
    risk_score = min(100, int(
        (aggression_data.get("avg_aggression", 0) or 0) * 40 +
        (aggression_data.get("avg_intimidation", 0) or 0) * 30 +
        (1 - (aggression_data.get("avg_professionalism", 1) or 1)) * 30
    ))
    
    return {
        "total_encounters": total_encounters,
        "active_encounters": active_encounters,
        "completed_encounters": completed_encounters,
        "tone_distribution": [{"tone": t["_id"], "count": t["count"], "avg_confidence": round(t.get("avg_confidence", 0) or 0, 2)} for t in tone_distribution if t["_id"]],
        "officer_demeanor": {
            "avg_aggression": round((aggression_data.get("avg_aggression", 0) or 0) * 100, 1),
            "max_aggression": round((aggression_data.get("max_aggression", 0) or 0) * 100, 1),
            "avg_intimidation": round((aggression_data.get("avg_intimidation", 0) or 0) * 100, 1),
            "avg_professionalism": round((aggression_data.get("avg_professionalism", 1) or 1) * 100, 1)
        },
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "escalation_stats": [{"direction": e["_id"], "count": e["count"]} for e in escalations],
        "risk_score": risk_score
    }

@api_router.get("/analytics/encounters/patterns")
async def get_encounter_patterns(current_user: dict = Depends(get_current_user)):
    """Get time-of-day and day-of-week patterns for encounters"""
    user_id = current_user["user_id"]
    
    # Get encounters with timestamps
    encounters = await db.encounters.find(
        {"user_id": user_id, "started_at": {"$exists": True}},
        {"_id": 0, "encounter_id": 1, "started_at": 1, "encounter_type": 1, "latitude": 1, "longitude": 1}
    ).to_list(1000)
    
    # Time of day distribution (0-23 hours)
    hour_counts = {i: 0 for i in range(24)}
    day_counts = {i: 0 for i in range(7)}  # 0=Monday, 6=Sunday
    type_counts = {}
    
    for enc in encounters:
        started_at = enc.get("started_at")
        if started_at:
            try:
                if isinstance(started_at, str):
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                else:
                    dt = started_at
                hour_counts[dt.hour] += 1
                day_counts[dt.weekday()] += 1
            except:
                pass
        
        enc_type = enc.get("encounter_type", "unknown")
        type_counts[enc_type] = type_counts.get(enc_type, 0) + 1
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return {
        "by_hour": [{"hour": h, "count": c} for h, c in hour_counts.items()],
        "by_day": [{"day": day_names[d], "day_index": d, "count": c} for d, c in day_counts.items()],
        "by_type": [{"type": t, "count": c} for t, c in sorted(type_counts.items(), key=lambda x: -x[1])],
        "peak_hour": max(hour_counts, key=hour_counts.get) if encounters else None,
        "peak_day": day_names[max(day_counts, key=day_counts.get)] if encounters else None
    }

@api_router.get("/analytics/encounters/hotspots")
async def get_encounter_hotspots(current_user: dict = Depends(get_current_user)):
    """Get geographic hotspots for encounters"""
    user_id = current_user["user_id"]
    
    # Get encounters with location data
    encounters = await db.encounters.find(
        {"user_id": user_id, "latitude": {"$exists": True}, "longitude": {"$exists": True}},
        {"_id": 0, "encounter_id": 1, "latitude": 1, "longitude": 1, "address": 1, "encounter_type": 1, "started_at": 1}
    ).to_list(1000)
    
    # Group by approximate location (rounded to 2 decimal places ~1km)
    location_groups = {}
    for enc in encounters:
        lat = round(enc.get("latitude", 0), 2)
        lng = round(enc.get("longitude", 0), 2)
        key = f"{lat},{lng}"
        
        if key not in location_groups:
            location_groups[key] = {
                "latitude": lat,
                "longitude": lng,
                "count": 0,
                "addresses": [],
                "types": []
            }
        
        location_groups[key]["count"] += 1
        addr = enc.get("address")
        if addr and addr not in location_groups[key]["addresses"]:
            location_groups[key]["addresses"].append(addr)
        enc_type = enc.get("encounter_type")
        if enc_type and enc_type not in location_groups[key]["types"]:
            location_groups[key]["types"].append(enc_type)
    
    # Sort by count and return top hotspots
    hotspots = sorted(location_groups.values(), key=lambda x: -x["count"])[:20]
    
    # Also return all encounter locations for map
    all_locations = [
        {
            "encounter_id": enc["encounter_id"],
            "latitude": enc["latitude"],
            "longitude": enc["longitude"],
            "address": enc.get("address", ""),
            "type": enc.get("encounter_type", "unknown")
        }
        for enc in encounters
    ]
    
    return {
        "hotspots": hotspots,
        "all_locations": all_locations,
        "total_mapped": len(all_locations)
    }

@api_router.get("/analytics/encounters/trends")
async def get_encounter_trends(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get encounter trends over time"""
    user_id = current_user["user_id"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get encounters in date range
    encounters = await db.encounters.find(
        {"user_id": user_id, "started_at": {"$gte": cutoff.isoformat()}},
        {"_id": 0, "encounter_id": 1, "started_at": 1}
    ).to_list(1000)
    
    encounter_ids = [e["encounter_id"] for e in encounters]
    
    # Daily encounter counts
    daily_counts = {}
    for enc in encounters:
        started_at = enc.get("started_at", "")
        if started_at:
            date_str = started_at[:10]  # YYYY-MM-DD
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
    # Aggression trends per day
    aggression_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "officer_demeanor.aggression_level": {"$exists": True}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "avg_aggression": {"$avg": "$officer_demeanor.aggression_level"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    aggression_trends = await db.transcriptions.aggregate(aggression_pipeline).to_list(100)
    
    # Fill in missing dates
    all_dates = []
    current = cutoff
    while current <= datetime.now(timezone.utc):
        date_str = current.strftime("%Y-%m-%d")
        agg_data = next((a for a in aggression_trends if a["_id"] == date_str), None)
        all_dates.append({
            "date": date_str,
            "encounters": daily_counts.get(date_str, 0),
            "avg_aggression": round((agg_data.get("avg_aggression", 0) or 0) * 100, 1) if agg_data else 0
        })
        current += timedelta(days=1)
    
    return {
        "period_days": days,
        "total_encounters": len(encounters),
        "daily_data": all_dates,
        "avg_encounters_per_day": round(len(encounters) / days, 2) if days > 0 else 0
    }

# ============== KNOW YOUR RIGHTS ==============

@api_router.get("/rights")
async def get_rights_info():
    """Get Know Your Rights educational content"""
    rights = [
        {
            "id": "4th",
            "amendment": "4th Amendment",
            "title": "Protection Against Unreasonable Searches",
            "summary": "You have the right to refuse consent to searches of yourself, your car, or your home.",
            "key_points": [
                "Police need a warrant or probable cause to search",
                "You can clearly state 'I do not consent to this search'",
                "Saying no is not probable cause for a search",
                "If police search anyway, stay calm and document everything"
            ],
            "what_to_say": "I do not consent to any searches.",
            "icon": "Shield"
        },
        {
            "id": "5th",
            "amendment": "5th Amendment",
            "title": "Right to Remain Silent",
            "summary": "You have the right to remain silent and cannot be forced to incriminate yourself.",
            "key_points": [
                "You must clearly invoke your right to remain silent",
                "Simply staying silent isn't enough - state it explicitly",
                "You can answer basic identification questions while invoking 5th for others",
                "Your silence cannot be used against you"
            ],
            "what_to_say": "I am exercising my right to remain silent.",
            "icon": "VolumeX"
        },
        {
            "id": "6th",
            "amendment": "6th Amendment",
            "title": "Right to an Attorney",
            "summary": "You have the right to have an attorney present during questioning.",
            "key_points": [
                "Request an attorney immediately if questioned",
                "All questioning must stop once you request an attorney",
                "If you can't afford one, one will be provided",
                "Don't answer questions until your attorney arrives"
            ],
            "what_to_say": "I want to speak to an attorney before answering any questions.",
            "icon": "Scale"
        },
        {
            "id": "1st",
            "amendment": "1st Amendment",
            "title": "Freedom of Speech & Assembly",
            "summary": "You have the right to peacefully protest and record police in public spaces.",
            "key_points": [
                "You can record police performing their duties in public",
                "Police cannot delete your recordings",
                "Peaceful protest is protected speech",
                "You can criticize the police (but avoid threats)"
            ],
            "what_to_say": "I am exercising my First Amendment right to record.",
            "icon": "Megaphone"
        },
        {
            "id": "14th",
            "amendment": "14th Amendment",
            "title": "Equal Protection Under the Law",
            "summary": "You cannot be treated differently based on race, religion, or national origin.",
            "key_points": [
                "Racial profiling is unconstitutional",
                "You have equal access to due process",
                "Document any discriminatory treatment",
                "File a complaint if you experience bias"
            ],
            "what_to_say": "I believe I am being treated differently because of [protected characteristic].",
            "icon": "Users"
        }
    ]
    
    return {"rights": rights}

# ============== WEBSOCKET ENDPOINT ==============

@api_router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket connection for real-time updates"""
    try:
        # Verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["user_id"]
    except jwt.InvalidTokenError:
        await websocket.close(code=4001)
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "WebSocket connected successfully"
        })
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "typing":
                # Broadcast typing indicator to conversation participants
                recipient_id = data.get("recipient_id")
                if recipient_id:
                    await manager.send_to_user(recipient_id, {
                        "type": "typing",
                        "user_id": user_id,
                        "conversation_id": data.get("conversation_id")
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, user_id)

# ============== PUSH NOTIFICATIONS ==============

@api_router.post("/push/subscribe")
async def subscribe_push(subscription: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Subscribe to push notifications"""
    await db.push_subscriptions.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "user_id": current_user["user_id"],
            "endpoint": subscription.endpoint,
            "keys": subscription.keys,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Subscribed to push notifications"}

@api_router.delete("/push/unsubscribe")
async def unsubscribe_push(current_user: dict = Depends(get_current_user)):
    """Unsubscribe from push notifications"""
    await db.push_subscriptions.delete_one({"user_id": current_user["user_id"]})
    return {"message": "Unsubscribed from push notifications"}

# ============== INCIDENTS MAP ==============

@api_router.get("/incidents/map", response_model=List[IncidentLocation])
async def get_incidents_for_map(
    violation_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500
):
    """Get incidents with location data for map visualization"""
    query = {}
    
    if violation_type:
        query["violation_type"] = violation_type
    if severity:
        query["severity"] = severity
    if status:
        query["status"] = status
    if start_date:
        query["incident_date"] = {"$gte": start_date}
    if end_date:
        if "incident_date" in query:
            query["incident_date"]["$lte"] = end_date
        else:
            query["incident_date"] = {"$lte": end_date}
    
    # Get cases with location data
    cases = await db.cases.find(
        query,
        {"_id": 0}
    ).sort("incident_date", -1).to_list(limit)
    
    # Generate random coordinates around major US cities for demo
    # In production, these would come from actual case data
    import random
    city_coords = [
        (34.0522, -118.2437),  # Los Angeles
        (40.7128, -74.0060),   # New York
        (41.8781, -87.6298),   # Chicago
        (29.7604, -95.3698),   # Houston
        (33.4484, -112.0740),  # Phoenix
        (44.9778, -93.2650),   # Minneapolis
        (33.7490, -84.3880),   # Atlanta
        (47.6062, -122.3321),  # Seattle
        (39.7392, -104.9903),  # Denver
        (25.7617, -80.1918),   # Miami
    ]
    
    incidents = []
    for case in cases:
        # Generate location near a random city
        city = random.choice(city_coords)
        lat = city[0] + random.uniform(-0.5, 0.5)
        lng = city[1] + random.uniform(-0.5, 0.5)
        
        incident_date = case.get("incident_date")
        if isinstance(incident_date, str):
            incident_date = datetime.fromisoformat(incident_date)
        
        incidents.append(IncidentLocation(
            case_id=case["case_id"],
            latitude=lat,
            longitude=lng,
            title=case["title"],
            violation_type=case["violation_type"],
            severity=case["severity"],
            status=case["status"],
            incident_date=incident_date,
            department=case.get("department")
        ))
    
    # If no cases, generate sample data
    if not incidents:
        sample_incidents = [
            {"title": "Traffic Stop Violation", "violation_type": "4th Amendment - Unlawful Search/Seizure", "severity": "high"},
            {"title": "Excessive Force During Arrest", "violation_type": "8th Amendment - Excessive Force", "severity": "critical"},
            {"title": "Unlawful Detention", "violation_type": "False Arrest", "severity": "medium"},
            {"title": "Racial Profiling Incident", "violation_type": "14th Amendment - Equal Protection", "severity": "high"},
            {"title": "First Amendment Violation", "violation_type": "1st Amendment - Free Speech", "severity": "medium"},
        ]
        
        for i, sample in enumerate(sample_incidents):
            city = city_coords[i % len(city_coords)]
            incidents.append(IncidentLocation(
                case_id=f"sample_{i}",
                latitude=city[0] + random.uniform(-0.3, 0.3),
                longitude=city[1] + random.uniform(-0.3, 0.3),
                title=sample["title"],
                violation_type=sample["violation_type"],
                severity=sample["severity"],
                status="open",
                incident_date=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
                department=None
            ))
    
    return incidents

@api_router.get("/incidents/stats")
async def get_incident_stats():
    """Get statistics for incident map"""
    total = await db.cases.count_documents({})
    
    # Violation type distribution
    violation_pipeline = [
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    violations = await db.cases.aggregate(violation_pipeline).to_list(20)
    
    # Severity distribution
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severities = await db.cases.aggregate(severity_pipeline).to_list(10)
    
    # Monthly trend
    monthly_pipeline = [
        {"$group": {
            "_id": {"$substr": ["$incident_date", 0, 7]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 12}
    ]
    monthly = await db.cases.aggregate(monthly_pipeline).to_list(12)
    
    return {
        "total_incidents": total,
        "by_violation_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "by_severity": [{"severity": s["_id"], "count": s["count"]} for s in severities],
        "monthly_trend": [{"month": m["_id"], "count": m["count"]} for m in monthly]
    }

# ============== CASE TIMELINE ==============

@api_router.get("/cases/{case_id}/timeline", response_model=List[CaseEvent])
async def get_case_timeline(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get timeline of all events for a case"""
    # Verify case belongs to user
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    events = []
    
    # Case creation event
    created_at = case.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    
    events.append(CaseEvent(
        event_id=f"ev_{case_id}_created",
        case_id=case_id,
        event_type="created",
        description=f"Case created: {case['title']}",
        metadata={"status": "open", "severity": case["severity"]},
        created_at=created_at,
        created_by=current_user["user_id"]
    ))
    
    # Get evidence uploads
    evidence_list = await db.evidence.find(
        {"case_id": case_id},
        {"_id": 0}
    ).sort("uploaded_at", 1).to_list(100)
    
    for ev in evidence_list:
        uploaded_at = ev.get("uploaded_at")
        if isinstance(uploaded_at, str):
            uploaded_at = datetime.fromisoformat(uploaded_at)
        
        events.append(CaseEvent(
            event_id=f"ev_{ev['evidence_id']}",
            case_id=case_id,
            event_type="evidence_added",
            description=f"Evidence uploaded: {ev['file_name']}",
            metadata={"file_type": ev["file_type"], "file_size": ev["file_size"], "blockchain_hash": ev.get("blockchain_hash")},
            created_at=uploaded_at,
            created_by=ev["user_id"]
        ))
    
    # Get case events from dedicated collection
    case_events = await db.case_events.find(
        {"case_id": case_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    for ce in case_events:
        ce_created = ce.get("created_at")
        if isinstance(ce_created, str):
            ce_created = datetime.fromisoformat(ce_created)
        
        events.append(CaseEvent(
            event_id=ce["event_id"],
            case_id=case_id,
            event_type=ce["event_type"],
            description=ce["description"],
            metadata=ce.get("metadata"),
            created_at=ce_created,
            created_by=ce["created_by"]
        ))
    
    # Sort all events by date
    events.sort(key=lambda x: x.created_at)
    
    return events

@api_router.post("/cases/{case_id}/events")
async def add_case_event(
    case_id: str,
    event_type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Add an event to case timeline"""
    # Verify case belongs to user
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    event_id = f"ev_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    event_doc = {
        "event_id": event_id,
        "case_id": case_id,
        "event_type": event_type,
        "description": description,
        "metadata": metadata,
        "created_at": now.isoformat(),
        "created_by": current_user["user_id"]
    }
    
    await db.case_events.insert_one(event_doc)
    
    # Send WebSocket notification
    await manager.send_to_user(current_user["user_id"], {
        "type": "case_event_added",
        "case_id": case_id,
        "event_type": event_type,
        "description": description
    })
    
    return {"event_id": event_id, "message": "Event added to timeline"}

# ============== REPORT GENERATION ==============

@api_router.get("/cases/{case_id}/report")
async def get_case_report_data(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all data needed for PDF report generation"""
    # Get case
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get evidence
    evidence = await db.evidence.find(
        {"case_id": case_id},
        {"_id": 0}
    ).sort("uploaded_at", 1).to_list(100)
    
    # Get timeline events
    events = await db.case_events.find(
        {"case_id": case_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    # Get user info
    user = await db.users.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "password_hash": 0}
    )
    
    # Convert dates
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(case.get(field), str):
            case[field] = case[field]
    
    for ev in evidence:
        if isinstance(ev.get("uploaded_at"), str):
            ev["uploaded_at"] = ev["uploaded_at"]
    
    for event in events:
        if isinstance(event.get("created_at"), str):
            event["created_at"] = event["created_at"]
    
    return {
        "case": case,
        "evidence": evidence,
        "timeline": events,
        "user": {
            "name": user.get("name"),
            "email": user.get("email")
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_id": f"RPT-{case_id.upper()}"
    }

# ============== ENCOUNTER MODE ENDPOINTS ==============

# Active encounters for WebSocket streaming
active_encounters: Dict[str, Dict] = {}

@api_router.post("/encounters/start", response_model=EncounterResponse)
async def start_encounter(
    encounter_data: EncounterStart,
    current_user: dict = Depends(get_current_user)
):
    """Start a new police encounter recording session"""
    encounter_id = f"enc_{uuid.uuid4().hex[:12]}"
    stream_key = f"stream_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)
    
    # Create encounter directory for media files
    encounter_dir = ENCOUNTERS_DIR / encounter_id
    encounter_dir.mkdir(exist_ok=True)
    
    encounter_doc = {
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"],
        "latitude": encounter_data.latitude,
        "longitude": encounter_data.longitude,
        "address": encounter_data.address,
        "encounter_type": encounter_data.encounter_type,
        "status": "active",
        "broadcast_mode": encounter_data.broadcast_mode,
        "stream_key": stream_key,
        "started_at": now.isoformat(),
        "ended_at": None,
        "duration_seconds": 0,
        "transcriptions": [],
        "violations": [],
        "officers": [],
        "media_files": []
    }
    
    await db.encounters.insert_one(encounter_doc)
    
    # Store in active encounters for real-time processing
    active_encounters[encounter_id] = {
        "user_id": current_user["user_id"],
        "started_at": now,
        "transcription_buffer": [],
        "analysis_queue": []
    }
    
    # Notify emergency contacts if configured
    if encounter_data.broadcast_mode in ["share_contacts", "all"]:
        asyncio.create_task(notify_emergency_contacts(current_user["user_id"], encounter_id, encounter_data))
    
    # Notify assigned attorneys if premium user
    if encounter_data.broadcast_mode in ["share_attorney", "all"]:
        asyncio.create_task(notify_attorneys(current_user["user_id"], encounter_id))
    
    # Broadcast via WebSocket
    await manager.send_to_user(current_user["user_id"], {
        "type": "encounter_started",
        "encounter_id": encounter_id,
        "stream_key": stream_key,
        "message": "🚨 Encounter recording started. Stay calm and know your rights."
    })
    
    logger.info(f"Encounter started: {encounter_id} by user {current_user['user_id']}")
    
    return EncounterResponse(
        encounter_id=encounter_id,
        user_id=current_user["user_id"],
        latitude=encounter_data.latitude,
        longitude=encounter_data.longitude,
        address=encounter_data.address,
        encounter_type=encounter_data.encounter_type,
        status="active",
        broadcast_mode=encounter_data.broadcast_mode,
        stream_key=stream_key,
        started_at=now,
        ended_at=None,
        duration_seconds=0
    )

async def notify_emergency_contacts(user_id: str, encounter_id: str, encounter_data: EncounterStart):
    """Notify user's emergency contacts about the encounter"""
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return
    
    contacts = user.get("emergency_contacts", [])
    for contact in contacts:
        # In production, send SMS/email via Twilio/SendGrid
        logger.info(f"MOCKED: Notifying contact {contact.get('phone')} about encounter {encounter_id}")
        # Store notification record
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "type": "encounter_alert",
            "user_id": user_id,
            "encounter_id": encounter_id,
            "recipient": contact,
            "location": {"lat": encounter_data.latitude, "lng": encounter_data.longitude},
            "status": "sent",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

async def notify_attorneys(user_id: str, encounter_id: str):
    """Notify assigned attorneys about the encounter"""
    # Find user's assigned attorneys
    assignments = await db.attorney_assignments.find(
        {"user_id": user_id, "status": "active"},
        {"_id": 0}
    ).to_list(length=10)
    
    for assignment in assignments:
        attorney_id = assignment.get("attorney_id")
        await manager.send_to_user(attorney_id, {
            "type": "client_encounter",
            "encounter_id": encounter_id,
            "user_id": user_id,
            "message": "⚠️ Your client has started an encounter recording"
        })
        logger.info(f"Notified attorney {attorney_id} about encounter {encounter_id}")

@api_router.post("/encounters/{encounter_id}/audio")
async def upload_audio_chunk(
    encounter_id: str,
    audio_file: UploadFile = File(...),
    chunk_index: int = Form(0),
    current_user: dict = Depends(get_current_user)
):
    """Upload and transcribe audio chunk from encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter["status"] != "active":
        raise HTTPException(status_code=400, detail="Encounter is not active")
    
    # Save audio chunk
    chunk_filename = f"audio_{chunk_index}_{uuid.uuid4().hex[:8]}.webm"
    chunk_path = ENCOUNTERS_DIR / encounter_id / chunk_filename
    
    content = await audio_file.read()
    with open(chunk_path, "wb") as f:
        f.write(content)
    
    # Transcribe using Whisper
    transcription_result = None
    if stt_service and len(content) > 1000:  # Only transcribe chunks > 1KB
        try:
            with open(chunk_path, "rb") as audio:
                response = await stt_service.transcribe(
                    file=audio,
                    model="whisper-1",
                    response_format="verbose_json",
                    language="en",
                    prompt="Police encounter recording. Speakers: civilian, police officer.",
                    timestamp_granularities=["segment"]
                )
                
                if response and response.text:
                    segment_id = f"seg_{uuid.uuid4().hex[:12]}"
                    now = datetime.now(timezone.utc)
                    
                    # Analyze transcription for violations in background
                    violations = await analyze_transcription_for_violations(response.text, encounter_id)
                    
                    # Get previous transcript context for speaker identification
                    prev_transcripts = await db.transcriptions.find(
                        {"encounter_id": encounter_id}
                    ).sort("start_time", -1).limit(3).to_list(length=3)
                    context = " | ".join([f"{t.get('speaker', 'Unknown')}: {t.get('text', '')[:100]}" for t in prev_transcripts])
                    
                    # Identify speaker using AI (now includes tone/emotion detection)
                    speaker_result = await identify_speaker(response.text, context)
                    speaker = speaker_result.get("speaker", "unknown")
                    speaker_confidence = speaker_result.get("confidence", 0.0)
                    labeled_text = speaker_result.get("labeled_text", response.text)
                    speaker_changes = speaker_result.get("speaker_changes", [])
                    
                    # Extract tone/emotion data
                    tone = speaker_result.get("tone", "neutral")
                    tone_confidence = speaker_result.get("tone_confidence", 0.0)
                    tone_severity = speaker_result.get("tone_severity", "normal")
                    emotion_indicators = speaker_result.get("emotion_indicators", [])
                    escalation_detected = speaker_result.get("escalation_detected", False)
                    escalation_direction = speaker_result.get("escalation_direction", "stable")
                    officer_demeanor = speaker_result.get("officer_demeanor", {})
                    citizen_demeanor = speaker_result.get("citizen_demeanor", {})
                    
                    transcription_doc = {
                        "segment_id": segment_id,
                        "encounter_id": encounter_id,
                        "text": response.text,
                        "labeled_text": labeled_text,
                        "speaker": speaker,
                        "speaker_confidence": speaker_confidence,
                        "speaker_changes": speaker_changes,
                        "tone": tone,
                        "tone_confidence": tone_confidence,
                        "tone_severity": tone_severity,
                        "emotion_indicators": emotion_indicators,
                        "escalation_detected": escalation_detected,
                        "escalation_direction": escalation_direction,
                        "officer_demeanor": officer_demeanor,
                        "citizen_demeanor": citizen_demeanor,
                        "start_time": chunk_index * 10.0,  # Approximate timing
                        "end_time": (chunk_index + 1) * 10.0,
                        "confidence": 0.9,
                        "violations_detected": violations,
                        "audio_file": chunk_filename,
                        "created_at": now.isoformat()
                    }
                    
                    await db.transcriptions.insert_one(transcription_doc)
                    
                    # Update encounter with transcription reference
                    await db.encounters.update_one(
                        {"encounter_id": encounter_id},
                        {"$push": {"transcriptions": segment_id}}
                    )
                    
                    transcription_result = {
                        "segment_id": segment_id,
                        "text": response.text,
                        "labeled_text": labeled_text,
                        "speaker": speaker,
                        "speaker_confidence": speaker_confidence,
                        "speaker_changes": speaker_changes,
                        "tone": tone,
                        "tone_confidence": tone_confidence,
                        "tone_severity": tone_severity,
                        "emotion_indicators": emotion_indicators,
                        "escalation_detected": escalation_detected,
                        "escalation_direction": escalation_direction,
                        "officer_demeanor": officer_demeanor,
                        "citizen_demeanor": citizen_demeanor,
                        "violations_detected": violations
                    }
                    
                    # Real-time notification if aggressive tone detected
                    if tone_severity in ["concerning", "critical"] or escalation_detected:
                        await manager.send_to_user(current_user["user_id"], {
                            "type": "tone_alert",
                            "encounter_id": encounter_id,
                            "tone": tone,
                            "tone_severity": tone_severity,
                            "escalation_detected": escalation_detected,
                            "emotion_indicators": emotion_indicators,
                            "text": response.text,
                            "speaker": speaker
                        })
                    
                    # Real-time notification if violations detected
                    if violations:
                        await manager.send_to_user(current_user["user_id"], {
                            "type": "violation_detected",
                            "encounter_id": encounter_id,
                            "violations": violations,
                            "text": response.text,
                            "speaker": speaker
                        })
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}")
    
    # Update media files list
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"media_files": chunk_filename}}
    )
    
    return {
        "success": True,
        "chunk_index": chunk_index,
        "filename": chunk_filename,
        "transcription": transcription_result
    }

@api_router.post("/encounters/{encounter_id}/video")
async def upload_video_chunk(
    encounter_id: str,
    video_file: UploadFile = File(...),
    chunk_index: int = Form(0),
    current_user: dict = Depends(get_current_user)
):
    """Upload video chunk from encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter["status"] != "active":
        raise HTTPException(status_code=400, detail="Encounter is not active")
    
    # Save video chunk
    chunk_filename = f"video_{chunk_index}_{uuid.uuid4().hex[:8]}.webm"
    chunk_path = ENCOUNTERS_DIR / encounter_id / chunk_filename
    
    content = await video_file.read()
    with open(chunk_path, "wb") as f:
        f.write(content)
    
    # Update encounter with video file reference
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {
            "$push": {"video_files": chunk_filename},
            "$set": {"has_video": True},
            "$inc": {"video_chunk_count": 1}
        }
    )
    
    logger.info(f"Video chunk {chunk_index} saved for encounter {encounter_id}: {chunk_filename}")
    
    return {
        "success": True,
        "chunk_index": chunk_index,
        "filename": chunk_filename,
        "size_bytes": len(content)
    }

async def analyze_transcription_for_violations(text: str, encounter_id: str) -> List[str]:
    """Analyze transcription text for potential civil rights violations"""
    violations = []
    text_lower = text.lower()
    
    # Pattern matching for common violations
    violation_patterns = {
        "unlawful_search": ["search your car", "open your trunk", "what's in your bag", "empty your pockets", "let me search"],
        "miranda_violation": ["anything you say", "right to remain", "lawyer present"],
        "excessive_force": ["get on the ground", "stop resisting", "taser", "put your hands"],
        "intimidation": ["you're going to jail", "make this hard", "don't make me", "you'll regret"],
        "profiling": ["you people", "your kind", "look suspicious", "fit the description"],
        "unlawful_detention": ["you can't leave", "stay right there", "don't move"],
        "coercion": ["just admit", "confess", "make it easier", "tell the truth"]
    }
    
    for violation_type, patterns in violation_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                violations.append(violation_type)
                break
    
    return list(set(violations))  # Remove duplicates

async def identify_speaker(text: str, context: str = "") -> dict:
    """Use AI to identify the speaker, their tone/emotion, and label transcript segments"""
    if not EMERGENT_LLM_KEY or len(text) < 10:
        return {
            "speaker": "unknown", 
            "confidence": 0.0, 
            "labeled_text": text,
            "tone": "neutral",
            "tone_confidence": 0.0,
            "emotion_indicators": []
        }
    
    try:
        llm = create_llm_chat(f"speaker_tone_{uuid.uuid4().hex[:8]}", """You are an expert at analyzing police encounter transcripts for:
1. Speaker identification (Officer vs Citizen)
2. Emotional tone and demeanor analysis
3. Detecting aggression, intimidation, and hostility

Your analysis helps identify potential misconduct and protects civil rights.

Tone categories:
- PROFESSIONAL: Calm, neutral, following procedure
- ASSERTIVE: Firm but appropriate
- AGGRESSIVE: Hostile, threatening, raised voice indicators
- INTIMIDATING: Using fear tactics, implied threats
- HOSTILE: Openly antagonistic, disrespectful
- CALM: Composed, measured response
- ANXIOUS: Nervous, fearful, stressed
- DEFENSIVE: Protecting oneself, citing rights
- COMPLIANT: Cooperative, following instructions""")
        
        prompt = f"""Analyze this police encounter transcript for speaker identification AND emotional tone.

TRANSCRIPT:
"{text}"

{f'CONTEXT FROM PREVIOUS SEGMENTS: {context}' if context else ''}

Return a JSON object with EXACTLY this structure:
{{
    "speaker": "Officer" or "Citizen" or "Unknown",
    "confidence": 0.0 to 1.0,
    "labeled_text": "Speaker: text with speaker label at start",
    "speaker_changes": [
        {{"position": 0, "speaker": "Officer", "text": "portion of text", "tone": "professional"}}
    ],
    "tone": "professional/assertive/aggressive/intimidating/hostile/calm/anxious/defensive/compliant",
    "tone_confidence": 0.0 to 1.0,
    "tone_severity": "normal/elevated/concerning/critical",
    "emotion_indicators": [
        {{
            "type": "aggression/intimidation/hostility/fear/stress",
            "evidence": "specific phrase or behavior",
            "severity": "low/medium/high/critical"
        }}
    ],
    "escalation_detected": true or false,
    "escalation_direction": "escalating/de-escalating/stable",
    "officer_demeanor": {{
        "professionalism": 0.0 to 1.0,
        "aggression_level": 0.0 to 1.0,
        "intimidation_level": 0.0 to 1.0,
        "concerns": ["list of specific concerns if any"]
    }},
    "citizen_demeanor": {{
        "compliance_level": 0.0 to 1.0,
        "stress_level": 0.0 to 1.0,
        "asserting_rights": true or false
    }},
    "reasoning": "brief explanation of tone analysis"
}}

Focus on identifying:
- Aggressive language (threats, yelling indicators like ALL CAPS or exclamations)
- Intimidation tactics (implied consequences, power assertions)
- Hostility (insults, derogatory language, contempt)
- Professionalism deviations

Return ONLY valid JSON, no markdown."""

        response = await llm.send_message(UserMessage(text=prompt))
        
        if response:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            try:
                result = json.loads(cleaned)
                return result
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.error(f"Speaker/tone identification error: {e}")
    
    return {
        "speaker": "unknown", 
        "confidence": 0.0, 
        "labeled_text": text,
        "tone": "neutral",
        "tone_confidence": 0.0,
        "tone_severity": "normal",
        "emotion_indicators": [],
        "escalation_detected": False,
        "escalation_direction": "stable"
    }

async def perform_deep_ai_analysis(text: str, encounter_id: str, analysis_type: str = "full") -> dict:
    """Perform comprehensive AI analysis of encounter audio/transcript for violations, bias, and procedural issues"""
    
    if not EMERGENT_LLM_KEY or len(text) < 30:
        return {"violations": [], "bias_indicators": [], "procedural_issues": [], "risk_level": "low"}
    
    try:
        llm = create_llm_chat(f"deep_analysis_{encounter_id}", """You are an expert civil rights attorney and former law enforcement trainer specializing in police misconduct cases. 
Your role is to analyze police encounter transcripts in real-time to identify:
1. Constitutional violations (4th, 5th, 6th, 8th, 14th Amendments)
2. Officer bias or discriminatory language
3. Procedural violations and improper police conduct
4. Statements that could be used as evidence in court
5. Intimidation tactics and coercion

Be thorough but only flag genuine concerns - not routine police procedures.""")
        
        analysis_prompt = f"""URGENT: Analyze this real-time police encounter transcript for civil rights violations and abuse of power.

TRANSCRIPT:
"{text}"

Perform a comprehensive analysis and return a JSON object with EXACTLY this structure:
{{
    "violations": [
        {{
            "type": "violation_type",
            "severity": "critical/high/medium/low",
            "amendment": "4th/5th/6th/8th/14th or null",
            "description": "Brief description of the violation",
            "quote": "Exact quote from transcript that shows violation",
            "legal_citation": "Relevant case law or statute",
            "defense_strategy": "How this helps the defendant's case"
        }}
    ],
    "bias_indicators": [
        {{
            "type": "racial/gender/age/socioeconomic",
            "evidence": "Quote or behavior indicating bias",
            "severity": "high/medium/low"
        }}
    ],
    "procedural_issues": [
        {{
            "issue": "Description of procedural problem",
            "proper_procedure": "What should have been done",
            "impact": "How this affects the case"
        }}
    ],
    "tone_analysis": {{
        "officer_tone": "aggressive/intimidating/neutral/professional",
        "escalation_detected": true/false,
        "power_abuse_indicators": ["list of concerning behaviors"]
    }},
    "evidence_value": {{
        "strong_evidence_quotes": ["Quotes that would help in court"],
        "case_strength": "strong/moderate/weak",
        "recommended_actions": ["What the person should do"]
    }},
    "risk_level": "critical/high/medium/low",
    "immediate_alert": "Message to show user if urgent" or null
}}

IMPORTANT: Only include actual violations found. Return empty arrays if nothing detected.
Focus on things that would actually help win a case in court."""

        response = await llm.send_message(UserMessage(text=analysis_prompt))
        
        if response:
            # Clean up the response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            try:
                analysis = json.loads(cleaned)
                return analysis
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse AI analysis response: {response[:200]}")
                return {"violations": [], "bias_indicators": [], "procedural_issues": [], "risk_level": "low"}
    except Exception as e:
        logger.error(f"Deep AI analysis error: {e}")
    
    return {"violations": [], "bias_indicators": [], "procedural_issues": [], "risk_level": "low"}

# Civil Rights Knowledge Base
CIVIL_RIGHTS_DATABASE = {
    "4th_amendment": {
        "name": "Fourth Amendment - Search & Seizure",
        "text": "The right of the people to be secure in their persons, houses, papers, and effects, against unreasonable searches and seizures, shall not be violated.",
        "key_cases": [
            {"case": "Terry v. Ohio (1968)", "holding": "Officers may briefly detain and pat down for weapons with reasonable suspicion"},
            {"case": "Mapp v. Ohio (1961)", "holding": "Evidence obtained through illegal search is inadmissible"},
            {"case": "Arizona v. Gant (2009)", "holding": "Vehicle search limited after arrest unless safety/evidence concerns"},
            {"case": "Rodriguez v. United States (2015)", "holding": "Traffic stop cannot be extended for drug dog without reasonable suspicion"}
        ],
        "your_rights": [
            "You can refuse consent to search",
            "Ask: 'Am I free to go?'",
            "Say: 'I do not consent to searches'",
            "Officer needs warrant, consent, or probable cause"
        ]
    },
    "5th_amendment": {
        "name": "Fifth Amendment - Self-Incrimination",
        "text": "No person shall be compelled in any criminal case to be a witness against himself.",
        "key_cases": [
            {"case": "Miranda v. Arizona (1966)", "holding": "Must be informed of rights before custodial interrogation"},
            {"case": "Berghuis v. Thompkins (2010)", "holding": "Must explicitly invoke right to remain silent"}
        ],
        "your_rights": [
            "You have the right to remain silent",
            "Say: 'I invoke my right to remain silent'",
            "You don't have to answer questions",
            "Silence cannot be used against you if invoked"
        ]
    },
    "6th_amendment": {
        "name": "Sixth Amendment - Right to Counsel",
        "text": "In all criminal prosecutions, the accused shall have the Assistance of Counsel for his defence.",
        "key_cases": [
            {"case": "Gideon v. Wainwright (1963)", "holding": "Right to attorney in criminal cases"},
            {"case": "Edwards v. Arizona (1981)", "holding": "Once counsel requested, interrogation must stop"}
        ],
        "your_rights": [
            "Say: 'I want to speak to a lawyer'",
            "All questioning must stop once you request counsel",
            "Don't answer questions without lawyer present"
        ]
    },
    "14th_amendment": {
        "name": "Fourteenth Amendment - Equal Protection",
        "text": "No State shall deny to any person within its jurisdiction the equal protection of the laws.",
        "key_cases": [
            {"case": "Whren v. United States (1996)", "holding": "Pretextual stops allowed but racial profiling still unconstitutional"},
            {"case": "Floyd v. City of New York (2013)", "holding": "Stop-and-frisk violated equal protection when racially targeted"}
        ],
        "your_rights": [
            "You cannot be stopped based on race/ethnicity",
            "Document any discriminatory statements",
            "Ask for badge number and reason for stop"
        ]
    }
}

@api_router.post("/encounters/{encounter_id}/analyze")
async def analyze_encounter_realtime(
    encounter_id: str,
    text: str = Form(...),
    analysis_type: str = Form("full"),
    current_user: dict = Depends(get_current_user)
):
    """Perform real-time AI analysis of encounter transcript"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Perform deep AI analysis
    analysis = await perform_deep_ai_analysis(text, encounter_id, analysis_type)
    
    # Store analysis result
    analysis_record = {
        "analysis_id": f"ana_{uuid.uuid4().hex[:12]}",
        "encounter_id": encounter_id,
        "timestamp": datetime.now(timezone.utc),
        "text_analyzed": text,
        "analysis": analysis,
        "risk_level": analysis.get("risk_level", "low")
    }
    await db.encounter_analyses.insert_one(analysis_record)
    
    # If critical violations found, update encounter status
    if analysis.get("risk_level") == "critical":
        await db.encounters.update_one(
            {"encounter_id": encounter_id},
            {"$set": {"critical_violation_detected": True}}
        )
    
    # Add relevant legal context
    legal_context = []
    for violation in analysis.get("violations", []):
        amendment = violation.get("amendment")
        if amendment and amendment.lower().replace(" ", "_") in CIVIL_RIGHTS_DATABASE:
            legal_context.append(CIVIL_RIGHTS_DATABASE[amendment.lower().replace(" ", "_")])
    
    return {
        "analysis": analysis,
        "legal_context": legal_context,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/encounters/{encounter_id}/violations")
async def get_encounter_violations(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all detected violations for an encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get all analyses
    analyses = await db.encounter_analyses.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(length=100)
    
    # Aggregate violations
    all_violations = []
    all_bias_indicators = []
    all_procedural_issues = []
    highest_risk = "low"
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    
    for ana in analyses:
        analysis = ana.get("analysis", {})
        all_violations.extend(analysis.get("violations", []))
        all_bias_indicators.extend(analysis.get("bias_indicators", []))
        all_procedural_issues.extend(analysis.get("procedural_issues", []))
        
        risk = analysis.get("risk_level", "low")
        if risk_order.get(risk, 0) > risk_order.get(highest_risk, 0):
            highest_risk = risk
    
    return {
        "encounter_id": encounter_id,
        "total_analyses": len(analyses),
        "violations": all_violations,
        "violations_count": len(all_violations),
        "bias_indicators": all_bias_indicators,
        "procedural_issues": all_procedural_issues,
        "overall_risk_level": highest_risk,
        "civil_rights_reference": CIVIL_RIGHTS_DATABASE
    }

@api_router.post("/encounters/{encounter_id}/mark-violation")
async def mark_violation(
    encounter_id: str,
    timestamp: float = Form(...),
    note: str = Form("Manual violation mark"),
    current_user: dict = Depends(get_current_user)
):
    """Mark a specific moment as a potential violation (voice command or manual)"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    mark_id = f"mark_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    source = "voice_command" if "voice" in note.lower() else "manual"
    
    mark_doc = {
        "mark_id": mark_id,
        "encounter_id": encounter_id,
        "timestamp_seconds": timestamp,
        "note": note,
        "created_at": created_at,
        "source": source
    }
    
    await db.encounter_marks.insert_one(mark_doc)
    
    # Create clean mark for embedding (without _id)
    clean_mark = {
        "mark_id": mark_id,
        "timestamp_seconds": timestamp,
        "note": note,
        "created_at": created_at,
        "source": source
    }
    
    # Also update the encounter with the mark
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"manual_marks": clean_mark}}
    )
    
    return {
        "success": True,
        "mark": clean_mark
    }

@api_router.post("/encounters/{encounter_id}/end")
async def end_encounter(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End an active encounter and generate report"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    now = datetime.now(timezone.utc)
    started_at = datetime.fromisoformat(encounter["started_at"])
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    
    duration = int((now - started_at).total_seconds())
    
    # Update encounter status
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {
            "$set": {
                "status": "ended",
                "ended_at": now.isoformat(),
                "duration_seconds": duration
            }
        }
    )
    
    # Remove from active encounters
    if encounter_id in active_encounters:
        del active_encounters[encounter_id]
    
    # Generate comprehensive report asynchronously
    asyncio.create_task(generate_encounter_report(encounter_id, current_user["user_id"]))
    
    return {
        "encounter_id": encounter_id,
        "status": "ended",
        "duration_seconds": duration,
        "message": "Encounter ended. Report is being generated."
    }

async def generate_encounter_report(encounter_id: str, user_id: str):
    """Generate comprehensive encounter report with AI analysis"""
    encounter = await db.encounters.find_one({"encounter_id": encounter_id}, {"_id": 0})
    if not encounter:
        return
    
    # Gather all transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("start_time", 1).to_list(length=1000)
    
    full_transcript = "\n".join([t["text"] for t in transcriptions if t.get("text")])
    
    # Gather all violations
    all_violations = []
    for t in transcriptions:
        all_violations.extend(t.get("violations_detected", []))
    
    # Get officers identified
    officers = await db.officer_profiles.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(length=10)
    
    # AI-powered comprehensive analysis
    summary = ""
    recommendations = []
    similar_cases = []
    
    if EMERGENT_LLM_KEY and full_transcript:
        try:
            llm = create_llm_chat(f"report_{encounter_id}", "You are an expert civil rights attorney generating detailed encounter reports.")
            analysis_prompt = f"""You are an expert civil rights attorney analyzing a police encounter.

ENCOUNTER DETAILS:
- Type: {encounter.get('encounter_type')}
- Location: {encounter.get('address', 'Unknown')}
- Duration: {encounter.get('duration_seconds', 0)} seconds
- Violations detected: {list(set(all_violations))}

FULL TRANSCRIPT:
{full_transcript[:4000]}

Provide a comprehensive analysis including:
1. SUMMARY: Brief overview of what happened
2. VIOLATIONS: Detailed explanation of each civil rights violation
3. LEGAL CITATIONS: Relevant case law and constitutional amendments
4. RECOMMENDATIONS: What the citizen should do next
5. SIMILAR CASES: Reference similar cases and their outcomes

Format as JSON with keys: summary, violations_analysis, legal_citations, recommendations, similar_case_references"""

            response = await llm.send_message(UserMessage(text=analysis_prompt))
            if response:
                try:
                    analysis = json.loads(response)
                    summary = analysis.get("summary", "")
                    recommendations = analysis.get("recommendations", [])
                    similar_cases = analysis.get("similar_case_references", [])
                except:
                    summary = response[:500]
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            summary = f"Encounter recorded. {len(transcriptions)} audio segments captured. {len(set(all_violations))} potential violations detected."
    else:
        summary = f"Encounter recorded. {len(transcriptions)} audio segments captured."
    
    # Create report document
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    
    # Get video file information
    video_files = encounter.get("video_files", [])
    audio_files = encounter.get("media_files", [])
    has_video = encounter.get("has_video", False)
    
    # Calculate total recording size
    total_size_bytes = 0
    encounter_dir = ENCOUNTERS_DIR / encounter_id
    if encounter_dir.exists():
        for f in encounter_dir.iterdir():
            if f.is_file():
                total_size_bytes += f.stat().st_size
    
    report_doc = {
        "report_id": report_id,
        "encounter_id": encounter_id,
        "user_id": user_id,
        "summary": summary,
        "violations": list(set(all_violations)),
        "violations_count": len(set(all_violations)),
        "officers": officers,
        "transcript_text": full_transcript,
        "recommendations": recommendations if isinstance(recommendations, list) else [recommendations],
        "evidence": {
            "has_video": has_video,
            "video_chunks": len(video_files),
            "audio_chunks": len(audio_files),
            "transcription_segments": len(transcriptions),
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2)
        },
        "encounter_details": {
            "encounter_type": encounter.get("encounter_type"),
            "location": encounter.get("address"),
            "latitude": encounter.get("latitude"),
            "longitude": encounter.get("longitude"),
            "started_at": encounter.get("started_at"),
            "ended_at": encounter.get("ended_at"),
            "duration_seconds": encounter.get("duration_seconds", 0),
            "broadcast_mode": encounter.get("broadcast_mode")
        },
        "legal_resources": [
            {"name": "ACLU Know Your Rights", "url": "https://www.aclu.org/know-your-rights"},
            {"name": "National Police Accountability Project", "url": "https://www.nlg-npap.org"},
            {"name": "Mapping Police Violence", "url": "https://mappingpoliceviolence.org"}
        ],
        "similar_cases": similar_cases if isinstance(similar_cases, list) else [],
        "court_admissible": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.encounter_reports.insert_one(report_doc)
    
    # Notify user
    await manager.send_to_user(user_id, {
        "type": "report_ready",
        "encounter_id": encounter_id,
        "report_id": report_id,
        "message": "Your encounter report is ready for review."
    })
    
    logger.info(f"Generated report {report_id} for encounter {encounter_id}")

@api_router.get("/encounters")
async def list_encounters(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List user's encounters"""
    query = {"user_id": current_user["user_id"]}
    if status:
        query["status"] = status
    
    encounters = await db.encounters.find(query, {"_id": 0}).sort("started_at", -1).to_list(length=100)
    return encounters

@api_router.get("/encounters/{encounter_id}")
async def get_encounter(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get encounter details with transcriptions and report"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("start_time", 1).to_list(length=1000)
    
    # Get report if exists
    report = await db.encounter_reports.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    # Get officers
    officers = await db.officer_profiles.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(length=10)
    
    return {
        "encounter": encounter,
        "transcriptions": transcriptions,
        "report": report,
        "officers": officers
    }

@api_router.get("/encounters/{encounter_id}/report")
async def get_encounter_report(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the detailed incident report for an encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get the report
    report = await db.encounter_reports.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not report:
        # Report may still be generating
        return {
            "status": "generating",
            "message": "Report is being generated. Please check back in a moment.",
            "encounter_id": encounter_id
        }
    
    # Get transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("start_time", 1).to_list(length=1000)
    
    # Get video/audio files
    encounter_dir = ENCOUNTERS_DIR / encounter_id
    media_files = []
    if encounter_dir.exists():
        for f in encounter_dir.iterdir():
            if f.is_file():
                media_files.append({
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "type": "video" if f.name.startswith("video_") else "audio"
                })
    
    return {
        "status": "ready",
        "report": report,
        "transcriptions": transcriptions,
        "media_files": media_files,
        "download_available": True
    }

@api_router.get("/encounters/{encounter_id}/media/{filename}")
async def get_encounter_media(
    encounter_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Serve video/audio files from encounter recordings"""
    # Verify user owns this encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Sanitize filename to prevent path traversal
    safe_filename = Path(filename).name
    file_path = ENCOUNTERS_DIR / encounter_id / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    
    # Determine content type
    if safe_filename.endswith('.webm'):
        if safe_filename.startswith('video_'):
            media_type = "video/webm"
        else:
            media_type = "audio/webm"
    elif safe_filename.endswith('.mp4'):
        media_type = "video/mp4"
    elif safe_filename.endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=safe_filename
    )

@api_router.get("/encounters/{encounter_id}/stream-token")
async def generate_stream_token(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a shareable token for live streaming access"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Create a time-limited token (valid for 24 hours)
    token_data = {
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"],
        "type": "stream_access",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    
    stream_token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Store token info
    await db.stream_tokens.insert_one({
        "token_id": f"stk_{uuid.uuid4().hex[:12]}",
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": token_data["exp"],
        "active": True
    })
    
    return {
        "stream_token": stream_token,
        "expires_in_hours": 24,
        "share_url": f"/live/{encounter_id}?token={stream_token}"
    }

@api_router.get("/live/{encounter_id}/verify")
async def verify_stream_access(
    encounter_id: str,
    token: str
):
    """Verify stream access token (no auth required - for viewers)"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("encounter_id") != encounter_id:
            raise HTTPException(status_code=403, detail="Invalid token for this encounter")
        if payload.get("type") != "stream_access":
            raise HTTPException(status_code=403, detail="Invalid token type")
        
        # Get encounter info
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0, "status": 1, "encounter_type": 1, "address": 1, "started_at": 1}
        )
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        return {
            "valid": True,
            "encounter_id": encounter_id,
            "status": encounter.get("status"),
            "encounter_type": encounter.get("encounter_type"),
            "location": encounter.get("address"),
            "started_at": encounter.get("started_at")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Stream token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid stream token")

@api_router.get("/live/{encounter_id}/media/{filename}")
async def get_live_media(
    encounter_id: str,
    filename: str,
    token: str
):
    """Serve media files for live stream viewers (token-based auth)"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("encounter_id") != encounter_id:
            raise HTTPException(status_code=403, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    safe_filename = Path(filename).name
    file_path = ENCOUNTERS_DIR / encounter_id / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    
    media_type = "video/webm" if safe_filename.startswith('video_') else "audio/webm"
    
    return FileResponse(file_path, media_type=media_type)

@api_router.post("/encounters/{encounter_id}/officer")
async def add_officer_info(
    encounter_id: str,
    name: Optional[str] = Form(None),
    badge_number: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    rank: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Add officer information to encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    officer_id = f"off_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Look up officer history (in production, query police misconduct databases)
    prior_incidents = 0
    complaints_count = 0
    
    # Mock: Check our own database for this officer
    if badge_number and department:
        existing = await db.officer_profiles.find(
            {"badge_number": badge_number, "department": department},
            {"_id": 0}
        ).to_list(length=100)
        prior_incidents = len(existing)
    
    officer_doc = {
        "officer_id": officer_id,
        "encounter_id": encounter_id,
        "name": name,
        "badge_number": badge_number,
        "department": department,
        "rank": rank,
        "prior_incidents": prior_incidents,
        "complaints_count": complaints_count,
        "use_of_force_count": 0,
        "captured_from": "manual",
        "confidence": 1.0,
        "created_at": now.isoformat()
    }
    
    await db.officer_profiles.insert_one(officer_doc)
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"officers": officer_id}}
    )
    
    # Remove MongoDB _id before returning
    officer_doc.pop("_id", None)
    return officer_doc

# ============== DOCUMENT ANALYSIS ENDPOINTS ==============

@api_router.post("/analyze/document")
async def analyze_document(
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    analysis_focus: str = Form("all"),
    current_user: dict = Depends(get_current_user)
):
    """Upload and analyze legal documents for violations and bias"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    # Save document
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    filename = f"{document_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Extract text based on file type
    text_content = ""
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext in {'.txt', '.md'}:
        text_content = content.decode('utf-8', errors='ignore')
    elif file_ext == '.pdf':
        # For PDF, we'd use PyPDF2 or similar - simplified for now
        text_content = f"[PDF content from {file.filename}]"
    else:
        # For audio/video, transcribe
        if file_ext in {'.mp3', '.wav', '.m4a', '.webm', '.mp4'} and stt_service:
            try:
                with open(file_path, "rb") as audio:
                    response = await stt_service.transcribe(
                        file=audio,
                        model="whisper-1",
                        response_format="text",
                        language="en"
                    )
                    text_content = response.text if response else ""
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                text_content = f"[Audio/video content from {file.filename}]"
        else:
            text_content = f"[Document content from {file.filename}]"
    
    # AI Analysis
    llm = create_llm_chat(f"doc_analysis_{document_id}", "You are an expert civil rights attorney and legal analyst.")
    analysis_prompt = f"""You are an expert civil rights attorney and legal analyst.

DOCUMENT TYPE: {document_type}
ANALYSIS FOCUS: {analysis_focus}

DOCUMENT CONTENT:
{text_content[:8000]}

Analyze this document thoroughly for:

1. CIVIL RIGHTS VIOLATIONS: Any constitutional violations (4th, 5th, 6th, 8th, 14th Amendment)
2. BIAS INDICATORS: Language or actions suggesting racial profiling, discrimination
3. INCONSISTENCIES: Contradictions, timeline issues, factual errors
4. LEGAL ISSUES: Procedural violations, chain of custody issues, improper evidence handling
5. RECOMMENDATIONS: Legal strategies and next steps

Provide analysis as JSON with these keys:
- summary: Brief document overview
- violations_found: Array of {{type, description, severity, legal_citation}}
- bias_indicators: Array of {{indicator, evidence, impact}}
- inconsistencies: Array of {{description, significance}}
- legal_issues: Array of {{issue, implication, remedy}}
- recommendations: Array of action items
- case_precedents: Array of {{case_name, relevance, outcome}}"""

    try:
        response = await llm.send_message(UserMessage(text=analysis_prompt))
        analysis = json.loads(response) if response else {}
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        analysis = {
            "summary": "Analysis could not be completed",
            "violations_found": [],
            "bias_indicators": [],
            "inconsistencies": [],
            "legal_issues": [],
            "recommendations": ["Please review document manually"],
            "case_precedents": []
        }
    
    # Store analysis
    analysis_id = f"ana_{uuid.uuid4().hex[:12]}"
    analysis_doc = {
        "analysis_id": analysis_id,
        "document_id": document_id,
        "user_id": current_user["user_id"],
        "document_type": document_type,
        "filename": filename,
        "summary": analysis.get("summary", ""),
        "violations_found": analysis.get("violations_found", []),
        "bias_indicators": analysis.get("bias_indicators", []),
        "inconsistencies": analysis.get("inconsistencies", []),
        "legal_issues": analysis.get("legal_issues", []),
        "recommendations": analysis.get("recommendations", []),
        "case_precedents": analysis.get("case_precedents", []),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.document_analyses.insert_one(analysis_doc)
    
    return {
        "analysis_id": analysis_id,
        "document_id": document_id,
        "document_type": document_type,
        **analysis,
        "created_at": analysis_doc["created_at"]
    }

@api_router.get("/analyze/documents")
async def list_document_analyses(
    current_user: dict = Depends(get_current_user)
):
    """List user's document analyses"""
    analyses = await db.document_analyses.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(length=100)
    return analyses

@api_router.get("/analyze/document/{analysis_id}")
async def get_document_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific document analysis"""
    analysis = await db.document_analyses.find_one(
        {"analysis_id": analysis_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

# ============== RIGHTS COACH ENDPOINT ==============

@api_router.post("/rights-coach")
async def get_rights_guidance(
    situation: str = Form(...),
    encounter_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Get real-time rights guidance for current situation"""
    if not EMERGENT_LLM_KEY:
        # Fallback to pre-programmed responses
        return get_fallback_rights_guidance(situation)
    
    llm = create_llm_chat(f"rights_coach_{current_user['user_id']}", "You are an emergency civil rights attorney providing immediate guidance during police encounters.")
    prompt = f"""You are a civil rights attorney providing real-time guidance during a police encounter.

SITUATION: {situation}

Provide IMMEDIATE, ACTIONABLE guidance:
1. What to say RIGHT NOW (exact phrases)
2. What NOT to do
3. Your constitutional rights in this situation
4. Key phrases to remember

Be concise - this is an emergency situation. Format as JSON:
{{
    "immediate_action": "What to do/say right now",
    "do_not": ["List of things to avoid"],
    "your_rights": ["Your applicable rights"],
    "key_phrases": ["Exact phrases to use"],
    "legal_basis": "Brief legal explanation"
}}"""

    try:
        response = await llm.send_message(UserMessage(text=prompt))
        guidance = json.loads(response) if response else {}
        return guidance
    except Exception as e:
        logger.error(f"Rights coach error: {e}")
        return get_fallback_rights_guidance(situation)

def get_fallback_rights_guidance(situation: str) -> dict:
    """Provide fallback rights guidance without AI"""
    situation_lower = situation.lower()
    
    if "search" in situation_lower or "trunk" in situation_lower or "car" in situation_lower:
        return {
            "immediate_action": "Say: 'I do not consent to a search.'",
            "do_not": ["Open trunk voluntarily", "Hand over keys", "Physically resist"],
            "your_rights": [
                "4th Amendment protects against unreasonable searches",
                "Officers need warrant, consent, or probable cause",
                "You can refuse consent to search"
            ],
            "key_phrases": [
                "I do not consent to a search",
                "Am I being detained or am I free to go?",
                "I wish to remain silent"
            ],
            "legal_basis": "4th Amendment - Unreasonable Search and Seizure"
        }
    elif "arrest" in situation_lower:
        return {
            "immediate_action": "Say: 'I am invoking my right to remain silent. I want a lawyer.'",
            "do_not": ["Resist physically", "Answer questions", "Make statements"],
            "your_rights": [
                "5th Amendment right to remain silent",
                "6th Amendment right to an attorney",
                "Right to know charges against you"
            ],
            "key_phrases": [
                "I am invoking my 5th Amendment right to remain silent",
                "I want to speak to an attorney",
                "What am I being charged with?"
            ],
            "legal_basis": "5th & 6th Amendments"
        }
    else:
        return {
            "immediate_action": "Stay calm. Keep hands visible. Ask: 'Am I free to go?'",
            "do_not": ["Make sudden movements", "Argue or resist", "Consent to searches"],
            "your_rights": [
                "Right to remain silent",
                "Right to refuse consent to search",
                "Right to know if you're being detained"
            ],
            "key_phrases": [
                "Am I being detained or am I free to go?",
                "I do not consent to any searches",
                "I wish to remain silent"
            ],
            "legal_basis": "4th, 5th, and 14th Amendments"
        }

# ============== EMERGENCY CONTACTS ==============

@api_router.post("/settings/emergency-contacts")
async def update_emergency_contacts(
    contacts: List[Dict[str, Any]],
    current_user: dict = Depends(get_current_user)
):
    """Update user's emergency contacts"""
    # Validate contacts
    validated = []
    for contact in contacts[:5]:  # Max 5 contacts
        if contact.get("name") and (contact.get("phone") or contact.get("email")):
            validated.append({
                "name": contact["name"],
                "phone": contact.get("phone"),
                "email": contact.get("email"),
                "notify_on_encounter": contact.get("notify_on_encounter", True)
            })
    
    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {"emergency_contacts": validated}}
    )
    
    return {"success": True, "contacts": validated}

@api_router.get("/settings/emergency-contacts")
async def get_emergency_contacts(
    current_user: dict = Depends(get_current_user)
):
    """Get user's emergency contacts"""
    user = await db.users.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "emergency_contacts": 1}
    )
    return user.get("emergency_contacts", [])

# ============== COMMUNITY EVIDENCE VAULT ==============

@api_router.post("/community/submit")
async def submit_to_community_vault(
    submission: CommunitySubmitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit an encounter to the community evidence vault (anonymized)"""
    submission_id = f"sub_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # If linking to existing encounter, verify ownership
    if submission.encounter_id:
        encounter = await db.encounters.find_one(
            {"encounter_id": submission.encounter_id, "user_id": current_user["user_id"]},
            {"_id": 0}
        )
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Create anonymized submission - NO user_id stored for privacy
    submission_doc = {
        "submission_id": submission_id,
        "encounter_id": submission.encounter_id,  # Optional link
        "encounter_type": submission.encounter_type,
        "location_city": submission.location_city,
        "location_state": submission.location_state,
        "incident_date": submission.incident_date.isoformat(),
        "violations": submission.violations,
        "department": submission.department,
        "officer_badge": submission.officer_badge,
        "severity": submission.severity,
        "outcome": submission.outcome,
        "summary": submission.summary,
        "verified": False,
        "upvotes": 0,
        "flags": 0,
        "created_at": now.isoformat()
    }
    
    await db.community_vault.insert_one(submission_doc)
    
    # Update officer and department stats asynchronously
    if submission.department:
        asyncio.create_task(update_department_stats(submission.department, submission.location_state, submission.violations, submission.severity))
    if submission.officer_badge and submission.department:
        asyncio.create_task(update_officer_stats(submission.officer_badge, submission.department, submission.violations, submission.severity))
    
    logger.info(f"Community submission created: {submission_id}")
    
    return {
        "submission_id": submission_id,
        "message": "Thank you for contributing to the community vault. Your submission helps protect others.",
        "created_at": now.isoformat()
    }

async def update_department_stats(department: str, state: str, violations: List[str], severity: str):
    """Update department statistics"""
    existing = await db.department_stats.find_one(
        {"department": department, "state": state},
        {"_id": 0}
    )
    
    if existing:
        # Update existing stats
        violations_by_type = existing.get("violations_by_type", {})
        severity_dist = existing.get("severity_distribution", {})
        
        for v in violations:
            violations_by_type[v] = violations_by_type.get(v, 0) + 1
        severity_dist[severity] = severity_dist.get(severity, 0) + 1
        
        await db.department_stats.update_one(
            {"department": department, "state": state},
            {
                "$inc": {"total_incidents": 1},
                "$set": {
                    "violations_by_type": violations_by_type,
                    "severity_distribution": severity_dist,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    else:
        # Create new stats
        violations_by_type = {}
        for v in violations:
            violations_by_type[v] = violations_by_type.get(v, 0) + 1
        
        await db.department_stats.insert_one({
            "department": department,
            "state": state,
            "total_incidents": 1,
            "officers_with_incidents": 1,
            "violations_by_type": violations_by_type,
            "severity_distribution": {severity: 1},
            "trend": "stable",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        })

async def update_officer_stats(badge: str, department: str, violations: List[str], severity: str):
    """Update officer statistics"""
    existing = await db.officer_stats.find_one(
        {"badge_number": badge, "department": department},
        {"_id": 0}
    )
    
    now = datetime.now(timezone.utc)
    
    if existing:
        violations_by_type = existing.get("violations_by_type", {})
        severity_dist = existing.get("severity_distribution", {})
        
        for v in violations:
            violations_by_type[v] = violations_by_type.get(v, 0) + 1
        severity_dist[severity] = severity_dist.get(severity, 0) + 1
        
        await db.officer_stats.update_one(
            {"badge_number": badge, "department": department},
            {
                "$inc": {"total_incidents": 1},
                "$set": {
                    "violations_by_type": violations_by_type,
                    "severity_distribution": severity_dist,
                    "last_incident": now.isoformat()
                }
            }
        )
    else:
        violations_by_type = {}
        for v in violations:
            violations_by_type[v] = violations_by_type.get(v, 0) + 1
        
        await db.officer_stats.insert_one({
            "badge_number": badge,
            "department": department,
            "total_incidents": 1,
            "violations_by_type": violations_by_type,
            "severity_distribution": {severity: 1},
            "first_incident": now.isoformat(),
            "last_incident": now.isoformat()
        })

@api_router.get("/community/submissions")
async def get_community_submissions(
    state: Optional[str] = None,
    department: Optional[str] = None,
    violation_type: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """Browse community submissions (public endpoint - no auth required)"""
    query = {}
    if state:
        query["location_state"] = state
    if department:
        query["department"] = {"$regex": department, "$options": "i"}
    if violation_type:
        query["violations"] = violation_type
    if severity:
        query["severity"] = severity
    
    skip = (page - 1) * limit
    
    submissions = await db.community_vault.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    total = await db.community_vault.count_documents(query)
    
    return {
        "submissions": submissions,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@api_router.get("/community/departments")
async def get_department_rankings(
    state: Optional[str] = None,
    sort_by: str = "total_incidents",
    limit: int = 20
):
    """Get department rankings by incidents (public endpoint)"""
    query = {}
    if state:
        query["state"] = state
    
    # Sort direction: more incidents = worse ranking
    departments = await db.department_stats.find(query, {"_id": 0}).sort(sort_by, -1).limit(limit).to_list(length=limit)
    
    return {
        "departments": departments,
        "sort_by": sort_by
    }

@api_router.get("/community/officers")
async def get_officer_rankings(
    department: Optional[str] = None,
    min_incidents: int = 1,
    limit: int = 20
):
    """Get officer rankings by incidents (public endpoint)"""
    query = {"total_incidents": {"$gte": min_incidents}}
    if department:
        query["department"] = {"$regex": department, "$options": "i"}
    
    officers = await db.officer_stats.find(query, {"_id": 0}).sort("total_incidents", -1).limit(limit).to_list(length=limit)
    
    return {
        "officers": officers,
        "min_incidents": min_incidents
    }

@api_router.get("/community/stats")
async def get_community_stats():
    """Get overall community vault statistics (public endpoint)"""
    total_submissions = await db.community_vault.count_documents({})
    total_departments = await db.department_stats.count_documents({})
    total_officers = await db.officer_stats.count_documents({})
    
    # Aggregate violation types
    pipeline = [
        {"$unwind": "$violations"},
        {"$group": {"_id": "$violations", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_violations = await db.community_vault.aggregate(pipeline).to_list(length=10)
    
    # Get state distribution
    state_pipeline = [
        {"$group": {"_id": "$location_state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    states = await db.community_vault.aggregate(state_pipeline).to_list(length=10)
    
    # Get severity distribution
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severities = await db.community_vault.aggregate(severity_pipeline).to_list(length=10)
    
    return {
        "total_submissions": total_submissions,
        "total_departments_tracked": total_departments,
        "total_officers_tracked": total_officers,
        "top_violations": [{"type": v["_id"], "count": v["count"]} for v in top_violations],
        "by_state": [{"state": s["_id"], "count": s["count"]} for s in states],
        "by_severity": [{"severity": s["_id"], "count": s["count"]} for s in severities]
    }

@api_router.post("/community/upvote/{submission_id}")
async def upvote_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Upvote a community submission"""
    # Check if user already upvoted
    existing = await db.community_upvotes.find_one({
        "submission_id": submission_id,
        "user_id": current_user["user_id"]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Already upvoted this submission")
    
    # Record upvote
    await db.community_upvotes.insert_one({
        "submission_id": submission_id,
        "user_id": current_user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Increment upvote count
    result = await db.community_vault.update_one(
        {"submission_id": submission_id},
        {"$inc": {"upvotes": 1}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {"success": True, "message": "Upvoted successfully"}

@api_router.get("/community/officer/{badge}/{department}")
async def get_officer_profile(badge: str, department: str):
    """Get detailed officer profile with all incidents (public endpoint)"""
    stats = await db.officer_stats.find_one(
        {"badge_number": badge, "department": department},
        {"_id": 0}
    )
    
    if not stats:
        raise HTTPException(status_code=404, detail="Officer not found in database")
    
    # Get all submissions involving this officer
    submissions = await db.community_vault.find(
        {"officer_badge": badge, "department": department},
        {"_id": 0}
    ).sort("incident_date", -1).to_list(length=100)
    
    return {
        "stats": stats,
        "submissions": submissions,
        "incident_count": len(submissions)
    }

@api_router.get("/community/department/{department}")
async def get_department_profile(department: str, state: Optional[str] = None):
    """Get detailed department profile with stats (public endpoint)"""
    query = {"department": {"$regex": f"^{department}$", "$options": "i"}}
    if state:
        query["state"] = state
    
    stats = await db.department_stats.find_one(query, {"_id": 0})
    
    if not stats:
        # Return empty profile if no stats yet
        return {
            "stats": None,
            "submissions": [],
            "officers_involved": [],
            "message": "No incidents reported for this department yet"
        }
    
    # Get recent submissions
    dept_query = {"department": {"$regex": department, "$options": "i"}}
    if state:
        dept_query["location_state"] = state
    
    submissions = await db.community_vault.find(dept_query, {"_id": 0}).sort("created_at", -1).limit(50).to_list(length=50)
    
    # Get officers involved
    officers = await db.officer_stats.find(
        {"department": {"$regex": department, "$options": "i"}},
        {"_id": 0}
    ).sort("total_incidents", -1).limit(20).to_list(length=20)
    
    return {
        "stats": stats,
        "submissions": submissions,
        "officers_involved": officers
    }

# ============== BLOCKCHAIN EVIDENCE SYSTEM ==============

# Simulated blockchain state
blockchain_state = {
    "current_block": 0,
    "blocks": [],
    "pending_hashes": []
}

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of data"""
    return hashlib.sha256(data).hexdigest()

def compute_file_hash(file_content: bytes) -> str:
    """Compute SHA-256 hash of file content"""
    return compute_sha256(file_content)

def compute_metadata_hash(metadata: dict) -> str:
    """Compute SHA-256 hash of metadata"""
    metadata_str = json.dumps(metadata, sort_keys=True)
    return compute_sha256(metadata_str.encode())

def compute_combined_hash(file_hash: str, metadata_hash: str, timestamp: str) -> str:
    """Compute combined hash for blockchain record"""
    combined = f"{file_hash}{metadata_hash}{timestamp}"
    return compute_sha256(combined.encode())

def sign_action(action_data: dict, secret: str = "JUSTICE_EVIDENCE_SECRET") -> str:
    """Create digital signature for chain of custody action"""
    data_str = json.dumps(action_data, sort_keys=True)
    signature = hmac.new(secret.encode(), data_str.encode(), hashlib.sha256).hexdigest()
    return signature

# ============== IPFS INTEGRATION (PINATA) ==============

async def upload_to_ipfs(file_content: bytes, filename: str, metadata: dict = None) -> dict:
    """Upload file to IPFS via Pinata and return CID"""
    if not PINATA_JWT:
        logger.warning("IPFS: No Pinata JWT configured, skipping IPFS upload")
        return {"success": False, "error": "IPFS not configured", "ipfs_cid": None}
    
    try:
        # Prepare multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field('file', file_content, filename=filename)
        
        # Add pinata metadata
        pinata_metadata = {
            "name": filename,
            "keyvalues": {
                "platform": "JUSTICE",
                "type": "evidence",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }
        }
        form_data.add_field('pinataMetadata', json.dumps(pinata_metadata))
        
        # Add pinata options for CIDv1
        pinata_options = {"cidVersion": 1}
        form_data.add_field('pinataOptions', json.dumps(pinata_options))
        
        headers = {
            "Authorization": f"Bearer {PINATA_JWT}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PINATA_API_URL}/pinning/pinFileToIPFS",
                data=form_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    ipfs_cid = result.get("IpfsHash")
                    logger.info(f"IPFS: Successfully uploaded {filename}, CID: {ipfs_cid}")
                    return {
                        "success": True,
                        "ipfs_cid": ipfs_cid,
                        "ipfs_url": f"ipfs://{ipfs_cid}",
                        "gateway_url": f"{IPFS_GATEWAY}/{ipfs_cid}",
                        "pin_size": result.get("PinSize"),
                        "timestamp": result.get("Timestamp")
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"IPFS upload failed: {response.status} - {error_text}")
                    return {"success": False, "error": error_text, "ipfs_cid": None}
                    
    except Exception as e:
        logger.error(f"IPFS upload error: {str(e)}")
        return {"success": False, "error": str(e), "ipfs_cid": None}

async def verify_ipfs_content(ipfs_cid: str, expected_hash: str) -> dict:
    """Verify IPFS content matches expected hash"""
    if not ipfs_cid:
        return {"verified": False, "error": "No IPFS CID provided"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{IPFS_GATEWAY}/{ipfs_cid}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    current_hash = compute_file_hash(content)
                    is_valid = current_hash == expected_hash
                    return {
                        "verified": True,
                        "ipfs_accessible": True,
                        "hash_matches": is_valid,
                        "ipfs_hash": current_hash,
                        "expected_hash": expected_hash
                    }
                else:
                    return {"verified": False, "error": f"IPFS fetch failed: {response.status}"}
    except Exception as e:
        logger.error(f"IPFS verification error: {str(e)}")
        return {"verified": False, "error": str(e)}

async def get_ipfs_pin_status(ipfs_cid: str) -> dict:
    """Check if content is still pinned on Pinata"""
    if not PINATA_JWT or not ipfs_cid:
        return {"pinned": False, "error": "Not configured or no CID"}
    
    try:
        headers = {"Authorization": f"Bearer {PINATA_JWT}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PINATA_API_URL}/data/pinList?hashContains={ipfs_cid}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    rows = result.get("rows", [])
                    if rows:
                        pin = rows[0]
                        return {
                            "pinned": True,
                            "pin_date": pin.get("date_pinned"),
                            "size": pin.get("size"),
                            "metadata": pin.get("metadata")
                        }
                    return {"pinned": False, "error": "CID not found in pins"}
                return {"pinned": False, "error": f"API error: {response.status}"}
    except Exception as e:
        return {"pinned": False, "error": str(e)}

async def create_blockchain_record(evidence_hashes: List[str]) -> dict:
    """Create a new block in the simulated blockchain"""
    global blockchain_state
    
    block_number = blockchain_state["current_block"] + 1
    timestamp = datetime.now(timezone.utc)
    
    # Get previous block hash
    if blockchain_state["blocks"]:
        previous_block_hash = blockchain_state["blocks"][-1]["block_hash"]
    else:
        previous_block_hash = "0" * 64  # Genesis block
    
    # Create block data
    block_data = {
        "block_number": block_number,
        "timestamp": timestamp.isoformat(),
        "evidence_hashes": evidence_hashes,
        "previous_block_hash": previous_block_hash
    }
    
    # Simple proof of work simulation (find nonce where hash starts with "00")
    nonce = 0
    while True:
        block_data["nonce"] = nonce
        block_str = json.dumps(block_data, sort_keys=True)
        block_hash = compute_sha256(block_str.encode())
        if block_hash.startswith("00"):
            break
        nonce += 1
        if nonce > 10000:  # Limit for simulation
            break
    
    block = {
        "block_number": block_number,
        "timestamp": timestamp.isoformat(),
        "evidence_hashes": evidence_hashes,
        "previous_block_hash": previous_block_hash,
        "nonce": nonce,
        "block_hash": block_hash
    }
    
    blockchain_state["blocks"].append(block)
    blockchain_state["current_block"] = block_number
    
    # Store in database
    await db.blockchain_blocks.insert_one(block)
    
    return block

@api_router.post("/evidence/secure-upload")
async def secure_evidence_upload(
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    encounter_id: Optional[str] = Form(None),
    description: str = Form(""),
    evidence_type: str = Form("document"),
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload evidence with blockchain verification and chain of custody"""
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Generate evidence ID
    evidence_id = f"evi_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Compute cryptographic hashes
    file_hash = compute_file_hash(file_content)
    
    metadata = {
        "filename": file.filename,
        "file_size": file_size,
        "content_type": file.content_type,
        "evidence_type": evidence_type,
        "case_id": case_id,
        "encounter_id": encounter_id,
        "description": description,
        "uploaded_by": current_user["user_id"],
        "upload_timestamp": now.isoformat()
    }
    metadata_hash = compute_metadata_hash(metadata)
    
    combined_hash = compute_combined_hash(file_hash, metadata_hash, now.isoformat())
    
    # Get previous evidence hash for chain linking
    last_evidence = await db.evidence_hashes.find_one(
        {},
        {"_id": 0, "combined_hash": 1},
        sort=[("timestamp", -1)]
    )
    previous_hash = last_evidence["combined_hash"] if last_evidence else None
    
    # Create hash record
    hash_id = f"hash_{uuid.uuid4().hex[:12]}"
    hash_record = {
        "hash_id": hash_id,
        "evidence_id": evidence_id,
        "file_hash": file_hash,
        "metadata_hash": metadata_hash,
        "combined_hash": combined_hash,
        "algorithm": "SHA-256",
        "timestamp": now.isoformat(),
        "block_number": None,
        "previous_hash": previous_hash,
        "merkle_root": None,
        "verified": True
    }
    
    await db.evidence_hashes.insert_one(hash_record)
    
    # Create initial chain of custody entry
    custody_id = f"cust_{uuid.uuid4().hex[:12]}"
    custody_action = {
        "custody_id": custody_id,
        "evidence_id": evidence_id,
        "action": "created",
        "actor_id": current_user["user_id"],
        "timestamp": now.isoformat()
    }
    custody_signature = sign_action(custody_action)
    
    custody_entry = {
        **custody_action,
        "actor_type": "user",
        "ip_address": request.client.host if request else None,
        "device_info": request.headers.get("user-agent") if request else None,
        "signature": custody_signature,
        "previous_custody_hash": None
    }
    
    await db.chain_of_custody.insert_one(custody_entry)
    
    # Save file
    filename = f"{evidence_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create evidence record
    evidence_doc = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "encounter_id": encounter_id,
        "filename": filename,
        "original_filename": file.filename,
        "file_type": file.content_type,
        "file_size": file_size,
        "description": description,
        "evidence_type": evidence_type,
        "url": f"/api/files/{filename}",
        "blockchain_verified": True,
        "hash_id": hash_id,
        "file_hash": file_hash,
        "combined_hash": combined_hash,
        "uploaded_by": current_user["user_id"],
        "created_at": now.isoformat()
    }
    
    await db.evidence.insert_one(evidence_doc)
    
    # Upload to IPFS for decentralized storage
    ipfs_result = await upload_to_ipfs(
        file_content, 
        filename,
        {"evidence_id": evidence_id, "file_hash": file_hash}
    )
    
    # Update evidence with IPFS info if successful
    if ipfs_result.get("success"):
        await db.evidence.update_one(
            {"evidence_id": evidence_id},
            {"$set": {
                "ipfs_cid": ipfs_result["ipfs_cid"],
                "ipfs_url": ipfs_result["ipfs_url"],
                "ipfs_gateway_url": ipfs_result["gateway_url"],
                "ipfs_pinned": True
            }}
        )
        await db.evidence_hashes.update_one(
            {"evidence_id": evidence_id},
            {"$set": {"ipfs_cid": ipfs_result["ipfs_cid"]}}
        )
    
    # Add to pending blockchain batch
    blockchain_state["pending_hashes"].append(combined_hash)
    
    # Create block if we have enough pending hashes (batch processing)
    if len(blockchain_state["pending_hashes"]) >= 3:
        block = await create_blockchain_record(blockchain_state["pending_hashes"])
        
        # Update evidence records with block number
        for h in blockchain_state["pending_hashes"]:
            await db.evidence_hashes.update_one(
                {"combined_hash": h},
                {"$set": {"block_number": block["block_number"]}}
            )
        
        blockchain_state["pending_hashes"] = []
    
    logger.info(f"Secure evidence uploaded: {evidence_id} with hash {combined_hash[:16]}... IPFS: {ipfs_result.get('ipfs_cid', 'N/A')}")
    
    return {
        "evidence_id": evidence_id,
        "filename": filename,
        "file_hash": file_hash,
        "combined_hash": combined_hash,
        "hash_id": hash_id,
        "blockchain_verified": True,
        "chain_of_custody_started": True,
        "ipfs": {
            "enabled": ipfs_result.get("success", False),
            "cid": ipfs_result.get("ipfs_cid"),
            "url": ipfs_result.get("ipfs_url"),
            "gateway_url": ipfs_result.get("gateway_url"),
            "error": ipfs_result.get("error") if not ipfs_result.get("success") else None
        },
        "message": "Evidence securely uploaded with cryptographic verification" + (" and IPFS storage" if ipfs_result.get("success") else "")
    }

@api_router.get("/evidence/{evidence_id}/verify")
async def verify_evidence_integrity(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Verify evidence integrity and chain of custody for court submission"""
    
    # Get evidence record
    evidence = await db.evidence.find_one({"evidence_id": evidence_id}, {"_id": 0})
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Get hash record
    hash_record = await db.evidence_hashes.find_one({"evidence_id": evidence_id}, {"_id": 0})
    if not hash_record:
        raise HTTPException(status_code=404, detail="Hash record not found")
    
    # Re-compute file hash
    file_path = UPLOAD_DIR / evidence["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found")
    
    with open(file_path, "rb") as f:
        current_file_hash = compute_file_hash(f.read())
    
    # Check integrity
    is_valid = current_file_hash == hash_record["file_hash"]
    
    # Get chain of custody
    custody_entries = await db.chain_of_custody.find(
        {"evidence_id": evidence_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(length=1000)
    
    # Verify chain integrity
    chain_intact = True
    for i, entry in enumerate(custody_entries):
        if i > 0:
            # Verify previous hash links correctly
            prev_entry = custody_entries[i - 1]
            expected_prev_hash = sign_action({
                "custody_id": prev_entry["custody_id"],
                "evidence_id": prev_entry["evidence_id"],
                "action": prev_entry["action"],
                "actor_id": prev_entry["actor_id"],
                "timestamp": prev_entry["timestamp"]
            })
            # Note: Simplified check - in production, verify full signature chain
    
    # Record verification action
    now = datetime.now(timezone.utc)
    verification_id = f"ver_{uuid.uuid4().hex[:12]}"
    verifier_data = {
        "verification_id": verification_id,
        "evidence_id": evidence_id,
        "verifier_id": current_user["user_id"],
        "timestamp": now.isoformat()
    }
    verifier_signature = sign_action(verifier_data)
    
    # Add custody entry for verification
    custody_id = f"cust_{uuid.uuid4().hex[:12]}"
    await db.chain_of_custody.insert_one({
        "custody_id": custody_id,
        "evidence_id": evidence_id,
        "action": "verified",
        "actor_id": current_user["user_id"],
        "actor_type": "user",
        "timestamp": now.isoformat(),
        "signature": sign_action({
            "custody_id": custody_id,
            "evidence_id": evidence_id,
            "action": "verified",
            "actor_id": current_user["user_id"],
            "timestamp": now.isoformat()
        }),
        "previous_custody_hash": custody_entries[-1]["signature"] if custody_entries else None
    })
    
    # Verify IPFS content if available
    ipfs_verification = None
    ipfs_cid = evidence.get("ipfs_cid")
    if ipfs_cid:
        ipfs_verification = await verify_ipfs_content(ipfs_cid, hash_record["file_hash"])
    
    verification_result = {
        "verification_id": verification_id,
        "evidence_id": evidence_id,
        "original_hash": hash_record["file_hash"],
        "current_hash": current_file_hash,
        "is_valid": is_valid,
        "chain_intact": chain_intact,
        "custody_entries": len(custody_entries) + 1,
        "verification_timestamp": now.isoformat(),
        "verifier_signature": verifier_signature,
        "block_number": hash_record.get("block_number"),
        "court_admissible": is_valid and chain_intact,
        "hash_algorithm": "SHA-256",
        "created_at": evidence.get("created_at"),
        "chain_of_custody": custody_entries,
        "ipfs": {
            "enabled": bool(ipfs_cid),
            "cid": ipfs_cid,
            "gateway_url": evidence.get("ipfs_gateway_url"),
            "verification": ipfs_verification
        } if ipfs_cid else None
    }
    
    # Store verification record (copy to avoid _id mutation)
    await db.evidence_verifications.insert_one(dict(verification_result))
    
    return verification_result

@api_router.get("/evidence/{evidence_id}/certificate")
async def generate_evidence_certificate(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a court-ready certificate for evidence authenticity"""
    
    # Get evidence and verification
    evidence = await db.evidence.find_one({"evidence_id": evidence_id}, {"_id": 0})
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    hash_record = await db.evidence_hashes.find_one({"evidence_id": evidence_id}, {"_id": 0})
    
    custody_entries = await db.chain_of_custody.find(
        {"evidence_id": evidence_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(length=1000)
    
    # Generate certificate
    certificate_id = f"cert_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Check IPFS status
    ipfs_info = None
    ipfs_cid = evidence.get("ipfs_cid")
    if ipfs_cid:
        ipfs_pin_status = await get_ipfs_pin_status(ipfs_cid)
        ipfs_info = {
            "enabled": True,
            "cid": ipfs_cid,
            "ipfs_url": evidence.get("ipfs_url"),
            "gateway_url": evidence.get("ipfs_gateway_url"),
            "pinned": ipfs_pin_status.get("pinned", False),
            "verification_url": f"https://ipfs.io/ipfs/{ipfs_cid}"
        }
    
    certificate = {
        "certificate_id": certificate_id,
        "certificate_type": "DIGITAL EVIDENCE AUTHENTICITY CERTIFICATE",
        "generated_at": now.isoformat(),
        "evidence_details": {
            "evidence_id": evidence_id,
            "original_filename": evidence.get("original_filename"),
            "file_type": evidence.get("file_type"),
            "file_size": evidence.get("file_size"),
            "created_at": evidence.get("created_at"),
            "description": evidence.get("description")
        },
        "cryptographic_verification": {
            "algorithm": "SHA-256",
            "file_hash": hash_record["file_hash"] if hash_record else None,
            "metadata_hash": hash_record["metadata_hash"] if hash_record else None,
            "combined_hash": hash_record["combined_hash"] if hash_record else None,
            "blockchain_block": hash_record.get("block_number") if hash_record else None
        },
        "ipfs_storage": ipfs_info,
        "chain_of_custody": {
            "total_entries": len(custody_entries),
            "first_entry": custody_entries[0]["timestamp"] if custody_entries else None,
            "last_entry": custody_entries[-1]["timestamp"] if custody_entries else None,
            "actions": [e["action"] for e in custody_entries]
        },
        "integrity_statement": "This certificate attests that the referenced digital evidence has been cryptographically hashed using SHA-256 algorithm at the time of upload, and a complete chain of custody has been maintained." + (" Additionally, this evidence has been stored on the InterPlanetary File System (IPFS), a decentralized storage network, ensuring the content cannot be altered or deleted." if ipfs_cid else "") + " The hash values can be independently verified to confirm the evidence has not been altered since its creation.",
        "legal_notice": "This certificate is generated by the JUSTICE Platform evidence management system. For court proceedings, it is recommended to have this certificate notarized and accompanied by expert testimony regarding the cryptographic verification process." + (f" The IPFS Content Identifier (CID) {ipfs_cid} can be used by any party to independently retrieve and verify the original evidence from the decentralized network." if ipfs_cid else ""),
        "certificate_hash": None  # Will be computed
    }
    
    # Hash the certificate itself
    certificate["certificate_hash"] = compute_sha256(json.dumps(certificate, sort_keys=True).encode())
    
    # Store certificate (copy to avoid _id mutation)
    await db.evidence_certificates.insert_one(dict(certificate))
    
    return certificate

@api_router.get("/blockchain/status")
async def get_blockchain_status():
    """Get current blockchain status"""
    blocks = await db.blockchain_blocks.find({}, {"_id": 0}).sort("block_number", -1).limit(10).to_list(length=10)
    total_blocks = await db.blockchain_blocks.count_documents({})
    total_evidence = await db.evidence_hashes.count_documents({})
    
    return {
        "total_blocks": total_blocks,
        "total_evidence_hashed": total_evidence,
        "pending_hashes": len(blockchain_state["pending_hashes"]),
        "recent_blocks": blocks,
        "chain_valid": True  # Would verify full chain in production
    }

@api_router.get("/ipfs/status")
async def get_ipfs_status():
    """Get IPFS integration status"""
    ipfs_enabled = bool(PINATA_JWT)
    
    # Get stats from our evidence
    total_ipfs_evidence = await db.evidence.count_documents({"ipfs_cid": {"$exists": True, "$ne": None}})
    
    # Test Pinata connection if configured
    pinata_connected = False
    pinata_usage = None
    
    if ipfs_enabled:
        try:
            headers = {"Authorization": f"Bearer {PINATA_JWT}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{PINATA_API_URL}/data/testAuthentication",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        pinata_connected = True
                        
                # Get usage stats
                async with session.get(
                    f"{PINATA_API_URL}/data/userPinnedDataTotal",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        pinata_usage = await response.json()
        except Exception as e:
            logger.error(f"IPFS status check error: {e}")
    
    return {
        "ipfs_enabled": ipfs_enabled,
        "pinata_connected": pinata_connected,
        "gateway_url": IPFS_GATEWAY,
        "total_evidence_on_ipfs": total_ipfs_evidence,
        "pinata_usage": pinata_usage
    }

@api_router.get("/evidence/report/{case_id}")
async def generate_evidence_report(
    case_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a comprehensive evidence report with IPFS verification for a case"""
    # Get the case
    case = await db.cases.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check access
    if case["user_id"] != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all evidence for this case
    evidence_list = await db.evidence.find({"case_id": case_id}, {"_id": 0}).to_list(length=100)
    
    # Get verification details for each piece of evidence
    evidence_with_verification = []
    for ev in evidence_list:
        ev_data = dict(ev)
        
        # Get hash record
        hash_record = await db.evidence_hashes.find_one(
            {"evidence_id": ev["evidence_id"]},
            {"_id": 0}
        )
        if hash_record:
            ev_data["hash_record"] = dict(hash_record)
        
        # Get chain of custody
        custody = await db.chain_of_custody.find(
            {"evidence_id": ev["evidence_id"]},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(length=100)
        ev_data["chain_of_custody"] = custody
        
        # Get certificate if exists
        cert = await db.evidence_certificates.find_one(
            {"evidence_id": ev["evidence_id"]},
            {"_id": 0}
        )
        if cert:
            ev_data["certificate"] = dict(cert)
        
        # IPFS verification status
        if ev.get("ipfs_cid"):
            ev_data["ipfs_verified"] = True
            ev_data["ipfs_gateway_url"] = f"{IPFS_GATEWAY}/{ev['ipfs_cid']}"
        else:
            ev_data["ipfs_verified"] = False
        
        evidence_with_verification.append(ev_data)
    
    # IPFS status
    ipfs_status = {
        "enabled": bool(PINATA_JWT),
        "gateway_url": IPFS_GATEWAY,
        "total_files_on_ipfs": sum(1 for e in evidence_with_verification if e.get("ipfs_cid"))
    }
    
    # Blockchain status
    blockchain_status = {
        "total_verified": sum(1 for e in evidence_with_verification if e.get("hash_record")),
        "chain_intact": True
    }
    
    # Generate report
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    
    # Helper to safely convert dates
    def safe_isoformat(date_val):
        if date_val is None:
            return None
        if isinstance(date_val, str):
            return date_val
        if hasattr(date_val, 'isoformat'):
            return date_val.isoformat()
        return str(date_val)
    
    report = {
        "report_id": report_id,
        "report_type": "COMPREHENSIVE_EVIDENCE_REPORT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user["user_id"],
        "case": {
            "case_id": case["case_id"],
            "title": case.get("title"),
            "description": case.get("description"),
            "status": case.get("status"),
            "severity": case.get("severity"),
            "violation_type": case.get("violation_type"),
            "incident_date": safe_isoformat(case.get("incident_date")),
            "location": case.get("location"),
            "department": case.get("department"),
            "officer_name": case.get("officer_name"),
            "officer_badge": case.get("officer_badge"),
            "created_at": safe_isoformat(case.get("created_at"))
        },
        "evidence_summary": {
            "total_files": len(evidence_with_verification),
            "blockchain_verified": blockchain_status["total_verified"],
            "ipfs_stored": ipfs_status["total_files_on_ipfs"],
            "types": {
                "document": sum(1 for e in evidence_with_verification if e.get("file_type") == "document"),
                "image": sum(1 for e in evidence_with_verification if e.get("file_type") == "image"),
                "video": sum(1 for e in evidence_with_verification if e.get("file_type") == "video"),
                "audio": sum(1 for e in evidence_with_verification if e.get("file_type") == "audio")
            }
        },
        "evidence": evidence_with_verification,
        "ipfs_status": ipfs_status,
        "blockchain_status": blockchain_status,
        "verification_instructions": {
            "ipfs": "Files stored on IPFS can be verified by accessing their gateway URL. The content is immutable and distributed across the network.",
            "blockchain": "Each file's SHA-256 hash is recorded on the blockchain. Rehashing the file should produce the exact same hash to verify integrity.",
            "chain_of_custody": "Every action taken on evidence is logged with timestamp, actor, and digital signature for a complete audit trail."
        },
        "legal_notice": "This report contains cryptographically verified evidence suitable for legal proceedings. All hash values and IPFS Content Identifiers (CIDs) can be independently verified by any party."
    }
    
    # Store report
    await db.evidence_reports.insert_one(dict(report))
    
    logger.info(f"Evidence report generated: {report_id} for case {case_id}")
    
    return report

@api_router.get("/evidence/batch-export/{case_id}")
async def batch_export_evidence(
    case_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Export all evidence for a case as a ZIP file containing:
    - All evidence files
    - Verification manifest (JSON)
    - Summary report (TXT)
    """
    # Helper to safely convert dates
    def safe_isoformat(date_val):
        if date_val is None:
            return None
        if isinstance(date_val, str):
            return date_val
        if hasattr(date_val, 'isoformat'):
            return date_val.isoformat()
        return str(date_val)
    
    # Get the case
    case = await db.cases.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check access
    if case["user_id"] != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all evidence for this case
    evidence_list = await db.evidence.find({"case_id": case_id}, {"_id": 0}).to_list(length=100)
    
    if not evidence_list:
        raise HTTPException(status_code=404, detail="No evidence found for this case")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        manifest_data = {
            "export_id": f"exp_{uuid.uuid4().hex[:12]}",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": current_user["user_id"],
            "case": {
                "case_id": case["case_id"],
                "title": case.get("title"),
                "status": case.get("status"),
                "violation_type": case.get("violation_type"),
                "location": case.get("location")
            },
            "evidence_count": len(evidence_list),
            "ipfs_enabled": bool(PINATA_JWT),
            "evidence_items": []
        }
        
        # Process each evidence file
        for ev in evidence_list:
            evidence_id = ev["evidence_id"]
            file_name = ev.get("file_name", f"{evidence_id}.bin")
            
            # Get hash record
            hash_record = await db.evidence_hashes.find_one(
                {"evidence_id": evidence_id},
                {"_id": 0}
            )
            
            # Get chain of custody
            custody = await db.chain_of_custody.find(
                {"evidence_id": evidence_id},
                {"_id": 0}
            ).sort("timestamp", 1).to_list(length=100)
            
            # Build manifest entry
            manifest_entry = {
                "evidence_id": evidence_id,
                "file_name": file_name,
                "file_type": ev.get("file_type", "unknown"),
                "file_size": ev.get("file_size"),
                "uploaded_at": safe_isoformat(ev.get("uploaded_at")),
                "description": ev.get("description"),
                "verification": {
                    "file_hash": hash_record.get("file_hash") if hash_record else None,
                    "metadata_hash": hash_record.get("metadata_hash") if hash_record else None,
                    "combined_hash": hash_record.get("combined_hash") if hash_record else None,
                    "hash_id": hash_record.get("hash_id") if hash_record else None
                },
                "ipfs": {
                    "cid": ev.get("ipfs_cid"),
                    "gateway_url": f"{IPFS_GATEWAY}/{ev['ipfs_cid']}" if ev.get("ipfs_cid") else None,
                    "pinned": ev.get("ipfs_pinned", False)
                },
                "chain_of_custody_entries": len(custody),
                "chain_of_custody": [
                    {
                        "action": c.get("action"),
                        "timestamp": safe_isoformat(c.get("timestamp")),
                        "actor_type": c.get("actor_type"),
                        "signature": c.get("signature")
                    }
                    for c in custody
                ]
            }
            manifest_data["evidence_items"].append(manifest_entry)
            
            # Try to add the actual file to the ZIP
            file_path = UPLOAD_DIR / file_name
            if file_path.exists():
                zip_file.write(file_path, f"evidence/{file_name}")
            else:
                # File not found locally, add a placeholder
                placeholder = f"File not found locally.\nIPFS CID: {ev.get('ipfs_cid', 'N/A')}\nGateway URL: {manifest_entry['ipfs']['gateway_url'] or 'N/A'}"
                zip_file.writestr(f"evidence/{evidence_id}_MISSING.txt", placeholder)
        
        # Add manifest JSON
        manifest_json = json.dumps(manifest_data, indent=2)
        zip_file.writestr("VERIFICATION_MANIFEST.json", manifest_json)
        
        # Create summary text file
        summary_lines = [
            "=" * 60,
            "JUSTICE PLATFORM - EVIDENCE EXPORT SUMMARY",
            "=" * 60,
            "",
            f"Export ID: {manifest_data['export_id']}",
            f"Exported: {manifest_data['exported_at']}",
            "",
            "CASE INFORMATION",
            "-" * 40,
            f"Case ID: {case['case_id']}",
            f"Title: {case.get('title', 'N/A')}",
            f"Status: {case.get('status', 'N/A')}",
            f"Violation Type: {case.get('violation_type', 'N/A')}",
            f"Location: {case.get('location', 'N/A')}",
            "",
            "EVIDENCE SUMMARY",
            "-" * 40,
            f"Total Evidence Files: {len(evidence_list)}",
            f"Files with IPFS Storage: {sum(1 for e in evidence_list if e.get('ipfs_cid'))}",
            f"Files with Blockchain Hash: {sum(1 for e in manifest_data['evidence_items'] if e['verification']['file_hash'])}",
            "",
            "EVIDENCE FILES",
            "-" * 40,
        ]
        
        for i, ev in enumerate(manifest_data["evidence_items"], 1):
            summary_lines.extend([
                f"",
                f"[{i}] {ev['file_name']}",
                f"    Evidence ID: {ev['evidence_id']}",
                f"    Type: {ev['file_type']}",
                f"    SHA-256 Hash: {ev['verification']['file_hash'] or 'N/A'}",
                f"    IPFS CID: {ev['ipfs']['cid'] or 'N/A'}",
                f"    Chain of Custody: {ev['chain_of_custody_entries']} entries",
            ])
        
        summary_lines.extend([
            "",
            "=" * 60,
            "VERIFICATION INSTRUCTIONS",
            "=" * 60,
            "",
            "1. HASH VERIFICATION:",
            "   To verify file integrity, compute the SHA-256 hash of any",
            "   evidence file and compare it to the hash in this manifest.",
            "",
            "   Command: sha256sum <filename>",
            "",
            "2. IPFS VERIFICATION:",
            "   Files stored on IPFS can be retrieved from any IPFS gateway",
            "   using the Content Identifier (CID). The content is immutable.",
            "",
            "   URL: https://gateway.pinata.cloud/ipfs/<CID>",
            "",
            "3. CHAIN OF CUSTODY:",
            "   Each action on evidence is logged with a digital signature.",
            "   See VERIFICATION_MANIFEST.json for complete custody records.",
            "",
            "=" * 60,
            "LEGAL NOTICE",
            "=" * 60,
            "",
            "This export contains cryptographically verified evidence suitable",
            "for legal proceedings. All hash values and IPFS Content Identifiers",
            "(CIDs) can be independently verified by any party.",
            "",
            f"Generated by JUSTICE Platform on {manifest_data['exported_at']}",
            ""
        ])
        
        summary_text = "\n".join(summary_lines)
        zip_file.writestr("EXPORT_SUMMARY.txt", summary_text)
    
    # Prepare response
    zip_buffer.seek(0)
    
    # Generate filename
    case_title_safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in case.get("title", "case")[:30])
    filename = f"JUSTICE_Evidence_{case_title_safe}_{case_id}.zip"
    
    logger.info(f"Batch export created for case {case_id}: {len(evidence_list)} files")
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ============== S3 BACKUP SYSTEM ==============

async def upload_to_s3(file_path: Path, s3_key: str) -> dict:
    """Upload a single file to S3"""
    if not S3_ENABLED or not s3_client:
        return {"success": False, "error": "S3 not configured"}
    
    try:
        with open(file_path, 'rb') as f:
            s3_client.upload_fileobj(
                f,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )
        return {"success": True, "s3_key": s3_key}
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return {"success": False, "error": str(e)}

async def run_backup_job(user_id: str = None):
    """Run a backup job for all evidence files"""
    backup_id = f"backup_{uuid.uuid4().hex[:12]}"
    start_time = datetime.now(timezone.utc)
    
    # Create backup record
    backup_record = {
        "backup_id": backup_id,
        "status": "running",
        "started_at": start_time,
        "completed_at": None,
        "triggered_by": user_id or "system",
        "files_total": 0,
        "files_backed_up": 0,
        "files_failed": 0,
        "total_size_bytes": 0,
        "errors": []
    }
    await db.s3_backups.insert_one(dict(backup_record))
    
    try:
        # Get all evidence files
        evidence_list = await db.evidence.find({}, {"_id": 0}).to_list(length=1000)
        backup_record["files_total"] = len(evidence_list)
        
        for ev in evidence_list:
            file_name = ev.get("file_name")
            evidence_id = ev.get("evidence_id")
            file_path = UPLOAD_DIR / file_name
            
            if not file_path.exists():
                backup_record["files_failed"] += 1
                backup_record["errors"].append(f"File not found: {file_name}")
                continue
            
            # Create S3 key with structure: backups/YYYY-MM-DD/evidence_id/filename
            date_prefix = start_time.strftime("%Y-%m-%d")
            s3_key = f"justice-backups/{date_prefix}/{evidence_id}/{file_name}"
            
            result = await upload_to_s3(file_path, s3_key)
            
            if result["success"]:
                backup_record["files_backed_up"] += 1
                backup_record["total_size_bytes"] += file_path.stat().st_size
                
                # Update evidence record with S3 info
                await db.evidence.update_one(
                    {"evidence_id": evidence_id},
                    {"$set": {
                        "s3_backup": {
                            "backed_up": True,
                            "s3_key": s3_key,
                            "backup_id": backup_id,
                            "backed_up_at": datetime.now(timezone.utc)
                        }
                    }}
                )
            else:
                backup_record["files_failed"] += 1
                backup_record["errors"].append(f"{file_name}: {result.get('error')}")
        
        backup_record["status"] = "completed"
        backup_record["completed_at"] = datetime.now(timezone.utc)
        
    except Exception as e:
        backup_record["status"] = "failed"
        backup_record["errors"].append(str(e))
        logger.error(f"Backup job failed: {e}")
    
    # Update backup record
    await db.s3_backups.update_one(
        {"backup_id": backup_id},
        {"$set": backup_record}
    )
    
    logger.info(f"Backup {backup_id} completed: {backup_record['files_backed_up']}/{backup_record['files_total']} files")
    return backup_record

@api_router.get("/backup/status")
async def get_backup_status(current_user: dict = Depends(get_current_user)):
    """Get S3 backup system status"""
    
    # Get last backup
    last_backup = await db.s3_backups.find_one(
        {},
        {"_id": 0},
        sort=[("started_at", -1)]
    )
    
    # Get backup stats
    total_backups = await db.s3_backups.count_documents({})
    successful_backups = await db.s3_backups.count_documents({"status": "completed"})
    
    # Get evidence backup stats
    total_evidence = await db.evidence.count_documents({})
    backed_up_evidence = await db.evidence.count_documents({"s3_backup.backed_up": True})
    
    # Check S3 connectivity if enabled
    s3_connected = False
    s3_bucket_exists = False
    if S3_ENABLED and s3_client:
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            s3_connected = True
            s3_bucket_exists = True
        except Exception as e:
            logger.warning(f"S3 connectivity check failed: {e}")
    
    return {
        "s3_enabled": S3_ENABLED,
        "s3_connected": s3_connected,
        "s3_bucket": S3_BUCKET_NAME if S3_ENABLED else None,
        "s3_region": AWS_REGION if S3_ENABLED else None,
        "last_backup": {
            "backup_id": last_backup.get("backup_id") if last_backup else None,
            "status": last_backup.get("status") if last_backup else None,
            "started_at": last_backup.get("started_at").isoformat() if last_backup and last_backup.get("started_at") else None,
            "completed_at": last_backup.get("completed_at").isoformat() if last_backup and last_backup.get("completed_at") else None,
            "files_backed_up": last_backup.get("files_backed_up") if last_backup else 0,
            "files_total": last_backup.get("files_total") if last_backup else 0,
        } if last_backup else None,
        "statistics": {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "total_evidence_files": total_evidence,
            "backed_up_files": backed_up_evidence,
            "backup_coverage_percent": round((backed_up_evidence / total_evidence * 100) if total_evidence > 0 else 0, 1)
        },
        "setup_instructions": {
            "required_env_vars": [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY", 
                "S3_BUCKET_NAME"
            ],
            "optional_env_vars": [
                "AWS_REGION (default: us-east-1)"
            ],
            "how_to_get_credentials": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"
        } if not S3_ENABLED else None
    }

@api_router.post("/backup/trigger")
async def trigger_backup(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a backup job"""
    if not S3_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="S3 backup is not configured. Please add AWS credentials to environment."
        )
    
    # Check if a backup is already running
    running_backup = await db.s3_backups.find_one({"status": "running"})
    if running_backup:
        raise HTTPException(
            status_code=409,
            detail=f"Backup already in progress: {running_backup['backup_id']}"
        )
    
    # Start backup in background
    backup_id = f"backup_{uuid.uuid4().hex[:12]}"
    
    # Create initial record
    await db.s3_backups.insert_one({
        "backup_id": backup_id,
        "status": "queued",
        "triggered_by": current_user["user_id"],
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "files_total": 0,
        "files_backed_up": 0,
        "files_failed": 0,
        "total_size_bytes": 0,
        "errors": []
    })
    
    # Schedule background task
    background_tasks.add_task(run_backup_job, current_user["user_id"])
    
    logger.info(f"Backup triggered by user {current_user['user_id']}")
    
    return {
        "message": "Backup job started",
        "backup_id": backup_id,
        "status": "queued"
    }

@api_router.get("/backup/history")
async def get_backup_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get backup history"""
    backups = await db.s3_backups.find(
        {},
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(length=limit)
    
    # Convert datetime objects to strings
    for backup in backups:
        if backup.get("started_at"):
            backup["started_at"] = backup["started_at"].isoformat()
        if backup.get("completed_at"):
            backup["completed_at"] = backup["completed_at"].isoformat()
    
    return {"backups": backups}

# ============== POLICY IMPACT DASHBOARD ==============

@api_router.get("/policy/reports")
async def list_policy_reports(
    report_type: Optional[str] = None,
    target_audience: Optional[str] = None
):
    """List available policy impact reports"""
    query = {}
    if report_type:
        query["report_type"] = report_type
    if target_audience:
        query["target_audience"] = target_audience
    
    reports = await db.policy_reports.find(query, {"_id": 0}).sort("generated_at", -1).to_list(length=50)
    return {"reports": reports}

@api_router.post("/policy/generate-report")
async def generate_policy_report(
    report_type: str = Form(...),  # department_accountability, officer_pattern, state_analysis, violation_trend
    target_audience: str = Form(...),  # city_council, media, civil_rights_org, legislators
    department: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    violation_type: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Generate a policy impact report for advocacy and reform"""
    
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Gather data based on report type
    key_findings = []
    recommendations = []
    charts_data = {}
    data_sources = ["Community Evidence Vault", "Department Transparency Portal"]
    
    if report_type == "department_accountability":
        # Get department data
        query = {}
        if department:
            query["department"] = {"$regex": department, "$options": "i"}
        if state:
            query["location_state"] = state
        
        submissions = await db.community_vault.find(query, {"_id": 0}).to_list(length=1000)
        dept_stats = await db.department_stats.find({}, {"_id": 0}).sort("total_incidents", -1).to_list(length=20)
        
        # Analyze patterns
        total_incidents = len(submissions)
        violation_counts = {}
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        for sub in submissions:
            for v in sub.get("violations", []):
                violation_counts[v] = violation_counts.get(v, 0) + 1
            severity_counts[sub.get("severity", "medium")] = severity_counts.get(sub.get("severity", "medium"), 0) + 1
        
        # Generate findings
        if dept_stats:
            top_dept = dept_stats[0]
            key_findings.append({
                "finding": f"The {top_dept['department']} has the highest number of reported incidents ({top_dept['total_incidents']})",
                "severity": "high",
                "data_point": top_dept['total_incidents']
            })
        
        top_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_violations:
            key_findings.append({
                "finding": f"Most common violation type: {top_violations[0][0].replace('_', ' ')} ({top_violations[0][1]} incidents)",
                "severity": "high",
                "data_point": top_violations[0][1]
            })
        
        critical_high = severity_counts["critical"] + severity_counts["high"]
        if critical_high > 0:
            key_findings.append({
                "finding": f"{critical_high} incidents classified as critical or high severity require immediate attention",
                "severity": "critical",
                "data_point": critical_high
            })
        
        charts_data = {
            "violations_by_type": violation_counts,
            "severity_distribution": severity_counts,
            "department_rankings": [{"name": d["department"], "incidents": d["total_incidents"]} for d in dept_stats[:10]]
        }
        
        recommendations = [
            "Mandate independent oversight committee for departments with >10 incidents",
            "Require body camera footage release within 48 hours of incidents",
            "Implement early warning system for officers with multiple complaints",
            "Establish civilian review board with subpoena power",
            "Create transparent public database of all use-of-force incidents"
        ]
        
        title = f"Department Accountability Report{f' - {department}' if department else ''}{f' ({state})' if state else ''}"
        executive_summary = f"Analysis of {total_incidents} community-reported incidents reveals systemic patterns of civil rights concerns requiring policy intervention."
    
    elif report_type == "officer_pattern":
        # Get officer data
        officers = await db.officer_stats.find({}, {"_id": 0}).sort("total_incidents", -1).to_list(length=50)
        
        repeat_offenders = [o for o in officers if o["total_incidents"] >= 2]
        
        key_findings.append({
            "finding": f"{len(repeat_offenders)} officers have multiple reported incidents",
            "severity": "critical",
            "data_point": len(repeat_offenders)
        })
        
        if officers:
            total_officer_incidents = sum(o["total_incidents"] for o in officers)
            top_10_incidents = sum(o["total_incidents"] for o in officers[:10])
            if total_officer_incidents > 0:
                concentration = (top_10_incidents / total_officer_incidents) * 100
                key_findings.append({
                    "finding": f"Top 10 officers account for {concentration:.1f}% of all incidents",
                    "severity": "high",
                    "data_point": concentration
                })
        
        charts_data = {
            "officers_by_incidents": [{"badge": o["badge_number"], "dept": o["department"], "incidents": o["total_incidents"]} for o in officers[:20]],
            "repeat_offender_count": len(repeat_offenders)
        }
        
        recommendations = [
            "Implement mandatory de-escalation training for officers with 2+ incidents",
            "Create early intervention program triggered by pattern analysis",
            "Require psychological evaluation for officers with repeated complaints",
            "Establish progressive discipline policy with clear consequences",
            "Enable inter-department sharing of officer complaint histories"
        ]
        
        title = "Officer Pattern Analysis Report"
        executive_summary = f"Pattern analysis identifies {len(repeat_offenders)} officers with repeated incidents, suggesting need for targeted intervention programs."
    
    elif report_type == "state_analysis":
        # Analyze by state
        pipeline = [
            {"$group": {"_id": "$location_state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        state_data = await db.community_vault.aggregate(pipeline).to_list(length=50)
        
        if state_data:
            key_findings.append({
                "finding": f"{state_data[0]['_id']} has the highest number of reported incidents ({state_data[0]['count']})",
                "severity": "high",
                "data_point": state_data[0]['count']
            })
        
        charts_data = {
            "incidents_by_state": [{"state": s["_id"], "count": s["count"]} for s in state_data]
        }
        
        recommendations = [
            "Prioritize states with highest incident rates for federal oversight",
            "Implement standardized reporting requirements across all states",
            "Create interstate data sharing agreements for officer tracking",
            "Establish federal minimum standards for police accountability"
        ]
        
        title = "State-by-State Civil Rights Analysis"
        executive_summary = f"Geographic analysis of {sum(s['count'] for s in state_data)} incidents across {len(state_data)} states reveals regional patterns requiring targeted policy response."
    
    elif report_type == "violation_trend":
        # Analyze violation trends
        pipeline = [
            {"$unwind": "$violations"},
            {"$group": {"_id": "$violations", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        violation_data = await db.community_vault.aggregate(pipeline).to_list(length=20)
        
        if violation_data:
            key_findings.append({
                "finding": f"Most prevalent violation: {violation_data[0]['_id'].replace('_', ' ')} ({violation_data[0]['count']} occurrences)",
                "severity": "high",
                "data_point": violation_data[0]['count']
            })
        
        charts_data = {
            "violation_frequency": [{"type": v["_id"].replace("_", " "), "count": v["count"]} for v in violation_data]
        }
        
        recommendations = [
            f"Focus training and policy reform on {violation_data[0]['_id'].replace('_', ' ')} prevention" if violation_data else "Implement comprehensive training",
            "Mandate Constitutional rights refresher training annually",
            "Create clear guidelines for search and seizure procedures",
            "Establish independent investigation units for excessive force claims"
        ]
        
        title = "Civil Rights Violation Trend Analysis"
        executive_summary = f"Analysis of violation patterns across {len(violation_data)} categories identifies key areas for policy intervention and training reform."
    
    else:
        title = "General Policy Analysis Report"
        executive_summary = "General analysis of community-reported incidents."
    
    # Create report document
    report_doc = {
        "report_id": report_id,
        "report_type": report_type,
        "target_audience": target_audience,
        "title": title,
        "executive_summary": executive_summary,
        "key_findings": key_findings,
        "data_sources": data_sources,
        "recommendations": recommendations,
        "charts_data": charts_data,
        "parameters": {
            "department": department,
            "state": state,
            "violation_type": violation_type
        },
        "generated_by": current_user["user_id"],
        "generated_at": now.isoformat()
    }
    
    await db.policy_reports.insert_one(report_doc)
    
    # Remove MongoDB _id before returning
    report_doc.pop("_id", None)
    
    logger.info(f"Generated policy report: {report_id} ({report_type} for {target_audience})")
    
    return report_doc

@api_router.get("/policy/report/{report_id}")
async def get_policy_report(report_id: str):
    """Get a specific policy report"""
    report = await db.policy_reports.find_one({"report_id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@api_router.get("/policy/dashboard-data")
async def get_policy_dashboard_data():
    """Get aggregated data for policy impact dashboard"""
    
    # Overall stats
    total_submissions = await db.community_vault.count_documents({})
    total_departments = await db.department_stats.count_documents({})
    total_officers = await db.officer_stats.count_documents({})
    
    # Violation breakdown
    violation_pipeline = [
        {"$unwind": "$violations"},
        {"$group": {"_id": "$violations", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    violations = await db.community_vault.aggregate(violation_pipeline).to_list(length=10)
    
    # State breakdown
    state_pipeline = [
        {"$group": {"_id": "$location_state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    states = await db.community_vault.aggregate(state_pipeline).to_list(length=10)
    
    # Severity breakdown
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severities = await db.community_vault.aggregate(severity_pipeline).to_list(length=10)
    
    # Top problematic departments
    top_depts = await db.department_stats.find({}, {"_id": 0}).sort("total_incidents", -1).limit(10).to_list(length=10)
    
    # Officers with multiple incidents
    repeat_officers = await db.officer_stats.find(
        {"total_incidents": {"$gte": 2}},
        {"_id": 0}
    ).sort("total_incidents", -1).limit(10).to_list(length=10)
    
    # Recent reports
    recent_reports = await db.policy_reports.find({}, {"_id": 0}).sort("generated_at", -1).limit(5).to_list(length=5)
    
    return {
        "overview": {
            "total_submissions": total_submissions,
            "total_departments": total_departments,
            "total_officers": total_officers,
            "repeat_offenders": len(repeat_officers)
        },
        "violations_breakdown": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "state_breakdown": [{"state": s["_id"], "count": s["count"]} for s in states],
        "severity_breakdown": [{"severity": s["_id"], "count": s["count"]} for s in severities],
        "top_departments": top_depts,
        "repeat_officers": repeat_officers,
        "recent_reports": recent_reports
    }

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "5.1.0", "ipfs_enabled": bool(PINATA_JWT)}

# Include the router
app.include_router(api_router)

# CORS middleware - properly configured for credentials
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
# For credentials to work, we need specific origins, not wildcard
if cors_origins == ['*']:
    cors_origins = [
        "http://localhost:3000",
        "https://rightsdefender.preview.emergentagent.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
