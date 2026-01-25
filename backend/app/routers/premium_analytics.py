"""
Premium Analytics API - Predictive analytics, trends, and audit reports
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from app.services.premium_analytics import premium_analytics
from app.routers.auth import get_current_user

router = APIRouter(prefix="/premium-analytics", tags=["Premium Analytics"])


class ComparisonRequest(BaseModel):
    department_ids: List[str]


@router.get("/risk-prediction/{department_id}")
async def get_risk_prediction(
    department_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get predictive risk assessment for a department.
    
    Analyzes historical violation patterns to predict future risk.
    Premium feature for oversight committees and legal teams.
    """
    result = await premium_analytics.get_department_risk_prediction(department_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return {"success": True, "prediction": result}


@router.get("/trends")
async def get_violation_trends(
    department_id: Optional[str] = None,
    state: Optional[str] = None,
    months: int = Query(default=12, ge=1, le=36),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze violation trends over time.
    
    Returns monthly breakdown, type distribution, and trend direction.
    """
    result = await premium_analytics.get_violation_trends(
        department_id=department_id,
        state=state,
        months=months
    )
    
    return {"success": True, "trends": result}


@router.get("/audit-report")
async def generate_audit_report(
    department_id: Optional[str] = None,
    state: Optional[str] = None,
    include_officers: bool = True,
    include_settlements: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate comprehensive audit report for oversight committees.
    
    Includes department rankings, violation analysis, and recommendations.
    """
    # Check user role for settlement data
    user_role = current_user.get("role", "citizen")
    if user_role == "citizen" and include_settlements:
        include_settlements = False  # Citizens don't see settlement details
    
    result = await premium_analytics.generate_audit_report(
        department_id=department_id,
        state=state,
        include_officers=include_officers,
        include_settlements=include_settlements
    )
    
    return {"success": True, "report": result}


@router.post("/compare-departments")
async def compare_departments(
    request: ComparisonRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Side-by-side comparison of multiple departments.
    
    Maximum 10 departments per comparison.
    """
    if len(request.department_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 departments per comparison")
    
    if len(request.department_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 departments to compare")
    
    result = await premium_analytics.compare_departments(request.department_ids)
    
    return {"success": True, "comparison": result}


@router.get("/state-overview/{state}")
async def get_state_overview(
    state: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get accountability overview for an entire state.
    """
    from app.db.database import db
    
    state = state.upper()
    
    # Get all departments in state
    departments = await db.accountability_departments.find(
        {"state": state},
        {"_id": 0}
    ).to_list(100)
    
    if not departments:
        raise HTTPException(status_code=404, detail=f"No departments found in {state}")
    
    dept_ids = [d["department_id"] for d in departments]
    
    # Get violation counts
    violations = await db.officer_violations.find(
        {"department_id": {"$in": dept_ids}},
        {"_id": 0, "severity": 1, "settlement_amount": 1, "outcome": 1}
    ).to_list(5000)
    
    # Get officer counts
    officers = await db.officers.find(
        {"department_id": {"$in": dept_ids}},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate averages
    avg_score = sum(d.get("accountability_score", 50) for d in departments) / len(departments)
    total_settlements = sum(v.get("settlement_amount") or 0 for v in violations)
    
    # Outcome breakdown
    outcomes = {}
    for v in violations:
        outcome = v.get("outcome", "pending")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    return {
        "success": True,
        "state": state,
        "overview": {
            "department_count": len(departments),
            "officer_count": len(officers),
            "violation_count": len(violations),
            "average_accountability_score": round(avg_score, 1),
            "total_settlements": total_settlements,
            "violations_per_department": round(len(violations) / len(departments), 1),
            "outcome_breakdown": outcomes
        },
        "best_department": max(departments, key=lambda x: x.get("accountability_score", 0)) if departments else None,
        "worst_department": min(departments, key=lambda x: x.get("accountability_score", 100)) if departments else None
    }


@router.get("/hotspots")
async def get_violation_hotspots(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Identify departments with highest violation rates (hotspots).
    """
    from app.db.database import db
    
    # Get all departments with their violation counts
    departments = await db.accountability_departments.find(
        {},
        {"_id": 0}
    ).to_list(200)
    
    hotspots = []
    for dept in departments:
        violations = await db.officer_violations.count_documents(
            {"department_id": dept["department_id"]}
        )
        officers = await db.officers.count_documents(
            {"department_id": dept["department_id"]}
        )
        
        if officers > 0:
            rate = violations / officers
            hotspots.append({
                "department_id": dept["department_id"],
                "name": dept.get("name"),
                "city": dept.get("city"),
                "state": dept.get("state"),
                "violation_count": violations,
                "officer_count": officers,
                "violations_per_officer": round(rate, 2),
                "accountability_score": dept.get("accountability_score")
            })
    
    # Sort by violations per officer
    hotspots.sort(key=lambda x: x["violations_per_officer"], reverse=True)
    
    return {
        "success": True,
        "hotspots": hotspots[:limit],
        "total_analyzed": len(hotspots)
    }
