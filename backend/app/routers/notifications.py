"""
Notifications Router - Real-time alerts and notification management
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid

from app.db.database import db
from app.core.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreate(BaseModel):
    type: str  # message, case_update, attorney_response, sos_alert, system, warning
    title: str
    message: str
    link: Optional[str] = None
    metadata: Optional[dict] = None


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
    
    # Return without _id for JSON serialization
    del notification["_id"] if "_id" in notification else None
    
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
