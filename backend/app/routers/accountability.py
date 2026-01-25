"""
Officer Accountability Router
Public transparency portal and officer/department tracking
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.core.security import get_current_user, get_current_user_optional
from app.services.accountability import accountability_service
from app.models.accountability import (
    OfficerCreate, DepartmentCreate,
    ViolationType, ViolationSeverity
)

router = APIRouter(prefix="/accountability", tags=["Accountability"])


# ============== Request Models ==============

class ReportViolationRequest(BaseModel):
    badge_number: str
    department_name: str
    department_city: Optional[str] = None
    department_state: str
    violation_type: str
    severity: str
    description: str
    incident_date: str
    incident_location: Optional[dict] = None
    encounter_id: Optional[str] = None
    evidence_ids: Optional[List[str]] = None
    ai_analysis_id: Optional[str] = None
    ai_confidence: Optional[float] = None


class UpdateViolationOutcomeRequest(BaseModel):
    outcome: str  # sustained, not_sustained, exonerated, unfounded
    disciplinary_action: Optional[str] = None
    settlement_amount: Optional[float] = None


class CreateOfficerRequest(BaseModel):
    badge_number: str
    department_id: str
    first_name: str
    last_name: str
    rank: Optional[str] = "Officer"
    unit: Optional[str] = None
    hire_date: Optional[str] = None


class CreateDepartmentRequest(BaseModel):
    name: str
    city: str
    state: str
    county: Optional[str] = None
    jurisdiction_type: str = "municipal"
    total_officers: Optional[int] = None
    website: Optional[str] = None


# ============== Public Endpoints (No Auth Required) ==============

@router.get("/public/departments")
async def get_public_departments(
    state: Optional[str] = Query(default=None, description="Filter by state"),
    sort_by: str = Query(default="accountability_score", enum=["accountability_score", "total_violations", "name"]),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Get public department scorecards.
    No authentication required - this is public transparency data.
    """
    departments = await accountability_service.search_departments(
        state=state,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    
    # Calculate total count
    total = await accountability_service.search_departments(state=state, limit=10000)
    
    return {
        "departments": departments,
        "total": len(total),
        "limit": limit,
        "offset": offset
    }


@router.get("/public/departments/{department_id}")
async def get_public_department(department_id: str):
    """Get public department scorecard by ID"""
    department = await accountability_service.get_department(department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Get officers with violations in this department
    problem_officers = await accountability_service.search_officers(
        department_id=department_id,
        min_violations=1,
        limit=20
    )
    
    return {
        "department": department,
        "officers_with_violations": problem_officers,
        "officer_count": len(problem_officers)
    }


@router.get("/public/officers")
async def search_public_officers(
    query: Optional[str] = Query(default=None, description="Search by name or badge"),
    department_id: Optional[str] = None,
    min_violations: Optional[int] = Query(default=None, ge=1),
    max_score: Optional[float] = Query(default=None, le=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Search officers in the accountability database.
    Public access for transparency.
    """
    officers = await accountability_service.search_officers(
        query=query,
        department_id=department_id,
        min_violations=min_violations,
        max_score=max_score,
        limit=limit,
        offset=offset
    )
    
    return {
        "officers": officers,
        "count": len(officers),
        "limit": limit,
        "offset": offset
    }


@router.get("/public/officers/quick-lookup")
async def quick_officer_lookup(
    badge: str = Query(..., description="Badge number to search"),
    state: Optional[str] = Query(default=None, description="State abbreviation (optional)")
):
    """
    Quick badge number lookup across all departments.
    Designed for citizens to check officer accountability during encounters.
    No authentication required - public transparency data.
    """
    from app.db.database import db
    
    # Search for officers with matching badge number
    query = {"badge_number": {"$regex": f"^{badge}$", "$options": "i"}}
    
    # If state provided, filter by department state
    if state:
        # Get department IDs in this state
        departments = await db.accountability_departments.find(
            {"state": state.upper()},
            {"_id": 0, "department_id": 1}
        ).to_list(100)
        dept_ids = [d["department_id"] for d in departments]
        query["department_id"] = {"$in": dept_ids}
    
    officers = await db.officers.find(
        query,
        {"_id": 0}
    ).to_list(10)
    
    if not officers:
        return {
            "found": False,
            "message": f"No officer found with badge #{badge}" + (f" in {state}" if state else ""),
            "officers": []
        }
    
    # Enrich with violation summaries
    results = []
    for officer in officers:
        # Get recent violations
        recent_violations = await db.officer_violations.find(
            {"officer_id": officer["officer_id"]},
            {"_id": 0, "violation_type": 1, "severity": 1, "outcome": 1, "incident_date": 1}
        ).sort("incident_date", -1).limit(5).to_list(5)
        
        results.append({
            "officer_id": officer["officer_id"],
            "badge_number": officer["badge_number"],
            "full_name": officer.get("full_name", "Unknown"),
            "rank": officer.get("rank", "Officer"),
            "department_name": officer.get("department_name", "Unknown"),
            "department_id": officer.get("department_id"),
            "accountability_score": officer.get("accountability_score", 100),
            "total_violations": officer.get("total_violations", 0),
            "sustained_violations": officer.get("sustained_violations", 0),
            "pending_violations": officer.get("pending_violations", 0),
            "recent_violations": recent_violations,
            "warning_level": _get_warning_level(officer.get("accountability_score", 100))
        })
    
    return {
        "found": True,
        "count": len(results),
        "officers": results
}


def _get_warning_level(score: float) -> dict:
    """Get warning level based on accountability score"""
    if score >= 80:
        return {"level": "low", "color": "green", "message": "Officer has good accountability record"}
    elif score >= 60:
        return {"level": "medium", "color": "yellow", "message": "Exercise normal caution"}
    elif score >= 40:
        return {"level": "elevated", "color": "orange", "message": "Officer has documented issues - record interaction"}
    else:
        return {"level": "high", "color": "red", "message": "Multiple violations on record - strongly recommend recording"}


@router.get("/public/officers/badge/{badge_number}")
async def get_officer_by_badge(
    badge_number: str,
    department_id: str = Query(..., description="Department ID")
):
    """Look up officer by badge number"""
    officer = await accountability_service.get_officer_by_badge(badge_number, department_id)
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    violations = await accountability_service.get_officer_violations(officer["officer_id"])
    
    return {
        "officer": officer,
        "violations": violations,
        "violation_count": len(violations)
    }


@router.get("/public/officers/{officer_id}")
async def get_public_officer(officer_id: str):
    """Get public officer profile and violation history"""
    officer = await accountability_service.get_officer(officer_id)
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    violations = await accountability_service.get_officer_violations(officer_id)
    
    return {
        "officer": officer,
        "violations": violations,
        "violation_count": len(violations)
    }


@router.get("/public/leaderboard")
async def get_department_leaderboard(
    state: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50)
):
    """Get department rankings - best and worst"""
    return await accountability_service.get_department_leaderboard(state=state, limit=limit)


@router.get("/public/stats")
async def get_public_stats():
    """Get aggregate accountability statistics"""
    from app.db.database import db
    
    total_departments = await db.accountability_departments.count_documents({})
    total_officers = await db.officers.count_documents({})
    total_violations = await db.officer_violations.count_documents({})
    sustained_violations = await db.officer_violations.count_documents({"outcome": "sustained"})
    pending_violations = await db.officer_violations.count_documents({"outcome": "pending"})
    
    # Get violation distribution
    violation_pipeline = [
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_type = await db.officer_violations.aggregate(violation_pipeline).to_list(10)
    
    # Get severity distribution
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_severity = await db.officer_violations.aggregate(severity_pipeline).to_list(10)
    
    # Get state distribution
    state_pipeline = [
        {"$group": {"_id": "$state", "count": {"$sum": 1}, "avg_score": {"$avg": "$accountability_score"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_state = await db.accountability_departments.aggregate(state_pipeline).to_list(10)
    
    # Calculate totals
    settlement_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$settlement_amount"}}}
    ]
    settlement_result = await db.officer_violations.aggregate(settlement_pipeline).to_list(1)
    total_settlements = settlement_result[0]["total"] if settlement_result else 0
    
    return {
        "total_departments": total_departments,
        "total_officers_tracked": total_officers,
        "total_violations": total_violations,
        "sustained_violations": sustained_violations,
        "pending_violations": pending_violations,
        "total_settlements": total_settlements,
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in by_type if v["_id"]],
        "violations_by_severity": [{"severity": s["_id"], "count": s["count"]} for s in by_severity if s["_id"]],
        "by_state": [{"state": s["_id"], "departments": s["count"], "avg_score": round(s["avg_score"], 1)} for s in by_state if s["_id"]]
    }


@router.get("/public/violation-types")
async def get_violation_types():
    """Get all violation types and their descriptions"""
    return {
        "violation_types": [
            {"type": "unlawful_search", "label": "Unlawful Search", "amendment": "4th", "severity_typical": "serious"},
            {"type": "unlawful_seizure", "label": "Unlawful Seizure", "amendment": "4th", "severity_typical": "serious"},
            {"type": "excessive_force", "label": "Excessive Force", "amendment": "4th", "severity_typical": "critical"},
            {"type": "false_arrest", "label": "False Arrest", "amendment": "4th", "severity_typical": "serious"},
            {"type": "miranda_violation", "label": "Miranda Violation", "amendment": "5th", "severity_typical": "moderate"},
            {"type": "coerced_confession", "label": "Coerced Confession", "amendment": "5th", "severity_typical": "critical"},
            {"type": "recording_interference", "label": "Recording Interference", "amendment": "1st", "severity_typical": "moderate"},
            {"type": "speech_suppression", "label": "Speech Suppression", "amendment": "1st", "severity_typical": "moderate"},
            {"type": "racial_profiling", "label": "Racial Profiling", "amendment": "14th", "severity_typical": "serious"},
            {"type": "discriminatory_enforcement", "label": "Discriminatory Enforcement", "amendment": "14th", "severity_typical": "serious"},
            {"type": "due_process_violation", "label": "Due Process Violation", "amendment": "14th", "severity_typical": "serious"},
            {"type": "dishonesty", "label": "Dishonesty", "amendment": None, "severity_typical": "serious"},
            {"type": "evidence_tampering", "label": "Evidence Tampering", "amendment": None, "severity_typical": "critical"},
            {"type": "intimidation", "label": "Intimidation", "amendment": None, "severity_typical": "moderate"},
            {"type": "retaliation", "label": "Retaliation", "amendment": None, "severity_typical": "serious"},
            {"type": "policy_violation", "label": "Policy Violation", "amendment": None, "severity_typical": "minor"},
            {"type": "conduct_unbecoming", "label": "Conduct Unbecoming", "amendment": None, "severity_typical": "minor"},
        ],
        "severity_levels": [
            {"level": "minor", "weight": 1, "description": "Warning-level offense"},
            {"level": "moderate", "weight": 3, "description": "Suspension-level offense"},
            {"level": "serious", "weight": 5, "description": "Termination-level offense"},
            {"level": "critical", "weight": 10, "description": "Criminal-level offense"}
        ]
    }


# ============== Authenticated Endpoints ==============

@router.post("/violations/report")
async def report_violation(
    request: ReportViolationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Report a violation against an officer.
    Requires authentication to track reporter.
    """
    # Find or create department
    department = await accountability_service.find_or_create_department(
        name=request.department_name,
        city=request.department_city,
        state=request.department_state
    )
    
    if not department:
        raise HTTPException(status_code=400, detail="Could not create department record")
    
    result = await accountability_service.report_violation(
        badge_number=request.badge_number,
        department_id=department["department_id"],
        violation_type=request.violation_type,
        severity=request.severity,
        description=request.description,
        incident_date=request.incident_date,
        reported_by=current_user["user_id"],
        encounter_id=request.encounter_id,
        evidence_ids=request.evidence_ids,
        ai_analysis_id=request.ai_analysis_id,
        ai_confidence=request.ai_confidence,
        incident_location=request.incident_location
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to report violation"))
    
    return result


@router.post("/officers")
async def create_officer(
    request: CreateOfficerRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new officer profile"""
    data = OfficerCreate(**request.dict())
    result = await accountability_service.create_officer(data, current_user["user_id"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create officer"))
    
    return result


@router.post("/departments")
async def create_department(
    request: CreateDepartmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new department"""
    data = DepartmentCreate(**request.dict())
    result = await accountability_service.create_department(data, current_user["user_id"])
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create department"))
    
    return result


@router.patch("/violations/{violation_id}/outcome")
async def update_violation_outcome(
    violation_id: str,
    request: UpdateViolationOutcomeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update violation outcome (for admins/attorneys)"""
    # TODO: Add role check for admin/attorney
    
    result = await accountability_service.update_violation_outcome(
        violation_id=violation_id,
        outcome=request.outcome,
        disciplinary_action=request.disciplinary_action,
        settlement_amount=request.settlement_amount,
        updated_by=current_user["user_id"]
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to update violation"))
    
    return result


@router.get("/my-reports")
async def get_my_reports(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100)
):
    """Get violations reported by the current user"""
    from app.db.database import db
    
    violations = await db.officer_violations.find(
        {"reported_by": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "violations": violations,
        "count": len(violations)
    }


# ============== Integration with Encounters ==============

@router.post("/encounters/{encounter_id}/link-officer")
async def link_officer_to_encounter(
    encounter_id: str,
    badge_number: str = Query(...),
    department_name: str = Query(...),
    department_state: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Link an officer to an encounter for tracking"""
    from app.db.database import db
    
    # Find or create department
    department = await accountability_service.find_or_create_department(
        name=department_name,
        state=department_state
    )
    
    if not department:
        raise HTTPException(status_code=400, detail="Could not create department")
    
    # Find or create officer
    officer = await accountability_service.find_or_create_officer(
        badge_number=badge_number,
        department_id=department["department_id"],
        department_name=department["name"],
        created_by=current_user["user_id"]
    )
    
    if not officer:
        raise HTTPException(status_code=400, detail="Could not create officer record")
    
    # Update encounter with officer info
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {
            "officer_badge": badge_number,
            "officer_id": officer["officer_id"],
            "officer_name": officer.get("full_name"),
            "department_id": department["department_id"],
            "department_name": department["name"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "officer_id": officer["officer_id"],
        "department_id": department["department_id"],
        "message": f"Linked Officer {officer.get('full_name')} (Badge #{badge_number}) to encounter"
    }
