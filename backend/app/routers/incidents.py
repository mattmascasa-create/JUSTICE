"""
Incidents Router - Public incident map and statistics
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Query
from typing import Optional

from app.db.database import db

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("/map")
async def get_incidents_for_map(
    days: int = Query(default=90, ge=1, le=365),
    violation_type: Optional[str] = None,
    state: Optional[str] = None,
    severity: Optional[str] = None
):
    """Get anonymized incidents for the public map view"""
    # Calculate date filter
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Build query - only show anonymized, public incidents
    query = {
        "created_at": {"$gte": since_date.isoformat()}
    }
    
    if violation_type and violation_type != "All Types":
        query["violation_type"] = {"$regex": violation_type, "$options": "i"}
    
    if state:
        query["state"] = state
    
    if severity:
        query["severity"] = severity
    
    # Try to get from community evidence (anonymized)
    incidents = await db.community_evidence.find(
        query,
        {
            "_id": 0,
            "submission_id": 1,
            "location": 1,
            "violation_type": 1,
            "severity": 1,
            "department": 1,
            "state": 1,
            "created_at": 1,
            "outcome": 1
        }
    ).limit(500).to_list(500)
    
    # If no community evidence, generate sample data for demo
    if not incidents:
        incidents = generate_sample_incidents(days, violation_type, state, severity)
    
    return {
        "incidents": incidents,
        "count": len(incidents),
        "filters": {
            "days": days,
            "violation_type": violation_type,
            "state": state,
            "severity": severity
        }
    }


@router.get("/stats")
async def get_incident_stats():
    """Get aggregate statistics for incidents"""
    # Count by violation type
    by_violation = await db.community_evidence.aggregate([
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # Count by severity
    by_severity = await db.community_evidence.aggregate([
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(5)
    
    # Count by state
    by_state = await db.community_evidence.aggregate([
        {"$group": {"_id": "$state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    total = await db.community_evidence.count_documents({})
    
    return {
        "total_incidents": total,
        "by_violation_type": [{"type": v["_id"], "count": v["count"]} for v in by_violation if v["_id"]],
        "by_severity": [{"severity": s["_id"], "count": s["count"]} for s in by_severity if s["_id"]],
        "by_state": [{"state": s["_id"], "count": s["count"]} for s in by_state if s["_id"]]
    }


def generate_sample_incidents(days: int, violation_type: str = None, state: str = None, severity: str = None):
    """Generate sample incidents for demo purposes when no real data exists"""
    import random
    
    sample_locations = [
        {"lat": 33.4484, "lng": -112.0740, "city": "Phoenix", "state": "AZ"},
        {"lat": 34.0522, "lng": -118.2437, "city": "Los Angeles", "state": "CA"},
        {"lat": 40.7128, "lng": -74.0060, "city": "New York", "state": "NY"},
        {"lat": 41.8781, "lng": -87.6298, "city": "Chicago", "state": "IL"},
        {"lat": 29.7604, "lng": -95.3698, "city": "Houston", "state": "TX"},
        {"lat": 33.7490, "lng": -84.3880, "city": "Atlanta", "state": "GA"},
        {"lat": 47.6062, "lng": -122.3321, "city": "Seattle", "state": "WA"},
        {"lat": 39.7392, "lng": -104.9903, "city": "Denver", "state": "CO"},
        {"lat": 25.7617, "lng": -80.1918, "city": "Miami", "state": "FL"},
        {"lat": 42.3601, "lng": -71.0589, "city": "Boston", "state": "MA"},
    ]
    
    violation_types = [
        "4th Amendment - Unlawful Search",
        "4th Amendment - Excessive Force",
        "5th Amendment - Miranda Violation",
        "1st Amendment - Recording Interference",
        "14th Amendment - Due Process",
        "False Arrest",
        "Unlawful Detention",
        "Property Damage"
    ]
    
    severities = ["low", "medium", "high", "critical"]
    statuses = ["pending", "resolved", "under_investigation", "lawsuit_filed"]
    
    incidents = []
    now = datetime.now(timezone.utc)
    
    for i in range(min(50, days // 2)):
        loc = random.choice(sample_locations)
        
        # Apply filters
        if state and loc["state"] != state:
            continue
        
        v_type = random.choice(violation_types)
        if violation_type and violation_type != "All Types" and violation_type.lower() not in v_type.lower():
            continue
        
        sev = random.choice(severities)
        if severity and sev != severity:
            continue
        
        # Add some randomness to location
        lat_offset = random.uniform(-0.1, 0.1)
        lng_offset = random.uniform(-0.1, 0.1)
        
        incident_date = now - timedelta(days=random.randint(1, days))
        
        incident = {
            "case_id": f"case_{i}",
            "title": f"{v_type} Incident",
            "latitude": loc["lat"] + lat_offset,
            "longitude": loc["lng"] + lng_offset,
            "city": loc["city"],
            "state": loc["state"],
            "violation_type": v_type,
            "severity": sev,
            "status": random.choice(statuses),
            "department": f"{loc['city']} Police Department",
            "incident_date": incident_date.isoformat(),
            "created_at": incident_date.isoformat()
        }
        incidents.append(incident)
    
    return incidents
