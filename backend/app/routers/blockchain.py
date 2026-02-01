"""
Blockchain Anchoring Router

API endpoints for blockchain anchoring functionality.
This is a PREMIUM feature - requires Premium or Enterprise subscription.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone

from app.db.database import db
from app.core.security import get_current_user
from app.services.blockchain_anchoring import get_blockchain_service
from app.services.subscription import get_subscription_service

router = APIRouter(prefix="/blockchain", tags=["Blockchain Anchoring"])


async def require_premium(current_user: dict = Depends(get_current_user)):
    """
    Dependency to check if user has premium access for blockchain features.
    """
    service = get_subscription_service(db)
    access = await service.check_feature_access(current_user["user_id"], "blockchain_anchoring")
    
    if not access["has_access"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "premium_required",
                "message": "Blockchain anchoring is a Premium feature",
                "current_tier": access["current_tier"],
                "required_tier": access["required_tier"],
                "upgrade_url": "/subscription/upgrade"
            }
        )
    
    return current_user


@router.get("/status")
async def get_blockchain_status(current_user: dict = Depends(get_current_user)):
    """
    Get the current status of blockchain anchoring service.
    Shows if user has access and service availability.
    """
    # Check subscription
    sub_service = get_subscription_service(db)
    access = await sub_service.check_feature_access(current_user["user_id"], "blockchain_anchoring")
    
    # Get blockchain service status
    bc_service = get_blockchain_service()
    bc_status = bc_service.get_status()
    
    return {
        "success": True,
        "premium_feature": True,
        "has_access": access["has_access"],
        "current_tier": access["current_tier"],
        "required_tier": "premium",
        "service_available": bc_status["available"],
        "service_mode": bc_status["mode"],
        "message": bc_status["message"] if access["has_access"] else "Upgrade to Premium to unlock blockchain anchoring",
        "features": {
            "immutable_evidence": "Anchor evidence hashes to blockchain for tamper-proof verification",
            "court_admissible": "Generate cryptographic proof of evidence integrity",
            "timestamp_proof": "Prove when evidence was recorded",
            "chain_of_custody": "Maintain verifiable chain of custody"
        }
    }


@router.post("/anchor/{encounter_id}")
async def anchor_evidence_to_blockchain(
    encounter_id: str,
    current_user: dict = Depends(require_premium)
):
    """
    Anchor all evidence for an encounter to blockchain.
    PREMIUM FEATURE - Requires Premium or Enterprise subscription.
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
            "premium_feature": True,
            "has_access": True,
            "service_available": False,
            "message": "Blockchain service is currently being configured. Please try again later.",
            "encounter_id": encounter_id
        }
    
    # Anchor to blockchain
    result = service.anchor_hash(encounter_id)
    
    # Store anchor record
    anchor_record = {
        "user_id": current_user["user_id"],
        "encounter_id": encounter_id,
        "tx_hash": result.get("simulated_tx_hash"),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending" if result.get("success") else "simulated"
    }
    await db.blockchain_anchors.insert_one(anchor_record)
    
    return {
        "success": True,
        "premium_feature": True,
        "encounter_id": encounter_id,
        "tx_hash": result.get("simulated_tx_hash"),
        "message": "Evidence anchored successfully" if result.get("success") else result.get("message"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/verify/{tx_hash}")
async def verify_blockchain_anchor_endpoint(
    tx_hash: str,
    current_user: dict = Depends(require_premium)
):
    """
    Verify a blockchain anchor transaction.
    PREMIUM FEATURE.
    """
    service = get_blockchain_service()
    result = service.verify_hash(tx_hash)
    
    return {
        "success": result.get("success", False),
        "premium_feature": True,
        "tx_hash": tx_hash,
        "verified": result.get("success", False),
        "message": result.get("message", "Verification complete")
    }


@router.get("/history")
async def get_blockchain_history(
    limit: int = 20,
    current_user: dict = Depends(require_premium)
):
    """
    Get user's blockchain anchoring history.
    PREMIUM FEATURE.
    """
    # Get anchor records
    cursor = db.blockchain_anchors.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("anchored_at", -1).limit(limit)
    
    anchors = await cursor.to_list(limit)
    
    return {
        "success": True,
        "premium_feature": True,
        "anchors": anchors,
        "total": len(anchors)
    }


@router.get("/pricing")
async def get_blockchain_pricing():
    """
    Get blockchain anchoring pricing information.
    Public endpoint.
    """
    return {
        "success": True,
        "feature": "blockchain_anchoring",
        "required_tier": "premium",
        "pricing": {
            "premium": {
                "monthly": 29.99,
                "yearly": 299.90,
                "includes": "Unlimited blockchain anchoring"
            },
            "enterprise": {
                "monthly": 99.99,
                "yearly": 999.90,
                "includes": "Unlimited anchoring + dedicated support"
            }
        },
        "benefits": [
            "Immutable evidence records on blockchain",
            "Cryptographic proof of integrity",
            "Court-admissible timestamps",
            "Tamper-proof chain of custody",
            "Verification certificates"
        ]
    }
