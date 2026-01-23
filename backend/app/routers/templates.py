"""
Report Templates Router - CRUD endpoints for managing custom report templates
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.db.database import db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Report Templates"])


# ============== MODELS ==============

class BrandingConfig(BaseModel):
    firm_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: str = "#4f46e5"  # Indigo default
    secondary_color: str = "#7c3aed"  # Purple default
    accent_color: str = "#3b82f6"  # Blue default


class SectionConfig(BaseModel):
    show_overview: bool = True
    show_key_points: bool = True
    show_action_items: bool = True
    show_legal_concerns: bool = True
    show_recommendations: bool = True
    show_follow_up: bool = True
    show_call_info: bool = True
    show_timestamps: bool = True


class TemplateCreate(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    branding: Optional[BrandingConfig] = None
    sections: Optional[SectionConfig] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    intro_message: Optional[str] = None
    confidentiality_notice: Optional[str] = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    description: Optional[str] = None
    branding: Optional[BrandingConfig] = None
    sections: Optional[SectionConfig] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    intro_message: Optional[str] = None
    confidentiality_notice: Optional[str] = None
    is_default: Optional[bool] = None


# ============== ENDPOINTS ==============

@router.get("/my")
async def get_my_templates(current_user: dict = Depends(get_current_user)):
    """Get all report templates for the current user"""
    user_id = current_user["user_id"]
    
    templates = await db.report_templates.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    # Format datetime fields
    for template in templates:
        for field in ["created_at", "updated_at"]:
            if template.get(field) and hasattr(template[field], 'isoformat'):
                template[field] = template[field].isoformat()
    
    return {"templates": templates}


@router.post("/create")
async def create_template(
    template_data: TemplateCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new report template"""
    user_id = current_user["user_id"]
    
    # Check template limit (max 10 per user)
    existing_count = await db.report_templates.count_documents({"user_id": user_id})
    if existing_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 templates allowed per user")
    
    now = datetime.now(timezone.utc)
    template_id = f"tmpl_{uuid.uuid4().hex[:12]}"
    
    # If setting as default, unset other defaults
    if template_data.is_default:
        await db.report_templates.update_many(
            {"user_id": user_id, "is_default": True},
            {"$set": {"is_default": False}}
        )
    
    # Build branding config
    branding = template_data.branding.dict() if template_data.branding else {
        "firm_name": None,
        "logo_url": None,
        "primary_color": "#4f46e5",
        "secondary_color": "#7c3aed",
        "accent_color": "#3b82f6"
    }
    
    # Build sections config
    sections = template_data.sections.dict() if template_data.sections else {
        "show_overview": True,
        "show_key_points": True,
        "show_action_items": True,
        "show_legal_concerns": True,
        "show_recommendations": True,
        "show_follow_up": True,
        "show_call_info": True,
        "show_timestamps": True
    }
    
    template_doc = {
        "template_id": template_id,
        "user_id": user_id,
        "template_name": template_data.template_name,
        "description": template_data.description,
        "branding": branding,
        "sections": sections,
        "header_text": template_data.header_text,
        "footer_text": template_data.footer_text,
        "intro_message": template_data.intro_message,
        "confidentiality_notice": template_data.confidentiality_notice or (
            "This document contains confidential attorney-client communication. "
            "If you are not the intended recipient, please delete this document."
        ),
        "is_default": template_data.is_default,
        "created_at": now,
        "updated_at": now
    }
    
    await db.report_templates.insert_one(template_doc)
    
    logger.info(f"Created report template {template_id} for user {user_id}")
    
    # Remove MongoDB _id before returning
    template_doc.pop("_id", None)
    template_doc["created_at"] = template_doc["created_at"].isoformat()
    template_doc["updated_at"] = template_doc["updated_at"].isoformat()
    
    return {
        "status": "created",
        "template": template_doc
    }


@router.get("/default")
async def get_default_template(current_user: dict = Depends(get_current_user)):
    """Get the user's default template or system default"""
    user_id = current_user["user_id"]
    
    # Try to find user's default template
    template = await db.report_templates.find_one(
        {"user_id": user_id, "is_default": True},
        {"_id": 0}
    )
    
    if not template:
        # Return system default config
        return {
            "template": {
                "template_id": "system_default",
                "template_name": "Default Template",
                "is_default": True,
                "branding": {
                    "firm_name": "JUSTICE Platform",
                    "logo_url": None,
                    "primary_color": "#4f46e5",
                    "secondary_color": "#7c3aed",
                    "accent_color": "#3b82f6"
                },
                "sections": {
                    "show_overview": True,
                    "show_key_points": True,
                    "show_action_items": True,
                    "show_legal_concerns": True,
                    "show_recommendations": True,
                    "show_follow_up": True,
                    "show_call_info": True,
                    "show_timestamps": True
                },
                "header_text": None,
                "footer_text": None,
                "intro_message": None,
                "confidentiality_notice": (
                    "This document contains confidential attorney-client communication. "
                    "If you are not the intended recipient, please delete this document."
                )
            }
        }
    
    # Format datetime fields
    for field in ["created_at", "updated_at"]:
        if template.get(field) and hasattr(template[field], 'isoformat'):
            template[field] = template[field].isoformat()
    
    return {"template": template}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific report template"""
    user_id = current_user["user_id"]
    
    template = await db.report_templates.find_one(
        {"template_id": template_id, "user_id": user_id},
        {"_id": 0}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Format datetime fields
    for field in ["created_at", "updated_at"]:
        if template.get(field) and hasattr(template[field], 'isoformat'):
            template[field] = template[field].isoformat()
    
    return {"template": template}


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    update_data: TemplateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a report template"""
    user_id = current_user["user_id"]
    
    # Find existing template
    template = await db.report_templates.find_one(
        {"template_id": template_id, "user_id": user_id}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Build update document
    updates = {"updated_at": datetime.now(timezone.utc)}
    
    if update_data.template_name is not None:
        updates["template_name"] = update_data.template_name
    
    if update_data.description is not None:
        updates["description"] = update_data.description
    
    if update_data.branding is not None:
        updates["branding"] = update_data.branding.dict()
    
    if update_data.sections is not None:
        updates["sections"] = update_data.sections.dict()
    
    if update_data.header_text is not None:
        updates["header_text"] = update_data.header_text
    
    if update_data.footer_text is not None:
        updates["footer_text"] = update_data.footer_text
    
    if update_data.intro_message is not None:
        updates["intro_message"] = update_data.intro_message
    
    if update_data.confidentiality_notice is not None:
        updates["confidentiality_notice"] = update_data.confidentiality_notice
    
    if update_data.is_default is not None:
        if update_data.is_default:
            # Unset other defaults
            await db.report_templates.update_many(
                {"user_id": user_id, "is_default": True},
                {"$set": {"is_default": False}}
            )
        updates["is_default"] = update_data.is_default
    
    await db.report_templates.update_one(
        {"template_id": template_id},
        {"$set": updates}
    )
    
    logger.info(f"Updated report template {template_id}")
    
    # Get updated template
    updated = await db.report_templates.find_one(
        {"template_id": template_id},
        {"_id": 0}
    )
    
    # Format datetime fields
    for field in ["created_at", "updated_at"]:
        if updated.get(field) and hasattr(updated[field], 'isoformat'):
            updated[field] = updated[field].isoformat()
    
    return {
        "status": "updated",
        "template": updated
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a report template"""
    user_id = current_user["user_id"]
    
    result = await db.report_templates.delete_one(
        {"template_id": template_id, "user_id": user_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update any schedules using this template to use default
    await db.scheduled_reports.update_many(
        {"user_id": user_id, "template_id": template_id},
        {"$unset": {"template_id": ""}}
    )
    
    logger.info(f"Deleted report template {template_id}")
    
    return {
        "status": "deleted",
        "template_id": template_id
    }


@router.post("/{template_id}/set-default")
async def set_default_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Set a template as the default"""
    user_id = current_user["user_id"]
    
    template = await db.report_templates.find_one(
        {"template_id": template_id, "user_id": user_id}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Unset all other defaults
    await db.report_templates.update_many(
        {"user_id": user_id, "is_default": True},
        {"$set": {"is_default": False}}
    )
    
    # Set this one as default
    await db.report_templates.update_one(
        {"template_id": template_id},
        {"$set": {
            "is_default": True,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    logger.info(f"Set template {template_id} as default for user {user_id}")
    
    return {
        "status": "success",
        "template_id": template_id,
        "is_default": True
    }


@router.post("/{template_id}/duplicate")
async def duplicate_template(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Create a copy of an existing template"""
    user_id = current_user["user_id"]
    
    # Check template limit
    existing_count = await db.report_templates.count_documents({"user_id": user_id})
    if existing_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 templates allowed per user")
    
    template = await db.report_templates.find_one(
        {"template_id": template_id, "user_id": user_id}
    )
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    now = datetime.now(timezone.utc)
    new_template_id = f"tmpl_{uuid.uuid4().hex[:12]}"
    
    # Create new template with same settings
    new_template = {
        "template_id": new_template_id,
        "user_id": user_id,
        "template_name": f"{template['template_name']} (Copy)",
        "description": template.get("description"),
        "branding": template.get("branding"),
        "sections": template.get("sections"),
        "header_text": template.get("header_text"),
        "footer_text": template.get("footer_text"),
        "intro_message": template.get("intro_message"),
        "confidentiality_notice": template.get("confidentiality_notice"),
        "is_default": False,
        "created_at": now,
        "updated_at": now
    }
    
    await db.report_templates.insert_one(new_template)
    
    logger.info(f"Duplicated template {template_id} to {new_template_id}")
    
    new_template.pop("_id", None)
    new_template["created_at"] = new_template["created_at"].isoformat()
    new_template["updated_at"] = new_template["updated_at"].isoformat()
    
    return {
        "status": "duplicated",
        "template": new_template
    }
