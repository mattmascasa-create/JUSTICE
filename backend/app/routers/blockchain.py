"""
Blockchain Anchoring Router (STUBBED)

API endpoints for blockchain anchoring functionality.
Currently returns stubbed responses as blockchain is not configured.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone

from app.db.database import db
from app.core.security import get_current_user
from app.services.blockchain_anchoring import get_blockchain_service

router = APIRouter(prefix="/blockchain", tags=["Blockchain Anchoring"])


@router.get("/status")
async def get_blockchain_status(current_user: dict = Depends(get_current_user)):
    """
    Get the current status of blockchain anchoring service.
    """
    service = get_blockchain_service()
    status = service.get_status()
    
    return {
        "success": True,
        "available": status["available"],
        "network": None,
        "network_name": "Not Connected",
        "mode": status["mode"],
        "message": status["message"],
        "wallet_balance_matic": 0,
        "low_balance_warning": False
    }


@router.post("/anchor/{encounter_id}")
async def anchor_evidence_to_blockchain(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Anchor all evidence for an encounter to blockchain.
    Currently stubbed - returns simulated response.
    """
    # Verify encounter belongs to user
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    service = get_blockchain_service()
    
    if not service.is_available():
        return {
            "success": False,
            "stubbed": True,
            "message": "Blockchain anchoring is not available in this deployment",
            "encounter_id": encounter_id,
            "note": "Contact support to enable blockchain anchoring"
        }
    
    # This would normally anchor to blockchain
    result = service.anchor_hash(encounter_id)
    
    return {
        "success": result.get("success", False),
        "stubbed": True,
        "encounter_id": encounter_id,
        "simulated_tx_hash": result.get("simulated_tx_hash"),
        "message": result.get("message"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/verify/{tx_hash}")
async def verify_blockchain_anchor_endpoint(
    tx_hash: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify a blockchain anchor transaction.
    Currently stubbed.
    """
    service = get_blockchain_service()
    result = service.verify_hash(tx_hash)
    
    return {
        "success": False,
        "stubbed": True,
        "tx_hash": tx_hash,
        "verified": False,
        "message": "Blockchain verification is not available in this deployment"
    }


@router.get("/history")
async def get_blockchain_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's blockchain anchoring history.
    Currently returns empty list as blockchain is stubbed.
    """
    return {
        "success": True,
        "stubbed": True,
        "anchors": [],
        "total": 0,
        "message": "Blockchain anchoring history not available - feature is stubbed"
    }
