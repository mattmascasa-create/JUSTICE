"""
Witness Network Service - Community-based encounter monitoring and protection
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from math import cos, sqrt, radians, sin, atan2
import uuid

from app.db.database import db
from app.services.push_service import send_push_to_user

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_RADIUS_MILES = 1.0
EARTH_RADIUS_MILES = 3959


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in miles using Haversine formula"""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return EARTH_RADIUS_MILES * c


async def enable_witness_mode(user_id: str, location: Dict) -> Dict:
    """Enable witness mode for a user at their current location"""
    
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "witness_mode_enabled": True,
                "witness_mode_enabled_at": datetime.now(timezone.utc),
                "last_known_location": {
                    "lat": location.get("lat"),
                    "lng": location.get("lng"),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    # Add to active witnesses collection for faster queries
    await db.active_witnesses.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "location": location,
                "enabled_at": datetime.now(timezone.utc),
                "active": True
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Witness mode enabled. You'll be alerted to nearby encounters."
    }


async def disable_witness_mode(user_id: str) -> Dict:
    """Disable witness mode for a user"""
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"witness_mode_enabled": False}}
    )
    
    await db.active_witnesses.update_one(
        {"user_id": user_id},
        {"$set": {"active": False}}
    )
    
    return {"success": True, "message": "Witness mode disabled"}


async def update_witness_location(user_id: str, location: Dict) -> Dict:
    """Update a witness's current location"""
    
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "last_known_location": {
                    "lat": location.get("lat"),
                    "lng": location.get("lng"),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    await db.active_witnesses.update_one(
        {"user_id": user_id},
        {"$set": {"location": location}}
    )
    
    return {"success": True}


async def find_nearby_witnesses(
    location: Dict,
    radius_miles: float = DEFAULT_RADIUS_MILES,
    exclude_user_id: Optional[str] = None
) -> List[Dict]:
    """Find active witnesses within radius of a location"""
    
    lat = location.get("lat")
    lng = location.get("lng")
    
    if not lat or not lng:
        return []
    
    # Approximate bounding box (faster than calculating distance for all)
    lat_range = radius_miles / 69.0  # ~69 miles per degree latitude
    lng_range = radius_miles / (69.0 * cos(radians(lat)))
    
    query = {
        "active": True,
        "location.lat": {"$gte": lat - lat_range, "$lte": lat + lat_range},
        "location.lng": {"$gte": lng - lng_range, "$lte": lng + lng_range}
    }
    
    if exclude_user_id:
        query["user_id"] = {"$ne": exclude_user_id}
    
    candidates = await db.active_witnesses.find(
        query,
        {"_id": 0}
    ).to_list(500)
    
    # Filter by actual distance
    nearby = []
    for witness in candidates:
        w_loc = witness.get("location", {})
        distance = haversine_distance(lat, lng, w_loc.get("lat", 0), w_loc.get("lng", 0))
        if distance <= radius_miles:
            witness["distance_miles"] = round(distance, 2)
            nearby.append(witness)
    
    # Sort by distance
    nearby.sort(key=lambda x: x["distance_miles"])
    
    return nearby


async def broadcast_encounter_alert(
    encounter_id: str,
    user_id: str,
    user_name: str,
    location: Dict,
    encounter_type: str = "general",
    radius_miles: float = DEFAULT_RADIUS_MILES
) -> Dict:
    """Broadcast an encounter alert to nearby witnesses"""
    
    alert_id = f"alert_{uuid.uuid4().hex[:12]}"
    
    # Find nearby witnesses
    witnesses = await find_nearby_witnesses(
        location=location,
        radius_miles=radius_miles,
        exclude_user_id=user_id
    )
    
    if not witnesses:
        return {
            "alert_id": alert_id,
            "witnesses_alerted": 0,
            "message": "No witnesses found nearby"
        }
    
    # Create the alert record
    alert = {
        "alert_id": alert_id,
        "encounter_id": encounter_id,
        "user_id": user_id,
        "user_name": user_name,
        "location": location,
        "encounter_type": encounter_type,
        "created_at": datetime.now(timezone.utc),
        "witnesses_notified": [],
        "active": True
    }
    
    share_url = f"/encounter/watch/{encounter_id}"
    notified = 0
    
    for witness in witnesses:
        try:
            await send_push_to_user(
                db=db,
                user_id=witness["user_id"],
                title=f"👁️ Witness Alert: {user_name}",
                body=f"Police encounter {witness['distance_miles']} miles away. Tap to watch.",
                url=share_url,
                tag="witness_alert"
            )
            
            alert["witnesses_notified"].append({
                "user_id": witness["user_id"],
                "distance_miles": witness["distance_miles"],
                "notified_at": datetime.now(timezone.utc)
            })
            notified += 1
            
        except Exception as e:
            logger.error(f"Failed to notify witness {witness['user_id']}: {e}")
    
    await db.witness_alerts.insert_one(alert)
    
    return {
        "alert_id": alert_id,
        "witnesses_alerted": notified,
        "total_nearby": len(witnesses)
    }


async def join_as_witness(
    encounter_id: str,
    witness_user_id: str,
    witness_name: str
) -> Dict:
    """Register as an active witness for an encounter"""
    
    witness_record = {
        "witness_id": f"wit_{uuid.uuid4().hex[:12]}",
        "encounter_id": encounter_id,
        "user_id": witness_user_id,
        "name": witness_name,
        "joined_at": datetime.now(timezone.utc),
        "is_recording": False,
        "recording_url": None
    }
    
    await db.encounter_witnesses.insert_one(witness_record)
    
    # Update encounter viewer count
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$inc": {"witness_count": 1}}
    )
    
    # Notify the encounter owner
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0, "user_id": 1}
    )
    
    if encounter:
        await send_push_to_user(
            db=db,
            user_id=encounter["user_id"],
            title="👁️ Witness Joined",
            body=f"{witness_name} is now watching your encounter",
            tag="witness_joined"
        )
    
    return {
        "success": True,
        "witness_id": witness_record["witness_id"],
        "message": f"You are now witnessing this encounter"
    }


async def submit_witness_recording(
    encounter_id: str,
    witness_user_id: str,
    recording_url: str,
    recording_type: str = "video"
) -> Dict:
    """Submit a witness recording for an encounter"""
    
    recording_id = f"wrec_{uuid.uuid4().hex[:12]}"
    
    recording = {
        "recording_id": recording_id,
        "encounter_id": encounter_id,
        "witness_user_id": witness_user_id,
        "recording_url": recording_url,
        "recording_type": recording_type,
        "submitted_at": datetime.now(timezone.utc),
        "verified": False
    }
    
    await db.witness_recordings.insert_one(recording)
    
    # Update the witness record
    await db.encounter_witnesses.update_one(
        {"encounter_id": encounter_id, "user_id": witness_user_id},
        {
            "$set": {
                "is_recording": True,
                "recording_url": recording_url
            }
        }
    )
    
    return {
        "success": True,
        "recording_id": recording_id,
        "message": "Witness recording submitted successfully"
    }


async def get_encounter_witnesses(encounter_id: str) -> List[Dict]:
    """Get all witnesses for an encounter"""
    
    witnesses = await db.encounter_witnesses.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(100)
    
    return witnesses


async def get_witness_stats(user_id: str) -> Dict:
    """Get witness statistics for a user"""
    
    total_witnessed = await db.encounter_witnesses.count_documents({"user_id": user_id})
    recordings_submitted = await db.witness_recordings.count_documents({"witness_user_id": user_id})
    
    # Calculate reputation score
    reputation = min(100, total_witnessed * 5 + recordings_submitted * 10)
    
    return {
        "total_witnessed": total_witnessed,
        "recordings_submitted": recordings_submitted,
        "reputation_score": reputation,
        "badge": get_witness_badge(reputation)
    }


def get_witness_badge(reputation: int) -> Dict:
    """Get witness badge based on reputation"""
    if reputation >= 80:
        return {"name": "Guardian", "level": 4, "color": "gold"}
    elif reputation >= 50:
        return {"name": "Protector", "level": 3, "color": "purple"}
    elif reputation >= 25:
        return {"name": "Watcher", "level": 2, "color": "blue"}
    elif reputation >= 10:
        return {"name": "Observer", "level": 1, "color": "green"}
    else:
        return {"name": "New Witness", "level": 0, "color": "gray"}
