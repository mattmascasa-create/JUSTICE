"""
Location Alerts Router - Proactive coaching based on user location
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.routers.auth import get_current_user
from app.services.location_alerts import location_alert_service

router = APIRouter(prefix="/location-alerts", tags=["Location Alerts"])


@router.get("/check")
async def check_location_alerts(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if user is near any problematic precincts.
    Returns coaching alerts if user is within alert radius of
    departments with low accountability scores.
    """
    alerts = await location_alert_service.check_location_alerts(
        latitude=lat,
        longitude=lon,
        user_id=str(current_user.get("_id") or current_user.get("user_id"))
    )
    
    return {
        "success": True,
        "alerts": alerts,
        "alert_count": len(alerts),
        "has_critical": any(a.get("warning_level") == "critical" for a in alerts),
        "has_high": any(a.get("warning_level") == "high" for a in alerts)
    }


@router.get("/history")
async def get_alert_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get user's location alert history"""
    user_id = str(current_user.get("_id") or current_user.get("user_id"))
    
    history = await location_alert_service.get_user_alert_history(
        user_id=user_id,
        limit=limit
    )
    
    return {
        "success": True,
        "history": history,
        "count": len(history)
    }


@router.get("/precincts")
async def get_monitored_precincts():
    """Get list of precincts being monitored for location alerts"""
    precincts = location_alert_service.PRECINCT_LOCATIONS
    
    return {
        "success": True,
        "precincts": [
            {
                "name": p["name"],
                "state": p["state"],
                "lat": p["lat"],
                "lon": p["lon"]
            }
            for p in precincts
        ],
        "total": len(precincts),
        "alert_radius_km": location_alert_service.ALERT_RADIUS_KM
    }
