"""
Legal Document Generator Router
Endpoints for generating legal documents
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.legal_documents import legal_document_service, DocumentType
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
