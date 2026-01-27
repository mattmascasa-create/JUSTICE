"""
Legal Services Router - FOIA Requests, Legal Briefs, Miranda Detection
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from app.routers.auth import get_current_user
from app.services.legal_services import foia_generator, miranda_detector, legal_brief_generator
from app.db.database import db

router = APIRouter(prefix="/legal", tags=["Legal Services"])


# Request Models
class FOIARequest(BaseModel):
    requester_name: str
    requester_address: str
    requester_email: str
    department_name: str
    department_address: str
    incident_date: str
    incident_location: str
    officer_names: Optional[List[str]] = None
    officer_badges: Optional[List[str]] = None
    state: Optional[str] = "DEFAULT"
    additional_details: Optional[str] = None


class MirandaAnalysisRequest(BaseModel):
    transcript: str
    encounter_type: Optional[str] = "general"
    encounter_id: Optional[str] = None


class LegalBriefRequest(BaseModel):
    case_title: str
    plaintiff_name: str
    defendant_department: str
    incident_date: str
    incident_summary: str
    violations: List[dict]
    evidence_list: List[dict]
    witness_statements: Optional[List[str]] = None
    state: Optional[str] = "federal"


# FOIA Endpoints
@router.post("/foia/generate")
async def generate_foia_request(
    request: FOIARequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a FOIA/Public Records request for body camera footage"""
    
    result = foia_generator.generate_request(
        requester_name=request.requester_name,
        requester_address=request.requester_address,
        requester_email=request.requester_email,
        department_name=request.department_name,
        department_address=request.department_address,
        incident_date=request.incident_date,
        incident_location=request.incident_location,
        officer_names=request.officer_names,
        officer_badges=request.officer_badges,
        state=request.state,
        additional_details=request.additional_details
    )
    
    # Save to database
    await db.foia_requests.insert_one({
        "user_id": current_user.get("user_id"),
        "request_id": result["request_id"],
        "department": request.department_name,
        "incident_date": request.incident_date,
        "state": request.state,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        **result
    }


@router.get("/foia/laws")
async def get_foia_laws():
    """Get list of state-specific FOIA laws"""
    from app.services.legal_services import FOIA_LAWS
    return {
        "success": True,
        "laws": FOIA_LAWS
    }


@router.get("/foia/my-requests")
async def get_my_foia_requests(
    current_user: dict = Depends(get_current_user)
):
    """Get user's FOIA request history"""
    requests = await db.foia_requests.find(
        {"user_id": current_user.get("user_id")},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "requests": requests,
        "count": len(requests)
    }


# Miranda Detection Endpoints
@router.post("/miranda/analyze")
async def analyze_miranda_rights(
    request: MirandaAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze transcript to detect if Miranda rights should have been read"""
    
    result = miranda_detector.analyze_transcript(
        transcript=request.transcript,
        encounter_type=request.encounter_type
    )
    
    # If encounter_id provided, update encounter with Miranda analysis
    if request.encounter_id:
        await db.encounters.update_one(
            {"encounter_id": request.encounter_id, "user_id": current_user.get("user_id")},
            {"$set": {"miranda_analysis": result}}
        )
    
    return {
        "success": True,
        **result
    }


@router.post("/miranda/analyze-encounter/{encounter_id}")
async def analyze_encounter_miranda(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Analyze an existing encounter for Miranda violations"""
    
    # Get encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get all transcriptions for this encounter
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id}
    ).to_list(1000)
    
    if not transcriptions:
        raise HTTPException(status_code=400, detail="No transcriptions found for this encounter")
    
    # Combine all transcription text
    full_transcript = " ".join([t.get("text", "") for t in transcriptions])
    
    # Analyze
    result = miranda_detector.analyze_transcript(
        transcript=full_transcript,
        encounter_type=encounter.get("encounter_type", "general")
    )
    
    # Update encounter
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {"miranda_analysis": result}}
    )
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        **result
    }


# Legal Brief Endpoints
@router.post("/brief/generate")
async def generate_legal_brief(
    request: LegalBriefRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a draft legal brief for civil rights violations"""
    
    result = await legal_brief_generator.generate_brief(
        case_title=request.case_title,
        plaintiff_name=request.plaintiff_name,
        defendant_department=request.defendant_department,
        incident_date=request.incident_date,
        incident_summary=request.incident_summary,
        violations=request.violations,
        evidence_list=request.evidence_list,
        witness_statements=request.witness_statements,
        state=request.state
    )
    
    # Save to database
    await db.legal_briefs.insert_one({
        "user_id": current_user.get("user_id"),
        "brief_id": result["brief_id"],
        "case_title": request.case_title,
        "defendant": request.defendant_department,
        "violations_count": len(request.violations),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        **result
    }


@router.post("/brief/from-encounter/{encounter_id}")
async def generate_brief_from_encounter(
    encounter_id: str,
    plaintiff_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a legal brief from an existing encounter's detected violations"""
    
    # Get encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get AI analysis if available
    ai_analysis = encounter.get("ai_analysis", {})
    
    # Build violations list
    violations = []
    for v in ai_analysis.get("violations", []):
        violations.append({
            "type": v.get("type", "constitutional_violation"),
            "amendment": v.get("amendment", "Fourth"),
            "description": v.get("description", ""),
            "severity": v.get("severity", 5),
            "evidence_quote": v.get("quote", "")
        })
    
    # Add any manual violation marks
    manual_marks = encounter.get("manual_violation_marks", [])
    for mark in manual_marks:
        violations.append({
            "type": mark.get("type", "marked_violation"),
            "description": mark.get("note", "Manually marked by user"),
            "severity": 7
        })
    
    if not violations:
        raise HTTPException(status_code=400, detail="No violations detected in this encounter")
    
    # Build evidence list
    evidence_list = []
    for media in encounter.get("media_files", []):
        evidence_list.append({
            "type": "Recording",
            "description": media,
            "hash": encounter.get("evidence_hash", ""),
            "timestamp": encounter.get("start_time", "")
        })
    
    # Get transcriptions for summary
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id}
    ).to_list(100)
    
    summary_text = " ".join([t.get("text", "")[:200] for t in transcriptions[:5]])
    
    # Generate brief
    result = await legal_brief_generator.generate_brief(
        case_title=f"{plaintiff_name} v. {encounter.get('department', 'Law Enforcement Agency')}",
        plaintiff_name=plaintiff_name,
        defendant_department=encounter.get("department", "Law Enforcement Agency"),
        incident_date=encounter.get("start_time", "")[:10] if encounter.get("start_time") else "Unknown",
        incident_summary=summary_text or "See attached evidence and transcriptions.",
        violations=violations,
        evidence_list=evidence_list,
        state="federal"
    )
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        **result
    }


@router.get("/brief/my-briefs")
async def get_my_legal_briefs(
    current_user: dict = Depends(get_current_user)
):
    """Get user's generated legal briefs"""
    briefs = await db.legal_briefs.find(
        {"user_id": current_user.get("user_id")},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "briefs": briefs,
        "count": len(briefs)
    }


# Legal Hotline Endpoints (Directory)
@router.get("/hotline/numbers")
async def get_legal_hotlines():
    """Get list of civil rights legal hotlines"""
    hotlines = [
        {
            "name": "ACLU National",
            "phone": "212-549-2500",
            "description": "American Civil Liberties Union",
            "hours": "9 AM - 5 PM ET",
            "website": "https://www.aclu.org"
        },
        {
            "name": "NAACP Legal Defense Fund",
            "phone": "212-965-2200",
            "description": "Civil rights legal assistance",
            "hours": "9 AM - 5 PM ET",
            "website": "https://www.naacpldf.org"
        },
        {
            "name": "National Lawyers Guild",
            "phone": "212-679-5100",
            "description": "Progressive legal organization",
            "hours": "Varies by chapter",
            "website": "https://www.nlg.org"
        },
        {
            "name": "Lawyers' Committee for Civil Rights",
            "phone": "202-662-8600",
            "description": "Pro bono civil rights legal services",
            "hours": "9 AM - 5 PM ET",
            "website": "https://www.lawyerscommittee.org"
        },
        {
            "name": "National Police Accountability Project",
            "phone": "510-663-5506",
            "description": "Dedicated to police misconduct cases",
            "hours": "9 AM - 5 PM PT",
            "website": "https://www.nlg-npap.org"
        },
        {
            "name": "Know Your Rights Camp Legal",
            "phone": "Contact via website",
            "description": "Colin Kaepernick's legal assistance program",
            "hours": "24/7 online resources",
            "website": "https://www.knowyourrightscamp.com"
        }
    ]
    
    return {
        "success": True,
        "hotlines": hotlines,
        "emergency_note": "In case of immediate danger, call 911. For legal emergencies during encounters, use the JUSTICE app's SOS feature to alert your attorney."
    }


@router.get("/hotline/by-state/{state}")
async def get_state_legal_resources(state: str):
    """Get state-specific legal resources"""
    
    # State-specific civil rights organizations
    state_resources = {
        "CA": [
            {"name": "ACLU of California", "phone": "415-621-2493", "website": "https://www.aclunc.org"},
            {"name": "California Lawyers Association", "phone": "916-516-1760", "website": "https://calawyers.org"}
        ],
        "NY": [
            {"name": "NYCLU", "phone": "212-607-3300", "website": "https://www.nyclu.org"},
            {"name": "Legal Aid Society", "phone": "212-577-3300", "website": "https://www.legalaidnyc.org"}
        ],
        "TX": [
            {"name": "ACLU of Texas", "phone": "713-942-8146", "website": "https://www.aclutx.org"},
            {"name": "Texas RioGrande Legal Aid", "phone": "888-988-9996", "website": "https://www.trla.org"}
        ],
        "FL": [
            {"name": "ACLU of Florida", "phone": "786-363-2700", "website": "https://www.aclufl.org"},
            {"name": "Florida Justice Institute", "phone": "305-358-2081", "website": "https://www.floridajusticeinstitute.org"}
        ],
        "IL": [
            {"name": "ACLU of Illinois", "phone": "312-201-9740", "website": "https://www.aclu-il.org"},
            {"name": "Chicago Lawyers' Committee", "phone": "312-630-9744", "website": "https://www.clccrul.org"}
        ]
    }
    
    resources = state_resources.get(state.upper(), [])
    
    return {
        "success": True,
        "state": state.upper(),
        "resources": resources,
        "note": "Contact your local bar association for additional referrals to civil rights attorneys."
    }
