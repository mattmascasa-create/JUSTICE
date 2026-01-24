"""
Know Your Rights Training Router
Interactive learning endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.rights_training import rights_training_service

router = APIRouter(prefix="/training", tags=["Rights Training"])


class SubmitAnswerRequest(BaseModel):
    scenario_id: str
    answer_id: str


@router.get("/categories")
async def get_categories():
    """Get all training categories"""
    categories = rights_training_service.get_categories()
    return {"categories": categories}


@router.get("/scenarios")
async def get_scenarios(category: Optional[str] = None):
    """Get scenarios, optionally filtered by category"""
    scenarios = rights_training_service.get_scenarios(category)
    # Remove correct answers from response
    safe_scenarios = []
    for s in scenarios:
        safe_s = {**s}
        safe_s["options"] = [{"id": o["id"], "text": o["text"]} for o in s["options"]]
        safe_scenarios.append(safe_s)
    return {"scenarios": safe_scenarios, "count": len(safe_scenarios)}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a specific scenario"""
    scenario = rights_training_service.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Remove correct answers
    safe_scenario = {**scenario}
    safe_scenario["options"] = [{"id": o["id"], "text": o["text"]} for o in scenario["options"]]
    return safe_scenario


@router.get("/progress")
async def get_progress(current_user: dict = Depends(get_current_user)):
    """Get user's training progress"""
    progress = await rights_training_service.get_user_progress(current_user["user_id"])
    return progress


@router.post("/submit")
async def submit_answer(
    request: SubmitAnswerRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit an answer to a scenario"""
    result = await rights_training_service.submit_answer(
        current_user["user_id"],
        request.scenario_id,
        request.answer_id
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to submit answer"))
    
    return result


@router.get("/badges")
async def get_badges():
    """Get all available badges"""
    badges = rights_training_service.get_badges()
    return {"badges": badges}


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get top learners"""
    leaders = await rights_training_service.get_leaderboard(limit)
    return {"leaderboard": leaders}
