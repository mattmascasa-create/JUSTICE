"""
AI Witness Corroboration Router
API endpoints for finding corroborating evidence
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.routers.auth import get_current_user
from app.services.witness_corroboration import witness_corroboration_service
from app.db.database import db

router = APIRouter(prefix="/corroboration", tags=["Witness Corroboration"])


@router.post("/analyze/{encounter_id}")
async def analyze_corroboration(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze an encounter for corroborating evidence.
    Searches multiple sources to find supporting evidence.
    """
    
    # Verify encounter belongs to user
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found or access denied")
    
    # Find corroborating evidence
    result = await witness_corroboration_service.find_corroborating_evidence(
        encounter_id=encounter_id,
        user_id=current_user.get("user_id")
    )
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/history")
async def get_corroboration_history(
    limit: int = Query(default=10, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get user's corroboration analysis history"""
    
    history = await witness_corroboration_service.get_corroboration_history(
        user_id=current_user.get("user_id"),
        limit=limit
    )
    
    return {
        "success": True,
        "history": history,
        "count": len(history)
    }


@router.get("/{corroboration_id}")
async def get_corroboration_details(
    corroboration_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get details of a specific corroboration analysis"""
    
    result = await db.corroborations.find_one(
        {
            "corroboration_id": corroboration_id,
            "user_id": current_user.get("user_id")
        },
        {"_id": 0}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Corroboration not found")
    
    return result


@router.get("/encounter/{encounter_id}/summary")
async def get_encounter_corroboration_summary(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a quick summary of corroboration for an encounter"""
    
    # Check if we already have a recent analysis
    existing = await db.corroborations.find_one(
        {
            "encounter_id": encounter_id,
            "user_id": current_user.get("user_id")
        },
        {"_id": 0}
    )
    
    if existing:
        return {
            "has_analysis": True,
            "corroboration_id": existing.get("corroboration_id"),
            "score": existing.get("corroboration_score"),
            "interpretation": existing.get("score_interpretation"),
            "generated_at": existing.get("generated_at"),
            "nearby_count": existing.get("nearby_encounters", {}).get("count", 0),
            "officer_complaints": existing.get("officer_history", {}).get("total_prior_complaints", 0)
        }
    
    return {
        "has_analysis": False,
        "message": "No corroboration analysis found. Use POST /corroboration/analyze/{encounter_id} to generate one."
    }
