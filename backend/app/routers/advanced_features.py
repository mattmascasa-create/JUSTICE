"""
Advanced Features Router - Rights Coach, Dead Man's Switch, Witness Network,
Violation Detection, Legal Precedents, and FOIA Automation
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.db.database import db
from app.core.security import get_current_user

# Import services
from app.services.rights_coach import get_ai_rights_guidance, get_quick_guidance, analyze_for_violations
from app.services.dead_mans_switch import (
    get_dead_mans_switch_config, update_dead_mans_switch_config,
    register_activity, check_inactivity, trigger_dead_mans_switch, disarm_switch
)
from app.services.witness_network import (
    enable_witness_mode, disable_witness_mode, update_witness_location,
    find_nearby_witnesses, broadcast_encounter_alert, join_as_witness,
    submit_witness_recording, get_encounter_witnesses, get_witness_stats
)
from app.services.violation_detection import (
    analyze_encounter_for_violations, get_quick_violation_flags,
    generate_violation_report, get_violation_statistics
)
from app.services.legal_precedent import (
    find_matching_precedents, get_case_law_by_amendment,
    search_case_law, estimate_case_value
)
from app.services.foia_automation import (
    generate_foia_request, submit_foia_request, update_foia_status,
    get_user_foia_requests, generate_appeal_letter, get_foia_statistics
)

router = APIRouter(prefix="/advanced", tags=["Advanced Features"])


# ============== RIGHTS COACH ==============

class RightsCoachRequest(BaseModel):
    transcript: str
    encounter_type: str = "general"
    context: Optional[dict] = None


@router.post("/rights-coach/guidance")
async def get_rights_guidance(
    request: RightsCoachRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered real-time rights guidance"""
    guidance = await get_ai_rights_guidance(
        transcript=request.transcript,
        encounter_type=request.encounter_type,
        current_context=request.context
    )
    return guidance


@router.post("/rights-coach/quick")
async def get_quick_rights_guidance(
    phrase: str,
    encounter_type: str = "general",
    current_user: dict = Depends(get_current_user)
):
    """Get instant rights guidance based on keyword matching (no AI latency)"""
    guidance = get_quick_guidance(phrase, encounter_type)
    return {"guidance": guidance, "instant": True}


# ============== DEAD MAN'S SWITCH ==============

class DeadMansSwitchConfig(BaseModel):
    enabled: bool = True
    inactivity_threshold: int = 60
    warning_time: int = 45
    auto_broadcast: bool = True
    auto_upload: bool = True
    notify_emergency_contacts: bool = True
    notify_witness_network: bool = True
    sensitivity: str = "normal"


@router.get("/dead-mans-switch/config")
async def get_switch_config(current_user: dict = Depends(get_current_user)):
    """Get dead man's switch configuration"""
    config = await get_dead_mans_switch_config(current_user["user_id"])
    return config


@router.put("/dead-mans-switch/config")
async def update_switch_config(
    config: DeadMansSwitchConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update dead man's switch configuration"""
    result = await update_dead_mans_switch_config(
        current_user["user_id"],
        config.model_dump()
    )
    return result


@router.post("/dead-mans-switch/activity/{encounter_id}")
async def register_user_activity(
    encounter_id: str,
    activity_type: str = "touch",
    current_user: dict = Depends(get_current_user)
):
    """Register user activity to reset the switch timer"""
    result = await register_activity(
        encounter_id=encounter_id,
        user_id=current_user["user_id"],
        activity_type=activity_type
    )
    return result


@router.get("/dead-mans-switch/status/{encounter_id}")
async def get_switch_status(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check dead man's switch status for an encounter"""
    status = await check_inactivity(encounter_id)
    return status


@router.post("/dead-mans-switch/trigger/{encounter_id}")
async def manual_trigger_switch(
    encounter_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger the dead man's switch (panic button)"""
    result = await trigger_dead_mans_switch(
        encounter_id=encounter_id,
        user_id=current_user["user_id"]
    )
    return result


@router.post("/dead-mans-switch/disarm/{encounter_id}")
async def disarm_dead_mans_switch(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Disarm the dead man's switch (user is okay)"""
    result = await disarm_switch(
        encounter_id=encounter_id,
        user_id=current_user["user_id"]
    )
    return result


# ============== WITNESS NETWORK ==============

class LocationData(BaseModel):
    lat: float
    lng: float


@router.post("/witness/enable")
async def enable_witness(
    location: LocationData,
    current_user: dict = Depends(get_current_user)
):
    """Enable witness mode at current location"""
    result = await enable_witness_mode(
        current_user["user_id"],
        location.model_dump()
    )
    return result


@router.post("/witness/disable")
async def disable_witness(current_user: dict = Depends(get_current_user)):
    """Disable witness mode"""
    result = await disable_witness_mode(current_user["user_id"])
    return result


@router.post("/witness/location")
async def update_location(
    location: LocationData,
    current_user: dict = Depends(get_current_user)
):
    """Update witness location"""
    result = await update_witness_location(
        current_user["user_id"],
        location.model_dump()
    )
    return result


@router.get("/witness/nearby")
async def get_nearby_witnesses(
    lat: float,
    lng: float,
    radius: float = 1.0,
    current_user: dict = Depends(get_current_user)
):
    """Find nearby witnesses"""
    witnesses = await find_nearby_witnesses(
        location={"lat": lat, "lng": lng},
        radius_miles=radius,
        exclude_user_id=current_user["user_id"]
    )
    return {"witnesses": witnesses, "count": len(witnesses)}


@router.post("/witness/broadcast/{encounter_id}")
async def broadcast_alert(
    encounter_id: str,
    location: LocationData,
    current_user: dict = Depends(get_current_user)
):
    """Broadcast encounter alert to nearby witnesses"""
    user = await db.users.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "name": 1}
    )
    
    result = await broadcast_encounter_alert(
        encounter_id=encounter_id,
        user_id=current_user["user_id"],
        user_name=user.get("name", "Someone"),
        location=location.model_dump()
    )
    return result


@router.post("/witness/join/{encounter_id}")
async def join_encounter_as_witness(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Join an encounter as a witness"""
    user = await db.users.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "name": 1}
    )
    
    result = await join_as_witness(
        encounter_id=encounter_id,
        witness_user_id=current_user["user_id"],
        witness_name=user.get("name", "Anonymous Witness")
    )
    return result


@router.get("/witness/stats")
async def get_my_witness_stats(current_user: dict = Depends(get_current_user)):
    """Get witness statistics for current user"""
    stats = await get_witness_stats(current_user["user_id"])
    return stats


@router.get("/witness/encounter/{encounter_id}")
async def get_witnesses_for_encounter(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all witnesses for an encounter"""
    witnesses = await get_encounter_witnesses(encounter_id)
    return {"witnesses": witnesses, "count": len(witnesses)}


# ============== VIOLATION DETECTION ==============

class ViolationAnalysisRequest(BaseModel):
    encounter_id: str
    transcript: str
    encounter_type: str = "general"


@router.post("/violations/analyze")
async def analyze_violations(
    request: ViolationAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Analyze encounter for constitutional violations"""
    analysis = await analyze_encounter_for_violations(
        encounter_id=request.encounter_id,
        transcript=request.transcript,
        encounter_type=request.encounter_type
    )
    return analysis


@router.post("/violations/quick-scan")
async def quick_violation_scan(
    transcript: str,
    current_user: dict = Depends(get_current_user)
):
    """Quick pattern-based violation scan (instant, no AI)"""
    flags = await get_quick_violation_flags(transcript)
    return {"flags": flags, "count": len(flags)}


@router.get("/violations/report/{encounter_id}")
async def get_violation_report(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate formal violation report for an encounter"""
    report = await generate_violation_report(encounter_id)
    return report


@router.get("/violations/stats")
async def get_violations_stats(current_user: dict = Depends(get_current_user)):
    """Get violation statistics for current user"""
    stats = await get_violation_statistics(current_user["user_id"])
    return stats


# ============== LEGAL PRECEDENT ==============

class PrecedentSearchRequest(BaseModel):
    encounter_id: str
    violations: List[dict]
    transcript: str
    encounter_type: str = "general"


@router.post("/legal/precedents")
async def search_precedents(
    request: PrecedentSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Find matching legal precedents for encounter"""
    result = await find_matching_precedents(
        encounter_id=request.encounter_id,
        violations=request.violations,
        transcript=request.transcript,
        encounter_type=request.encounter_type
    )
    return result


@router.get("/legal/cases/{amendment}")
async def get_cases_by_amendment(
    amendment: str,
    current_user: dict = Depends(get_current_user)
):
    """Get case law for a specific amendment"""
    cases = await get_case_law_by_amendment(amendment)
    return {"cases": cases, "count": len(cases)}


@router.post("/legal/search")
async def search_cases(
    keywords: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Search case law by keywords"""
    results = await search_case_law(keywords)
    return {"results": results, "count": len(results)}


class CaseValueRequest(BaseModel):
    violations: List[dict]
    has_injury: bool = False
    has_arrest: bool = False
    has_video: bool = True


@router.post("/legal/estimate-value")
async def estimate_case_worth(
    request: CaseValueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Estimate potential case value"""
    estimate = await estimate_case_value(
        violations=request.violations,
        has_injury=request.has_injury,
        has_arrest=request.has_arrest,
        has_video=request.has_video
    )
    return estimate


# ============== FOIA AUTOMATION ==============

class FOIAGenerateRequest(BaseModel):
    encounter_id: str
    department_code: Optional[str] = None
    custom_department: Optional[dict] = None


@router.post("/foia/generate")
async def generate_foia(
    request: FOIAGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a FOIA request for body cam footage"""
    result = await generate_foia_request(
        user_id=current_user["user_id"],
        encounter_id=request.encounter_id,
        department_code=request.department_code,
        custom_department=request.custom_department
    )
    return result


@router.post("/foia/submit/{request_id}")
async def submit_foia(
    request_id: str,
    submission_method: str = "email",
    current_user: dict = Depends(get_current_user)
):
    """Mark FOIA request as submitted"""
    result = await submit_foia_request(request_id, submission_method)
    return result


class FOIAStatusUpdate(BaseModel):
    status: str
    response_notes: Optional[str] = None
    documents_received: Optional[List[str]] = None


@router.put("/foia/status/{request_id}")
async def update_foia(
    request_id: str,
    update: FOIAStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update FOIA request status"""
    result = await update_foia_status(
        request_id=request_id,
        new_status=update.status,
        response_notes=update.response_notes,
        documents_received=update.documents_received
    )
    return result


@router.get("/foia/my-requests")
async def get_my_foia_requests(current_user: dict = Depends(get_current_user)):
    """Get all FOIA requests for current user"""
    requests = await get_user_foia_requests(current_user["user_id"])
    return {"requests": requests, "count": len(requests)}


@router.post("/foia/appeal/{request_id}")
async def generate_foia_appeal(
    request_id: str,
    denial_reason: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate appeal letter for denied FOIA request"""
    result = await generate_appeal_letter(request_id, denial_reason)
    return result


@router.get("/foia/stats")
async def get_foia_stats(current_user: dict = Depends(get_current_user)):
    """Get FOIA request statistics"""
    stats = await get_foia_statistics()
    return stats
