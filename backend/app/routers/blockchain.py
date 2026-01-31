"""
Blockchain Anchoring Router
API endpoints for anchoring evidence to Polygon blockchain
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone

from app.db.database import db
from app.routers.auth import get_current_user
from app.services.blockchain_anchoring import (
    anchor_encounter_evidence,
    verify_blockchain_anchor,
    is_blockchain_available,
    get_wallet_balance,
    blockchain_service
)

router = APIRouter(prefix="/blockchain", tags=["Blockchain Anchoring"])


@router.get("/status")
async def get_blockchain_status(current_user: dict = Depends(get_current_user)):
    """
    Get the current status of blockchain anchoring service.
    """
    available = is_blockchain_available()
    balance = get_wallet_balance() if available else 0
    
    return {
        "success": True,
        "available": available,
        "network": blockchain_service.web3.eth.chain_id if available else None,
        "network_name": "Polygon Mumbai Testnet" if available else "Not Connected",
        "wallet_balance_matic": balance,
        "low_balance_warning": balance < 0.1 if available else False
    }


@router.post("/anchor/{encounter_id}")
async def anchor_evidence_to_blockchain(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Anchor all evidence for an encounter to Polygon blockchain.
    Creates a permanent, verifiable record of evidence existence.
    """
    # Verify encounter belongs to user
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check if already anchored
    existing_anchor = await db.blockchain_anchors.find_one(
        {"encounter_id": encounter_id, "status": "confirmed"},
        {"_id": 0}
    )
    
    if existing_anchor:
        return {
            "success": True,
            "already_anchored": True,
            "anchor": existing_anchor
        }
    
    # Get evidence hashes for this encounter
    evidence_hashes = []
    cursor = db.evidence_hashes.find(
        {"encounter_id": encounter_id},
        {"_id": 0, "content_hash": 1, "chain_hash": 1}
    )
    
    async for record in cursor:
        if record.get("content_hash"):
            evidence_hashes.append(record["content_hash"])
        if record.get("chain_hash"):
            evidence_hashes.append(record["chain_hash"])
    
    if not evidence_hashes:
        raise HTTPException(
            status_code=400, 
            detail="No evidence hashes found. Record evidence first."
        )
    
    # Metadata for the anchor
    metadata = {
        "encounter_type": encounter.get("encounter_type"),
        "started_at": encounter.get("started_at"),
        "user_id_hash": encounter.get("user_id", "")[:8],  # Partial for privacy
        "evidence_count": len(evidence_hashes)
    }
    
    # Anchor to blockchain
    result = await anchor_encounter_evidence(encounter_id, evidence_hashes, metadata)
    
    if not result.get("success"):
        # Store as pending if blockchain unavailable
        if result.get("fallback"):
            pending_anchor = {
                "encounter_id": encounter_id,
                "user_id": current_user["user_id"],
                "status": "pending",
                "evidence_hashes": evidence_hashes,
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "reason": result.get("error", "Blockchain service unavailable")
            }
            await db.blockchain_anchors.insert_one(pending_anchor)
            
            return {
                "success": True,
                "status": "pending",
                "message": "Evidence queued for blockchain anchoring when service is available",
                "evidence_count": len(evidence_hashes)
            }
        
        raise HTTPException(status_code=500, detail=result.get("error", "Anchoring failed"))
    
    # Store successful anchor
    anchor_record = {
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"],
        "status": "confirmed" if result.get("confirmed") else "pending_confirmation",
        "transaction_hash": result.get("transaction_hash"),
        "merkle_root": result.get("merkle_root"),
        "block_number": result.get("block_number"),
        "network": result.get("network"),
        "explorer_url": result.get("explorer_url"),
        "evidence_count": len(evidence_hashes),
        "gas_used": result.get("gas_used"),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "anchor_data": result.get("anchor_data")
    }
    
    await db.blockchain_anchors.insert_one(anchor_record)
    
    # Update encounter with anchor reference
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {
            "$set": {
                "blockchain_anchor": {
                    "transaction_hash": result.get("transaction_hash"),
                    "merkle_root": result.get("merkle_root"),
                    "network": result.get("network"),
                    "anchored_at": anchor_record["anchored_at"]
                }
            }
        }
    )
    
    return {
        "success": True,
        "status": "anchored",
        "transaction_hash": result.get("transaction_hash"),
        "merkle_root": result.get("merkle_root"),
        "block_number": result.get("block_number"),
        "network": result.get("network"),
        "explorer_url": result.get("explorer_url"),
        "evidence_count": len(evidence_hashes),
        "message": "Evidence permanently anchored to Polygon blockchain"
    }


@router.get("/verify/{transaction_hash}")
async def verify_anchor(transaction_hash: str):
    """
    Verify a blockchain anchor by checking the transaction on-chain.
    This is a public endpoint - anyone can verify.
    """
    result = verify_blockchain_anchor(transaction_hash)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Verification failed"))
    
    return {
        "success": True,
        "verified": result.get("verified"),
        "transaction_hash": transaction_hash,
        "block_number": result.get("block_number"),
        "block_timestamp": result.get("block_timestamp"),
        "confirmations": result.get("confirmations"),
        "anchor_data": result.get("anchor_data"),
        "network": result.get("network")
    }


@router.get("/encounter/{encounter_id}")
async def get_encounter_anchor(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get blockchain anchor details for an encounter.
    """
    anchor = await db.blockchain_anchors.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not anchor:
        return {
            "success": True,
            "anchored": False,
            "message": "This encounter has not been anchored to blockchain yet"
        }
    
    # If confirmed, verify on-chain
    if anchor.get("status") == "confirmed" and anchor.get("transaction_hash"):
        on_chain = verify_blockchain_anchor(anchor["transaction_hash"])
        anchor["on_chain_verification"] = on_chain
    
    return {
        "success": True,
        "anchored": True,
        "anchor": anchor
    }


@router.get("/certificate/{encounter_id}")
async def get_blockchain_certificate(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a blockchain anchoring certificate for court use.
    """
    anchor = await db.blockchain_anchors.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not anchor or anchor.get("status") != "confirmed":
        raise HTTPException(
            status_code=404, 
            detail="No confirmed blockchain anchor found for this encounter"
        )
    
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0, "encounter_type": 1, "started_at": 1, "ended_at": 1, "location": 1}
    )
    
    # Build certificate
    certificate = {
        "certificate_type": "BLOCKCHAIN_EVIDENCE_ANCHOR_CERTIFICATE",
        "certificate_id": f"BC-{encounter_id[:8].upper()}-{anchor.get('block_number', 'PENDING')}",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        
        "encounter": {
            "id": encounter_id,
            "type": encounter.get("encounter_type") if encounter else None,
            "started": encounter.get("started_at") if encounter else None,
            "ended": encounter.get("ended_at") if encounter else None
        },
        
        "blockchain_proof": {
            "network": "Polygon" + (" Mainnet" if anchor.get("network") == "mainnet" else " Mumbai Testnet"),
            "transaction_hash": anchor.get("transaction_hash"),
            "block_number": anchor.get("block_number"),
            "merkle_root": anchor.get("merkle_root"),
            "anchored_at": anchor.get("anchored_at"),
            "explorer_url": anchor.get("explorer_url"),
            "evidence_count": anchor.get("evidence_count")
        },
        
        "verification": {
            "status": "BLOCKCHAIN_VERIFIED",
            "method": "Polygon blockchain transaction with embedded Merkle root",
            "permanence": "Transaction is permanently recorded on public blockchain",
            "verifiable_by": "Anyone can verify using the transaction hash on Polygonscan"
        },
        
        "legal_statement": (
            "This certificate confirms that the cryptographic hash root (Merkle root) of "
            "the digital evidence associated with the above encounter has been permanently "
            "recorded on the Polygon blockchain. The blockchain transaction provides an "
            "immutable timestamp proving the evidence existed in its current form at the "
            "time of anchoring. This transaction is publicly verifiable by any party using "
            "the provided transaction hash on Polygonscan or any Polygon block explorer. "
            "The Merkle root encompasses all individual evidence hashes, allowing verification "
            "of any specific piece of evidence against this anchor."
        ),
        
        "platform": "JUSTICE Civil Rights Defense System",
        "blockchain": "Polygon (MATIC)",
        "hash_algorithm": "SHA-256 with Merkle tree aggregation"
    }
    
    return {"success": True, "certificate": certificate}


@router.get("/my-anchors")
async def get_user_anchors(
    limit: int = Query(default=20, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all blockchain anchors for the current user.
    """
    anchors = []
    cursor = db.blockchain_anchors.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("anchored_at", -1).limit(limit)
    
    async for anchor in cursor:
        anchors.append(anchor)
    
    return {
        "success": True,
        "anchors": anchors,
        "count": len(anchors)
    }
