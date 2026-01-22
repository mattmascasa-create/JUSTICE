"""
Attorney Collaboration Router
Handles attorney invitations, case notes, messaging, and dashboard.
"""
from fastapi import APIRouter, HTTPException, Depends, Form
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import secrets

from app.db.database import db
from app.core.security import get_current_user, hash_password, verify_password, create_access_token
from app.services.websocket import manager

router = APIRouter(prefix="/attorney", tags=["Attorney"])


# ============== ATTORNEY INVITATION ==============

@router.post("/invite")
async def invite_attorney(
    email: str = Form(...),
    encounter_id: str = Form(...),
    message: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Invite an attorney to collaborate on an encounter.
    Generates a secure invite link valid for 48 hours.
    """
    # Verify user owns the encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check for existing pending invite
    existing = await db.attorney_invites.find_one({
        "email": email.lower(),
        "encounter_id": encounter_id,
        "status": "pending"
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Invitation already sent to this attorney")
    
    # Generate secure invite token
    invite_token = secrets.token_urlsafe(32)
    invite_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=48)
    
    invite_doc = {
        "invite_id": invite_id,
        "invite_token": invite_token,
        "email": email.lower(),
        "encounter_id": encounter_id,
        "client_id": current_user["user_id"],
        "client_name": current_user.get("name"),
        "message": message,
        "status": "pending",
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    
    await db.attorney_invites.insert_one(invite_doc)
    
    # Generate invite URL
    invite_url = f"/attorney/accept-invite?token={invite_token}"
    
    return {
        "success": True,
        "invite_id": invite_id,
        "invite_url": invite_url,
        "email": email.lower(),
        "expires_at": expires_at.isoformat(),
        "message": f"Invitation sent to {email}. They must register or login within 48 hours."
    }


@router.get("/invite/{invite_token}/details")
async def get_invite_details(invite_token: str):
    """
    Public endpoint - Get invite details for acceptance page.
    """
    invite = await db.attorney_invites.find_one(
        {"invite_token": invite_token},
        {"_id": 0}
    )
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Check expiration
    expires_at = datetime.fromisoformat(invite["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Invitation has expired")
    
    if invite["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation already {invite['status']}")
    
    return {
        "invite_id": invite["invite_id"],
        "client_name": invite.get("client_name"),
        "message": invite.get("message"),
        "expires_at": invite["expires_at"]
    }


@router.post("/accept-invite")
async def accept_invite(
    invite_token: str = Form(...),
    name: str = Form(...),
    password: str = Form(...)
):
    """
    Accept attorney invitation - creates account if needed.
    Basic registration - verification can be done later.
    """
    invite = await db.attorney_invites.find_one(
        {"invite_token": invite_token},
        {"_id": 0}
    )
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Check expiration
    expires_at = datetime.fromisoformat(invite["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Invitation has expired")
    
    if invite["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation already {invite['status']}")
    
    email = invite["email"]
    now = datetime.now(timezone.utc)
    
    # Check if attorney user already exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        # Existing user - just add attorney access
        attorney_id = existing_user["user_id"]
        
        # Update role if not already attorney
        if existing_user.get("role") != "attorney":
            await db.users.update_one(
                {"user_id": attorney_id},
                {"$set": {"role": "attorney"}}
            )
    else:
        # Create new attorney account
        attorney_id = f"att_{uuid.uuid4().hex[:12]}"
        hashed_pw = hash_password(password)
        
        user_doc = {
            "user_id": attorney_id,
            "email": email,
            "name": name,
            "password": hashed_pw,
            "role": "attorney",
            "attorney_profile": {
                "verified": False,
                "clients": [],
                "created_at": now.isoformat()
            },
            "created_at": now.isoformat()
        }
        
        await db.users.insert_one(user_doc)
    
    # Grant access to the encounter
    access_doc = {
        "access_id": f"acc_{uuid.uuid4().hex[:12]}",
        "attorney_id": attorney_id,
        "client_id": invite["client_id"],
        "encounter_id": invite["encounter_id"],
        "granted_at": now.isoformat(),
        "status": "active"
    }
    
    await db.attorney_access.insert_one(access_doc)
    
    # Update invite status
    await db.attorney_invites.update_one(
        {"invite_token": invite_token},
        {"$set": {
            "status": "accepted",
            "accepted_at": now.isoformat(),
            "attorney_id": attorney_id
        }}
    )
    
    # Add client to attorney's client list
    await db.users.update_one(
        {"user_id": attorney_id},
        {"$addToSet": {"attorney_profile.clients": invite["client_id"]}}
    )
    
    # Generate token
    token = create_access_token(attorney_id)
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "message": "Invitation accepted. You now have access to the encounter.",
        "attorney_id": attorney_id
    }


@router.post("/accept-invite/existing")
async def accept_invite_existing_user(
    invite_token: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Accept invitation as existing user - login and accept.
    """
    invite = await db.attorney_invites.find_one(
        {"invite_token": invite_token},
        {"_id": 0}
    )
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if invite["email"].lower() != email.lower():
        raise HTTPException(status_code=400, detail="Email does not match invitation")
    
    # Verify login
    user = await db.users.find_one({"email": email.lower()}, {"_id": 0})
    if not user or not verify_password(password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Continue with acceptance
    now = datetime.now(timezone.utc)
    attorney_id = user["user_id"]
    
    # Update role if needed
    if user.get("role") != "attorney":
        await db.users.update_one(
            {"user_id": attorney_id},
            {"$set": {"role": "attorney"}}
        )
    
    # Grant access
    access_doc = {
        "access_id": f"acc_{uuid.uuid4().hex[:12]}",
        "attorney_id": attorney_id,
        "client_id": invite["client_id"],
        "encounter_id": invite["encounter_id"],
        "granted_at": now.isoformat(),
        "status": "active"
    }
    
    await db.attorney_access.insert_one(access_doc)
    
    # Update invite
    await db.attorney_invites.update_one(
        {"invite_token": invite_token},
        {"$set": {
            "status": "accepted",
            "accepted_at": now.isoformat(),
            "attorney_id": attorney_id
        }}
    )
    
    # Add client
    await db.users.update_one(
        {"user_id": attorney_id},
        {"$addToSet": {"attorney_profile.clients": invite["client_id"]}}
    )
    
    token = create_access_token(attorney_id)
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "message": "Access granted to encounter."
    }


# ============== ATTORNEY VERIFICATION ==============

@router.post("/verify")
async def verify_attorney(
    bar_number: str = Form(...),
    firm_name: str = Form(None),
    specialization: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit attorney verification details.
    In production, this would trigger a verification process.
    """
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Only attorneys can verify their credentials")
    
    now = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "attorney_profile.bar_number": bar_number,
            "attorney_profile.firm_name": firm_name,
            "attorney_profile.specialization": specialization,
            "attorney_profile.verified": True,  # Auto-verify for demo
            "attorney_profile.verification_date": now.isoformat()
        }}
    )
    
    return {
        "success": True,
        "message": "Verification submitted successfully.",
        "verified": True
    }


# ============== ATTORNEY DASHBOARD ==============

@router.get("/dashboard")
async def get_attorney_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get attorney dashboard with stats and recent activity.
    """
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    attorney_id = current_user["user_id"]
    
    # Get all access grants
    access_list = await db.attorney_access.find(
        {"attorney_id": attorney_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    client_ids = list(set(a["client_id"] for a in access_list))
    encounter_ids = [a["encounter_id"] for a in access_list]
    
    # Get client details
    clients = []
    for client_id in client_ids:
        client = await db.users.find_one(
            {"user_id": client_id},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1}
        )
        if client:
            # Count encounters for this client
            client_encounters = [a for a in access_list if a["client_id"] == client_id]
            clients.append({
                "client_id": client["user_id"],
                "client_name": client.get("name"),
                "client_email": client.get("email"),
                "encounter_count": len(client_encounters),
                "last_activity": client_encounters[0].get("granted_at") if client_encounters else None
            })
    
    # Get unread messages count
    unread_count = await db.attorney_messages.count_documents({
        "recipient_id": attorney_id,
        "read": False
    })
    
    # Get encounters with highlights
    encounters_with_highlights = 0
    total_highlights = 0
    for enc_id in encounter_ids:
        enc = await db.encounters.find_one(
            {"encounter_id": enc_id},
            {"_id": 0, "highlights_count": 1}
        )
        if enc and enc.get("highlights_count", 0) > 0:
            encounters_with_highlights += 1
            total_highlights += enc.get("highlights_count", 0)
    
    return {
        "attorney_id": attorney_id,
        "attorney_name": current_user.get("name"),
        "verified": current_user.get("attorney_profile", {}).get("verified", False),
        "stats": {
            "total_clients": len(client_ids),
            "total_encounters": len(encounter_ids),
            "pending_reviews": encounters_with_highlights,
            "unread_messages": unread_count,
            "total_highlights": total_highlights
        },
        "clients": clients,
        "encounter_ids": encounter_ids
    }


@router.get("/clients")
async def get_attorney_clients(current_user: dict = Depends(get_current_user)):
    """Get all clients for this attorney."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    access_list = await db.attorney_access.find(
        {"attorney_id": current_user["user_id"], "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    client_ids = list(set(a["client_id"] for a in access_list))
    
    clients = []
    for client_id in client_ids:
        client = await db.users.find_one(
            {"user_id": client_id},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "created_at": 1}
        )
        if client:
            # Get encounter count
            enc_count = len([a for a in access_list if a["client_id"] == client_id])
            clients.append({
                "client_id": client["user_id"],
                "name": client.get("name"),
                "email": client.get("email"),
                "encounter_count": enc_count
            })
    
    return {"clients": clients}


@router.get("/encounters")
async def get_attorney_encounters(current_user: dict = Depends(get_current_user)):
    """Get all encounters this attorney has access to."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    access_list = await db.attorney_access.find(
        {"attorney_id": current_user["user_id"], "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    encounters = []
    for access in access_list:
        enc = await db.encounters.find_one(
            {"encounter_id": access["encounter_id"]},
            {"_id": 0}
        )
        if enc:
            # Get client name
            client = await db.users.find_one(
                {"user_id": access["client_id"]},
                {"_id": 0, "name": 1}
            )
            encounters.append({
                "encounter_id": enc["encounter_id"],
                "client_name": client.get("name") if client else "Unknown",
                "client_id": access["client_id"],
                "encounter_type": enc.get("encounter_type"),
                "status": enc.get("status"),
                "started_at": enc.get("started_at"),
                "address": enc.get("address"),
                "highlights_count": enc.get("highlights_count", 0),
                "access_granted_at": access["granted_at"]
            })
    
    return {"encounters": encounters}


# ============== CASE NOTES ==============

@router.post("/notes")
async def create_case_note(
    encounter_id: str = Form(...),
    content: str = Form(...),
    note_type: str = Form("general"),
    current_user: dict = Depends(get_current_user)
):
    """Create a case note for an encounter."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    # Verify access
    access = await db.attorney_access.find_one({
        "attorney_id": current_user["user_id"],
        "encounter_id": encounter_id,
        "status": "active"
    })
    
    if not access:
        raise HTTPException(status_code=403, detail="No access to this encounter")
    
    now = datetime.now(timezone.utc)
    note_id = f"note_{uuid.uuid4().hex[:12]}"
    
    note_doc = {
        "note_id": note_id,
        "encounter_id": encounter_id,
        "attorney_id": current_user["user_id"],
        "attorney_name": current_user.get("name"),
        "content": content,
        "note_type": note_type,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.case_notes.insert_one(note_doc)
    
    return {
        "success": True,
        "note_id": note_id,
        "created_at": now.isoformat()
    }


@router.get("/notes/{encounter_id}")
async def get_case_notes(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Get all case notes for an encounter."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    # Verify access
    access = await db.attorney_access.find_one({
        "attorney_id": current_user["user_id"],
        "encounter_id": encounter_id,
        "status": "active"
    })
    
    if not access:
        raise HTTPException(status_code=403, detail="No access to this encounter")
    
    notes = await db.case_notes.find(
        {"encounter_id": encounter_id, "attorney_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"notes": notes}


@router.put("/notes/{note_id}")
async def update_case_note(
    note_id: str,
    content: str = Form(...),
    note_type: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Update a case note."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    note = await db.case_notes.find_one({
        "note_id": note_id,
        "attorney_id": current_user["user_id"]
    })
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    update = {
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if note_type:
        update["note_type"] = note_type
    
    await db.case_notes.update_one(
        {"note_id": note_id},
        {"$set": update}
    )
    
    return {"success": True, "note_id": note_id}


@router.delete("/notes/{note_id}")
async def delete_case_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a case note."""
    if current_user.get("role") != "attorney":
        raise HTTPException(status_code=403, detail="Attorney access required")
    
    result = await db.case_notes.delete_one({
        "note_id": note_id,
        "attorney_id": current_user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"success": True}


# ============== MESSAGING ==============

@router.post("/messages")
async def send_message(
    recipient_id: str = Form(...),
    content: str = Form(...),
    encounter_id: str = Form(None),
    message_type: str = Form("text"),
    current_user: dict = Depends(get_current_user)
):
    """Send a message to client or attorney."""
    now = datetime.now(timezone.utc)
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    
    message_doc = {
        "message_id": message_id,
        "sender_id": current_user["user_id"],
        "sender_name": current_user.get("name"),
        "recipient_id": recipient_id,
        "encounter_id": encounter_id,
        "content": content,
        "message_type": message_type,
        "read": False,
        "created_at": now.isoformat()
    }
    
    await db.attorney_messages.insert_one(message_doc)
    
    # Send real-time notification
    await manager.send_to_user(recipient_id, {
        "type": "new_attorney_message",
        "message_id": message_id,
        "sender_id": current_user["user_id"],
        "sender_name": current_user.get("name"),
        "content": content[:100],  # Preview
        "encounter_id": encounter_id,
        "timestamp": now.isoformat()
    })
    
    return {
        "success": True,
        "message_id": message_id,
        "created_at": now.isoformat()
    }


@router.get("/messages")
async def get_messages(
    contact_id: str = None,
    encounter_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get messages - inbox or conversation with specific contact."""
    user_id = current_user["user_id"]
    
    query = {
        "$or": [
            {"sender_id": user_id},
            {"recipient_id": user_id}
        ]
    }
    
    if contact_id:
        query["$or"] = [
            {"sender_id": user_id, "recipient_id": contact_id},
            {"sender_id": contact_id, "recipient_id": user_id}
        ]
    
    if encounter_id:
        query["encounter_id"] = encounter_id
    
    messages = await db.attorney_messages.find(
        query,
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    return {"messages": messages}


@router.get("/messages/inbox")
async def get_inbox(current_user: dict = Depends(get_current_user)):
    """Get message inbox with conversation summaries."""
    user_id = current_user["user_id"]
    
    # Get all messages involving this user
    messages = await db.attorney_messages.find(
        {"$or": [{"sender_id": user_id}, {"recipient_id": user_id}]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    # Group by contact
    conversations = {}
    for msg in messages:
        contact_id = msg["sender_id"] if msg["sender_id"] != user_id else msg["recipient_id"]
        if contact_id not in conversations:
            conversations[contact_id] = {
                "contact_id": contact_id,
                "contact_name": msg.get("sender_name") if msg["sender_id"] != user_id else None,
                "last_message": msg["content"][:100],
                "last_message_at": msg["created_at"],
                "unread_count": 0
            }
        if msg["recipient_id"] == user_id and not msg.get("read"):
            conversations[contact_id]["unread_count"] += 1
    
    # Get contact names for those we don't have
    for contact_id, conv in conversations.items():
        if not conv["contact_name"]:
            user = await db.users.find_one({"user_id": contact_id}, {"_id": 0, "name": 1})
            conv["contact_name"] = user.get("name") if user else "Unknown"
    
    return {"conversations": list(conversations.values())}


@router.put("/messages/{message_id}/read")
async def mark_message_read(message_id: str, current_user: dict = Depends(get_current_user)):
    """Mark a message as read."""
    await db.attorney_messages.update_one(
        {"message_id": message_id, "recipient_id": current_user["user_id"]},
        {"$set": {"read": True}}
    )
    return {"success": True}


@router.put("/messages/read-all")
async def mark_all_read(
    contact_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Mark all messages from a contact as read."""
    query = {"recipient_id": current_user["user_id"], "read": False}
    if contact_id:
        query["sender_id"] = contact_id
    
    result = await db.attorney_messages.update_many(query, {"$set": {"read": True}})
    
    return {"success": True, "marked_read": result.modified_count}


# ============== ACCESS MANAGEMENT ==============

@router.delete("/access/{encounter_id}")
async def revoke_attorney_access(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Client revokes attorney access to an encounter."""
    # Verify ownership
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    result = await db.attorney_access.update_many(
        {"encounter_id": encounter_id, "client_id": current_user["user_id"]},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "revoked_count": result.modified_count}


@router.get("/my-attorneys")
async def get_my_attorneys(current_user: dict = Depends(get_current_user)):
    """Client gets list of attorneys with access to their encounters."""
    access_list = await db.attorney_access.find(
        {"client_id": current_user["user_id"], "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    attorney_ids = list(set(a["attorney_id"] for a in access_list))
    
    attorneys = []
    for att_id in attorney_ids:
        att = await db.users.find_one(
            {"user_id": att_id},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "attorney_profile": 1}
        )
        if att:
            # Get encounters this attorney has access to
            att_encounters = [a["encounter_id"] for a in access_list if a["attorney_id"] == att_id]
            attorneys.append({
                "attorney_id": att["user_id"],
                "name": att.get("name"),
                "email": att.get("email"),
                "verified": att.get("attorney_profile", {}).get("verified", False),
                "firm_name": att.get("attorney_profile", {}).get("firm_name"),
                "encounter_count": len(att_encounters),
                "encounters": att_encounters
            })
    
    return {"attorneys": attorneys}
