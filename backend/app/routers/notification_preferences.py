"""
Notification Preferences Router - User notification settings management
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.database import db
from app.core.security import get_current_user

router = APIRouter(prefix="/notification-preferences", tags=["Notification Preferences"])


class NotificationPreferences(BaseModel):
    # In-app notifications (always on by default)
    in_app_enabled: bool = True
    
    # Push notification settings
    push_enabled: bool = True
    push_messages: bool = True
    push_case_updates: bool = True
    push_attorney_responses: bool = True
    push_sos_alerts: bool = True  # Critical - always recommended
    push_system: bool = False
    push_warnings: bool = True
    
    # Email notification settings
    email_enabled: bool = False
    email_daily_digest: bool = False
    email_case_updates: bool = True
    email_attorney_responses: bool = True
    email_sos_alerts: bool = True
    
    # Quiet hours (don't send push during these times)
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"  # 10 PM
    quiet_hours_end: Optional[str] = "08:00"    # 8 AM


# Default preferences
DEFAULT_PREFERENCES = NotificationPreferences().model_dump()


@router.get("")
async def get_preferences(current_user: dict = Depends(get_current_user)):
    """Get user's notification preferences"""
    user_id = current_user["user_id"]
    
    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id},
        {"_id": 0, "user_id": 0}
    )
    
    if not prefs:
        return DEFAULT_PREFERENCES
    
    # Merge with defaults to ensure all fields exist
    return {**DEFAULT_PREFERENCES, **prefs}


@router.put("")
async def update_preferences(
    preferences: NotificationPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user's notification preferences"""
    user_id = current_user["user_id"]
    
    prefs_dict = preferences.model_dump()
    prefs_dict["updated_at"] = datetime.now(timezone.utc)
    
    await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": prefs_dict, "$setOnInsert": {"user_id": user_id, "created_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    return {"success": True, "preferences": prefs_dict}


@router.post("/reset")
async def reset_preferences(current_user: dict = Depends(get_current_user)):
    """Reset notification preferences to defaults"""
    user_id = current_user["user_id"]
    
    await db.notification_preferences.delete_one({"user_id": user_id})
    
    return {"success": True, "preferences": DEFAULT_PREFERENCES}


# Helper function to check if a notification type should be sent
async def should_send_notification(
    user_id: str,
    notification_type: str,
    channel: str = "push"  # push, email, in_app
) -> bool:
    """
    Check if a notification should be sent based on user preferences.
    
    Args:
        user_id: The user's ID
        notification_type: Type of notification (message, case_update, etc.)
        channel: Delivery channel (push, email, in_app)
    
    Returns:
        True if notification should be sent, False otherwise
    """
    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not prefs:
        prefs = DEFAULT_PREFERENCES
    
    # In-app notifications are always sent unless explicitly disabled
    if channel == "in_app":
        return prefs.get("in_app_enabled", True)
    
    # Check channel-level toggle
    if channel == "push" and not prefs.get("push_enabled", True):
        return False
    if channel == "email" and not prefs.get("email_enabled", False):
        return False
    
    # Check quiet hours for push notifications
    if channel == "push" and prefs.get("quiet_hours_enabled", False):
        from datetime import datetime
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        start = prefs.get("quiet_hours_start", "22:00")
        end = prefs.get("quiet_hours_end", "08:00")
        
        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if start > end:
            if current_time >= start or current_time < end:
                return False
        else:
            if start <= current_time < end:
                return False
    
    # Map notification types to preference keys
    type_mapping = {
        "message": f"{channel}_messages",
        "case_update": f"{channel}_case_updates",
        "attorney_response": f"{channel}_attorney_responses",
        "sos_alert": f"{channel}_sos_alerts",
        "system": f"{channel}_system",
        "warning": f"{channel}_warnings"
    }
    
    pref_key = type_mapping.get(notification_type, f"{channel}_system")
    
    # Default to True for unknown types (except system which defaults False)
    default_value = notification_type != "system"
    
    return prefs.get(pref_key, default_value)
