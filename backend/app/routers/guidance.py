"""
Smart Guidance API Router
Provides contextual next-step recommendations for users
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.db.database import db
from app.core.security import get_current_user
from app.services.guidance_service import get_user_guidance, get_onboarding_checklist

router = APIRouter(prefix="/guidance", tags=["guidance"])


@router.get("/suggestions")
async def get_suggestions(
    current_page: Optional[str] = Query(None, description="Current page the user is viewing"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get personalized guidance suggestions based on user state and context.
    
    Returns up to 5 prioritized suggestions with:
    - Title and description
    - Action URL and label
    - Priority level (critical, high, medium, low)
    - Category (setup, safety, legal, evidence, action)
    - Estimated time to complete
    """
    user_id = current_user["user_id"]
    guidance = get_user_guidance(db, user_id, current_page)
    
    return {
        "success": True,
        "data": guidance
    }


@router.get("/onboarding")
async def get_onboarding(
    current_user: dict = Depends(get_current_user)
):
    """
    Get onboarding checklist for new users.
    
    Returns a checklist of setup items with completion status.
    """
    user_id = current_user["user_id"]
    checklist = get_onboarding_checklist(db, user_id)
    
    return {
        "success": True,
        "data": checklist
    }


@router.post("/dismiss/{suggestion_id}")
async def dismiss_suggestion(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Dismiss a suggestion so it won't be shown again (for this session or permanently).
    """
    user_id = str(current_user["_id"])
    
    # Store dismissed suggestions
    db.user_preferences.update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"dismissed_suggestions": suggestion_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        },
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Suggestion dismissed"
    }


@router.post("/complete/{suggestion_id}")
async def mark_suggestion_complete(
    suggestion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a suggestion as completed.
    """
    user_id = str(current_user["_id"])
    
    db.user_preferences.update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"completed_suggestions": suggestion_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        },
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Suggestion marked complete"
    }
