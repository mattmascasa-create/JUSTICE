"""
Admin Portal Router

Provides admin-only endpoints for:
- User management
- Support ticket system
- AI-assisted ticket resolution
- Platform analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr
from bson import ObjectId
import uuid

from app.core.security import get_current_user
from app.db.database import db


router = APIRouter(prefix="/admin", tags=["admin"])


# ============== PYDANTIC MODELS ==============

class TicketCreate(BaseModel):
    subject: str
    description: str
    category: str = "general"  # general, technical, billing, feature_request, bug_report
    priority: str = "medium"   # low, medium, high, urgent
    attachments: Optional[List[str]] = None

class TicketUpdate(BaseModel):
    status: Optional[str] = None  # open, in_progress, resolved, closed
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    internal_notes: Optional[str] = None
    resolution: Optional[str] = None

class TicketResponse(BaseModel):
    subject: str
    description: str
    response_text: str
    is_public: bool = True

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


# ============== HELPER FUNCTIONS ==============

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure user is an admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ============== TICKET ENDPOINTS (User-facing) ==============

@router.post("/tickets")
async def create_ticket(
    ticket: TicketCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new support ticket (any authenticated user)"""
    ticket_id = str(uuid.uuid4())[:12]
    
    ticket_doc = {
        "ticket_id": ticket_id,
        "user_id": current_user["user_id"],
        "user_email": current_user["email"],
        "user_name": current_user.get("name", "Unknown"),
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": "open",
        "attachments": ticket.attachments or [],
        "responses": [],
        "internal_notes": [],
        "assigned_to": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "resolved_at": None
    }
    
    await db.support_tickets.insert_one(ticket_doc)
    
    # Create notification for admins
    await db.notifications.insert_one({
        "notification_id": str(uuid.uuid4()),
        "user_id": "admin",  # Special admin notifications
        "type": "new_ticket",
        "title": f"New Support Ticket: {ticket.subject}",
        "message": f"Ticket #{ticket_id} from {current_user.get('name', 'User')} - {ticket.category}",
        "data": {"ticket_id": ticket_id},
        "read": False,
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": "Support ticket created successfully. We'll respond within 24 hours."
    }


@router.get("/tickets/my")
async def get_my_tickets(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get current user's support tickets"""
    query = {"user_id": current_user["user_id"]}
    if status:
        query["status"] = status
    
    tickets = await db.support_tickets.find(
        query,
        {"_id": 0, "internal_notes": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"tickets": tickets}


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific ticket (owner or admin)"""
    ticket = await db.support_tickets.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0}
    )
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    is_admin = current_user.get("role") == "admin"
    is_owner = ticket["user_id"] == current_user["user_id"]
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Remove internal notes for non-admins
    if not is_admin:
        ticket.pop("internal_notes", None)
    
    return ticket


# ============== ADMIN-ONLY ENDPOINTS ==============

@router.get("/dashboard")
async def admin_dashboard(admin: dict = Depends(require_admin)):
    """Get admin dashboard statistics"""
    # User stats
    total_users = await db.users.count_documents({})
    active_today = await db.users.count_documents({
        "last_active": {"$gte": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)}
    })
    
    # User role breakdown
    citizens = await db.users.count_documents({"role": "citizen"})
    attorneys = await db.users.count_documents({"role": "attorney"})
    admins = await db.users.count_documents({"role": "admin"})
    
    # Ticket stats
    open_tickets = await db.support_tickets.count_documents({"status": "open"})
    in_progress_tickets = await db.support_tickets.count_documents({"status": "in_progress"})
    urgent_tickets = await db.support_tickets.count_documents({"status": "open", "priority": "urgent"})
    
    # Recent activity
    recent_tickets = await db.support_tickets.find(
        {},
        {"_id": 0, "ticket_id": 1, "subject": 1, "status": 1, "priority": 1, "created_at": 1, "user_name": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Encounter stats
    total_encounters = await db.encounters.count_documents({})
    active_encounters = await db.encounters.count_documents({"status": "active"})
    
    # Case stats
    total_cases = await db.cases.count_documents({})
    
    return {
        "users": {
            "total": total_users,
            "active_today": active_today,
            "by_role": {
                "citizens": citizens,
                "attorneys": attorneys,
                "admins": admins
            }
        },
        "tickets": {
            "open": open_tickets,
            "in_progress": in_progress_tickets,
            "urgent": urgent_tickets,
            "recent": recent_tickets
        },
        "platform": {
            "total_encounters": total_encounters,
            "active_encounters": active_encounters,
            "total_cases": total_cases
        }
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """List all users (admin only)"""
    query = {}
    
    if role:
        query["role"] = role
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    
    users = await db.users.find(
        query,
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.users.count_documents(query)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update: UserUpdate,
    admin: dict = Depends(require_admin)
):
    """Update user details (admin only)"""
    update_doc = {"updated_at": datetime.now(timezone.utc)}
    
    if update.role is not None:
        if update.role not in ["citizen", "attorney", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        update_doc["role"] = update.role
    
    if update.is_active is not None:
        update_doc["is_active"] = update.is_active
    
    if update.notes is not None:
        update_doc["admin_notes"] = update.notes
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": "User updated"}


@router.get("/tickets")
async def list_all_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """List all support tickets (admin only)"""
    query = {}
    
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if category:
        query["category"] = category
    if assigned_to:
        query["assigned_to"] = assigned_to
    
    skip = (page - 1) * limit
    
    tickets = await db.support_tickets.find(
        query,
        {"_id": 0}
    ).sort([("priority_order", 1), ("created_at", -1)]).skip(skip).limit(limit).to_list(limit)
    
    # Add priority order for sorting
    priority_order = {"urgent": 1, "high": 2, "medium": 3, "low": 4}
    for t in tickets:
        t["priority_order"] = priority_order.get(t.get("priority"), 3)
    
    tickets.sort(key=lambda x: (x["priority_order"], x["created_at"]), reverse=False)
    
    total = await db.support_tickets.count_documents(query)
    
    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    update: TicketUpdate,
    admin: dict = Depends(require_admin)
):
    """Update a support ticket (admin only)"""
    update_doc = {"updated_at": datetime.now(timezone.utc)}
    
    if update.status:
        update_doc["status"] = update.status
        if update.status == "resolved":
            update_doc["resolved_at"] = datetime.now(timezone.utc)
    
    if update.priority:
        update_doc["priority"] = update.priority
    
    if update.assigned_to:
        update_doc["assigned_to"] = update.assigned_to
    
    if update.resolution:
        update_doc["resolution"] = update.resolution
    
    result = await db.support_tickets.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Add internal note if provided
    if update.internal_notes:
        await db.support_tickets.update_one(
            {"ticket_id": ticket_id},
            {"$push": {
                "internal_notes": {
                    "note": update.internal_notes,
                    "added_by": admin["user_id"],
                    "added_at": datetime.now(timezone.utc)
                }
            }}
        )
    
    return {"success": True, "message": "Ticket updated"}


@router.post("/tickets/{ticket_id}/respond")
async def respond_to_ticket(
    ticket_id: str,
    response: TicketResponse,
    admin: dict = Depends(require_admin)
):
    """Add a response to a support ticket (admin only)"""
    ticket = await db.support_tickets.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    response_doc = {
        "response_id": str(uuid.uuid4())[:8],
        "responder_id": admin["user_id"],
        "responder_name": admin.get("name", "Support"),
        "text": response.response_text,
        "is_public": response.is_public,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.support_tickets.update_one(
        {"ticket_id": ticket_id},
        {
            "$push": {"responses": response_doc},
            "$set": {
                "status": "in_progress",
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Notify the ticket owner
    if response.is_public:
        await db.notifications.insert_one({
            "notification_id": str(uuid.uuid4()),
            "user_id": ticket["user_id"],
            "type": "ticket_response",
            "title": f"Response to your ticket: {ticket['subject']}",
            "message": response.response_text[:200] + "..." if len(response.response_text) > 200 else response.response_text,
            "data": {"ticket_id": ticket_id},
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })
    
    return {"success": True, "message": "Response added"}


@router.post("/tickets/{ticket_id}/ai-suggest")
async def get_ai_suggestion(
    ticket_id: str,
    admin: dict = Depends(require_admin)
):
    """Get AI-generated response suggestion for a ticket"""
    ticket = await db.support_tickets.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Try to use LLM for suggestion
    try:
        from emergentintegrations.llm import LlmChat
        import os
        
        llm = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            model="gpt-4o-mini"
        )
        
        prompt = f"""You are a helpful customer support agent for JUSTICE, a civil rights defense platform.

A user submitted the following support ticket:

Subject: {ticket['subject']}
Category: {ticket['category']}
Priority: {ticket['priority']}
Description: {ticket['description']}

Previous responses: {len(ticket.get('responses', []))}

Please provide a helpful, professional response that:
1. Acknowledges their concern
2. Provides specific guidance or solutions
3. Offers next steps if needed
4. Maintains a supportive, empathetic tone

Keep the response concise but thorough (2-3 paragraphs max)."""

        response = await llm.chat(user_message=prompt)
        
        return {
            "success": True,
            "suggestion": response,
            "source": "ai"
        }
        
    except Exception as e:
        # Fallback to template-based suggestions
        templates = {
            "technical": f"Thank you for reporting this technical issue. We understand how frustrating this can be.\n\nWe've logged your report about \"{ticket['subject']}\" and our team is investigating. In the meantime, please try:\n1. Refreshing the page or clearing your browser cache\n2. Trying a different browser\n3. Ensuring you have a stable internet connection\n\nIf the issue persists, please reply with any error messages you see.",
            
            "general": f"Thank you for reaching out to JUSTICE support.\n\nWe've received your inquiry about \"{ticket['subject']}\" and want to help you as quickly as possible.\n\nCould you provide any additional details that might help us assist you better? Our team typically responds within 24 hours.",
            
            "bug_report": f"Thank you for reporting this bug. Your feedback helps us improve JUSTICE for everyone.\n\nWe've documented the issue regarding \"{ticket['subject']}\" and our development team will investigate. We'll update you once we have more information or a fix is deployed.",
            
            "feature_request": f"Thank you for your feature suggestion! We love hearing ideas from our users.\n\nYour request for \"{ticket['subject']}\" has been added to our feature consideration list. While we can't guarantee implementation timelines, user feedback like yours directly influences our roadmap."
        }
        
        category = ticket.get("category", "general")
        suggestion = templates.get(category, templates["general"])
        
        return {
            "success": True,
            "suggestion": suggestion,
            "source": "template"
        }


@router.get("/analytics")
async def get_admin_analytics(
    days: int = Query(30, ge=1, le=365),
    admin: dict = Depends(require_admin)
):
    """Get platform analytics (admin only)"""
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # User growth
    new_users = await db.users.count_documents({"created_at": {"$gte": start_date}})
    
    # Encounter activity
    encounters_period = await db.encounters.count_documents({"created_at": {"$gte": start_date}})
    
    # Case activity
    cases_period = await db.cases.count_documents({"created_at": {"$gte": start_date}})
    
    # Ticket resolution time (average)
    resolved_tickets = await db.support_tickets.find(
        {"resolved_at": {"$ne": None}, "created_at": {"$gte": start_date}},
        {"created_at": 1, "resolved_at": 1}
    ).to_list(1000)
    
    avg_resolution_hours = 0
    if resolved_tickets:
        total_hours = sum(
            (t["resolved_at"] - t["created_at"]).total_seconds() / 3600
            for t in resolved_tickets if t.get("resolved_at")
        )
        avg_resolution_hours = round(total_hours / len(resolved_tickets), 1)
    
    return {
        "period_days": days,
        "users": {
            "new_registrations": new_users
        },
        "activity": {
            "encounters": encounters_period,
            "cases": cases_period
        },
        "support": {
            "tickets_resolved": len(resolved_tickets),
            "avg_resolution_hours": avg_resolution_hours
        }
    }


# ============== ADMIN SETUP ENDPOINT ==============

@router.post("/setup/create-admin")
async def create_first_admin(
    email: EmailStr,
    current_user: dict = Depends(get_current_user)
):
    """
    Promote a user to admin (only works if no admins exist yet)
    This is for initial setup only.
    """
    # Check if any admins exist
    admin_count = await db.users.count_documents({"role": "admin"})
    
    if admin_count > 0:
        # If admins exist, require current user to be admin
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403, 
                detail="Admin already exists. Contact existing admin for promotion."
            )
    
    # Find user by email and promote
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"role": "admin", "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "message": f"User {email} promoted to admin"}
