"""
Multi-Cloud Backup Router - Redundant evidence storage across multiple cloud providers
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional

from app.routers.auth import get_current_user
from app.services.multi_cloud_backup import multi_cloud_backup
from app.db.database import db

router = APIRouter(prefix="/backup", tags=["Multi-Cloud Backup"])


@router.get("/providers")
async def get_enabled_providers(current_user: dict = Depends(get_current_user)):
    """Get list of enabled cloud backup providers"""
    providers = multi_cloud_backup.get_enabled_providers()
    
    return {
        "success": True,
        "providers": providers,
        "count": len(providers),
        "redundancy_available": len(providers) >= 2
    }


@router.post("/evidence/{evidence_id}")
async def backup_evidence(
    evidence_id: str,
    file: UploadFile = File(...),
    encounter_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Backup evidence to all available cloud providers.
    Uploads simultaneously to S3, IPFS, and local storage.
    """
    
    # Read file data
    file_data = await file.read()
    
    if len(file_data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Perform multi-cloud backup
    result = await multi_cloud_backup.backup_evidence(
        file_data=file_data,
        filename=file.filename,
        evidence_id=evidence_id,
        encounter_id=encounter_id,
        user_id=current_user.get("user_id"),
        metadata={
            "original_filename": file.filename,
            "content_type": file.content_type
        }
    )
    
    return {
        "success": True,
        "message": f"Evidence backed up to {result['total_backups']} providers",
        **result
    }


@router.post("/encounter/{encounter_id}/all")
async def backup_all_encounter_evidence(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Backup all evidence from an encounter to multiple clouds.
    Useful for ensuring complete redundancy after an encounter ends.
    """
    from pathlib import Path
    
    # Get encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Find all evidence files for this encounter
    evidence_dir = Path(f"/app/data/encounters/{encounter_id}")
    
    if not evidence_dir.exists():
        raise HTTPException(status_code=404, detail="No evidence files found")
    
    backup_results = []
    
    for file_path in evidence_dir.glob("**/*"):
        if file_path.is_file():
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                evidence_id = f"ev_{encounter_id}_{file_path.stem}"
                
                result = await multi_cloud_backup.backup_evidence(
                    file_data=file_data,
                    filename=file_path.name,
                    evidence_id=evidence_id,
                    encounter_id=encounter_id,
                    user_id=current_user.get("user_id")
                )
                
                backup_results.append({
                    "filename": file_path.name,
                    "evidence_id": evidence_id,
                    "success": result["total_backups"] > 0,
                    "providers_backed_up": result["total_backups"]
                })
            except Exception as e:
                backup_results.append({
                    "filename": file_path.name,
                    "success": False,
                    "error": str(e)
                })
    
    successful = sum(1 for r in backup_results if r.get("success"))
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "total_files": len(backup_results),
        "successful_backups": successful,
        "failed_backups": len(backup_results) - successful,
        "results": backup_results
    }


@router.get("/status/{evidence_id}")
async def get_backup_status(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get backup status for a specific evidence item"""
    
    status = await multi_cloud_backup.get_backup_status(
        evidence_id=evidence_id,
        user_id=current_user.get("user_id")
    )
    
    return {
        "success": True,
        **status
    }


@router.post("/verify/{evidence_id}")
async def verify_backup_integrity(
    evidence_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Verify backup integrity across all providers"""
    
    verification = await multi_cloud_backup.verify_backup_integrity(
        evidence_id=evidence_id,
        user_id=current_user.get("user_id")
    )
    
    return {
        "success": True,
        **verification
    }


@router.get("/history")
async def get_backup_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user's backup history"""
    
    backups = await db.evidence_backups.find(
        {"user_id": current_user.get("user_id")},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "success": True,
        "backups": backups,
        "count": len(backups)
    }
