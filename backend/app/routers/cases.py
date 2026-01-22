"""
Cases Router - Case management endpoints
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends

from app.db.database import db
from app.core.security import get_current_user
from app.services.websocket import manager
from app.models.schemas import CaseCreate, CaseUpdate, CaseResponse

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse)
async def create_case(case_data: CaseCreate, current_user: dict = Depends(get_current_user)):
    """Create a new case"""
    case_id = f"case_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    case_doc = {
        "case_id": case_id,
        "user_id": current_user["user_id"],
        "title": case_data.title,
        "description": case_data.description,
        "status": "open",
        "incident_date": case_data.incident_date.isoformat(),
        "location": case_data.location,
        "department": case_data.department,
        "officer_name": case_data.officer_name,
        "officer_badge": case_data.officer_badge,
        "violation_type": case_data.violation_type,
        "severity": case_data.severity,
        "evidence_count": 0,
        "assigned_attorney_id": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.cases.insert_one(case_doc)
    
    # Send WebSocket notification
    await manager.send_to_user(current_user["user_id"], {
        "type": "case_created",
        "case_id": case_id,
        "title": case_data.title
    })
    
    return CaseResponse(
        case_id=case_id,
        user_id=current_user["user_id"],
        title=case_data.title,
        description=case_data.description,
        status="open",
        incident_date=case_data.incident_date,
        location=case_data.location,
        department=case_data.department,
        officer_name=case_data.officer_name,
        officer_badge=case_data.officer_badge,
        violation_type=case_data.violation_type,
        severity=case_data.severity,
        evidence_count=0,
        assigned_attorney_id=None,
        created_at=now,
        updated_at=now
    )


@router.get("", response_model=List[CaseResponse])
async def get_cases(current_user: dict = Depends(get_current_user)):
    """Get all cases for current user"""
    cases = await db.cases.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    result = []
    for case in cases:
        for field in ["incident_date", "created_at", "updated_at"]:
            if isinstance(case.get(field), str):
                case[field] = datetime.fromisoformat(case[field])
        result.append(CaseResponse(**case))
    
    return result


@router.get("/similar")
async def search_similar_cases(
    violation_type: str,
    department: Optional[str] = None,
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Search for similar cases and their outcomes"""
    query = {"violation_type": violation_type, "status": {"$in": ["resolved", "closed"]}}
    if department:
        query["department"] = department
    
    similar = await db.cases.find(query, {"_id": 0}).limit(10).to_list(length=10)
    
    # Landmark case references
    external_cases = [
        {
            "case_name": "Terry v. Ohio (1968)",
            "violation_type": "4th Amendment",
            "outcome": "Established 'stop and frisk' standards - officers need reasonable suspicion",
            "relevance": "high" if "4th" in violation_type.lower() or "search" in violation_type.lower() else "medium"
        },
        {
            "case_name": "Miranda v. Arizona (1966)",
            "violation_type": "5th Amendment",
            "outcome": "Established Miranda rights requirement before interrogation",
            "relevance": "high" if "5th" in violation_type.lower() or "miranda" in violation_type.lower() else "medium"
        },
        {
            "case_name": "Graham v. Connor (1989)",
            "violation_type": "Excessive Force",
            "outcome": "Established 'objective reasonableness' standard for force",
            "relevance": "high" if "force" in violation_type.lower() or "8th" in violation_type.lower() else "medium"
        }
    ]
    
    return {
        "similar_cases_in_system": similar,
        "landmark_cases": external_cases,
        "total_found": len(similar)
    }


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific case by ID"""
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(case.get(field), str):
            case[field] = datetime.fromisoformat(case[field])
    
    return CaseResponse(**case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: str, case_data: CaseUpdate, current_user: dict = Depends(get_current_user)):
    """Update a case"""
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    update_data = {k: v for k, v in case_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    old_status = case.get("status")
    
    await db.cases.update_one(
        {"case_id": case_id},
        {"$set": update_data}
    )
    
    updated_case = await db.cases.find_one({"case_id": case_id}, {"_id": 0})
    
    for field in ["incident_date", "created_at", "updated_at"]:
        if isinstance(updated_case.get(field), str):
            updated_case[field] = datetime.fromisoformat(updated_case[field])
    
    # Send WebSocket notification for status change
    if case_data.status and case_data.status != old_status:
        await manager.send_to_user(current_user["user_id"], {
            "type": "case_status_changed",
            "case_id": case_id,
            "old_status": old_status,
            "new_status": case_data.status
        })
    
    return CaseResponse(**updated_case)


@router.delete("/{case_id}")
async def delete_case(case_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a case and its evidence"""
    result = await db.cases.delete_one(
        {"case_id": case_id, "user_id": current_user["user_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Also delete associated evidence
    await db.evidence.delete_many({"case_id": case_id})
    
    return {"message": "Case deleted successfully"}


@router.get("/{case_id}/timeline")
async def get_case_timeline(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get timeline of events for a case"""
    case = await db.cases.find_one(
        {"case_id": case_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get case events
    events = await db.case_events.find(
        {"case_id": case_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Get evidence uploads as events
    evidence = await db.evidence.find(
        {"case_id": case_id},
        {"_id": 0, "evidence_id": 1, "file_name": 1, "uploaded_at": 1}
    ).to_list(100)
    
    timeline = []
    
    # Add case creation
    timeline.append({
        "event_type": "case_created",
        "description": f"Case '{case.get('title')}' was created",
        "timestamp": case.get("created_at")
    })
    
    # Add evidence uploads
    for ev in evidence:
        timeline.append({
            "event_type": "evidence_added",
            "description": f"Evidence uploaded: {ev.get('file_name')}",
            "timestamp": ev.get("uploaded_at"),
            "evidence_id": ev.get("evidence_id")
        })
    
    # Add custom events
    for event in events:
        timeline.append({
            "event_type": event.get("event_type"),
            "description": event.get("description"),
            "timestamp": event.get("created_at"),
            "metadata": event.get("metadata")
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"case_id": case_id, "timeline": timeline}
