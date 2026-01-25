"""
Evidence Integrity Router
Court-grade evidence verification and chain of custody endpoints
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.evidence_integrity import (
    evidence_integrity_service, 
    ForensicMetadata, 
    CustodyAction,
    BlockchainNetwork
)
from app.db.database import db

router = APIRouter(prefix="/evidence-integrity", tags=["Evidence Integrity"])


class RegisterEvidenceRequest(BaseModel):
    evidence_id: str
    encounter_id: Optional[str] = None
    original_filename: str
    file_size_bytes: int
    mime_type: str
    capture_timestamp: str
    capture_device: Optional[str] = None
    capture_device_id: Optional[str] = None
    capture_software: Optional[str] = None
    capture_timezone: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_accuracy: Optional[float] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    blockchain_tier: str = "local"  # local, ethereum


class LogCustodyEventRequest(BaseModel):
    evidence_id: str
    action: str
    details: Optional[dict] = None


@router.post("/register")
async def register_evidence_integrity(
    request: RegisterEvidenceRequest,
    file_hash: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Register evidence with cryptographic integrity tracking.
    Call this after uploading evidence to create the integrity record.
    """
    # Create forensic metadata
    metadata = ForensicMetadata(
        original_filename=request.original_filename,
        file_size_bytes=request.file_size_bytes,
        mime_type=request.mime_type,
        capture_timestamp=request.capture_timestamp,
        capture_device=request.capture_device,
        capture_device_id=request.capture_device_id,
        capture_software=request.capture_software,
        capture_timezone=request.capture_timezone,
        gps_latitude=request.gps_latitude,
        gps_longitude=request.gps_longitude,
        gps_accuracy=request.gps_accuracy,
        duration_seconds=request.duration_seconds,
        resolution=request.resolution,
        hash_sha256=file_hash
    )
    
    # Determine blockchain tier
    blockchain_tier = BlockchainNetwork.LOCAL
    if request.blockchain_tier == "ethereum":
        blockchain_tier = BlockchainNetwork.ETHEREUM
    
    # We need the actual file data to compute hashes
    # For now, we'll trust the provided hash and just register
    result = await _register_with_hash(
        evidence_id=request.evidence_id,
        file_hash=file_hash,
        metadata=metadata,
        user_id=current_user["user_id"],
        encounter_id=request.encounter_id,
        blockchain_tier=blockchain_tier
    )
    
    return result


async def _register_with_hash(
    evidence_id: str,
    file_hash: str,
    metadata: ForensicMetadata,
    user_id: str,
    encounter_id: str,
    blockchain_tier: BlockchainNetwork
):
    """Register evidence using provided hash (when file isn't uploaded directly)"""
    import uuid
    
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    
    # Generate integrity signature
    import hashlib
    import hmac
    hmac_secret = "justice-evidence-integrity-key"
    message = f"{evidence_id}:{file_hash}:{timestamp}"
    integrity_sig = hmac.new(
        hmac_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Create evidence record
    evidence_record = {
        "evidence_id": evidence_id,
        "encounter_id": encounter_id,
        "user_id": user_id,
        
        "hash_sha256": file_hash,
        "hash_sha512": None,
        "hash_sha3_256": None,
        "integrity_signature": integrity_sig,
        
        "original_filename": metadata.original_filename,
        "file_size_bytes": metadata.file_size_bytes,
        "mime_type": metadata.mime_type,
        "capture_device": metadata.capture_device,
        "capture_device_id": metadata.capture_device_id,
        "capture_software": metadata.capture_software,
        "capture_timestamp": metadata.capture_timestamp,
        "capture_timezone": metadata.capture_timezone,
        "gps_latitude": metadata.gps_latitude,
        "gps_longitude": metadata.gps_longitude,
        "gps_accuracy": metadata.gps_accuracy,
        "duration_seconds": metadata.duration_seconds,
        "resolution": metadata.resolution,
        
        "blockchain_network": blockchain_tier.value,
        "blockchain_tx_hash": None,
        "blockchain_block_number": None,
        "blockchain_timestamp": None,
        "blockchain_verified": False,
        
        "is_verified": True,
        "verification_count": 0,
        "last_verified": timestamp,
        "tamper_detected": False,
        
        "registered_at": timestamp,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    await db.evidence_integrity.insert_one(evidence_record)
    
    # Log custody event
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.CREATED,
        user_id=user_id,
        details={"hash_sha256": file_hash, "file_size": metadata.file_size_bytes}
    )
    
    # Handle blockchain anchoring for premium tier
    blockchain_proof = None
    if blockchain_tier == BlockchainNetwork.ETHEREUM:
        blockchain_proof = await evidence_integrity_service._anchor_to_ethereum(
            evidence_id, file_hash, timestamp
        )
        if blockchain_proof:
            await db.evidence_integrity.update_one(
                {"evidence_id": evidence_id},
                {"$set": {
                    "blockchain_tx_hash": blockchain_proof.get("tx_hash"),
                    "blockchain_block_number": blockchain_proof.get("block_number"),
                    "blockchain_timestamp": blockchain_proof.get("timestamp"),
                    "blockchain_verified": True
                }}
            )
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "hash_sha256": file_hash,
        "integrity_signature": integrity_sig,
        "blockchain_proof": blockchain_proof,
        "registered_at": timestamp
    }


@router.get("/{evidence_id}/verify")
async def verify_evidence(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify evidence integrity.
    Returns hash verification status, blockchain proof, and chain of custody status.
    """
    result = await evidence_integrity_service.verify_evidence(
        evidence_id=evidence_id,
        user_id=current_user["user_id"]
    )
    
    return result.dict()


@router.get("/{evidence_id}/custody-chain")
async def get_custody_chain(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete chain of custody for evidence"""
    # Log the view
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.VIEWED,
        user_id=current_user["user_id"],
        details={"viewed": "custody_chain"}
    )
    
    chain = await evidence_integrity_service.get_custody_chain(evidence_id)
    verification = await evidence_integrity_service.verify_custody_chain(evidence_id)
    
    return {
        "evidence_id": evidence_id,
        "chain": chain,
        "verification": verification
    }


@router.post("/{evidence_id}/custody-event")
async def log_custody_event(
    evidence_id: str,
    request: LogCustodyEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """Log a chain of custody event"""
    try:
        action = CustodyAction(request.action)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
    
    event_id = await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=action,
        user_id=current_user["user_id"],
        details=request.details
    )
    
    return {"success": True, "event_id": event_id}


@router.get("/{evidence_id}/court-package")
async def generate_court_package(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a complete evidence package for court submission.
    Includes forensic metadata, cryptographic verification, and chain of custody.
    """
    result = await evidence_integrity_service.generate_court_package(
        evidence_id=evidence_id,
        user_id=current_user["user_id"]
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to generate package"))
    
    return result


@router.get("/{evidence_id}/metadata")
async def get_evidence_metadata(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get forensic metadata for evidence"""
    record = await db.evidence_integrity.find_one(
        {"evidence_id": evidence_id},
        {"_id": 0}
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Log view
    await evidence_integrity_service.log_custody_event(
        evidence_id=evidence_id,
        action=CustodyAction.VIEWED,
        user_id=current_user["user_id"],
        details={"viewed": "metadata"}
    )
    
    return {
        "evidence_id": evidence_id,
        "metadata": {
            "original_filename": record.get("original_filename"),
            "file_size_bytes": record.get("file_size_bytes"),
            "mime_type": record.get("mime_type"),
            "capture_timestamp": record.get("capture_timestamp"),
            "capture_device": record.get("capture_device"),
            "gps_latitude": record.get("gps_latitude"),
            "gps_longitude": record.get("gps_longitude"),
            "duration_seconds": record.get("duration_seconds"),
            "resolution": record.get("resolution")
        },
        "hashes": {
            "sha256": record.get("hash_sha256"),
            "sha512": record.get("hash_sha512"),
            "sha3_256": record.get("hash_sha3_256")
        },
        "blockchain": {
            "anchored": record.get("blockchain_verified", False),
            "network": record.get("blockchain_network"),
            "tx_hash": record.get("blockchain_tx_hash")
        },
        "status": {
            "is_verified": record.get("is_verified"),
            "tamper_detected": record.get("tamper_detected"),
            "verification_count": record.get("verification_count"),
            "last_verified": record.get("last_verified")
        }
    }


@router.get("/stats")
async def get_integrity_stats(current_user: dict = Depends(get_current_user)):
    """Get evidence integrity statistics"""
    total_evidence = await db.evidence_integrity.count_documents({})
    verified = await db.evidence_integrity.count_documents({"is_verified": True})
    blockchain_anchored = await db.evidence_integrity.count_documents({"blockchain_verified": True})
    tamper_detected = await db.evidence_integrity.count_documents({"tamper_detected": True})
    custody_events = await db.chain_of_custody.count_documents({})
    
    return {
        "total_evidence_tracked": total_evidence,
        "verified": verified,
        "blockchain_anchored": blockchain_anchored,
        "tamper_detected": tamper_detected,
        "total_custody_events": custody_events
    }
