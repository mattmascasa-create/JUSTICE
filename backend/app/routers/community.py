"""
Community Vault Router - Anonymous community evidence database
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends

from app.db.database import db
from app.core.security import get_current_user
from app.models.schemas import CommunitySubmitRequest

router = APIRouter(prefix="/community", tags=["Community Vault"])


@router.post("/submit")
async def submit_to_vault(
    submission: CommunitySubmitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit encounter data to community vault (anonymized)"""
    submission_id = f"comm_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    submission_doc = {
        "submission_id": submission_id,
        "encounter_id": submission.encounter_id,
        "encounter_type": submission.encounter_type,
        "location_city": submission.location_city,
        "location_state": submission.location_state,
        "incident_date": submission.incident_date.isoformat(),
        "violations": submission.violations,
        "department": submission.department,
        "officer_badge": submission.officer_badge,
        "severity": submission.severity,
        "outcome": submission.outcome,
        "summary": submission.summary,
        "verified": False,
        "upvotes": 0,
        "submitted_at": now.isoformat()
    }
    
    await db.community_evidence.insert_one(submission_doc)
    
    return {
        "success": True,
        "submission_id": submission_id,
        "message": "Thank you for contributing to community safety"
    }


@router.get("/submissions")
async def get_community_submissions(
    state: Optional[str] = None,
    department: Optional[str] = None,
    violation_type: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get community vault submissions with filters"""
    query = {}
    if state:
        query["location_state"] = state
    if department:
        query["department"] = {"$regex": department, "$options": "i"}
    if violation_type:
        query["violations"] = {"$in": [violation_type]}
    
    submissions = await db.community_evidence.find(
        query, {"_id": 0}
    ).sort("submitted_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.community_evidence.count_documents(query)
    
    return {
        "submissions": submissions,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/stats")
async def get_community_stats():
    """Get aggregated community statistics"""
    total = await db.community_evidence.count_documents({})
    
    # By state
    state_pipeline = [
        {"$group": {"_id": "$location_state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_state = await db.community_evidence.aggregate(state_pipeline).to_list(10)
    
    # By violation type
    violation_pipeline = [
        {"$unwind": "$violations"},
        {"$group": {"_id": "$violations", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_violation = await db.community_evidence.aggregate(violation_pipeline).to_list(10)
    
    # By severity
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    by_severity = await db.community_evidence.aggregate(severity_pipeline).to_list(10)
    
    # By department (top offenders)
    dept_pipeline = [
        {"$match": {"department": {"$ne": None}}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    by_department = await db.community_evidence.aggregate(dept_pipeline).to_list(10)
    
    return {
        "total_submissions": total,
        "by_state": [{"state": s["_id"], "count": s["count"]} for s in by_state],
        "by_violation_type": [{"type": v["_id"], "count": v["count"]} for v in by_violation],
        "by_severity": [{"severity": s["_id"], "count": s["count"]} for s in by_severity],
        "by_department": [{"department": d["_id"], "count": d["count"]} for d in by_department]
    }


@router.get("/officer/{badge_number}")
async def get_officer_history(badge_number: str, department: Optional[str] = None):
    """Get incident history for a specific officer badge"""
    query = {"officer_badge": badge_number}
    if department:
        query["department"] = department
    
    incidents = await db.community_evidence.find(
        query, {"_id": 0}
    ).sort("incident_date", -1).to_list(100)
    
    # Aggregate stats
    total = len(incidents)
    violations = {}
    severities = {}
    
    for inc in incidents:
        for v in inc.get("violations", []):
            violations[v] = violations.get(v, 0) + 1
        sev = inc.get("severity", "unknown")
        severities[sev] = severities.get(sev, 0) + 1
    
    return {
        "badge_number": badge_number,
        "department": department,
        "total_incidents": total,
        "violations_by_type": violations,
        "severity_distribution": severities,
        "incidents": incidents[:20]
    }


@router.get("/department/{department_name}")
async def get_department_stats(department_name: str):
    """Get statistics for a specific department"""
    query = {"department": {"$regex": department_name, "$options": "i"}}
    
    incidents = await db.community_evidence.find(
        query, {"_id": 0}
    ).sort("incident_date", -1).to_list(500)
    
    total = len(incidents)
    
    # Unique officers
    officers = set()
    violations = {}
    severities = {}
    
    for inc in incidents:
        if inc.get("officer_badge"):
            officers.add(inc["officer_badge"])
        for v in inc.get("violations", []):
            violations[v] = violations.get(v, 0) + 1
        sev = inc.get("severity", "unknown")
        severities[sev] = severities.get(sev, 0) + 1
    
    return {
        "department": department_name,
        "total_incidents": total,
        "unique_officers_involved": len(officers),
        "violations_by_type": violations,
        "severity_distribution": severities,
        "recent_incidents": incidents[:10]
    }


@router.post("/{submission_id}/upvote")
async def upvote_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    """Upvote a community submission"""
    result = await db.community_evidence.update_one(
        {"submission_id": submission_id},
        {"$inc": {"upvotes": 1}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {"success": True, "message": "Upvoted successfully"}


@router.get("/search")
async def search_community_vault(
    query: str,
    limit: int = 20
):
    """Search community vault submissions"""
    search_query = {
        "$or": [
            {"summary": {"$regex": query, "$options": "i"}},
            {"department": {"$regex": query, "$options": "i"}},
            {"location_city": {"$regex": query, "$options": "i"}},
            {"violations": {"$in": [query]}}
        ]
    }
    
    results = await db.community_evidence.find(
        search_query, {"_id": 0}
    ).sort("submitted_at", -1).limit(limit).to_list(limit)
    
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }
