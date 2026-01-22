"""
S3 Backup Router - Cloud backup for evidence files
"""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from app.db.database import db
from app.core.security import get_current_user
from app.core.config import (
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME,
    S3_ENABLED, UPLOADS_DIR
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backup", tags=["Backup"])

# Initialize S3 client if credentials are available
s3_client = None
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

if S3_ENABLED:
    try:
        import boto3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        logger.info(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}")


async def upload_to_s3(file_path: Path, s3_key: str) -> dict:
    """Upload a single file to S3"""
    if not S3_ENABLED or not s3_client:
        return {"success": False, "error": "S3 not configured"}
    
    try:
        with open(file_path, 'rb') as f:
            s3_client.upload_fileobj(
                f,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )
        return {"success": True, "s3_key": s3_key}
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return {"success": False, "error": str(e)}


async def run_backup_job(user_id: str = None):
    """Run a backup job for all evidence files"""
    backup_id = f"backup_{uuid.uuid4().hex[:12]}"
    start_time = datetime.now(timezone.utc)
    
    # Create backup record
    backup_record = {
        "backup_id": backup_id,
        "status": "running",
        "started_at": start_time,
        "completed_at": None,
        "triggered_by": user_id or "system",
        "files_total": 0,
        "files_backed_up": 0,
        "files_failed": 0,
        "total_size_bytes": 0,
        "errors": []
    }
    await db.s3_backups.insert_one(dict(backup_record))
    
    try:
        # Get all evidence files
        evidence_list = await db.evidence.find({}, {"_id": 0}).to_list(length=1000)
        backup_record["files_total"] = len(evidence_list)
        
        for ev in evidence_list:
            file_name = ev.get("file_name")
            evidence_id = ev.get("evidence_id")
            file_path = UPLOADS_DIR / file_name
            
            if not file_path.exists():
                backup_record["files_failed"] += 1
                backup_record["errors"].append(f"File not found: {file_name}")
                continue
            
            # Create S3 key with structure: backups/YYYY-MM-DD/evidence_id/filename
            date_prefix = start_time.strftime("%Y-%m-%d")
            s3_key = f"justice-backups/{date_prefix}/{evidence_id}/{file_name}"
            
            result = await upload_to_s3(file_path, s3_key)
            
            if result["success"]:
                backup_record["files_backed_up"] += 1
                backup_record["total_size_bytes"] += file_path.stat().st_size
                
                # Update evidence record with S3 info
                await db.evidence.update_one(
                    {"evidence_id": evidence_id},
                    {"$set": {
                        "s3_backup": {
                            "backed_up": True,
                            "s3_key": s3_key,
                            "backup_id": backup_id,
                            "backed_up_at": datetime.now(timezone.utc)
                        }
                    }}
                )
            else:
                backup_record["files_failed"] += 1
                backup_record["errors"].append(f"{file_name}: {result.get('error')}")
        
        backup_record["status"] = "completed"
        backup_record["completed_at"] = datetime.now(timezone.utc)
        
    except Exception as e:
        backup_record["status"] = "failed"
        backup_record["errors"].append(str(e))
        logger.error(f"Backup job failed: {e}")
    
    # Update backup record
    await db.s3_backups.update_one(
        {"backup_id": backup_id},
        {"$set": backup_record}
    )
    
    logger.info(f"Backup {backup_id} completed: {backup_record['files_backed_up']}/{backup_record['files_total']} files")
    return backup_record


@router.get("/status")
async def get_backup_status(current_user: dict = Depends(get_current_user)):
    """Get S3 backup system status"""
    
    # Get last backup
    last_backup = await db.s3_backups.find_one(
        {},
        {"_id": 0},
        sort=[("started_at", -1)]
    )
    
    # Get backup stats
    total_backups = await db.s3_backups.count_documents({})
    successful_backups = await db.s3_backups.count_documents({"status": "completed"})
    
    # Get evidence backup stats
    total_evidence = await db.evidence.count_documents({})
    backed_up_evidence = await db.evidence.count_documents({"s3_backup.backed_up": True})
    
    # Check S3 connectivity if enabled
    s3_connected = False
    s3_bucket_exists = False
    if S3_ENABLED and s3_client:
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            s3_connected = True
            s3_bucket_exists = True
        except Exception as e:
            logger.warning(f"S3 connectivity check failed: {e}")
    
    return {
        "s3_enabled": S3_ENABLED,
        "s3_connected": s3_connected,
        "s3_bucket": S3_BUCKET_NAME if S3_ENABLED else None,
        "s3_region": AWS_REGION if S3_ENABLED else None,
        "last_backup": {
            "backup_id": last_backup.get("backup_id") if last_backup else None,
            "status": last_backup.get("status") if last_backup else None,
            "started_at": last_backup.get("started_at").isoformat() if last_backup and last_backup.get("started_at") else None,
            "completed_at": last_backup.get("completed_at").isoformat() if last_backup and last_backup.get("completed_at") else None,
            "files_backed_up": last_backup.get("files_backed_up") if last_backup else 0,
            "files_total": last_backup.get("files_total") if last_backup else 0,
        } if last_backup else None,
        "statistics": {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "total_evidence_files": total_evidence,
            "backed_up_files": backed_up_evidence,
            "backup_coverage_percent": round((backed_up_evidence / total_evidence * 100) if total_evidence > 0 else 0, 1)
        },
        "setup_instructions": {
            "required_env_vars": [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY", 
                "S3_BUCKET_NAME"
            ],
            "optional_env_vars": [
                "AWS_REGION (default: us-east-1)"
            ],
            "how_to_get_credentials": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"
        } if not S3_ENABLED else None
    }


@router.post("/trigger")
async def trigger_backup(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a backup job"""
    if not S3_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="S3 backup is not configured. Please add AWS credentials to environment."
        )
    
    # Check if a backup is already running
    running_backup = await db.s3_backups.find_one({"status": "running"})
    if running_backup:
        raise HTTPException(
            status_code=409,
            detail=f"Backup already in progress: {running_backup['backup_id']}"
        )
    
    # Start backup in background
    backup_id = f"backup_{uuid.uuid4().hex[:12]}"
    
    # Create initial record
    await db.s3_backups.insert_one({
        "backup_id": backup_id,
        "status": "queued",
        "triggered_by": current_user["user_id"],
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "files_total": 0,
        "files_backed_up": 0,
        "files_failed": 0,
        "total_size_bytes": 0,
        "errors": []
    })
    
    # Schedule background task
    background_tasks.add_task(run_backup_job, current_user["user_id"])
    
    logger.info(f"Backup triggered by user {current_user['user_id']}")
    
    return {
        "message": "Backup job started",
        "backup_id": backup_id,
        "status": "queued"
    }


@router.get("/history")
async def get_backup_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get backup history"""
    backups = await db.s3_backups.find(
        {},
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(length=limit)
    
    # Convert datetime objects to strings
    for backup in backups:
        if backup.get("started_at"):
            backup["started_at"] = backup["started_at"].isoformat() if hasattr(backup["started_at"], 'isoformat') else str(backup["started_at"])
        if backup.get("completed_at"):
            backup["completed_at"] = backup["completed_at"].isoformat() if hasattr(backup["completed_at"], 'isoformat') else str(backup["completed_at"])
    
    return {"backups": backups}
