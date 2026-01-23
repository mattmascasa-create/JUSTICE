"""
Notifications Router - Real-time alerts and notification management
"""
import os
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid

from app.db.database import db
from app.core.security import get_current_user
from app.services.push_service import send_push_to_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# VAPID public key for frontend
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")


class NotificationCreate(BaseModel):
    type: str  # message, case_update, attorney_response, sos_alert, system, warning
    title: str
    message: str
    link: Optional[str] = None
    metadata: Optional[dict] = None


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict  # {p256dh: str, auth: str}


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Get the VAPID public key for push subscription"""
    return {"vapid_public_key": VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
async def subscribe_push(
    subscription: PushSubscription,
    current_user: dict = Depends(get_current_user)
):
    """Subscribe to push notifications"""
    user_id = current_user["user_id"]
    
    # Check if subscription already exists
    existing = await db.push_subscriptions.find_one({
        "user_id": user_id,
        "subscription.endpoint": subscription.endpoint
    })
    
    if existing:
        return {"success": True, "message": "Already subscribed"}
    
    # Store the subscription
    sub_doc = {
        "subscription_id": f"push_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "subscription": {
            "endpoint": subscription.endpoint,
            "keys": subscription.keys
        },
        "created_at": datetime.now(timezone.utc),
        "last_used": None
    }
    
    await db.push_subscriptions.insert_one(sub_doc)
    
    return {"success": True, "message": "Push subscription saved"}


@router.post("/push/unsubscribe")
async def unsubscribe_push(
    subscription: PushSubscription,
    current_user: dict = Depends(get_current_user)
):
    """Unsubscribe from push notifications"""
    user_id = current_user["user_id"]
    
    result = await db.push_subscriptions.delete_one({
        "user_id": user_id,
        "subscription.endpoint": subscription.endpoint
    })
    
    return {"success": True, "deleted": result.deleted_count > 0}


@router.get("/push/status")
async def get_push_status(current_user: dict = Depends(get_current_user)):
    """Check if user has push notifications enabled"""
    user_id = current_user["user_id"]
    
    count = await db.push_subscriptions.count_documents({"user_id": user_id})
    
    return {
        "enabled": count > 0,
        "subscription_count": count,
        "vapid_configured": bool(VAPID_PUBLIC_KEY)
    }


@router.get("")
async def get_notifications(
    limit: int = 50,
    include_read: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get user's notifications"""
    user_id = current_user["user_id"]
    
    query = {"user_id": user_id}
    if not include_read:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Count unread
    unread_count = await db.notifications.count_documents({
        "user_id": user_id,
        "read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications)
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a single notification as read"""
    user_id = current_user["user_id"]
    
    result = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}


@router.post("/mark-all-read")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    user_id = current_user["user_id"]
    
    result = await db.notifications.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "marked_count": result.modified_count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification"""
    user_id = current_user["user_id"]
    
    result = await db.notifications.delete_one({
        "notification_id": notification_id,
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}


@router.delete("")
async def clear_all_notifications(current_user: dict = Depends(get_current_user)):
    """Clear all notifications for the user"""
    user_id = current_user["user_id"]
    
    result = await db.notifications.delete_many({"user_id": user_id})
    
    return {"success": True, "deleted_count": result.deleted_count}


# Helper function to create notifications (used by other parts of the app)
async def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    link: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """Create a new notification for a user"""
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "link": link,
        "metadata": metadata or {},
        "read": False,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.notifications.insert_one(notification)
    
    # Remove _id for JSON serialization
    notification.pop("_id", None)
    
    return notification


# Endpoint to create test notifications (for development)
@router.post("/test")
async def create_test_notification(current_user: dict = Depends(get_current_user)):
    """Create a test notification (development only)"""
    import random
    
    types = ["message", "case_update", "attorney_response", "system", "warning"]
    titles = [
        "New message received",
        "Case status updated",
        "Attorney responded to your case",
        "System maintenance scheduled",
        "Action required on your case"
    ]
    messages = [
        "You have a new message from your attorney.",
        "Your case #12345 has been updated to 'Under Review'.",
        "Attorney Smith has provided feedback on your evidence.",
        "The system will undergo maintenance tonight at 11 PM.",
        "Please upload additional documentation for your case."
    ]
    
    idx = random.randint(0, len(types) - 1)
    
    notification = await create_notification(
        user_id=current_user["user_id"],
        notification_type=types[idx],
        title=titles[idx],
        message=messages[idx]
    )
    
    return {"success": True, "notification": notification}
