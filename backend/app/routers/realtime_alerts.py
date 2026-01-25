"""
Real-Time Violation Alerts API - Attorney notification system for live encounters
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.realtime_alerts import realtime_alerts, AlertSeverity
from app.routers.auth import get_current_user
from app.db.database import db

router = APIRouter(prefix="/realtime-alerts", tags=["Real-Time Alerts"])


class AnalyzeChunkRequest(BaseModel):
    encounter_id: str
    transcript_chunk: str
    timestamp: Optional[str] = None


class ManualAlertRequest(BaseModel):
    encounter_id: str
    message: str
    severity: str = "high"  # critical, high, medium, low


class AcknowledgeRequest(BaseModel):
    alert_id: str


@router.post("/analyze-chunk")
async def analyze_transcript_chunk(
    request: AnalyzeChunkRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze a transcript chunk in real-time for potential violations.
    
    Called during live transcription to detect violations as they happen.
    Automatically sends WebSocket alerts to connected attorneys.
    
    Returns list of detected violations/alerts.
    """
    if len(request.transcript_chunk) < 5:
        return {"success": True, "alerts": [], "message": "Chunk too short"}
    
    alerts = await realtime_alerts.analyze_transcript_chunk(
        encounter_id=request.encounter_id,
        transcript_chunk=request.transcript_chunk,
        user_id=current_user.get("user_id"),
        timestamp=request.timestamp
    )
    
    return {
        "success": True,
        "alerts": alerts,
        "alert_count": len(alerts),
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/manual-alert")
async def trigger_manual_alert(
    request: ManualAlertRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually trigger an alert to notify attorney.
    
    Use when citizen needs immediate attorney attention.
    Severity levels: critical, high, medium, low
    """
    valid_severities = ["critical", "high", "medium", "low"]
    if request.severity.lower() not in valid_severities:
        raise HTTPException(status_code=400, detail=f"Invalid severity. Use: {valid_severities}")
    
    alert = await realtime_alerts.trigger_manual_alert(
        encounter_id=request.encounter_id,
        user_id=current_user.get("user_id"),
        message=request.message,
        severity=request.severity.lower()
    )
    
    return {
        "success": True,
        "alert": alert,
        "message": "Alert sent to your attorney"
    }


@router.get("/encounter/{encounter_id}")
async def get_encounter_alerts(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all alerts for a specific encounter"""
    alerts = await realtime_alerts.get_encounter_alerts(encounter_id)
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "alerts": alerts,
        "total": len(alerts),
        "unacknowledged": sum(1 for a in alerts if not a.get("acknowledged"))
    }


@router.get("/my-alerts")
async def get_my_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    unacknowledged_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get alerts for the current user.
    
    For citizens: Returns alerts from their encounters
    For attorneys: Returns alerts from all linked clients
    """
    user_id = current_user.get("user_id")
    role = current_user.get("role", "citizen")
    
    if unacknowledged_only and role == "attorney":
        alerts = await realtime_alerts.get_unacknowledged_alerts(user_id)
    else:
        alerts = await realtime_alerts.get_user_alerts(user_id, limit)
    
    # Group by severity for dashboard
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for alert in alerts:
        sev = alert.get("severity", "medium")
        if sev in severity_counts:
            severity_counts[sev] += 1
    
    return {
        "success": True,
        "alerts": alerts,
        "total": len(alerts),
        "severity_breakdown": severity_counts,
        "unacknowledged": sum(1 for a in alerts if not a.get("acknowledged"))
    }


@router.post("/acknowledge")
async def acknowledge_alert(
    request: AcknowledgeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Acknowledge an alert (typically by attorney).
    
    Marks alert as reviewed so it doesn't keep appearing in unacknowledged list.
    """
    success = await realtime_alerts.acknowledge_alert(
        alert_id=request.alert_id,
        user_id=current_user.get("user_id")
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "success": True,
        "alert_id": request.alert_id,
        "acknowledged_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/acknowledge-all")
async def acknowledge_all_alerts(
    encounter_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge all alerts for an encounter or all user alerts"""
    user_id = current_user.get("user_id")
    
    query = {"acknowledged": False}
    if encounter_id:
        query["encounter_id"] = encounter_id
    else:
        # For attorneys, acknowledge their client alerts
        # For citizens, acknowledge their own alerts
        role = current_user.get("role", "citizen")
        if role == "attorney":
            query["attorney_id"] = user_id
        else:
            query["user_id"] = user_id
    
    result = await db.realtime_alerts.update_many(
        query,
        {
            "$set": {
                "acknowledged": True,
                "acknowledged_by": user_id,
                "acknowledged_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "acknowledged_count": result.modified_count
    }


@router.get("/stats")
async def get_alert_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """Get alert statistics for reporting"""
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate by violation type
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff.isoformat()}}},
        {"$group": {
            "_id": "$violation_type",
            "count": {"$sum": 1},
            "critical_count": {
                "$sum": {"$cond": [{"$eq": ["$severity", "critical"]}, 1, 0]}
            }
        }},
        {"$sort": {"count": -1}}
    ]
    
    by_type = await db.realtime_alerts.aggregate(pipeline).to_list(50)
    
    # Total counts
    total = await db.realtime_alerts.count_documents(
        {"created_at": {"$gte": cutoff.isoformat()}}
    )
    critical = await db.realtime_alerts.count_documents(
        {"created_at": {"$gte": cutoff.isoformat()}, "severity": "critical"}
    )
    acknowledged = await db.realtime_alerts.count_documents(
        {"created_at": {"$gte": cutoff.isoformat()}, "acknowledged": True}
    )
    
    return {
        "success": True,
        "period_days": days,
        "stats": {
            "total_alerts": total,
            "critical_alerts": critical,
            "acknowledged_alerts": acknowledged,
            "acknowledgment_rate": round(acknowledged / max(total, 1) * 100, 1)
        },
        "by_violation_type": [
            {"type": item["_id"], "count": item["count"], "critical": item["critical_count"]}
            for item in by_type
        ]
    }


@router.get("/keywords")
async def get_alert_keywords():
    """Get the list of keywords that trigger alerts (for documentation)"""
    from app.services.realtime_alerts import CRITICAL_KEYWORDS
    
    return {
        "success": True,
        "keywords": {
            violation_type: {
                "keywords": keywords,
                "severity": realtime_alerts._get_severity_for_violation(violation_type).value
            }
            for violation_type, keywords in CRITICAL_KEYWORDS.items()
        }
    }
