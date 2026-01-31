"""
3D Evidence Reconstruction Router

API endpoints for creating and viewing 3D reconstructions of encounters.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.db.database import db
from app.core.security import get_current_user
from app.services.reconstruction_3d import get_reconstruction_service


router = APIRouter(prefix="/reconstruction", tags=["3D Reconstruction"])


class CreateReconstructionRequest(BaseModel):
    encounter_id: str
    options: Optional[Dict[str, Any]] = None


class ReconstructionResponse(BaseModel):
    success: bool
    reconstruction: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/create", response_model=ReconstructionResponse)
async def create_reconstruction(
    request: CreateReconstructionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new 3D reconstruction from an encounter.
    
    This analyzes the encounter's video, audio, GPS data, and transcriptions
    to generate a navigable 3D scene visualization.
    """
    try:
        service = get_reconstruction_service(db)
        reconstruction = await service.create_reconstruction(
            user_id=current_user["user_id"],
            encounter_id=request.encounter_id,
            options=request.options
        )
        
        return ReconstructionResponse(
            success=True,
            reconstruction=reconstruction,
            message="3D reconstruction created successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reconstruction: {str(e)}")


@router.get("/{reconstruction_id}")
async def get_reconstruction(
    reconstruction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific 3D reconstruction with full scene data."""
    service = get_reconstruction_service(db)
    reconstruction = await service.get_reconstruction(
        user_id=current_user["user_id"],
        reconstruction_id=reconstruction_id
    )
    
    if not reconstruction:
        raise HTTPException(status_code=404, detail="Reconstruction not found")
    
    return {
        "success": True,
        "reconstruction": reconstruction
    }


@router.get("/encounter/{encounter_id}")
async def get_reconstruction_by_encounter(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get reconstruction for a specific encounter (creates if doesn't exist)."""
    service = get_reconstruction_service(db)
    
    # Check if reconstruction exists
    existing = await db.reconstructions_3d.find_one({
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"]
    }, {"_id": 0})
    
    if existing:
        return {
            "success": True,
            "reconstruction": existing,
            "cached": True
        }
    
    # Create new reconstruction
    try:
        reconstruction = await service.create_reconstruction(
            user_id=current_user["user_id"],
            encounter_id=encounter_id
        )
        return {
            "success": True,
            "reconstruction": reconstruction,
            "cached": False
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/")
async def list_reconstructions(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """List user's 3D reconstructions."""
    service = get_reconstruction_service(db)
    reconstructions = await service.list_reconstructions(
        user_id=current_user["user_id"],
        limit=limit
    )
    
    return {
        "success": True,
        "reconstructions": reconstructions,
        "count": len(reconstructions)
    }


@router.delete("/{reconstruction_id}")
async def delete_reconstruction(
    reconstruction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a 3D reconstruction."""
    service = get_reconstruction_service(db)
    deleted = await service.delete_reconstruction(
        user_id=current_user["user_id"],
        reconstruction_id=reconstruction_id
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Reconstruction not found")
    
    return {
        "success": True,
        "message": "Reconstruction deleted"
    }


@router.get("/preview/{encounter_id}")
async def get_reconstruction_preview(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a lightweight preview of what the reconstruction would look like.
    Useful for showing a thumbnail before generating the full reconstruction.
    """
    # Get encounter data
    encounter = await db.encounters.find_one({
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"]
    }, {"_id": 0})
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get evidence count
    evidence_count = await db.evidence.count_documents({
        "case_id": encounter.get("case_id"),
        "user_id": current_user["user_id"]
    })
    
    # Basic preview info
    return {
        "success": True,
        "preview": {
            "encounter_id": encounter_id,
            "encounter_type": encounter.get("encounter_type", "unknown"),
            "duration": encounter.get("duration", 0),
            "has_location": bool(encounter.get("location")),
            "has_transcriptions": len(encounter.get("transcriptions", [])) > 0,
            "violation_count": len(encounter.get("violations", [])),
            "evidence_count": evidence_count,
            "can_reconstruct": True,
            "estimated_complexity": "medium" if evidence_count < 10 else "high"
        }
    }
