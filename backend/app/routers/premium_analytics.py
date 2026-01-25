"""
Premium Analytics API - Predictive analytics, trends, and audit reports
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import io

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


@router.get("/audit-report/pdf")
async def export_audit_report_pdf(
    department_id: Optional[str] = None,
    state: Optional[str] = None,
    include_officers: bool = True,
    include_settlements: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and download audit report as PDF.
    
    Perfect for oversight committees and legal proceedings.
    """
    from fpdf import FPDF
    
    # Check user role for settlement data
    user_role = current_user.get("role", "citizen")
    if user_role == "citizen" and include_settlements:
        include_settlements = False
    
    # Generate report data
    report = await premium_analytics.generate_audit_report(
        department_id=department_id,
        state=state,
        include_officers=include_officers,
        include_settlements=include_settlements
    )
    
    # Create PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, "JUSTICE Platform", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Police Accountability Audit Report", ln=True, align="C")
    
    # Report metadata
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Report ID: {report['report_id']}", ln=True)
    pdf.cell(0, 8, f"Generated: {report['generated_at']}", ln=True)
    if state:
        pdf.cell(0, 8, f"State Filter: {state}", ln=True)
    pdf.ln(5)
    
    # Executive Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    
    summary = report.get("executive_summary", {})
    pdf.cell(0, 7, f"Departments Analyzed: {summary.get('departments_analyzed', 0)}", ln=True)
    pdf.cell(0, 7, f"Officers Tracked: {summary.get('total_officers_tracked', 0)}", ln=True)
    pdf.cell(0, 7, f"Total Violations: {summary.get('total_violations_recorded', 0)}", ln=True)
    if include_settlements and summary.get('total_settlements') != 'hidden':
        pdf.cell(0, 7, f"Total Settlements: ${summary.get('total_settlements', 0):,.2f}", ln=True)
    pdf.cell(0, 7, f"Avg Violations/Officer: {summary.get('average_violations_per_officer', 0)}", ln=True)
    pdf.ln(5)
    
    # Department Rankings
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Department Rankings", ln=True)
    
    # Best Accountability
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Top Performing Departments:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    for dept in report.get("department_rankings", {}).get("best_accountability", [])[:5]:
        score = dept.get("accountability_score", 0)
        pdf.cell(0, 6, f"  - {dept.get('name', 'Unknown')}: {score}/100", ln=True)
    pdf.ln(3)
    
    # Worst Accountability
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Departments Needing Improvement:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    for dept in report.get("department_rankings", {}).get("worst_accountability", [])[:5]:
        score = dept.get("accountability_score", 0)
        pdf.cell(0, 6, f"  - {dept.get('name', 'Unknown')}: {score}/100", ln=True)
    pdf.ln(5)
    
    # Recommendations
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Recommendations", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    for rec in report.get("recommendations", []):
        priority = rec.get("priority", "info").upper()
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(20, 6, f"[{priority}]")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, rec.get("recommendation", ""))
        pdf.ln(2)
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "This report is generated by the JUSTICE Platform for oversight and transparency purposes.", ln=True)
    pdf.cell(0, 5, "Data compiled from public records, court filings, and citizen reports.", ln=True)
    
    # Generate PDF bytes
    pdf_bytes = pdf.output()
    
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    state_suffix = f"_{state}" if state else ""
    filename = f"JUSTICE_Audit_Report{state_suffix}_{timestamp}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
