"""
Witness Network Router

Proximity-based witness alert system that notifies nearby JUSTICE users
when an encounter starts, allowing them to record corroborating evidence
from different angles.

Features:
- Location-based user discovery (opt-in)
- Real-time witness alerts
- Multi-angle evidence linking
- Witness recording management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import uuid
import math
import os

from app.core.security import get_current_user
from app.db.database import db

router = APIRouter(prefix="/witness-network", tags=["witness-network"])


# ============== PYDANTIC MODELS ==============

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None

class WitnessConfig(BaseModel):
    enabled: bool = True
    receive_alerts: bool = True
    share_location: bool = True
    alert_radius_meters: int = 500  # How far to look for witnesses
    auto_record: bool = False  # Auto-start recording when alerted
    quiet_hours_start: Optional[int] = None  # 0-23 hour
    quiet_hours_end: Optional[int] = None

class WitnessAlert(BaseModel):
    encounter_id: str
    latitude: float
    longitude: float
    encounter_type: str
    urgency: str = "normal"  # normal, high, critical
    message: Optional[str] = None

class WitnessRecording(BaseModel):
    original_encounter_id: str
    recording_type: str = "video"  # video, audio, photo
    notes: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in meters using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

async def find_nearby_witnesses(
    latitude: float,
    longitude: float,
    radius_meters: int,
    exclude_user_id: str
) -> List[dict]:
    """Find users who are nearby and have witness mode enabled"""
    
    # Get all users with recent location and witness mode enabled
    # In production, use geospatial indexes for efficiency
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    potential_witnesses = await db.user_locations.find({
        "user_id": {"$ne": exclude_user_id},
        "witness_enabled": True,
        "receive_alerts": True,
        "updated_at": {"$gte": five_mins_ago}
    }, {"_id": 0}).to_list(500)
    
    nearby = []
    for witness in potential_witnesses:
        if witness.get("latitude") and witness.get("longitude"):
            distance = haversine_distance(
                latitude, longitude,
                witness["latitude"], witness["longitude"]
            )
            if distance <= radius_meters:
                # Check quiet hours
                config = await db.witness_config.find_one(
                    {"user_id": witness["user_id"]},
                    {"_id": 0}
                )
                
                in_quiet_hours = False
                if config:
                    start = config.get("quiet_hours_start")
                    end = config.get("quiet_hours_end")
                    if start is not None and end is not None:
                        current_hour = datetime.now(timezone.utc).hour
                        if start <= end:
                            in_quiet_hours = start <= current_hour < end
                        else:  # Wraps around midnight
                            in_quiet_hours = current_hour >= start or current_hour < end
                
                if not in_quiet_hours:
                    nearby.append({
                        **witness,
                        "distance_meters": round(distance),
                        "auto_record": config.get("auto_record", False) if config else False
                    })
    
    # Sort by distance
    nearby.sort(key=lambda x: x["distance_meters"])
    
    return nearby

async def send_witness_alerts(
    witnesses: List[dict],
    alert_data: dict,
    requester_name: str
):
    """Send alerts to nearby witnesses"""
    
    for witness in witnesses:
        # Create notification
        notification = {
            "notification_id": str(uuid.uuid4()),
            "user_id": witness["user_id"],
            "type": "witness_alert",
            "title": "🚨 Nearby Incident - Witness Needed",
            "message": f"{requester_name} started recording {alert_data['encounter_type']} {witness['distance_meters']}m away. Your recording could help.",
            "data": {
                "encounter_id": alert_data["encounter_id"],
                "latitude": alert_data["latitude"],
                "longitude": alert_data["longitude"],
                "encounter_type": alert_data["encounter_type"],
                "distance": witness["distance_meters"],
                "urgency": alert_data.get("urgency", "normal"),
                "auto_record": witness.get("auto_record", False)
            },
            "read": False,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        
        await db.notifications.insert_one(notification)
        
        # Log the alert
        await db.witness_alerts_sent.insert_one({
            "alert_id": str(uuid.uuid4()),
            "encounter_id": alert_data["encounter_id"],
            "witness_user_id": witness["user_id"],
            "distance_meters": witness["distance_meters"],
            "auto_record": witness.get("auto_record", False),
            "sent_at": datetime.now(timezone.utc)
        })


# ============== CONFIGURATION ENDPOINTS ==============

@router.get("/config")
async def get_witness_config(current_user: dict = Depends(get_current_user)):
    """Get user's witness network configuration"""
    config = await db.witness_config.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not config:
        config = {
            "user_id": current_user["user_id"],
            "enabled": True,
            "receive_alerts": True,
            "share_location": True,
            "alert_radius_meters": 500,
            "auto_record": False,
            "quiet_hours_start": None,
            "quiet_hours_end": None
        }
    
    return config

@router.put("/config")
async def update_witness_config(
    config: WitnessConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update witness network configuration"""
    config_doc = {
        "user_id": current_user["user_id"],
        **config.dict(),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.witness_config.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    # Update location record if exists
    if config.enabled and config.share_location:
        await db.user_locations.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": {
                "witness_enabled": config.enabled,
                "receive_alerts": config.receive_alerts
            }}
        )
    
    return {"success": True, "message": "Witness configuration updated"}


# ============== LOCATION ENDPOINTS ==============

@router.post("/location")
async def update_location(
    location: LocationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user's current location (for witness discovery)"""
    
    # Check if user has witness mode enabled
    config = await db.witness_config.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not config or not config.get("share_location", True):
        return {"success": False, "message": "Location sharing disabled"}
    
    location_doc = {
        "user_id": current_user["user_id"],
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy": location.accuracy,
        "altitude": location.altitude,
        "witness_enabled": config.get("enabled", True),
        "receive_alerts": config.get("receive_alerts", True),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.user_locations.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": location_doc},
        upsert=True
    )
    
    return {"success": True, "message": "Location updated"}

@router.delete("/location")
async def clear_location(current_user: dict = Depends(get_current_user)):
    """Clear user's location (stop sharing)"""
    await db.user_locations.delete_one({"user_id": current_user["user_id"]})
    return {"success": True, "message": "Location cleared"}


# ============== ALERT ENDPOINTS ==============

@router.post("/alert")
async def send_witness_alert(
    alert: WitnessAlert,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Send alerts to nearby witnesses when starting an encounter"""
    
    # Get user's config for alert radius
    config = await db.witness_config.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    radius = config.get("alert_radius_meters", 500) if config else 500
    
    # Find nearby witnesses
    witnesses = await find_nearby_witnesses(
        alert.latitude,
        alert.longitude,
        radius,
        current_user["user_id"]
    )
    
    if not witnesses:
        return {
            "success": True,
            "witnesses_alerted": 0,
            "message": "No nearby witnesses found"
        }
    
    # Prepare alert data
    alert_data = {
        "encounter_id": alert.encounter_id,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "encounter_type": alert.encounter_type,
        "urgency": alert.urgency,
        "message": alert.message
    }
    
    # Send alerts in background
    requester_name = current_user.get("name", "A JUSTICE user")
    background_tasks.add_task(send_witness_alerts, witnesses, alert_data, requester_name)
    
    # Record the alert request
    await db.witness_alert_requests.insert_one({
        "request_id": str(uuid.uuid4()),
        "user_id": current_user["user_id"],
        "encounter_id": alert.encounter_id,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "radius_meters": radius,
        "witnesses_found": len(witnesses),
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "witnesses_alerted": len(witnesses),
        "closest_witness_meters": witnesses[0]["distance_meters"] if witnesses else None,
        "message": f"Alert sent to {len(witnesses)} nearby witness(es)"
    }

@router.get("/alerts")
async def get_my_alerts(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get witness alerts I've received"""
    
    alerts = await db.notifications.find(
        {
            "user_id": current_user["user_id"],
            "type": "witness_alert"
        },
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"alerts": alerts}

@router.post("/alerts/{notification_id}/respond")
async def respond_to_alert(
    notification_id: str,
    response: str,  # accepted, declined, recording_started
    current_user: dict = Depends(get_current_user)
):
    """Respond to a witness alert"""
    
    # Find the notification
    notification = await db.notifications.find_one(
        {"notification_id": notification_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not notification:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update notification
    await db.notifications.update_one(
        {"notification_id": notification_id},
        {"$set": {
            "read": True,
            "response": response,
            "responded_at": datetime.now(timezone.utc)
        }}
    )
    
    # Log the response
    await db.witness_responses.insert_one({
        "response_id": str(uuid.uuid4()),
        "notification_id": notification_id,
        "encounter_id": notification.get("data", {}).get("encounter_id"),
        "witness_user_id": current_user["user_id"],
        "response": response,
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"success": True, "message": f"Response recorded: {response}"}


# ============== WITNESS RECORDING ENDPOINTS ==============

@router.post("/recordings")
async def register_witness_recording(
    recording: WitnessRecording,
    current_user: dict = Depends(get_current_user)
):
    """Register a witness recording linked to an original encounter"""
    
    # Verify original encounter exists
    original = await db.encounters.find_one(
        {"encounter_id": recording.original_encounter_id},
        {"_id": 0, "encounter_id": 1, "user_id": 1}
    )
    
    if not original:
        raise HTTPException(status_code=404, detail="Original encounter not found")
    
    # Don't allow self-witness
    if original["user_id"] == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot witness your own encounter")
    
    recording_id = str(uuid.uuid4())[:12]
    
    recording_doc = {
        "recording_id": recording_id,
        "witness_user_id": current_user["user_id"],
        "witness_name": current_user.get("name", "Anonymous Witness"),
        "original_encounter_id": recording.original_encounter_id,
        "original_user_id": original["user_id"],
        "recording_type": recording.recording_type,
        "notes": recording.notes,
        "status": "recording",  # recording, completed, submitted
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.witness_recordings.insert_one(recording_doc)
    
    # Notify original user
    await db.notifications.insert_one({
        "notification_id": str(uuid.uuid4()),
        "user_id": original["user_id"],
        "type": "witness_recording",
        "title": "📹 Witness Recording Started",
        "message": "A nearby witness has started recording to support your encounter.",
        "data": {"recording_id": recording_id, "encounter_id": recording.original_encounter_id},
        "read": False,
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "recording_id": recording_id,
        "message": "Witness recording registered"
    }

@router.put("/recordings/{recording_id}/complete")
async def complete_witness_recording(
    recording_id: str,
    evidence_ids: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Mark a witness recording as complete"""
    
    result = await db.witness_recordings.update_one(
        {"recording_id": recording_id, "witness_user_id": current_user["user_id"]},
        {"$set": {
            "status": "completed",
            "evidence_ids": evidence_ids or [],
            "completed_at": datetime.now(timezone.utc)
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {"success": True, "message": "Recording marked as complete"}

@router.get("/recordings/for-encounter/{encounter_id}")
async def get_witness_recordings(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get witness recordings for an encounter (only original user can see)"""
    
    # Verify user owns the encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0, "user_id": 1}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    recordings = await db.witness_recordings.find(
        {"original_encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(50)
    
    return {"recordings": recordings, "count": len(recordings)}

@router.get("/my-witness-recordings")
async def get_my_witness_recordings(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get recordings I've made as a witness"""
    
    recordings = await db.witness_recordings.find(
        {"witness_user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"recordings": recordings}


# ============== STATS ENDPOINTS ==============

@router.get("/stats")
async def get_witness_network_stats(current_user: dict = Depends(get_current_user)):
    """Get witness network statistics"""
    
    # Count active witnesses (location updated in last 5 mins)
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    active_witnesses = await db.user_locations.count_documents({
        "witness_enabled": True,
        "updated_at": {"$gte": five_mins_ago}
    })
    
    # Total witness recordings
    total_recordings = await db.witness_recordings.count_documents({})
    
    # Completed recordings
    completed_recordings = await db.witness_recordings.count_documents({"status": "completed"})
    
    # Alerts sent today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    alerts_today = await db.witness_alert_requests.count_documents({
        "created_at": {"$gte": today_start}
    })
    
    # User's stats
    my_recordings = await db.witness_recordings.count_documents({
        "witness_user_id": current_user["user_id"]
    })
    
    my_alerts_received = await db.notifications.count_documents({
        "user_id": current_user["user_id"],
        "type": "witness_alert"
    })
    
    return {
        "network": {
            "active_witnesses": active_witnesses,
            "total_witness_recordings": total_recordings,
            "completed_recordings": completed_recordings,
            "alerts_sent_today": alerts_today
        },
        "personal": {
            "my_witness_recordings": my_recordings,
            "alerts_received": my_alerts_received
        }
    }
