"""
Class Action Finder Router

AI-powered pattern matching to identify potential class action opportunities
based on similar violations across users.

Features:
- Pattern analysis across all violations
- Similarity scoring
- User connection for collective action
- Class action case tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import uuid
import os

from app.core.security import get_current_user
from app.db.database import db

router = APIRouter(prefix="/class-action", tags=["class-action"])


# ============== PYDANTIC MODELS ==============

class PatternAnalysisRequest(BaseModel):
    encounter_id: Optional[str] = None
    violation_types: Optional[List[str]] = None
    department_id: Optional[str] = None
    officer_badge: Optional[str] = None
    date_range_days: int = 365

class ClassActionInterest(BaseModel):
    pattern_id: str
    contact_consent: bool = True
    notes: Optional[str] = None

class ClassActionCase(BaseModel):
    title: str
    description: str
    violation_types: List[str]
    department_ids: List[str]
    lead_attorney_email: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

async def find_similar_violations(
    violation_types: List[str],
    department_id: Optional[str] = None,
    officer_badge: Optional[str] = None,
    exclude_user_id: Optional[str] = None,
    days: int = 365
) -> List[dict]:
    """Find similar violations across all users"""
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Build query
    query = {
        "violation_type": {"$in": violation_types},
        "created_at": {"$gte": start_date}
    }
    
    if department_id:
        query["department_id"] = department_id
    
    if officer_badge:
        query["officer_badge"] = officer_badge
    
    if exclude_user_id:
        query["user_id"] = {"$ne": exclude_user_id}
    
    # Find matching violations
    violations = await db.violations.find(
        query,
        {"_id": 0}
    ).to_list(500)
    
    return violations

async def calculate_pattern_strength(similar_violations: List[dict]) -> dict:
    """Calculate the strength of a pattern for class action potential"""
    
    if not similar_violations:
        return {"strength": "none", "score": 0}
    
    count = len(similar_violations)
    
    # Count unique users affected
    unique_users = len(set(v.get("user_id") for v in similar_violations if v.get("user_id")))
    
    # Count unique departments involved
    unique_depts = len(set(v.get("department_id") for v in similar_violations if v.get("department_id")))
    
    # Calculate severity score
    severity_weights = {"minor": 1, "moderate": 2, "serious": 3, "critical": 5}
    total_severity = sum(
        severity_weights.get(v.get("severity", "moderate"), 2)
        for v in similar_violations
    )
    avg_severity = total_severity / count if count > 0 else 0
    
    # Calculate overall score
    score = (
        (unique_users * 10) +  # Users affected is most important
        (count * 2) +  # Total violations
        (avg_severity * 5) +  # Severity
        (unique_depts * 3)  # Multi-department adds strength
    )
    
    # Determine strength level
    if score >= 100:
        strength = "very_strong"
    elif score >= 50:
        strength = "strong"
    elif score >= 25:
        strength = "moderate"
    elif score >= 10:
        strength = "weak"
    else:
        strength = "insufficient"
    
    return {
        "strength": strength,
        "score": round(score, 1),
        "factors": {
            "users_affected": unique_users,
            "total_violations": count,
            "average_severity": round(avg_severity, 2),
            "departments_involved": unique_depts
        }
    }

async def generate_ai_analysis(pattern_data: dict) -> str:
    """Generate AI analysis of class action potential"""
    try:
        from emergentintegrations.llm.chat import LlmChat
        
        llm = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            model="gpt-4o-mini"
        )
        
        prompt = f"""Analyze this pattern of civil rights violations for class action lawsuit potential:

Pattern Data:
- Violation Types: {pattern_data.get('violation_types', [])}
- Total Similar Cases: {pattern_data.get('similar_count', 0)}
- Users Affected: {pattern_data.get('users_affected', 0)}
- Departments Involved: {pattern_data.get('departments', [])}
- Time Period: Last {pattern_data.get('days', 365)} days
- Pattern Strength: {pattern_data.get('strength', {}).get('strength', 'unknown')}

Provide a brief analysis (2-3 paragraphs) covering:
1. The legal basis for a potential class action (reference relevant civil rights laws)
2. Strengths and weaknesses of this pattern as a class action case
3. Recommended next steps for affected individuals

Be specific and actionable. Focus on 42 USC 1983 and constitutional violations where applicable."""

        response = await llm.chat(user_message=prompt)
        return response
        
    except Exception as e:
        # Fallback analysis
        strength = pattern_data.get('strength', {}).get('strength', 'unknown')
        users = pattern_data.get('users_affected', 0)
        
        if strength in ['very_strong', 'strong']:
            return f"""Based on the pattern analysis, there appears to be strong potential for collective legal action.

With {users} affected individuals reporting similar violations, this pattern suggests systemic issues that may warrant a class action lawsuit under 42 USC 1983 (Civil Rights Act). The consistency of violation types across multiple incidents strengthens the case for demonstrating a "policy or custom" of constitutional violations.

Recommended next steps: 1) Document all evidence thoroughly, 2) Consult with a civil rights attorney experienced in class actions, 3) Connect with other affected individuals through this platform to coordinate efforts."""
        else:
            return f"""The current pattern shows {users} similar cases, which may not yet meet the threshold for a traditional class action but could support individual lawsuits with shared evidence.

Continue documenting incidents and monitoring for additional similar cases. As more affected individuals come forward, the viability of collective action may increase.

Consider consulting with a civil rights attorney to discuss individual case options and the potential for joining or initiating collective action in the future."""


# ============== ENDPOINTS ==============

@router.post("/analyze")
async def analyze_patterns(
    request: PatternAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Analyze a case for class action patterns"""
    user_id = current_user["user_id"]
    
    # Get violation types from request or from user's encounter
    violation_types = request.violation_types
    
    if request.encounter_id and not violation_types:
        # Get violations from the specific encounter
        encounter_violations = await db.violations.find(
            {"encounter_id": request.encounter_id},
            {"_id": 0, "violation_type": 1}
        ).to_list(50)
        violation_types = list(set(v.get("violation_type") for v in encounter_violations if v.get("violation_type")))
    
    if not violation_types:
        # Get all user's violation types
        user_violations = await db.violations.find(
            {"user_id": user_id},
            {"_id": 0, "violation_type": 1}
        ).to_list(100)
        violation_types = list(set(v.get("violation_type") for v in user_violations if v.get("violation_type")))
    
    if not violation_types:
        return {
            "success": False,
            "message": "No violations found to analyze. Report a violation first.",
            "patterns": []
        }
    
    # Find similar violations
    similar = await find_similar_violations(
        violation_types=violation_types,
        department_id=request.department_id,
        officer_badge=request.officer_badge,
        exclude_user_id=user_id,
        days=request.date_range_days
    )
    
    # Calculate pattern strength
    strength = await calculate_pattern_strength(similar)
    
    # Get department names
    dept_ids = list(set(v.get("department_id") for v in similar if v.get("department_id")))
    departments = await db.departments.find(
        {"department_id": {"$in": dept_ids}},
        {"_id": 0, "department_id": 1, "name": 1}
    ).to_list(50)
    dept_names = {d["department_id"]: d["name"] for d in departments}
    
    # Prepare pattern data for AI analysis
    pattern_data = {
        "violation_types": violation_types,
        "similar_count": len(similar),
        "users_affected": strength["factors"]["users_affected"],
        "departments": [dept_names.get(d, d) for d in dept_ids],
        "days": request.date_range_days,
        "strength": strength
    }
    
    # Get AI analysis
    ai_analysis = await generate_ai_analysis(pattern_data)
    
    # Create pattern record
    pattern_id = str(uuid.uuid4())[:12]
    
    pattern_doc = {
        "pattern_id": pattern_id,
        "user_id": user_id,
        "encounter_id": request.encounter_id,
        "violation_types": violation_types,
        "similar_count": len(similar),
        "strength": strength,
        "departments_involved": dept_ids,
        "analysis": ai_analysis,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.class_action_patterns.insert_one(pattern_doc)
    
    # Group similar violations by violation type
    by_type = {}
    for v in similar:
        vtype = v.get("violation_type", "unknown")
        if vtype not in by_type:
            by_type[vtype] = {"count": 0, "users": set(), "departments": set()}
        by_type[vtype]["count"] += 1
        if v.get("user_id"):
            by_type[vtype]["users"].add(v["user_id"])
        if v.get("department_id"):
            by_type[vtype]["departments"].add(v["department_id"])
    
    # Convert sets to counts
    breakdown = []
    for vtype, data in by_type.items():
        breakdown.append({
            "violation_type": vtype,
            "count": data["count"],
            "users_affected": len(data["users"]),
            "departments": len(data["departments"])
        })
    
    return {
        "success": True,
        "pattern_id": pattern_id,
        "your_violation_types": violation_types,
        "similar_cases_found": len(similar),
        "pattern_strength": strength,
        "breakdown_by_type": sorted(breakdown, key=lambda x: x["count"], reverse=True),
        "departments_with_pattern": [
            {"id": d, "name": dept_names.get(d, d)} for d in dept_ids
        ],
        "ai_analysis": ai_analysis,
        "class_action_viable": strength["strength"] in ["very_strong", "strong"],
        "next_steps": [
            "Review the AI analysis above",
            "Document all evidence thoroughly",
            "Consider connecting with other affected users",
            "Consult with a civil rights attorney"
        ] if strength["strength"] in ["very_strong", "strong", "moderate"] else [
            "Continue documenting incidents",
            "Check back as more cases are reported",
            "Consider individual legal consultation"
        ]
    }

@router.post("/express-interest")
async def express_class_action_interest(
    interest: ClassActionInterest,
    current_user: dict = Depends(get_current_user)
):
    """Express interest in joining a class action for a pattern"""
    
    # Verify pattern exists
    pattern = await db.class_action_patterns.find_one(
        {"pattern_id": interest.pattern_id},
        {"_id": 0}
    )
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    # Record interest
    interest_doc = {
        "interest_id": str(uuid.uuid4())[:12],
        "pattern_id": interest.pattern_id,
        "user_id": current_user["user_id"],
        "user_email": current_user["email"],
        "user_name": current_user.get("name"),
        "contact_consent": interest.contact_consent,
        "notes": interest.notes,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.class_action_interests.insert_one(interest_doc)
    
    # Count total interested users for this pattern
    total_interested = await db.class_action_interests.count_documents(
        {"pattern_id": interest.pattern_id}
    )
    
    return {
        "success": True,
        "message": "Your interest has been recorded",
        "total_interested_users": total_interested,
        "what_happens_next": [
            "You'll be notified when a class action is formally initiated",
            "Attorneys monitoring this pattern will see aggregated interest",
            "Your contact info will only be shared if you consented"
        ]
    }

@router.get("/patterns")
async def get_active_patterns(
    min_strength: Optional[str] = None,
    violation_type: Optional[str] = None,
    department_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get active class action patterns"""
    
    query = {}
    
    if min_strength:
        strength_order = ["insufficient", "weak", "moderate", "strong", "very_strong"]
        min_index = strength_order.index(min_strength) if min_strength in strength_order else 0
        valid_strengths = strength_order[min_index:]
        query["strength.strength"] = {"$in": valid_strengths}
    
    if violation_type:
        query["violation_types"] = violation_type
    
    if department_id:
        query["departments_involved"] = department_id
    
    patterns = await db.class_action_patterns.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    # Add interest counts
    for pattern in patterns:
        count = await db.class_action_interests.count_documents(
            {"pattern_id": pattern["pattern_id"]}
        )
        pattern["interested_users"] = count
    
    return {"patterns": patterns}

@router.get("/my-patterns")
async def get_my_patterns(current_user: dict = Depends(get_current_user)):
    """Get patterns the user has analyzed or expressed interest in"""
    
    # Patterns user analyzed
    analyzed = await db.class_action_patterns.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    # Patterns user expressed interest in
    interests = await db.class_action_interests.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "pattern_id": 1}
    ).to_list(50)
    
    interest_pattern_ids = [i["pattern_id"] for i in interests]
    
    interested_patterns = []
    if interest_pattern_ids:
        interested_patterns = await db.class_action_patterns.find(
            {"pattern_id": {"$in": interest_pattern_ids}},
            {"_id": 0}
        ).to_list(50)
    
    return {
        "analyzed_patterns": analyzed,
        "interested_patterns": interested_patterns
    }

@router.get("/stats")
async def get_class_action_stats(current_user: dict = Depends(get_current_user)):
    """Get overall class action statistics"""
    
    # Total patterns
    total_patterns = await db.class_action_patterns.count_documents({})
    
    # Strong patterns
    strong_patterns = await db.class_action_patterns.count_documents({
        "strength.strength": {"$in": ["strong", "very_strong"]}
    })
    
    # Total interested users
    total_interests = await db.class_action_interests.count_documents({})
    
    # Most common violation types in patterns
    pipeline = [
        {"$unwind": "$violation_types"},
        {"$group": {"_id": "$violation_types", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    common_types = await db.class_action_patterns.aggregate(pipeline).to_list(10)
    
    return {
        "total_patterns_analyzed": total_patterns,
        "viable_class_actions": strong_patterns,
        "total_interested_users": total_interests,
        "most_common_violations": [
            {"type": t["_id"], "count": t["count"]} for t in common_types
        ]
    }

@router.get("/pattern/{pattern_id}")
async def get_pattern_details(
    pattern_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific pattern"""
    
    pattern = await db.class_action_patterns.find_one(
        {"pattern_id": pattern_id},
        {"_id": 0}
    )
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    # Get interest count
    interest_count = await db.class_action_interests.count_documents(
        {"pattern_id": pattern_id}
    )
    
    # Check if current user has expressed interest
    user_interest = await db.class_action_interests.find_one(
        {"pattern_id": pattern_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    # Get department details
    dept_ids = pattern.get("departments_involved", [])
    departments = []
    if dept_ids:
        departments = await db.departments.find(
            {"department_id": {"$in": dept_ids}},
            {"_id": 0, "department_id": 1, "name": 1, "state": 1}
        ).to_list(50)
    
    return {
        **pattern,
        "interested_users": interest_count,
        "user_has_expressed_interest": user_interest is not None,
        "department_details": departments
    }
