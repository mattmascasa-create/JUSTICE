"""
Scheduled Reports Router - CRUD endpoints for managing automated email report schedules
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.db.database import db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["Scheduled Reports"])


# ============== MODELS ==============

class ScheduleCreate(BaseModel):
    frequency: str  # daily, weekly, monthly
    send_hour: int = 9  # 0-23, default 9 AM UTC
    send_day: Optional[int] = 0  # 0-6 for weekly (Monday=0)
    send_date: Optional[int] = 1  # 1-28 for monthly
    recipient_emails: List[EmailStr]
    report_name: Optional[str] = None


class ScheduleUpdate(BaseModel):
    frequency: Optional[str] = None
    send_hour: Optional[int] = None
    send_day: Optional[int] = None
    send_date: Optional[int] = None
    recipient_emails: Optional[List[EmailStr]] = None
    report_name: Optional[str] = None
    is_active: Optional[bool] = None


# ============== ENDPOINTS ==============

@router.get("/my")
async def get_my_schedules(current_user: dict = Depends(get_current_user)):
    """Get all scheduled reports for the current user"""
    user_id = current_user["user_id"]
    
    schedules = await db.scheduled_reports.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    # Format datetime fields
    for schedule in schedules:
        for field in ["created_at", "updated_at", "last_sent"]:
            if schedule.get(field) and hasattr(schedule[field], 'isoformat'):
                schedule[field] = schedule[field].isoformat()
    
    return {"schedules": schedules}


@router.post("/create")
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new scheduled report"""
    user_id = current_user["user_id"]
    user_email = current_user.get("email", "")
    user_name = current_user.get("name", user_email)
    
    # Validate frequency
    if schedule_data.frequency not in ["daily", "weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Frequency must be 'daily', 'weekly', or 'monthly'")
    
    # Validate send_hour
    if not 0 <= schedule_data.send_hour <= 23:
        raise HTTPException(status_code=400, detail="send_hour must be between 0 and 23")
    
    # Validate send_day for weekly
    if schedule_data.frequency == "weekly":
        if schedule_data.send_day is None:
            schedule_data.send_day = 0  # Default to Monday
        elif not 0 <= schedule_data.send_day <= 6:
            raise HTTPException(status_code=400, detail="send_day must be between 0 (Monday) and 6 (Sunday)")
    
    # Validate send_date for monthly
    if schedule_data.frequency == "monthly":
        if schedule_data.send_date is None:
            schedule_data.send_date = 1  # Default to 1st
        elif not 1 <= schedule_data.send_date <= 28:
            raise HTTPException(status_code=400, detail="send_date must be between 1 and 28")
    
    # Validate recipients
    if not schedule_data.recipient_emails:
        raise HTTPException(status_code=400, detail="At least one recipient email is required")
    
    if len(schedule_data.recipient_emails) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 recipients allowed")
    
    # Check for existing schedules (limit to 5 per user)
    existing_count = await db.scheduled_reports.count_documents({"user_id": user_id})
    if existing_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 scheduled reports allowed per user")
    
    now = datetime.now(timezone.utc)
    schedule_id = f"sched_{uuid.uuid4().hex[:12]}"
    
    # Generate default name if not provided
    report_name = schedule_data.report_name
    if not report_name:
        freq_label = schedule_data.frequency.capitalize()
        report_name = f"{freq_label} Summary Report"
    
    schedule_doc = {
        "schedule_id": schedule_id,
        "user_id": user_id,
        "user_name": user_name,
        "user_email": user_email,
        "report_name": report_name,
        "frequency": schedule_data.frequency,
        "send_hour": schedule_data.send_hour,
        "send_day": schedule_data.send_day,
        "send_date": schedule_data.send_date,
        "recipient_emails": schedule_data.recipient_emails,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_sent": None,
        "last_result": None,
        "last_recording_count": 0
    }
    
    await db.scheduled_reports.insert_one(schedule_doc)
    
    logger.info(f"Created scheduled report {schedule_id} for user {user_id}")
    
    # Remove MongoDB _id before returning
    schedule_doc.pop("_id", None)
    schedule_doc["created_at"] = schedule_doc["created_at"].isoformat()
    schedule_doc["updated_at"] = schedule_doc["updated_at"].isoformat()
    
    return {
        "status": "created",
        "schedule": schedule_doc
    }


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific scheduled report"""
    user_id = current_user["user_id"]
    
    schedule = await db.scheduled_reports.find_one(
        {"schedule_id": schedule_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Format datetime fields
    for field in ["created_at", "updated_at", "last_sent"]:
        if schedule.get(field) and hasattr(schedule[field], 'isoformat'):
            schedule[field] = schedule[field].isoformat()
    
    return {"schedule": schedule}


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    update_data: ScheduleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a scheduled report"""
    user_id = current_user["user_id"]
    
    # Find existing schedule
    schedule = await db.scheduled_reports.find_one(
        {"schedule_id": schedule_id, "user_id": user_id}
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Build update document
    updates = {"updated_at": datetime.now(timezone.utc)}
    
    if update_data.frequency is not None:
        if update_data.frequency not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Frequency must be 'daily', 'weekly', or 'monthly'")
        updates["frequency"] = update_data.frequency
    
    if update_data.send_hour is not None:
        if not 0 <= update_data.send_hour <= 23:
            raise HTTPException(status_code=400, detail="send_hour must be between 0 and 23")
        updates["send_hour"] = update_data.send_hour
    
    if update_data.send_day is not None:
        if not 0 <= update_data.send_day <= 6:
            raise HTTPException(status_code=400, detail="send_day must be between 0 and 6")
        updates["send_day"] = update_data.send_day
    
    if update_data.send_date is not None:
        if not 1 <= update_data.send_date <= 28:
            raise HTTPException(status_code=400, detail="send_date must be between 1 and 28")
        updates["send_date"] = update_data.send_date
    
    if update_data.recipient_emails is not None:
        if not update_data.recipient_emails:
            raise HTTPException(status_code=400, detail="At least one recipient email is required")
        if len(update_data.recipient_emails) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 recipients allowed")
        updates["recipient_emails"] = update_data.recipient_emails
    
    if update_data.report_name is not None:
        updates["report_name"] = update_data.report_name
    
    if update_data.is_active is not None:
        updates["is_active"] = update_data.is_active
    
    await db.scheduled_reports.update_one(
        {"schedule_id": schedule_id},
        {"$set": updates}
    )
    
    logger.info(f"Updated scheduled report {schedule_id}")
    
    # Get updated schedule
    updated = await db.scheduled_reports.find_one(
        {"schedule_id": schedule_id},
        {"_id": 0}
    )
    
    # Format datetime fields
    for field in ["created_at", "updated_at", "last_sent"]:
        if updated.get(field) and hasattr(updated[field], 'isoformat'):
            updated[field] = updated[field].isoformat()
    
    return {
        "status": "updated",
        "schedule": updated
    }


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a scheduled report"""
    user_id = current_user["user_id"]
    
    result = await db.scheduled_reports.delete_one(
        {"schedule_id": schedule_id, "user_id": user_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    logger.info(f"Deleted scheduled report {schedule_id}")
    
    return {
        "status": "deleted",
        "schedule_id": schedule_id
    }


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Toggle a schedule's active status"""
    user_id = current_user["user_id"]
    
    schedule = await db.scheduled_reports.find_one(
        {"schedule_id": schedule_id, "user_id": user_id}
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    new_status = not schedule.get("is_active", True)
    
    await db.scheduled_reports.update_one(
        {"schedule_id": schedule_id},
        {"$set": {
            "is_active": new_status,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    status_text = "activated" if new_status else "paused"
    logger.info(f"Schedule {schedule_id} {status_text}")
    
    return {
        "status": status_text,
        "schedule_id": schedule_id,
        "is_active": new_status
    }


@router.post("/{schedule_id}/test")
async def test_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a test email for a scheduled report (uses last 7 days of data)"""
    from app.services.email_service import send_pdf_email, EmailDeliveryError
    from app.services.scheduled_reports import generate_scheduled_report_pdf, generate_scheduled_report_email_html
    from datetime import timedelta
    
    user_id = current_user["user_id"]
    user_name = current_user.get("name", current_user.get("email", "JUSTICE User"))
    
    schedule = await db.scheduled_reports.find_one(
        {"schedule_id": schedule_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=7)
    
    # Find recordings with summaries
    recordings_data = []
    recordings = await db.call_recordings.find({
        "participants": user_id,
        "ai_summary": {"$exists": True, "$ne": None},
        "started_at": {"$gte": start_date}
    }, {"_id": 0}).to_list(100)
    
    for recording in recordings:
        call = await db.video_calls.find_one(
            {"call_id": recording.get("call_id")}, 
            {"_id": 0}
        )
        recordings_data.append({
            "recording": recording,
            "call": call,
            "summary": recording.get("ai_summary")
        })
    
    if not recordings_data:
        raise HTTPException(
            status_code=400, 
            detail="No recordings with summaries found in the last 7 days. Create some call recordings and generate summaries first."
        )
    
    # Generate PDF
    pdf = generate_scheduled_report_pdf(recordings_data, "Test", user_name)
    pdf_bytes = bytes(pdf.output())
    pdf_filename = f"test_summary_report_{now.strftime('%Y%m%d')}.pdf"
    
    # Generate email
    email_html = generate_scheduled_report_email_html(
        recording_count=len(recordings_data),
        period_label="Test",
        sender_name=user_name,
        start_date=start_date,
        end_date=now
    )
    
    # Send test email
    try:
        recipients = schedule.get("recipient_emails", [])
        subject = f"[TEST] Summary Report - JUSTICE Platform"
        
        await send_pdf_email(
            to_emails=recipients,
            subject=subject,
            body_html=email_html,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
            sender_name=user_name
        )
        
        logger.info(f"Test email sent for schedule {schedule_id}")
        
        return {
            "status": "sent",
            "message": f"Test email sent to {len(recipients)} recipient(s)",
            "recipients": recipients,
            "recording_count": len(recordings_data)
        }
        
    except EmailDeliveryError as e:
        raise HTTPException(status_code=500, detail=str(e))
