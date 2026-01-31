"""
Evidence Chain of Custody Portal
Secure public-facing portal for attorneys and courts to view evidence with complete audit trail
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import secrets
import hashlib

from app.routers.auth import get_current_user
from app.services.evidence_integrity import evidence_integrity_service, CustodyAction
from app.db.database import db

router = APIRouter(prefix="/custody-portal", tags=["Chain of Custody Portal"])


class CreateAccessTokenRequest(BaseModel):
    evidence_id: str
    encounter_id: str
    recipient_email: str
    recipient_name: str
    recipient_role: str  # attorney, court, expert_witness, insurance
    access_level: str = "view"  # view, download, full
    expires_hours: int = 72  # Default 3 days
    notes: Optional[str] = None


class VerifyAccessRequest(BaseModel):
    access_token: str


# ============== TOKEN MANAGEMENT ==============

@router.post("/create-access")
async def create_access_token(
    request: CreateAccessTokenRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a secure access token for external parties to view evidence chain of custody.
    Only the evidence owner can create access tokens.
    """
    
    # Verify evidence belongs to user
    evidence = await db.evidence.find_one(
        {"evidence_id": request.evidence_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found or access denied")
    
    # Generate secure token
    access_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=request.expires_hours)
    
    token_record = {
        "token_hash": token_hash,
        "evidence_id": request.evidence_id,
        "encounter_id": request.encounter_id,
        "owner_id": current_user.get("user_id"),
        "owner_name": current_user.get("name"),
        "recipient_email": request.recipient_email,
        "recipient_name": request.recipient_name,
        "recipient_role": request.recipient_role,
        "access_level": request.access_level,
        "notes": request.notes,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "revoked": False,
        "access_count": 0,
        "last_accessed": None,
        "access_log": []
    }
    
    await db.custody_access_tokens.insert_one(token_record)
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=request.evidence_id,
        action=CustodyAction.SHARED,
        user_id=current_user.get("user_id"),
        details={
            "shared_with": request.recipient_email,
            "recipient_role": request.recipient_role,
            "access_level": request.access_level,
            "expires_at": expires_at.isoformat(),
            "actor_name": current_user.get("name")
        }
    )
    
    # Generate portal URL
    portal_url = f"https://rights-shield-2.preview.emergentagent.com/custody-portal?token={access_token}"
    
    return {
        "success": True,
        "access_token": access_token,
        "portal_url": portal_url,
        "expires_at": expires_at.isoformat(),
        "recipient": {
            "email": request.recipient_email,
            "name": request.recipient_name,
            "role": request.recipient_role
        },
        "access_level": request.access_level
    }


@router.get("/my-tokens")
async def get_my_access_tokens(
    current_user: dict = Depends(get_current_user)
):
    """Get all access tokens created by the user"""
    
    tokens = await db.custody_access_tokens.find(
        {"owner_id": current_user.get("user_id")},
        {"_id": 0, "token_hash": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "tokens": tokens,
        "count": len(tokens)
    }


@router.post("/revoke/{evidence_id}")
async def revoke_access_token(
    evidence_id: str,
    recipient_email: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Revoke an access token"""
    
    result = await db.custody_access_tokens.update_one(
        {
            "evidence_id": evidence_id,
            "owner_id": current_user.get("user_id"),
            "recipient_email": recipient_email
        },
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Token not found")
    
    return {
        "success": True,
        "message": f"Access revoked for {recipient_email}"
    }


# ============== PUBLIC PORTAL ACCESS ==============

@router.post("/verify-access")
async def verify_access_token(request: VerifyAccessRequest):
    """
    Verify an access token and return basic info.
    This is a public endpoint - no authentication required.
    """
    
    token_hash = hashlib.sha256(request.access_token.encode()).hexdigest()
    
    token_record = await db.custody_access_tokens.find_one(
        {"token_hash": token_hash},
        {"_id": 0, "token_hash": 0}
    )
    
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid or expired access token")
    
    if token_record.get("revoked"):
        raise HTTPException(status_code=403, detail="Access token has been revoked")
    
    expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Access token has expired")
    
    return {
        "valid": True,
        "evidence_id": token_record["evidence_id"],
        "encounter_id": token_record["encounter_id"],
        "owner_name": token_record["owner_name"],
        "recipient_name": token_record["recipient_name"],
        "recipient_role": token_record["recipient_role"],
        "access_level": token_record["access_level"],
        "expires_at": token_record["expires_at"],
        "notes": token_record.get("notes")
    }


@router.get("/evidence")
async def get_evidence_for_portal(
    token: str = Query(..., description="Access token")
):
    """
    Get evidence details for the custody portal.
    Public endpoint - access controlled via token.
    """
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    token_record = await db.custody_access_tokens.find_one({"token_hash": token_hash})
    
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    if token_record.get("revoked"):
        raise HTTPException(status_code=403, detail="Access has been revoked")
    
    expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Access token has expired")
    
    # Get evidence
    evidence = await db.evidence.find_one(
        {"evidence_id": token_record["evidence_id"]},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Get encounter info
    encounter = await db.encounters.find_one(
        {"encounter_id": token_record["encounter_id"]},
        {"_id": 0, "encounter_id": 1, "encounter_type": 1, "started_at": 1, "address": 1}
    )
    
    # Log access
    now = datetime.now(timezone.utc)
    await db.custody_access_tokens.update_one(
        {"token_hash": token_hash},
        {
            "$inc": {"access_count": 1},
            "$set": {"last_accessed": now.isoformat()},
            "$push": {"access_log": {"timestamp": now.isoformat(), "action": "view_evidence"}}
        }
    )
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=token_record["evidence_id"],
        action=CustodyAction.VIEWED,
        user_id=f"external_{token_record['recipient_role']}",
        details={
            "access_method": "custody_portal",
            "recipient_role": token_record["recipient_role"],
            "actor_name": token_record["recipient_name"]
        }
    )
    
    return {
        "success": True,
        "evidence": {
            "evidence_id": evidence.get("evidence_id"),
            "filename": evidence.get("filename"),
            "file_type": evidence.get("file_type"),
            "file_size": evidence.get("file_size"),
            "created_at": evidence.get("created_at"),
            "description": evidence.get("description"),
            "metadata": evidence.get("metadata", {})
        },
        "encounter": encounter,
        "access_info": {
            "owner_name": token_record["owner_name"],
            "access_level": token_record["access_level"],
            "expires_at": token_record["expires_at"]
        }
    }


@router.get("/chain-of-custody")
async def get_chain_of_custody_for_portal(
    token: str = Query(..., description="Access token")
):
    """
    Get complete chain of custody for the custody portal.
    Public endpoint - access controlled via token.
    """
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    token_record = await db.custody_access_tokens.find_one({"token_hash": token_hash})
    
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    if token_record.get("revoked"):
        raise HTTPException(status_code=403, detail="Access has been revoked")
    
    expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Access token has expired")
    
    evidence_id = token_record["evidence_id"]
    
    # Get chain of custody
    chain = await evidence_integrity_service.get_custody_chain(evidence_id)
    
    # Verify chain integrity
    verification = await evidence_integrity_service.verify_custody_chain(evidence_id)
    
    # Log access
    now = datetime.now(timezone.utc)
    await db.custody_access_tokens.update_one(
        {"token_hash": token_hash},
        {
            "$set": {"last_accessed": now.isoformat()},
            "$push": {"access_log": {"timestamp": now.isoformat(), "action": "view_custody_chain"}}
        }
    )
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.VIEWED,
        user_id=f"external_{token_record['recipient_role']}",
        details={
            "access_method": "custody_portal",
            "viewed": "chain_of_custody",
            "actor_name": token_record["recipient_name"]
        }
    )
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "chain_of_custody": chain,
        "verification": verification,
        "total_events": len(chain),
        "access_info": {
            "viewer_name": token_record["recipient_name"],
            "viewer_role": token_record["recipient_role"]
        }
    }


@router.get("/integrity-report")
async def get_integrity_report_for_portal(
    token: str = Query(..., description="Access token")
):
    """
    Get full evidence integrity report for the custody portal.
    Public endpoint - access controlled via token.
    """
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    token_record = await db.custody_access_tokens.find_one({"token_hash": token_hash})
    
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    if token_record.get("revoked"):
        raise HTTPException(status_code=403, detail="Access has been revoked")
    
    expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Access token has expired")
    
    evidence_id = token_record["evidence_id"]
    
    # Get evidence
    evidence = await db.evidence.find_one(
        {"evidence_id": evidence_id},
        {"_id": 0}
    )
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Get integrity verification
    integrity = await evidence_integrity_service.verify_evidence(evidence_id)
    
    # Get chain of custody
    chain = await evidence_integrity_service.get_custody_chain(evidence_id)
    
    # Get blockchain proof if exists
    blockchain_proof = await db.blockchain_anchors.find_one(
        {"evidence_id": evidence_id},
        {"_id": 0}
    )
    
    # Log access
    now = datetime.now(timezone.utc)
    await db.custody_access_tokens.update_one(
        {"token_hash": token_hash},
        {
            "$set": {"last_accessed": now.isoformat()},
            "$push": {"access_log": {"timestamp": now.isoformat(), "action": "view_integrity_report"}}
        }
    )
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.VERIFIED,
        user_id=f"external_{token_record['recipient_role']}",
        details={
            "access_method": "custody_portal",
            "viewed": "integrity_report",
            "actor_name": token_record["recipient_name"]
        }
    )
    
    return {
        "success": True,
        "report_generated_at": now.isoformat(),
        "evidence": {
            "evidence_id": evidence.get("evidence_id"),
            "filename": evidence.get("filename"),
            "file_type": evidence.get("file_type"),
            "file_size": evidence.get("file_size"),
            "created_at": evidence.get("created_at")
        },
        "integrity": integrity,
        "chain_of_custody": {
            "events": chain,
            "total_events": len(chain),
            "first_event": chain[0] if chain else None,
            "last_event": chain[-1] if chain else None
        },
        "blockchain_proof": blockchain_proof,
        "legal_notice": {
            "disclaimer": "This report is generated automatically and should be reviewed by legal counsel before use in court proceedings.",
            "standard": "FRE 901/707 Compliant",
            "generated_for": token_record["recipient_name"],
            "recipient_role": token_record["recipient_role"]
        }
    }


@router.get("/download-court-package")
async def download_court_package_for_portal(
    token: str = Query(..., description="Access token")
):
    """
    Get court-grade evidence package for download.
    Only available if access_level is 'download' or 'full'.
    """
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    token_record = await db.custody_access_tokens.find_one({"token_hash": token_hash})
    
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid access token")
    
    if token_record.get("revoked"):
        raise HTTPException(status_code=403, detail="Access has been revoked")
    
    expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Access token has expired")
    
    if token_record["access_level"] not in ["download", "full"]:
        raise HTTPException(status_code=403, detail="Download access not granted for this token")
    
    evidence_id = token_record["evidence_id"]
    
    # Generate court package
    court_package = await evidence_integrity_service.generate_court_package(
        evidence_id=evidence_id,
        generated_by=token_record["recipient_name"],
        purpose=f"Chain of Custody Portal - {token_record['recipient_role']}"
    )
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.EXPORTED,
        user_id=f"external_{token_record['recipient_role']}",
        details={
            "access_method": "custody_portal",
            "export_type": "court_package",
            "actor_name": token_record["recipient_name"]
        }
    )
    
    return court_package
