"""
Encounter Coaching API - Real-time guidance during police encounters
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.encounter_coach import encounter_coach, SITUATION_TEMPLATES, INSTANT_COACHING
from app.routers.auth import get_current_user
from app.db.database import db

router = APIRouter(prefix="/encounter-coach", tags=["Encounter Coaching"])


class AnalyzeRequest(BaseModel):
    transcript_chunk: str
    encounter_type: str = "general"  # traffic_stop, pedestrian_stop, home, arrest
    encounter_id: Optional[str] = None


class AskCoachRequest(BaseModel):
    question: str
    transcript_context: str = ""
    encounter_type: str = "general"


class QuickResponseRequest(BaseModel):
    scenario: str  # refuse_search, invoke_silence, request_attorney, etc.


@router.post("/analyze")
async def analyze_for_coaching(
    request: AnalyzeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze transcript chunk and return real-time coaching suggestions.
    
    Called continuously during an encounter to provide contextual guidance.
    Returns coaching messages sorted by priority (urgent first).
    
    Coaching categories:
    - de_escalation: Calming advice for tense situations
    - rights_reminder: Reminders about legal rights
    - response_suggestion: What to say in specific situations
    - warning: Important alerts about the situation
    - documentation: Reminders to note important details
    - safety: Physical safety guidance
    """
    if len(request.transcript_chunk) < 5:
        return {"success": True, "coaching": [], "message": "Chunk too short"}
    
    # Get instant coaching
    coaching = encounter_coach.analyze_for_coaching(
        transcript_chunk=request.transcript_chunk,
        encounter_type=request.encounter_type,
        encounter_id=request.encounter_id
    )
    
    # Log if there was coaching
    if coaching and request.encounter_id:
        await encounter_coach.log_coaching_delivered(
            encounter_id=request.encounter_id,
            user_id=current_user.get("user_id"),
            coaching_messages=coaching
        )
    
    return {
        "success": True,
        "coaching": coaching,
        "coaching_count": len(coaching),
        "encounter_type": request.encounter_type
    }


@router.post("/ask")
async def ask_coach(
    request: AskCoachRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask the AI coach a specific question during an encounter.
    
    Use for complex situations where instant coaching isn't sufficient.
    Returns brief, actionable guidance.
    
    Example questions:
    - "What should I do if they keep asking questions?"
    - "Can they search my car without my consent?"
    - "What do I say if they threaten to arrest me?"
    """
    if len(request.question) < 5:
        raise HTTPException(status_code=400, detail="Question too short")
    
    result = await encounter_coach.get_ai_coaching(
        transcript=request.transcript_context,
        encounter_type=request.encounter_type,
        specific_question=request.question
    )
    
    return {
        "success": result.get("success", False),
        "coaching": result.get("coaching") or result.get("fallback"),
        "tone": result.get("tone", "calm"),
        "generated_by": result.get("generated_by", "fallback")
    }


@router.get("/quick-response/{scenario}")
async def get_quick_response(
    scenario: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a quick response script for a specific scenario.
    
    Available scenarios:
    - refuse_search: How to refuse a search
    - invoke_silence: How to invoke right to remain silent
    - request_attorney: How to request an attorney
    - ask_if_detained: How to ask if you're being detained
    - ask_reason: How to ask why you're being stopped
    - assert_recording: How to assert your right to record
    - refuse_entry: How to refuse entry to your home
    - request_warrant: How to ask for a warrant
    
    Returns exact words to say and important notes.
    """
    response = encounter_coach.get_quick_response(scenario)
    
    return {
        "success": True,
        "scenario": scenario,
        "response": response
    }


@router.get("/quick-responses")
async def list_quick_responses():
    """List all available quick response scenarios"""
    scenarios = {
        "refuse_search": "How to refuse a search",
        "invoke_silence": "How to invoke right to remain silent",
        "request_attorney": "How to request an attorney",
        "ask_if_detained": "How to ask if you're being detained",
        "ask_reason": "How to ask why you're being stopped",
        "assert_recording": "How to assert your right to record",
        "refuse_entry": "How to refuse entry to your home",
        "request_warrant": "How to ask for a warrant"
    }
    
    return {
        "success": True,
        "scenarios": scenarios,
        "usage": "GET /encounter-coach/quick-response/{scenario}"
    }


@router.get("/situation/{encounter_type}/{situation}")
async def get_situation_coaching(
    encounter_type: str,
    situation: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get coaching for a specific situation within an encounter type.
    
    Encounter types: traffic_stop, pedestrian_stop, home, arrest
    
    Situations by type:
    - traffic_stop: initial, search_request, prolonged_stop
    - pedestrian_stop: initial, id_request, frisk
    - home: initial, entry_request, warrant
    - arrest: initial, questioning, booking
    """
    valid_types = ["traffic_stop", "pedestrian_stop", "home", "arrest"]
    if encounter_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid encounter type. Use: {valid_types}"
        )
    
    coaching = encounter_coach.get_situation_coaching(encounter_type, situation)
    
    if not coaching:
        available = list(SITUATION_TEMPLATES.get(encounter_type, {}).keys())
        raise HTTPException(
            status_code=404,
            detail=f"Situation not found. Available for {encounter_type}: {available}"
        )
    
    return {
        "success": True,
        "encounter_type": encounter_type,
        "situation": situation,
        "coaching": coaching
    }


@router.get("/triggers")
async def list_coaching_triggers():
    """
    List all phrases that trigger instant coaching.
    Useful for understanding what the system detects.
    """
    triggers_by_category = {}
    
    for situation_key, data in INSTANT_COACHING.items():
        category = data["category"].value
        if category not in triggers_by_category:
            triggers_by_category[category] = []
        
        triggers_by_category[category].append({
            "situation": situation_key,
            "triggers": data["triggers"],
            "coaching_preview": data["coaching"][:100] + "..." if len(data["coaching"]) > 100 else data["coaching"],
            "tone": data["tone"].value
        })
    
    return {
        "success": True,
        "categories": list(triggers_by_category.keys()),
        "triggers_by_category": triggers_by_category,
        "total_triggers": sum(len(d["triggers"]) for d in INSTANT_COACHING.values())
    }


@router.get("/encounter-types")
async def list_encounter_types():
    """List all encounter types with their available situation coaching"""
    return {
        "success": True,
        "encounter_types": {
            etype: {
                "situations": list(situations.keys()),
                "initial_coaching": situations.get("initial", "")[:100]
            }
            for etype, situations in SITUATION_TEMPLATES.items()
        }
    }


@router.post("/end-session/{encounter_id}")
async def end_coaching_session(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End a coaching session and get summary"""
    summary = encounter_coach.end_session(encounter_id)
    
    if not summary:
        return {
            "success": True,
            "message": "No active session found for this encounter"
        }
    
    return {
        "success": True,
        "session_summary": summary
    }


@router.get("/stats")
async def get_coaching_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get coaching usage statistics"""
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate by category
    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$unwind": "$coaching_messages"},
        {"$group": {
            "_id": "$coaching_messages.category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    by_category = await db.coaching_logs.aggregate(pipeline).to_list(20)
    
    # Total sessions
    total_sessions = await db.coaching_logs.count_documents(
        {"timestamp": {"$gte": cutoff}}
    )
    
    # Total coaching messages
    total_messages_pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$count"}}}
    ]
    total_result = await db.coaching_logs.aggregate(total_messages_pipeline).to_list(1)
    total_messages = total_result[0]["total"] if total_result else 0
    
    return {
        "success": True,
        "period_days": days,
        "stats": {
            "total_sessions": total_sessions,
            "total_coaching_messages": total_messages,
            "avg_messages_per_session": round(total_messages / max(total_sessions, 1), 1)
        },
        "by_category": [
            {"category": item["_id"], "count": item["count"]}
            for item in by_category
        ]
    }
