"""
Panic Gesture Router

Secret gesture detection for emergency stealth recording.
Allows users to start recording with a panic gesture when they
cannot safely interact with their phone.

Features:
- Panic gesture configuration
- Quick-start encounter creation
- Stealth mode activation
- Emergency contact notification (optional)
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid

from app.core.security import get_current_user
from app.db.database import db

router = APIRouter(prefix="/panic-gesture", tags=["panic-gesture"])


# ============== PYDANTIC MODELS ==============

class PanicGestureConfig(BaseModel):
    enabled: bool = True
    gesture_type: str = "shake"  # shake, volume_triple, power_triple, custom
    sensitivity: str = "medium"  # low, medium, high
    shake_threshold: int = 3  # Number of shakes
    shake_duration_ms: int = 1000  # Time window for shakes
    auto_stealth: bool = True  # Auto-enable stealth mode
    auto_record_video: bool = True
    auto_record_audio: bool = True
    notify_contacts: bool = False  # Notify dead man's switch contacts
    confirmation_vibrate: bool = True  # Vibrate to confirm activation
    cooldown_seconds: int = 30  # Prevent accidental re-triggers

class PanicTrigger(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gesture_type: str = "shake"
    trigger_source: str = "gesture"  # gesture, widget, voice


# ============== HELPER FUNCTIONS ==============

async def notify_emergency_contacts(user_id: str, encounter_id: str):
    """Notify dead man's switch contacts about panic trigger"""
    try:
        contacts = await db.trusted_contacts.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(20)
        
        if not contacts:
            return 0
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1})
        user_name = user.get("name", "A JUSTICE user") if user else "A JUSTICE user"
        
        for contact in contacts:
            await db.notifications.insert_one({
                "notification_id": str(uuid.uuid4()),
                "user_id": "external",
                "external_email": contact.get("email"),
                "external_phone": contact.get("phone"),
                "type": "panic_alert",
                "title": f"🚨 PANIC ALERT: {user_name}",
                "message": f"{user_name} triggered a panic gesture. Emergency recording started.",
                "data": {"encounter_id": encounter_id, "user_id": user_id},
                "read": False,
                "created_at": datetime.now(timezone.utc)
            })
        
        # Try SendGrid if configured
        try:
            import os
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            sendgrid_key = os.environ.get("SENDGRID_API_KEY")
            if sendgrid_key:
                sg = SendGridAPIClient(sendgrid_key)
                for contact in contacts:
                    if contact.get("email"):
                        message = Mail(
                            from_email="alerts@justice-app.com",
                            to_emails=contact["email"],
                            subject=f"🚨 PANIC ALERT: {user_name} needs help",
                            html_content=f"""
                            <h2>🚨 PANIC GESTURE TRIGGERED</h2>
                            <p><strong>{user_name}</strong> triggered an emergency panic gesture.</p>
                            <p>An emergency recording has been automatically started.</p>
                            <p>Please attempt to contact them immediately.</p>
                            <hr>
                            <p><em>This is an automated emergency alert from JUSTICE.</em></p>
                            """
                        )
                        sg.send(message)
        except Exception as e:
            print(f"SendGrid notification failed: {e}")
        
        return len(contacts)
        
    except Exception as e:
        print(f"Panic notification error: {e}")
        return 0


# ============== CONFIGURATION ENDPOINTS ==============

@router.get("/config")
async def get_panic_config(current_user: dict = Depends(get_current_user)):
    """Get panic gesture configuration"""
    config = await db.panic_gesture_config.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not config:
        config = {
            "user_id": current_user["user_id"],
            "enabled": True,
            "gesture_type": "shake",
            "sensitivity": "medium",
            "shake_threshold": 3,
            "shake_duration_ms": 1000,
            "auto_stealth": True,
            "auto_record_video": True,
            "auto_record_audio": True,
            "notify_contacts": False,
            "confirmation_vibrate": True,
            "cooldown_seconds": 30
        }
    
    return config

@router.put("/config")
async def update_panic_config(
    config: PanicGestureConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update panic gesture configuration"""
    config_doc = {
        "user_id": current_user["user_id"],
        **config.dict(),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.panic_gesture_config.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    return {"success": True, "message": "Panic gesture configuration updated"}


# ============== TRIGGER ENDPOINTS ==============

@router.post("/trigger")
async def trigger_panic_recording(
    trigger: PanicTrigger,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger panic recording - creates encounter in stealth mode"""
    
    user_id = current_user["user_id"]
    
    # Get config
    config = await db.panic_gesture_config.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not config:
        config = {
            "auto_stealth": True,
            "auto_record_video": True,
            "auto_record_audio": True,
            "notify_contacts": False
        }
    
    # Check cooldown
    last_trigger = await db.panic_triggers.find_one(
        {"user_id": user_id},
        {"_id": 0, "triggered_at": 1},
        sort=[("triggered_at", -1)]
    )
    
    if last_trigger:
        cooldown = config.get("cooldown_seconds", 30)
        time_since = (datetime.now(timezone.utc) - last_trigger["triggered_at"]).total_seconds()
        if time_since < cooldown:
            return {
                "success": False,
                "message": f"Cooldown active. Wait {int(cooldown - time_since)} seconds.",
                "cooldown_remaining": int(cooldown - time_since)
            }
    
    # Create encounter
    encounter_id = str(uuid.uuid4())
    
    encounter_doc = {
        "encounter_id": encounter_id,
        "user_id": user_id,
        "encounter_type": "panic_emergency",
        "status": "active",
        "stealth_mode": config.get("auto_stealth", True),
        "panic_triggered": True,
        "trigger_source": trigger.trigger_source,
        "latitude": trigger.latitude,
        "longitude": trigger.longitude,
        "settings": {
            "video_enabled": config.get("auto_record_video", True),
            "audio_enabled": config.get("auto_record_audio", True),
            "stealth_mode": config.get("auto_stealth", True)
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.encounters.insert_one(encounter_doc)
    
    # Log the trigger
    trigger_doc = {
        "trigger_id": str(uuid.uuid4())[:12],
        "user_id": user_id,
        "encounter_id": encounter_id,
        "gesture_type": trigger.gesture_type,
        "trigger_source": trigger.trigger_source,
        "latitude": trigger.latitude,
        "longitude": trigger.longitude,
        "triggered_at": datetime.now(timezone.utc)
    }
    
    await db.panic_triggers.insert_one(trigger_doc)
    
    # Notify contacts if enabled
    contacts_notified = 0
    if config.get("notify_contacts", False):
        background_tasks.add_task(notify_emergency_contacts, user_id, encounter_id)
        # Get count for response
        contacts = await db.trusted_contacts.count_documents({"user_id": user_id})
        contacts_notified = contacts
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "stealth_mode": config.get("auto_stealth", True),
        "video_enabled": config.get("auto_record_video", True),
        "audio_enabled": config.get("auto_record_audio", True),
        "contacts_notified": contacts_notified,
        "message": "Panic recording started"
    }

@router.post("/test")
async def test_panic_gesture(current_user: dict = Depends(get_current_user)):
    """Test panic gesture detection without starting recording"""
    
    config = await db.panic_gesture_config.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "message": "Panic gesture test successful",
        "config": {
            "enabled": config.get("enabled", True) if config else True,
            "gesture_type": config.get("gesture_type", "shake") if config else "shake",
            "sensitivity": config.get("sensitivity", "medium") if config else "medium"
        }
    }


# ============== HISTORY ENDPOINTS ==============

@router.get("/history")
async def get_panic_trigger_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get history of panic triggers"""
    
    triggers = await db.panic_triggers.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("triggered_at", -1).limit(limit).to_list(limit)
    
    return {"triggers": triggers, "count": len(triggers)}


# ============== GESTURE PRESETS ==============

@router.get("/presets")
async def get_gesture_presets():
    """Get available gesture presets"""
    return {
        "presets": [
            {
                "id": "shake",
                "name": "Shake Pattern",
                "description": "Shake your phone 3 times quickly",
                "icon": "📳",
                "sensitivity_options": ["low", "medium", "high"],
                "default_settings": {
                    "shake_threshold": 3,
                    "shake_duration_ms": 1000
                }
            },
            {
                "id": "volume_triple",
                "name": "Triple Volume Press",
                "description": "Press volume up or down 3 times quickly",
                "icon": "🔊",
                "sensitivity_options": ["low", "medium", "high"],
                "default_settings": {
                    "press_count": 3,
                    "press_duration_ms": 1500
                }
            },
            {
                "id": "power_triple",
                "name": "Triple Power Press",
                "description": "Press power button 3 times quickly (Android)",
                "icon": "⚡",
                "sensitivity_options": ["low", "medium", "high"],
                "default_settings": {
                    "press_count": 3,
                    "press_duration_ms": 1500
                },
                "platform_note": "May require accessibility permissions on some devices"
            },
            {
                "id": "squeeze",
                "name": "Squeeze Gesture",
                "description": "Squeeze edges of phone (supported devices)",
                "icon": "✊",
                "sensitivity_options": ["low", "medium", "high"],
                "default_settings": {
                    "squeeze_pressure": "medium"
                },
                "platform_note": "Only available on devices with squeeze sensors"
            }
        ]
    }
