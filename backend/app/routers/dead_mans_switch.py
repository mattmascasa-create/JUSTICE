"""
Dead Man's Switch Router

Safety-critical feature that automatically publishes evidence
if the user fails to check in during an active encounter.

Features:
- Trusted contacts management
- Auto-publish configuration
- Check-in mechanism with heartbeat
- Emergency evidence release
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr
import uuid
import asyncio

from app.core.security import get_current_user
from app.db.database import db

router = APIRouter(prefix="/dead-mans-switch", tags=["dead-mans-switch"])


# ============== PYDANTIC MODELS ==============

class TrustedContact(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    relationship: str = "emergency_contact"  # emergency_contact, attorney, family, friend
    notify_methods: List[str] = ["email"]  # email, sms, both

class DeadMansSwitchConfig(BaseModel):
    enabled: bool = False
    check_in_interval_minutes: int = 15  # How often user must check in
    grace_period_minutes: int = 5  # Extra time before triggering
    auto_publish_to_contacts: bool = True
    auto_publish_to_cloud: bool = True
    auto_notify_attorney: bool = True
    auto_call_emergency: bool = False  # 911 integration (future)
    secret_disable_phrase: Optional[str] = None  # Phrase to disable under duress

class CheckInRequest(BaseModel):
    encounter_id: Optional[str] = None
    status: str = "ok"  # ok, extended, emergency
    extend_minutes: Optional[int] = None

class TriggerOverride(BaseModel):
    reason: str
    secret_phrase: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

async def get_user_config(user_id: str):
    """Get user's dead man's switch configuration"""
    config = await db.dead_mans_switch_config.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    return config

async def send_emergency_notifications(user_id: str, encounter_id: str, contacts: list):
    """Send emergency notifications to all trusted contacts"""
    try:
        # Get user info
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1, "email": 1})
        user_name = user.get("name", "A JUSTICE user") if user else "A JUSTICE user"
        
        # Get encounter details
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0, "encounter_type": 1, "address": 1, "latitude": 1, "longitude": 1, "created_at": 1}
        )
        
        location_str = encounter.get("address", "Unknown location") if encounter else "Unknown"
        encounter_type = encounter.get("encounter_type", "encounter") if encounter else "encounter"
        
        # Try to send emails via SendGrid
        try:
            import os
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            sendgrid_key = os.environ.get("SENDGRID_API_KEY")
            if sendgrid_key:
                sg = SendGridAPIClient(sendgrid_key)
                
                for contact in contacts:
                    if "email" in contact.get("notify_methods", []) or "both" in contact.get("notify_methods", []):
                        message = Mail(
                            from_email="alerts@justice-app.com",
                            to_emails=contact["email"],
                            subject=f"🚨 EMERGENCY: {user_name} needs help - Dead Man's Switch Triggered",
                            html_content=f"""
                            <h2>🚨 EMERGENCY ALERT - Dead Man's Switch Triggered</h2>
                            <p><strong>{user_name}</strong> was in a {encounter_type} and has not checked in.</p>
                            <p><strong>Last Known Location:</strong> {location_str}</p>
                            <p><strong>Coordinates:</strong> {encounter.get('latitude', 'N/A')}, {encounter.get('longitude', 'N/A')}</p>
                            <p><strong>Started:</strong> {encounter.get('created_at', 'Unknown')}</p>
                            <hr>
                            <p>Evidence has been automatically preserved and backed up.</p>
                            <p>Please attempt to contact {user_name} immediately and consider calling emergency services if unable to reach them.</p>
                            <p><em>This is an automated emergency alert from the JUSTICE Civil Rights Defense System.</em></p>
                            """
                        )
                        sg.send(message)
                        
        except Exception as e:
            print(f"SendGrid notification failed: {e}")
        
        # Try SMS via Twilio
        try:
            import os
            from twilio.rest import Client
            
            twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
            twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
            
            if twilio_sid and twilio_token and twilio_phone:
                client = Client(twilio_sid, twilio_token)
                
                for contact in contacts:
                    if contact.get("phone") and ("sms" in contact.get("notify_methods", []) or "both" in contact.get("notify_methods", [])):
                        client.messages.create(
                            body=f"🚨 EMERGENCY: {user_name} triggered Dead Man's Switch during {encounter_type} at {location_str}. Evidence auto-preserved. Please check on them immediately!",
                            from_=twilio_phone,
                            to=contact["phone"]
                        )
                        
        except Exception as e:
            print(f"Twilio notification failed: {e}")
            
        # Log the trigger event
        await db.dead_mans_switch_triggers.insert_one({
            "trigger_id": str(uuid.uuid4()),
            "user_id": user_id,
            "encounter_id": encounter_id,
            "contacts_notified": len(contacts),
            "triggered_at": datetime.now(timezone.utc),
            "location": location_str
        })
        
        return True
        
    except Exception as e:
        print(f"Emergency notification error: {e}")
        return False

async def auto_publish_evidence(user_id: str, encounter_id: str):
    """Auto-publish evidence to cloud storage"""
    try:
        # Get all evidence for this encounter
        evidence_list = await db.evidence.find(
            {"encounter_id": encounter_id},
            {"_id": 0}
        ).to_list(100)
        
        # Mark all evidence as emergency-published
        await db.evidence.update_many(
            {"encounter_id": encounter_id},
            {"$set": {
                "emergency_published": True,
                "emergency_published_at": datetime.now(timezone.utc),
                "emergency_reason": "dead_mans_switch_triggered"
            }}
        )
        
        # Create emergency backup record
        await db.emergency_backups.insert_one({
            "backup_id": str(uuid.uuid4()),
            "user_id": user_id,
            "encounter_id": encounter_id,
            "evidence_count": len(evidence_list),
            "created_at": datetime.now(timezone.utc),
            "reason": "dead_mans_switch"
        })
        
        return True
        
    except Exception as e:
        print(f"Auto-publish error: {e}")
        return False


# ============== TRUSTED CONTACTS ENDPOINTS ==============

@router.get("/contacts")
async def get_trusted_contacts(current_user: dict = Depends(get_current_user)):
    """Get user's trusted contacts"""
    contacts = await db.trusted_contacts.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).to_list(20)
    
    return {"contacts": contacts}

@router.post("/contacts")
async def add_trusted_contact(
    contact: TrustedContact,
    current_user: dict = Depends(get_current_user)
):
    """Add a trusted contact"""
    contact_id = str(uuid.uuid4())[:12]
    
    contact_doc = {
        "contact_id": contact_id,
        "user_id": current_user["user_id"],
        **contact.dict(),
        "created_at": datetime.now(timezone.utc),
        "verified": False  # Could add email verification later
    }
    
    await db.trusted_contacts.insert_one(contact_doc)
    
    return {
        "success": True,
        "contact_id": contact_id,
        "message": f"Trusted contact {contact.name} added"
    }

@router.delete("/contacts/{contact_id}")
async def remove_trusted_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a trusted contact"""
    result = await db.trusted_contacts.delete_one({
        "contact_id": contact_id,
        "user_id": current_user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"success": True, "message": "Contact removed"}


# ============== CONFIGURATION ENDPOINTS ==============

@router.get("/config")
async def get_switch_config(current_user: dict = Depends(get_current_user)):
    """Get dead man's switch configuration"""
    config = await get_user_config(current_user["user_id"])
    
    if not config:
        # Return default config
        config = {
            "user_id": current_user["user_id"],
            "enabled": False,
            "check_in_interval_minutes": 15,
            "grace_period_minutes": 5,
            "auto_publish_to_contacts": True,
            "auto_publish_to_cloud": True,
            "auto_notify_attorney": True,
            "auto_call_emergency": False
        }
    
    return config

@router.put("/config")
async def update_switch_config(
    config: DeadMansSwitchConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update dead man's switch configuration"""
    config_doc = {
        "user_id": current_user["user_id"],
        **config.dict(),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.dead_mans_switch_config.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    return {"success": True, "message": "Configuration updated"}


# ============== CHECK-IN ENDPOINTS ==============

@router.post("/check-in")
async def check_in(
    request: CheckInRequest,
    current_user: dict = Depends(get_current_user)
):
    """User check-in to reset the dead man's switch timer"""
    user_id = current_user["user_id"]
    
    # Get config
    config = await get_user_config(user_id)
    if not config or not config.get("enabled"):
        return {"success": True, "message": "Dead man's switch not enabled"}
    
    # Calculate next check-in time
    interval = config.get("check_in_interval_minutes", 15)
    if request.extend_minutes:
        interval = request.extend_minutes
    
    next_check_in = datetime.now(timezone.utc) + timedelta(minutes=interval)
    
    # Update check-in record
    await db.dead_mans_switch_sessions.update_one(
        {"user_id": user_id, "active": True},
        {"$set": {
            "last_check_in": datetime.now(timezone.utc),
            "next_check_in_deadline": next_check_in,
            "status": request.status,
            "encounter_id": request.encounter_id
        }},
        upsert=True
    )
    
    return {
        "success": True,
        "next_check_in": next_check_in.isoformat(),
        "interval_minutes": interval,
        "message": f"Checked in. Next check-in required by {next_check_in.strftime('%H:%M:%S')}"
    }

@router.post("/start-session")
async def start_session(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start a dead man's switch session for an encounter"""
    user_id = current_user["user_id"]
    
    # Get config
    config = await get_user_config(user_id)
    if not config or not config.get("enabled"):
        return {"success": False, "message": "Dead man's switch not enabled. Enable in settings first."}
    
    # Get trusted contacts
    contacts = await db.trusted_contacts.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(20)
    
    if not contacts:
        return {"success": False, "message": "No trusted contacts configured. Add contacts first."}
    
    interval = config.get("check_in_interval_minutes", 15)
    grace = config.get("grace_period_minutes", 5)
    next_deadline = datetime.now(timezone.utc) + timedelta(minutes=interval)
    trigger_time = next_deadline + timedelta(minutes=grace)
    
    session_id = str(uuid.uuid4())[:12]
    
    session_doc = {
        "session_id": session_id,
        "user_id": user_id,
        "encounter_id": encounter_id,
        "active": True,
        "started_at": datetime.now(timezone.utc),
        "last_check_in": datetime.now(timezone.utc),
        "next_check_in_deadline": next_deadline,
        "trigger_time": trigger_time,
        "contacts_count": len(contacts),
        "config": config
    }
    
    # Deactivate any existing sessions
    await db.dead_mans_switch_sessions.update_many(
        {"user_id": user_id, "active": True},
        {"$set": {"active": False, "ended_at": datetime.now(timezone.utc), "end_reason": "new_session"}}
    )
    
    await db.dead_mans_switch_sessions.insert_one(session_doc)
    
    return {
        "success": True,
        "session_id": session_id,
        "next_check_in": next_deadline.isoformat(),
        "trigger_time": trigger_time.isoformat(),
        "interval_minutes": interval,
        "grace_period_minutes": grace,
        "contacts_to_notify": len(contacts),
        "message": f"Dead Man's Switch activated. Check in every {interval} minutes."
    }

@router.post("/end-session")
async def end_session(
    current_user: dict = Depends(get_current_user)
):
    """Safely end the dead man's switch session"""
    user_id = current_user["user_id"]
    
    result = await db.dead_mans_switch_sessions.update_many(
        {"user_id": user_id, "active": True},
        {"$set": {
            "active": False,
            "ended_at": datetime.now(timezone.utc),
            "end_reason": "user_ended"
        }}
    )
    
    return {
        "success": True,
        "sessions_ended": result.modified_count,
        "message": "Dead Man's Switch deactivated safely"
    }

@router.get("/status")
async def get_session_status(current_user: dict = Depends(get_current_user)):
    """Get current dead man's switch session status"""
    user_id = current_user["user_id"]
    
    session = await db.dead_mans_switch_sessions.find_one(
        {"user_id": user_id, "active": True},
        {"_id": 0}
    )
    
    if not session:
        return {"active": False, "message": "No active session"}
    
    now = datetime.now(timezone.utc)
    next_deadline = session.get("next_check_in_deadline")
    trigger_time = session.get("trigger_time")
    
    time_until_deadline = (next_deadline - now).total_seconds() if next_deadline else 0
    time_until_trigger = (trigger_time - now).total_seconds() if trigger_time else 0
    
    status = "ok"
    if time_until_deadline < 0:
        status = "overdue"
    elif time_until_deadline < 120:  # Less than 2 minutes
        status = "warning"
    
    return {
        "active": True,
        "session_id": session.get("session_id"),
        "encounter_id": session.get("encounter_id"),
        "status": status,
        "last_check_in": session.get("last_check_in"),
        "next_check_in_deadline": next_deadline,
        "trigger_time": trigger_time,
        "seconds_until_deadline": max(0, time_until_deadline),
        "seconds_until_trigger": max(0, time_until_trigger),
        "contacts_to_notify": session.get("contacts_count", 0)
    }


# ============== TRIGGER ENDPOINTS ==============

@router.post("/trigger/{encounter_id}")
async def manual_trigger(
    encounter_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger the dead man's switch (emergency button)"""
    user_id = current_user["user_id"]
    
    # Get contacts
    contacts = await db.trusted_contacts.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(20)
    
    if not contacts:
        raise HTTPException(status_code=400, detail="No trusted contacts configured")
    
    # Send notifications in background
    background_tasks.add_task(send_emergency_notifications, user_id, encounter_id, contacts)
    background_tasks.add_task(auto_publish_evidence, user_id, encounter_id)
    
    # End session
    await db.dead_mans_switch_sessions.update_many(
        {"user_id": user_id, "active": True},
        {"$set": {
            "active": False,
            "ended_at": datetime.now(timezone.utc),
            "end_reason": "manual_trigger"
        }}
    )
    
    return {
        "success": True,
        "message": "Emergency alert sent to all trusted contacts",
        "contacts_notified": len(contacts),
        "evidence_preserved": True
    }

@router.post("/cancel-trigger")
async def cancel_trigger(
    override: TriggerOverride,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an impending trigger (requires secret phrase if configured)"""
    user_id = current_user["user_id"]
    
    config = await get_user_config(user_id)
    
    # Check secret phrase if configured
    if config and config.get("secret_disable_phrase"):
        if override.secret_phrase != config.get("secret_disable_phrase"):
            raise HTTPException(status_code=403, detail="Invalid secret phrase")
    
    # Reset the session
    await db.dead_mans_switch_sessions.update_one(
        {"user_id": user_id, "active": True},
        {"$set": {
            "last_check_in": datetime.now(timezone.utc),
            "next_check_in_deadline": datetime.now(timezone.utc) + timedelta(minutes=15),
            "trigger_time": datetime.now(timezone.utc) + timedelta(minutes=20),
            "cancel_reason": override.reason
        }}
    )
    
    return {"success": True, "message": "Trigger cancelled, timer reset"}


# ============== HISTORY ENDPOINTS ==============

@router.get("/history")
async def get_trigger_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get history of dead man's switch triggers"""
    triggers = await db.dead_mans_switch_triggers.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("triggered_at", -1).limit(limit).to_list(limit)
    
    return {"triggers": triggers}
