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
from emergentintegrations.llm.openai import OpenAISpeechToText, LlmChat

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
app = FastAPI(title="JUSTICE Platform API", version="4.0.0")

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
    legal_issues: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    case_precedents: List[Dict[str, Any]] = []
    created_at: datetime

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
                    
                    transcription_doc = {
                        "segment_id": segment_id,
                        "encounter_id": encounter_id,
                        "text": response.text,
                        "speaker": "unknown",
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
                        "violations_detected": violations
                    }
                    
                    # Real-time notification if violations detected
                    if violations:
                        await manager.send_to_user(current_user["user_id"], {
                            "type": "violation_detected",
                            "encounter_id": encounter_id,
                            "violations": violations,
                            "text": response.text
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
    
    # AI-powered deep analysis if LLM service available
    if EMERGENT_LLM_KEY and len(text) > 50:
        try:
            llm = create_llm_chat(f"violation_analysis_{encounter_id}", "You are a civil rights legal expert analyzing police encounters for violations.")
            analysis_prompt = f"""Analyze this police encounter transcript for potential civil rights violations.
            
Transcript: "{text}"

Identify any of these violations if present:
- 4th Amendment (unlawful search/seizure)
- 5th Amendment (self-incrimination, Miranda)
- 6th Amendment (right to counsel)
- 8th Amendment (excessive force)
- 14th Amendment (equal protection)
- Racial profiling
- Intimidation/coercion
- Unlawful detention

Return ONLY a JSON array of violation types found, or empty array if none.
Example: ["4th_amendment_violation", "intimidation"]"""

            response = await llm.chat(analysis_prompt)
            if response:
                try:
                    ai_violations = json.loads(response)
                    if isinstance(ai_violations, list):
                        violations.extend(ai_violations)
                except:
                    pass
        except Exception as e:
            logger.error(f"AI violation analysis error: {e}")
    
    return list(set(violations))  # Remove duplicates

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

            response = await llm.chat(analysis_prompt)
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
    report_doc = {
        "report_id": report_id,
        "encounter_id": encounter_id,
        "user_id": user_id,
        "summary": summary,
        "violations": list(set(all_violations)),
        "officers": officers,
        "transcript_text": full_transcript,
        "recommendations": recommendations if isinstance(recommendations, list) else [recommendations],
        "legal_resources": [
            {"name": "ACLU Know Your Rights", "url": "https://www.aclu.org/know-your-rights"},
            {"name": "National Police Accountability Project", "url": "https://www.nlg-npap.org"},
            {"name": "Mapping Police Violence", "url": "https://mappingpoliceviolence.org"}
        ],
        "similar_cases": similar_cases if isinstance(similar_cases, list) else [],
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
        response = await llm.chat(analysis_prompt)
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
    if not llm_service:
        # Fallback to pre-programmed responses
        return get_fallback_rights_guidance(situation)
    
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
        response = await llm_service.chat(prompt)
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

# ============== SIMILAR CASES SEARCH ==============

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

# ============== EMERGENCY CONTACTS ==============

@api_router.post("/settings/emergency-contacts")
async def update_emergency_contacts(
    contacts: List[Dict[str, str]],
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

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "4.0.0"}

# Include the router
app.include_router(api_router)

# CORS middleware - properly configured for credentials
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',')
# For credentials to work, we need specific origins, not wildcard
if cors_origins == ['*']:
    cors_origins = [
        "http://localhost:3000",
        "https://caseguardian.preview.emergentagent.com"
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
