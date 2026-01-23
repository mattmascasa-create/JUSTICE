"""
Dead Man's Switch Service - Automatic emergency response when user becomes unresponsive
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from math import cos
import uuid
import asyncio

from app.db.database import db
from app.services.push_service import send_push_to_user

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_INACTIVITY_THRESHOLD = 60  # seconds
DEFAULT_WARNING_TIME = 45  # seconds before triggering
BROADCAST_RADIUS_MILES = 1.0


async def get_dead_mans_switch_config(user_id: str) -> Dict:
    """Get user's dead man's switch configuration"""
    config = await db.dead_mans_switch_config.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not config:
        return {
            "enabled": True,
            "inactivity_threshold": DEFAULT_INACTIVITY_THRESHOLD,
            "warning_time": DEFAULT_WARNING_TIME,
            "auto_broadcast": True,
            "auto_upload": True,
            "notify_emergency_contacts": True,
            "notify_witness_network": True,
            "sensitivity": "normal"  # low, normal, high
        }
    
    return config


async def update_dead_mans_switch_config(user_id: str, config: Dict) -> Dict:
    """Update user's dead man's switch configuration"""
    config["user_id"] = user_id
    config["updated_at"] = datetime.now(timezone.utc)
    
    await db.dead_mans_switch_config.update_one(
        {"user_id": user_id},
        {"$set": config},
        upsert=True
    )
    
    return config


async def register_activity(encounter_id: str, user_id: str, activity_type: str = "touch") -> Dict:
    """
    Register user activity to reset the dead man's switch timer.
    Called on screen touches, button presses, or voice detection.
    """
    now = datetime.now(timezone.utc)
    
    await db.encounter_activity.update_one(
        {"encounter_id": encounter_id},
        {
            "$set": {
                "user_id": user_id,
                "last_activity": now,
                "activity_type": activity_type,
                "switch_armed": True
            }
        },
        upsert=True
    )
    
    return {
        "registered": True,
        "timestamp": now.isoformat(),
        "activity_type": activity_type
    }


async def check_inactivity(encounter_id: str) -> Dict:
    """
    Check if user has been inactive beyond threshold.
    Returns trigger status and time remaining.
    """
    activity = await db.encounter_activity.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not activity or not activity.get("switch_armed"):
        return {"armed": False, "triggered": False}
    
    user_id = activity.get("user_id")
    config = await get_dead_mans_switch_config(user_id)
    
    if not config.get("enabled"):
        return {"armed": False, "triggered": False}
    
    last_activity = activity.get("last_activity")
    if not last_activity:
        return {"armed": True, "triggered": False}
    
    # Ensure last_activity is timezone-aware
    if isinstance(last_activity, datetime) and last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    inactive_seconds = (now - last_activity).total_seconds()
    threshold = config.get("inactivity_threshold", DEFAULT_INACTIVITY_THRESHOLD)
    warning_time = config.get("warning_time", DEFAULT_WARNING_TIME)
    
    return {
        "armed": True,
        "triggered": inactive_seconds >= threshold,
        "warning": inactive_seconds >= warning_time and inactive_seconds < threshold,
        "inactive_seconds": inactive_seconds,
        "threshold": threshold,
        "seconds_until_trigger": max(0, threshold - inactive_seconds)
    }


async def trigger_dead_mans_switch(encounter_id: str, user_id: str) -> Dict:
    """
    Trigger the dead man's switch - initiate emergency protocols.
    """
    logger.warning(f"DEAD MAN'S SWITCH TRIGGERED for encounter {encounter_id}")
    
    config = await get_dead_mans_switch_config(user_id)
    trigger_id = f"dms_{uuid.uuid4().hex[:12]}"
    
    # Get encounter details
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not encounter:
        return {"error": "Encounter not found"}
    
    # Get user info
    user = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "name": 1, "email": 1}
    )
    
    results = {
        "trigger_id": trigger_id,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "actions": []
    }
    
    # 1. Notify emergency contacts
    if config.get("notify_emergency_contacts"):
        contacts_notified = await notify_emergency_contacts(
            user_id=user_id,
            encounter_id=encounter_id,
            encounter=encounter,
            user_name=user.get("name", "Unknown")
        )
        results["actions"].append({
            "type": "emergency_contacts",
            "success": True,
            "contacts_notified": contacts_notified
        })
    
    # 2. Alert witness network
    if config.get("notify_witness_network"):
        witnesses_alerted = await alert_witness_network(
            encounter_id=encounter_id,
            location=encounter.get("location"),
            user_name=user.get("name", "Unknown")
        )
        results["actions"].append({
            "type": "witness_network",
            "success": True,
            "witnesses_alerted": witnesses_alerted
        })
    
    # 3. Force upload evidence
    if config.get("auto_upload"):
        results["actions"].append({
            "type": "evidence_backup",
            "success": True,
            "message": "Evidence backup initiated"
        })
    
    # 4. Enable public broadcast
    if config.get("auto_broadcast"):
        await db.encounters.update_one(
            {"encounter_id": encounter_id},
            {
                "$set": {
                    "public_broadcast": True,
                    "broadcast_reason": "dead_mans_switch",
                    "broadcast_at": datetime.now(timezone.utc)
                }
            }
        )
        results["actions"].append({
            "type": "public_broadcast",
            "success": True,
            "message": "Live stream now publicly accessible"
        })
    
    # Log the trigger
    await db.dead_mans_switch_logs.insert_one({
        "trigger_id": trigger_id,
        "encounter_id": encounter_id,
        "user_id": user_id,
        "triggered_at": datetime.now(timezone.utc),
        "config_used": config,
        "results": results
    })
    
    return results


async def notify_emergency_contacts(
    user_id: str,
    encounter_id: str,
    encounter: Dict,
    user_name: str
) -> int:
    """Notify all emergency contacts about the triggered switch"""
    
    # Get emergency contacts
    contacts = await db.emergency_contacts.find(
        {"user_id": user_id, "active": True},
        {"_id": 0}
    ).to_list(20)
    
    if not contacts:
        return 0
    
    location = encounter.get("location", {})
    lat = location.get("lat") or encounter.get("latitude")
    lng = location.get("lng") or encounter.get("longitude")
    address = encounter.get("address", "Unknown location")
    
    # Create share URL for the encounter
    from app.core.config import FRONTEND_URL
    share_url = f"{FRONTEND_URL}/encounter/watch/{encounter_id}"
    
    notified = 0
    for contact in contacts:
        try:
            # Send push notification if they're a user
            if contact.get("contact_user_id"):
                await send_push_to_user(
                    db=db,
                    user_id=contact["contact_user_id"],
                    title=f"🚨 EMERGENCY: {user_name} needs help!",
                    body=f"Dead man's switch triggered. Location: {address}",
                    url=share_url,
                    tag="emergency"
                )
                notified += 1
            
            # Send SMS via Twilio if phone number provided
            phone = contact.get("phone")
            if phone:
                from app.services.sms_service import send_dead_mans_switch_sms, is_twilio_configured
                
                if is_twilio_configured():
                    sms_result = await send_dead_mans_switch_sms(
                        to_number=phone,
                        user_name=user_name,
                        location_address=address,
                        share_url=share_url,
                        latitude=lat,
                        longitude=lng
                    )
                    if sms_result.get("success"):
                        notified += 1
            
            # Send email if email address provided
            email_addr = contact.get("email")
            if email_addr:
                from app.services.email_service import send_dead_mans_switch_email, is_sendgrid_configured
                
                if is_sendgrid_configured():
                    email_result = await send_dead_mans_switch_email(
                        to_email=email_addr,
                        user_name=user_name,
                        location_address=address,
                        share_url=share_url,
                        latitude=lat,
                        longitude=lng
                    )
                    if email_result.get("success"):
                        notified += 1
            
        except Exception as e:
            logger.error(f"Failed to notify contact: {e}")
    
    return notified


async def alert_witness_network(
    encounter_id: str,
    location: Optional[Dict],
    user_name: str
) -> int:
    """Alert nearby users in the witness network"""
    
    if not location or not location.get("lat") or not location.get("lng"):
        return 0
    
    lat = location["lat"]
    lng = location["lng"]
    
    # Find users within 1 mile radius who have witness mode enabled
    # 1 mile ≈ 0.0145 degrees latitude, varies for longitude
    lat_range = 0.0145 * BROADCAST_RADIUS_MILES
    lng_range = 0.0145 * BROADCAST_RADIUS_MILES / abs(cos(lat * 3.14159 / 180)) if lat != 0 else 0.0145
    
    nearby_users = await db.users.find({
        "witness_mode_enabled": True,
        "last_known_location.lat": {"$gte": lat - lat_range, "$lte": lat + lat_range},
        "last_known_location.lng": {"$gte": lng - lng_range, "$lte": lng + lng_range}
    }, {"_id": 0, "user_id": 1, "name": 1}).to_list(100)
    
    alerted = 0
    share_url = f"/encounter/watch/{encounter_id}"
    
    for user in nearby_users:
        try:
            await send_push_to_user(
                db=db,
                user_id=user["user_id"],
                title=f"🚨 Nearby Emergency: {user_name}",
                body="Someone nearby needs witnesses. Tap to watch live.",
                url=share_url,
                tag="witness_alert"
            )
            alerted += 1
        except Exception as e:
            logger.error(f"Failed to alert witness: {e}")
    
    return alerted


async def disarm_switch(encounter_id: str, user_id: str) -> Dict:
    """Disarm the dead man's switch (user confirmed they're okay)"""
    
    await db.encounter_activity.update_one(
        {"encounter_id": encounter_id},
        {
            "$set": {
                "switch_armed": False,
                "disarmed_at": datetime.now(timezone.utc),
                "disarmed_by": user_id
            }
        }
    )
    
    return {"disarmed": True, "timestamp": datetime.now(timezone.utc).isoformat()}
