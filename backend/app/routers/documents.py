"""
Legal Document Generator Router
Endpoints for generating legal documents
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.legal_documents import legal_document_service, DocumentType
from app.services.email_service import send_document_shared_email, is_sendgrid_configured
from app.db.database import db

router = APIRouter(prefix="/documents", tags=["Legal Documents"])


class GenerateDocumentRequest(BaseModel):
    encounter_id: str
    document_type: str
    user_statement: Optional[str] = None
    injuries: Optional[str] = None
    witnesses: Optional[str] = None


class ShareDocumentRequest(BaseModel):
    recipient_id: str
    message: Optional[str] = None


@router.get("/types")
async def get_document_types():
    """Get available document types"""
    types = legal_document_service.get_document_types()
    return {"document_types": types}


@router.post("/generate")
async def generate_document(
    request: GenerateDocumentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate a legal document from encounter data"""
    try:
        doc_type = DocumentType(request.document_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Must be one of: {[t.value for t in DocumentType]}"
        )
    
    additional_info = {}
    if request.user_statement:
        additional_info["user_statement"] = request.user_statement
    if request.injuries:
        additional_info["injuries"] = request.injuries
    if request.witnesses:
        additional_info["witnesses"] = request.witnesses
    
    result = await legal_document_service.generate_document(
        user_id=current_user["user_id"],
        encounter_id=request.encounter_id,
        document_type=doc_type,
        additional_info=additional_info if additional_info else None
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to generate document"))
    
    return result


@router.get("/my-documents")
async def get_my_documents(current_user: dict = Depends(get_current_user)):
    """Get all documents for current user"""
    docs = await legal_document_service.get_user_documents(current_user["user_id"])
    return {"documents": docs, "count": len(docs)}


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific document"""
    doc = await legal_document_service.get_document(document_id, current_user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a document"""
    success = await legal_document_service.delete_document(document_id, current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}


@router.post("/{document_id}/share")
async def share_document(
    document_id: str,
    request: ShareDocumentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Share a document with an attorney or other user"""
    # Get the document
    doc = await legal_document_service.get_document(document_id, current_user["user_id"])
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify recipient exists
    recipient = await db.users.find_one({"user_id": request.recipient_id}, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Create share record
    share_id = f"share_{uuid.uuid4().hex[:12]}"
    share_record = {
        "share_id": share_id,
        "document_id": document_id,
        "owner_id": current_user["user_id"],
        "owner_name": current_user.get("name", "Unknown"),
        "recipient_id": request.recipient_id,
        "recipient_name": recipient.get("name", "Unknown"),
        "document_title": doc.get("title"),
        "document_type": doc.get("document_type"),
        "message": request.message,
        "shared_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",  # pending, viewed, acknowledged
        "viewed_at": None
    }
    
    await db.document_shares.insert_one(share_record)
    
    # Create notification for recipient
    notification = {
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": request.recipient_id,
        "type": "document_shared",
        "title": "Document Shared With You",
        "message": f"{current_user.get('name', 'A user')} shared a {doc.get('title', 'legal document')} with you.",
        "data": {
            "share_id": share_id,
            "document_id": document_id,
            "from_user": current_user.get("name"),
            "document_type": doc.get("document_type")
        },
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Send email notification if recipient has email
    email_sent = False
    if recipient.get("email") and is_sendgrid_configured():
        try:
            # Build view URL
            frontend_url = os.environ.get("FRONTEND_URL", "https://legal-shield-11.preview.emergentagent.com")
            view_url = f"{frontend_url}/legal-documents?share={share_id}"
            
            email_result = await send_document_shared_email(
                to_email=recipient["email"],
                sender_name=current_user.get("name", "A JUSTICE user"),
                document_title=doc.get("title", "Legal Document"),
                document_type=doc.get("document_type", "document"),
                message=request.message,
                view_url=view_url
            )
            email_sent = email_result.get("success", False)
        except Exception as e:
            print(f"Failed to send share notification email: {e}")
    
    return {
        "success": True,
        "share_id": share_id,
        "message": f"Document shared with {recipient.get('name', 'user')}",
        "email_sent": email_sent
    }


@router.get("/shared/received")
async def get_received_shares(current_user: dict = Depends(get_current_user)):
    """Get documents shared with the current user"""
    shares = await db.document_shares.find(
        {"recipient_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("shared_at", -1).to_list(100)
    
    return {"shares": shares, "count": len(shares)}


@router.get("/shared/sent")
async def get_sent_shares(current_user: dict = Depends(get_current_user)):
    """Get documents the current user has shared"""
    shares = await db.document_shares.find(
        {"owner_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("shared_at", -1).to_list(100)
    
    return {"shares": shares, "count": len(shares)}


@router.get("/shared/{share_id}")
async def get_shared_document(
    share_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a shared document (for recipient)"""
    # Find the share record
    share = await db.document_shares.find_one(
        {"share_id": share_id},
        {"_id": 0}
    )
    
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    # Check if user is owner or recipient
    if share["recipient_id"] != current_user["user_id"] and share["owner_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the actual document
    doc = await db.legal_documents.find_one(
        {"document_id": share["document_id"]},
        {"_id": 0}
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document no longer exists")
    
    # Mark as viewed if recipient is accessing
    if share["recipient_id"] == current_user["user_id"] and share["status"] == "pending":
        await db.document_shares.update_one(
            {"share_id": share_id},
            {"$set": {"status": "viewed", "viewed_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {
        "share": share,
        "document": doc
    }

