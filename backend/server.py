from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
import bcrypt
import httpx
import json

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

# Create the main app
app = FastAPI(title="JUSTICE Platform API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    violation_detected: bool = False
    violation_type: Optional[str] = None
    rights_reminder: Optional[str] = None

class MessageCreate(BaseModel):
    recipient_id: str
    case_id: Optional[str] = None
    content: str

class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str
    sender_id: str
    recipient_id: str
    case_id: Optional[str] = None
    content: str
    read: bool = False
    created_at: datetime

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
    
    await db.cases.update_one(
        {"case_id": case_id},
        {"$set": update_data}
    )
    
    updated_case = await db.cases.find_one({"case_id": case_id}, {"_id": 0})
    
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(updated_case.get(field), str):
            updated_case[field] = datetime.fromisoformat(updated_case[field])
    
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
    
    # TODO: In production, this would trigger:
    # - SMS notifications via Twilio
    # - Email notifications to emergency contacts
    # - Attorney notifications for emergency responders
    logger.info(f"SOS Alert created: {alert_id} by user {current_user['user_id']}")
    
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

# ============== MESSAGING ==============

@api_router.post("/messages", response_model=MessageResponse)
async def send_message(message_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    message_doc = {
        "message_id": message_id,
        "sender_id": current_user["user_id"],
        "recipient_id": message_data.recipient_id,
        "case_id": message_data.case_id,
        "content": message_data.content,
        "read": False,
        "created_at": now.isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    return MessageResponse(
        message_id=message_id,
        sender_id=current_user["user_id"],
        recipient_id=message_data.recipient_id,
        case_id=message_data.case_id,
        content=message_data.content,
        read=False,
        created_at=now
    )

@api_router.get("/messages", response_model=List[MessageResponse])
async def get_messages(current_user: dict = Depends(get_current_user)):
    messages = await db.messages.find(
        {"$or": [
            {"sender_id": current_user["user_id"]},
            {"recipient_id": current_user["user_id"]}
        ]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
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
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "recent_cases": recent_cases
    }

@api_router.get("/analytics/public")
async def get_public_stats():
    """Public transparency data - no auth required"""
    total_cases = await db.cases.count_documents({})
    total_users = await db.users.count_documents({})
    resolved_cases = await db.cases.count_documents({"status": "resolved"})
    
    # Get violation types distribution
    violation_pipeline = [
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    violations = await db.cases.aggregate(violation_pipeline).to_list(10)
    
    return {
        "total_cases": total_cases,
        "total_users": total_users,
        "resolved_cases": resolved_cases,
        "success_rate": round((resolved_cases / total_cases * 100) if total_cases > 0 else 0, 1),
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations]
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

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
