"""
Emergency Contacts Router - Manage trusted contacts for emergency alerts
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
import uuid

from app.db.database import db
from app.core.security import get_current_user

router = APIRouter(prefix="/emergency-contacts", tags=["Emergency Contacts"])


class EmergencyContactCreate(BaseModel):
    name: str
    relationship: str  # family, friend, attorney, other
    phone: Optional[str] = None
    email: Optional[str] = None
    notify_on_encounter: bool = True
    notify_on_sos: bool = True
    notify_on_dead_mans_switch: bool = True
    priority: int = 1  # 1 = highest priority


class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notify_on_encounter: Optional[bool] = None
    notify_on_sos: Optional[bool] = None
    notify_on_dead_mans_switch: Optional[bool] = None
    priority: Optional[int] = None
    active: Optional[bool] = None


@router.get("")
async def get_emergency_contacts(current_user: dict = Depends(get_current_user)):
    """Get all emergency contacts for the current user"""
    user_id = current_user["user_id"]
    
    contacts = await db.emergency_contacts.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("priority", 1).to_list(50)
    
    return {
        "contacts": contacts,
        "count": len(contacts)
    }


@router.post("")
async def create_emergency_contact(
    contact: EmergencyContactCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a new emergency contact"""
    user_id = current_user["user_id"]
    
    # Check if user already has 10 contacts
    existing_count = await db.emergency_contacts.count_documents({"user_id": user_id})
    if existing_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 emergency contacts allowed")
    
    contact_doc = {
        "contact_id": f"ec_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        **contact.model_dump(),
        "active": True,
        "contact_user_id": None,  # Will be set if contact is also a JUSTICE user
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Check if contact email matches a JUSTICE user
    if contact.email:
        existing_user = await db.users.find_one(
            {"email": contact.email},
            {"_id": 0, "user_id": 1}
        )
        if existing_user:
            contact_doc["contact_user_id"] = existing_user["user_id"]
    
    await db.emergency_contacts.insert_one(contact_doc)
    contact_doc.pop("_id", None)
    
    return {
        "success": True,
        "contact": contact_doc
    }


@router.put("/{contact_id}")
async def update_emergency_contact(
    contact_id: str,
    update: EmergencyContactUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an emergency contact"""
    user_id = current_user["user_id"]
    
    # Build update dict with only provided fields
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.emergency_contacts.update_one(
        {"contact_id": contact_id, "user_id": user_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Get updated contact
    contact = await db.emergency_contacts.find_one(
        {"contact_id": contact_id},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "contact": contact
    }


@router.delete("/{contact_id}")
async def delete_emergency_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an emergency contact"""
    user_id = current_user["user_id"]
    
    result = await db.emergency_contacts.delete_one({
        "contact_id": contact_id,
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    return {"success": True}


@router.post("/{contact_id}/test")
async def test_emergency_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a test alert to an emergency contact"""
    user_id = current_user["user_id"]
    
    contact = await db.emergency_contacts.find_one(
        {"contact_id": contact_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    user = await db.users.find_one(
        {"user_id": user_id},
        {"_id": 0, "name": 1}
    )
    
    # If contact is a JUSTICE user, send in-app notification
    if contact.get("contact_user_id"):
        from app.routers.notifications import create_notification
        await create_notification(
            user_id=contact["contact_user_id"],
            notification_type="system",
            title="🧪 Test Alert",
            message=f"This is a test alert from {user.get('name', 'a JUSTICE user')}. You are set as their emergency contact.",
            send_push=True
        )
    
    # TODO: Send SMS if phone number provided (requires Twilio)
    # TODO: Send email if email provided
    
    return {
        "success": True,
        "message": f"Test alert sent to {contact['name']}"
    }


@router.post("/reorder")
async def reorder_contacts(
    contact_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Reorder emergency contacts by priority"""
    user_id = current_user["user_id"]
    
    for priority, contact_id in enumerate(contact_ids, 1):
        await db.emergency_contacts.update_one(
            {"contact_id": contact_id, "user_id": user_id},
            {"$set": {"priority": priority}}
        )
    
    return {"success": True, "message": "Contacts reordered"}
