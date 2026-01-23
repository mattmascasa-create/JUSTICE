"""
SOS Router - Emergency alert endpoints
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.db.database import db
from app.core.security import get_current_user
from app.services.websocket import manager
from app.models.schemas import SOSAlertCreate, SOSAlertResponse

router = APIRouter(prefix="/sos", tags=["SOS Alerts"])


class EncounterSOSRequest(BaseModel):
    """Request model for encounter-based SOS"""
    encounter_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    message: Optional[str] = None


@router.post("/encounter")
async def create_encounter_sos(
    request: EncounterSOSRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create SOS alert during an active encounter.
    Notifies all emergency contacts with encounter link and location.
    """
    alert_id = f"sos_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    user_id = current_user["user_id"]
    user_name = current_user.get("name", "A JUSTICE user")
    
    # Get encounter details
    encounter = await db.encounters.find_one(
        {"encounter_id": request.encounter_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Use encounter location if not provided
    latitude = request.latitude or encounter.get("latitude")
    longitude = request.longitude or encounter.get("longitude")
    address = request.address or encounter.get("address", "Unknown location")
    
    # Ensure share is active for the encounter
    share_url = None
    share_token = encounter.get("share_token")
    if encounter.get("share_active") and share_token:
        share_url = f"/live/{request.encounter_id}?token={share_token}"
    else:
        # Auto-create share link for SOS
        share_token = uuid.uuid4().hex[:16]
        await db.encounters.update_one(
            {"encounter_id": request.encounter_id},
            {"$set": {
                "share_active": True,
                "share_token": share_token,
                "share_created_at": now.isoformat()
            }}
        )
        share_url = f"/live/{request.encounter_id}?token={share_token}"
    
    # Create SOS alert record
    alert_doc = {
        "alert_id": alert_id,
        "user_id": user_id,
        "encounter_id": request.encounter_id,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "share_url": share_url,
        "message": request.message or "Emergency SOS - I need help!",
        "status": "active",
        "created_at": now.isoformat(),
        "resolved_at": None,
        "contacts_notified": []
    }
    
    await db.sos_alerts.insert_one(alert_doc)
    
    # Get emergency contacts with SOS notifications enabled
    contacts = await db.emergency_contacts.find(
        {"user_id": user_id, "notify_on_sos": True, "active": True},
        {"_id": 0}
    ).sort("priority", 1).to_list(10)
    
    notified_contacts = []
    
    # Notify each emergency contact
    for contact in contacts:
        contact_id = contact.get("contact_id")
        
        # If contact is a JUSTICE user, send in-app notification
        if contact.get("contact_user_id"):
            # Send WebSocket notification
            await manager.send_to_user(contact["contact_user_id"], {
                "type": "sos_alert",
                "alert_id": alert_id,
                "user_name": user_name,
                "encounter_id": request.encounter_id,
                "share_url": share_url,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": address
                },
                "message": f"🚨 EMERGENCY SOS from {user_name}! They are in a police encounter and need help.",
                "timestamp": now.isoformat()
            })
            
            # Create persistent notification
            from app.routers.notifications import create_notification
            await create_notification(
                user_id=contact["contact_user_id"],
                notification_type="sos_alert",
                title=f"🚨 EMERGENCY SOS from {user_name}",
                message=f"{user_name} is in a police encounter at {address} and needs help! Click to watch live.",
                metadata={
                    "alert_id": alert_id,
                    "encounter_id": request.encounter_id,
                    "share_url": share_url,
                    "location": {"lat": latitude, "lng": longitude}
                },
                send_push=True
            )
            
            notified_contacts.append({
                "contact_id": contact_id,
                "name": contact.get("name"),
                "method": "in_app",
                "notified_at": now.isoformat()
            })
        
        # Send SMS if phone provided
        phone = contact.get("phone")
        if phone:
            from app.services.sms_service import send_sos_alert_sms, is_twilio_configured
            
            if is_twilio_configured():
                # Build full share URL
                from app.core.config import FRONTEND_URL
                full_share_url = f"{FRONTEND_URL}{share_url}"
                
                sms_result = await send_sos_alert_sms(
                    to_number=phone,
                    user_name=user_name,
                    location_address=address,
                    share_url=full_share_url,
                    latitude=latitude,
                    longitude=longitude
                )
                
                if sms_result.get("success"):
                    notified_contacts.append({
                        "contact_id": contact_id,
                        "name": contact.get("name"),
                        "method": "sms",
                        "phone": phone,
                        "message_sid": sms_result.get("message_sid"),
                        "notified_at": now.isoformat()
                    })
    
    # Update alert with notified contacts
    await db.sos_alerts.update_one(
        {"alert_id": alert_id},
        {"$set": {"contacts_notified": notified_contacts}}
    )
    
    return {
        "success": True,
        "alert_id": alert_id,
        "contacts_notified": len(notified_contacts),
        "share_url": share_url,
        "message": f"SOS alert sent to {len(notified_contacts)} emergency contact(s)"
    }


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
