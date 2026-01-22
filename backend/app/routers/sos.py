"""
SOS Router - Emergency alert endpoints
"""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from app.db.database import db
from app.core.security import get_current_user
from app.services.websocket import manager
from app.models.schemas import SOSAlertCreate, SOSAlertResponse

router = APIRouter(prefix="/sos", tags=["SOS Alerts"])


@router.post("", response_model=SOSAlertResponse)
async def create_sos_alert(alert_data: SOSAlertCreate, current_user: dict = Depends(get_current_user)):
    """Create a new SOS emergency alert"""
    alert_id = f"sos_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    alert_doc = {
        "alert_id": alert_id,
        "user_id": current_user["user_id"],
        "latitude": alert_data.latitude,
        "longitude": alert_data.longitude,
        "address": alert_data.address,
        "status": "active",
        "created_at": now.isoformat(),
        "resolved_at": None
    }
    
    await db.sos_alerts.insert_one(alert_doc)
    
    # Get user's emergency contacts
    contacts = await db.emergency_contacts.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).to_list(10)
    
    # Notify emergency contacts via WebSocket
    for contact in contacts:
        if contact.get("contact_user_id"):
            await manager.send_to_user(contact["contact_user_id"], {
                "type": "sos_alert",
                "alert_id": alert_id,
                "user_name": current_user.get("name"),
                "location": {
                    "latitude": alert_data.latitude,
                    "longitude": alert_data.longitude,
                    "address": alert_data.address
                },
                "message": f"SOS Alert from {current_user.get('name')}!"
            })
    
    # In production, also send SMS/push notifications
    
    return SOSAlertResponse(
        alert_id=alert_id,
        user_id=current_user["user_id"],
        latitude=alert_data.latitude,
        longitude=alert_data.longitude,
        address=alert_data.address,
        status="active",
        created_at=now,
        resolved_at=None
    )


@router.get("/active", response_model=List[SOSAlertResponse])
async def get_active_alerts(current_user: dict = Depends(get_current_user)):
    """Get active SOS alerts for current user"""
    alerts = await db.sos_alerts.find(
        {"user_id": current_user["user_id"], "status": "active"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(10)
    
    result = []
    for alert in alerts:
        if isinstance(alert.get("created_at"), str):
            alert["created_at"] = datetime.fromisoformat(alert["created_at"])
        if alert.get("resolved_at") and isinstance(alert["resolved_at"], str):
            alert["resolved_at"] = datetime.fromisoformat(alert["resolved_at"])
        result.append(SOSAlertResponse(**alert))
    
    return result


@router.get("/history", response_model=List[SOSAlertResponse])
async def get_sos_history(current_user: dict = Depends(get_current_user)):
    """Get SOS alert history"""
    alerts = await db.sos_alerts.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    result = []
    for alert in alerts:
        if isinstance(alert.get("created_at"), str):
            alert["created_at"] = datetime.fromisoformat(alert["created_at"])
        if alert.get("resolved_at") and isinstance(alert["resolved_at"], str):
            alert["resolved_at"] = datetime.fromisoformat(alert["resolved_at"])
        result.append(SOSAlertResponse(**alert))
    
    return result


@router.post("/{alert_id}/resolve")
async def resolve_sos_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """Resolve/cancel an SOS alert"""
    alert = await db.sos_alerts.find_one(
        {"alert_id": alert_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    now = datetime.now(timezone.utc)
    
    await db.sos_alerts.update_one(
        {"alert_id": alert_id},
        {"$set": {"status": "resolved", "resolved_at": now.isoformat()}}
    )
    
    # Notify emergency contacts that alert is resolved
    contacts = await db.emergency_contacts.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).to_list(10)
    
    for contact in contacts:
        if contact.get("contact_user_id"):
            await manager.send_to_user(contact["contact_user_id"], {
                "type": "sos_resolved",
                "alert_id": alert_id,
                "user_name": current_user.get("name"),
                "message": f"SOS Alert from {current_user.get('name')} has been resolved."
            })
    
    return {"message": "Alert resolved successfully", "resolved_at": now.isoformat()}


@router.get("/{alert_id}", response_model=SOSAlertResponse)
async def get_sos_alert(alert_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific SOS alert"""
    alert = await db.sos_alerts.find_one(
        {"alert_id": alert_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if isinstance(alert.get("created_at"), str):
        alert["created_at"] = datetime.fromisoformat(alert["created_at"])
    if alert.get("resolved_at") and isinstance(alert["resolved_at"], str):
        alert["resolved_at"] = datetime.fromisoformat(alert["resolved_at"])
    
    return SOSAlertResponse(**alert)
