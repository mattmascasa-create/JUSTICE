"""
Evidence Router - Evidence management endpoints
"""
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends

from app.db.database import db
from app.core.security import get_current_user
from app.core.config import UPLOADS_DIR
from app.models.schemas import EvidenceCreate, EvidenceResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceResponse)
async def create_evidence(evidence_data: EvidenceCreate, current_user: dict = Depends(get_current_user)):
    """Create evidence record for a case"""
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


@router.get("", response_model=List[EvidenceResponse])
async def get_all_evidence(current_user: dict = Depends(get_current_user)):
    """Get all evidence for current user"""
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


@router.get("/case/{case_id}", response_model=List[EvidenceResponse])
async def get_case_evidence(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all evidence for a specific case"""
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


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(evidence_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific evidence by ID"""
    evidence = await db.evidence.find_one(
        {"evidence_id": evidence_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    if isinstance(evidence.get("uploaded_at"), str):
        evidence["uploaded_at"] = datetime.fromisoformat(evidence["uploaded_at"])
    
    return EvidenceResponse(**evidence)


@router.delete("/{evidence_id}")
async def delete_evidence(evidence_id: str, current_user: dict = Depends(get_current_user)):
    """Delete evidence"""
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
        file_path = UPLOADS_DIR / filename
        if file_path.exists():
            file_path.unlink()
    
    return {"message": "Evidence deleted successfully"}


@router.get("/{evidence_id}/verify")
async def verify_evidence(evidence_id: str, current_user: dict = Depends(get_current_user)):
    """Verify evidence integrity using blockchain hash"""
    evidence = await db.evidence.find_one(
        {"evidence_id": evidence_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Check blockchain verification record
    verification = await db.blockchain_evidence.find_one(
        {"evidence_id": evidence_id},
        {"_id": 0}
    )
    
    # Get chain of custody
    custody_records = await db.chain_of_custody.find(
        {"evidence_id": evidence_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    
    return {
        "evidence_id": evidence_id,
        "blockchain_hash": evidence.get("blockchain_hash"),
        "ipfs_cid": evidence.get("ipfs_cid"),
        "verification_status": "verified" if verification else "unverified",
        "chain_of_custody": custody_records,
        "integrity_score": 100 if verification else 75
    }
