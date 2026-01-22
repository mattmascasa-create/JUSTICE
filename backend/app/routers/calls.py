"""
Video Call Router - WebRTC signaling and call management with recording
"""
import uuid
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Form, WebSocket, WebSocketDisconnect, UploadFile, File

from app.db.database import db
from app.core.security import get_current_user
from app.core.config import S3_ENABLED, S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, UPLOADS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["Video Calls"])

# In-memory store for active calls and WebSocket connections
active_calls = {}  # call_id -> call_info
call_connections = {}  # call_id -> {user_id: websocket}

# Initialize S3 client for recordings
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
        logger.info("S3 client initialized for call recordings")
    except Exception as e:
        logger.error(f"Failed to initialize S3 client for recordings: {e}")


@router.post("/initiate")
async def initiate_call(
    recipient_id: str = Form(...),
    call_type: str = Form("video"),  # video, audio
    encounter_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Initiate a video/audio call with another user"""
    caller_id = current_user["user_id"]
    
    # Verify recipient exists
    recipient = await db.users.find_one({"user_id": recipient_id}, {"_id": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Check if either party is already in a call
    for call_id, call in active_calls.items():
        if call["status"] == "active":
            if caller_id in [call["caller_id"], call["recipient_id"]]:
                raise HTTPException(status_code=409, detail="You are already in an active call")
            if recipient_id in [call["caller_id"], call["recipient_id"]]:
                raise HTTPException(status_code=409, detail="Recipient is already in a call")
    
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    call_record = {
        "call_id": call_id,
        "caller_id": caller_id,
        "caller_name": current_user.get("name", "Unknown"),
        "recipient_id": recipient_id,
        "recipient_name": recipient.get("name", "Unknown"),
        "call_type": call_type,
        "encounter_id": encounter_id,
        "status": "pending",  # pending, active, ended, rejected, missed
        "initiated_at": now,
        "answered_at": None,
        "ended_at": None,
        "duration_seconds": 0,
        "end_reason": None
    }
    
    # Store in memory for active signaling
    active_calls[call_id] = call_record
    
    # Store in database for history
    await db.video_calls.insert_one(dict(call_record))
    
    logger.info(f"Call {call_id} initiated by {caller_id} to {recipient_id}")
    
    return {
        "call_id": call_id,
        "status": "pending",
        "caller_name": current_user.get("name"),
        "recipient_id": recipient_id,
        "recipient_name": recipient.get("name"),
        "call_type": call_type
    }


@router.post("/{call_id}/answer")
async def answer_call(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Answer an incoming call"""
    user_id = current_user["user_id"]
    
    call = active_calls.get(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found or expired")
    
    if call["recipient_id"] != user_id:
        raise HTTPException(status_code=403, detail="You are not the recipient of this call")
    
    if call["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Call cannot be answered (status: {call['status']})")
    
    now = datetime.now(timezone.utc)
    call["status"] = "active"
    call["answered_at"] = now
    
    # Update in database
    await db.video_calls.update_one(
        {"call_id": call_id},
        {"$set": {"status": "active", "answered_at": now}}
    )
    
    logger.info(f"Call {call_id} answered by {user_id}")
    
    return {"call_id": call_id, "status": "active"}


@router.post("/{call_id}/reject")
async def reject_call(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject an incoming call"""
    user_id = current_user["user_id"]
    
    call = active_calls.get(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found or expired")
    
    if call["recipient_id"] != user_id:
        raise HTTPException(status_code=403, detail="You are not the recipient of this call")
    
    now = datetime.now(timezone.utc)
    call["status"] = "rejected"
    call["ended_at"] = now
    call["end_reason"] = "rejected"
    
    # Update in database
    await db.video_calls.update_one(
        {"call_id": call_id},
        {"$set": {"status": "rejected", "ended_at": now, "end_reason": "rejected"}}
    )
    
    # Remove from active calls
    active_calls.pop(call_id, None)
    
    logger.info(f"Call {call_id} rejected by {user_id}")
    
    return {"call_id": call_id, "status": "rejected"}


@router.post("/{call_id}/end")
async def end_call(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End an active call"""
    user_id = current_user["user_id"]
    
    call = active_calls.get(call_id)
    if not call:
        # Try to find in database
        call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call["caller_id"], call["recipient_id"]]:
        raise HTTPException(status_code=403, detail="You are not a participant of this call")
    
    now = datetime.now(timezone.utc)
    duration = 0
    if call.get("answered_at"):
        answered_at = call["answered_at"]
        if isinstance(answered_at, str):
            answered_at = datetime.fromisoformat(answered_at.replace('Z', '+00:00'))
        duration = int((now - answered_at).total_seconds())
    
    # Update call record
    update_data = {
        "status": "ended",
        "ended_at": now,
        "duration_seconds": duration,
        "end_reason": "user_ended"
    }
    
    await db.video_calls.update_one(
        {"call_id": call_id},
        {"$set": update_data}
    )
    
    # Remove from active calls
    active_calls.pop(call_id, None)
    call_connections.pop(call_id, None)
    
    logger.info(f"Call {call_id} ended by {user_id}, duration: {duration}s")
    
    return {
        "call_id": call_id,
        "status": "ended",
        "duration_seconds": duration
    }


@router.get("/active")
async def get_active_call(current_user: dict = Depends(get_current_user)):
    """Get user's current active or pending call"""
    user_id = current_user["user_id"]
    
    for call_id, call in active_calls.items():
        if call["status"] in ["pending", "active"]:
            if user_id in [call["caller_id"], call["recipient_id"]]:
                return {
                    "has_active_call": True,
                    "call": {
                        "call_id": call["call_id"],
                        "caller_id": call["caller_id"],
                        "caller_name": call["caller_name"],
                        "recipient_id": call["recipient_id"],
                        "recipient_name": call["recipient_name"],
                        "call_type": call["call_type"],
                        "status": call["status"],
                        "is_caller": user_id == call["caller_id"]
                    }
                }
    
    return {"has_active_call": False, "call": None}


@router.get("/incoming")
async def get_incoming_calls(current_user: dict = Depends(get_current_user)):
    """Get incoming calls for the user"""
    user_id = current_user["user_id"]
    
    incoming = []
    for call_id, call in active_calls.items():
        if call["status"] == "pending" and call["recipient_id"] == user_id:
            incoming.append({
                "call_id": call["call_id"],
                "caller_id": call["caller_id"],
                "caller_name": call["caller_name"],
                "call_type": call["call_type"],
                "initiated_at": call["initiated_at"].isoformat() if hasattr(call["initiated_at"], 'isoformat') else call["initiated_at"]
            })
    
    return {"incoming_calls": incoming}


@router.get("/history")
async def get_call_history(
    limit: int = 20,
    contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get call history for the user"""
    user_id = current_user["user_id"]
    
    query = {
        "$or": [
            {"caller_id": user_id},
            {"recipient_id": user_id}
        ]
    }
    
    if contact_id:
        query = {
            "$or": [
                {"caller_id": user_id, "recipient_id": contact_id},
                {"caller_id": contact_id, "recipient_id": user_id}
            ]
        }
    
    calls = await db.video_calls.find(
        query,
        {"_id": 0}
    ).sort("initiated_at", -1).limit(limit).to_list(length=limit)
    
    # Convert datetime objects
    for call in calls:
        for field in ["initiated_at", "answered_at", "ended_at"]:
            if call.get(field) and hasattr(call[field], 'isoformat'):
                call[field] = call[field].isoformat()
    
    return {"calls": calls}


# WebSocket endpoint for call signaling
@router.websocket("/signal/{call_id}")
async def call_signaling(websocket: WebSocket, call_id: str):
    """WebSocket endpoint for WebRTC signaling"""
    await websocket.accept()
    
    # Get user from token
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="No token provided")
            return
        
        from app.core.security import get_current_user_ws
        user = await get_current_user_ws(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = user["user_id"]
    except Exception as e:
        logger.error(f"Auth error in signaling: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Verify call exists and user is participant
    call = active_calls.get(call_id)
    if not call:
        await websocket.close(code=4004, reason="Call not found")
        return
    
    if user_id not in [call["caller_id"], call["recipient_id"]]:
        await websocket.close(code=4003, reason="Not a participant")
        return
    
    # Register connection
    if call_id not in call_connections:
        call_connections[call_id] = {}
    call_connections[call_id][user_id] = websocket
    
    logger.info(f"User {user_id} connected to call {call_id} signaling")
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            # Forward signaling messages to the other participant
            other_user_id = call["recipient_id"] if user_id == call["caller_id"] else call["caller_id"]
            other_ws = call_connections.get(call_id, {}).get(other_user_id)
            
            if message_type in ["offer", "answer", "ice-candidate"]:
                if other_ws:
                    await other_ws.send_json({
                        "type": message_type,
                        "from": user_id,
                        "data": data.get("data")
                    })
            elif message_type == "call-accepted":
                if other_ws:
                    await other_ws.send_json({"type": "call-accepted", "from": user_id})
            elif message_type == "call-rejected":
                if other_ws:
                    await other_ws.send_json({"type": "call-rejected", "from": user_id})
            elif message_type == "call-ended":
                if other_ws:
                    await other_ws.send_json({"type": "call-ended", "from": user_id})
                break
            elif message_type == "screen-share-start":
                if other_ws:
                    await other_ws.send_json({"type": "screen-share-start", "from": user_id})
            elif message_type == "screen-share-stop":
                if other_ws:
                    await other_ws.send_json({"type": "screen-share-stop", "from": user_id})
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected from call {call_id}")
    except Exception as e:
        logger.error(f"Signaling error: {e}")
    finally:
        # Cleanup
        if call_id in call_connections and user_id in call_connections[call_id]:
            del call_connections[call_id][user_id]
            if not call_connections[call_id]:
                del call_connections[call_id]


# ============== CALL RECORDING ENDPOINTS ==============

@router.post("/{call_id}/recording/start")
async def start_recording(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start recording a call - notifies both parties"""
    user_id = current_user["user_id"]
    
    # Verify call exists
    call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call["caller_id"], call["recipient_id"]]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    recording_id = f"rec_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Create recording record
    recording = {
        "recording_id": recording_id,
        "call_id": call_id,
        "started_by": user_id,
        "started_at": now,
        "ended_at": None,
        "duration_seconds": 0,
        "file_size_bytes": 0,
        "s3_key": None,
        "s3_url": None,
        "local_path": None,
        "status": "recording",  # recording, uploading, completed, failed
        "participants": [call["caller_id"], call["recipient_id"]]
    }
    
    await db.call_recordings.insert_one(dict(recording))
    
    # Update call with recording info
    await db.video_calls.update_one(
        {"call_id": call_id},
        {"$set": {"is_recording": True, "current_recording_id": recording_id}}
    )
    
    # Notify other participant via WebSocket
    other_user_id = call["recipient_id"] if user_id == call["caller_id"] else call["caller_id"]
    other_ws = call_connections.get(call_id, {}).get(other_user_id)
    if other_ws:
        try:
            await other_ws.send_json({
                "type": "recording-started",
                "from": user_id,
                "recording_id": recording_id
            })
        except:
            pass
    
    logger.info(f"Recording {recording_id} started for call {call_id} by {user_id}")
    
    return {
        "recording_id": recording_id,
        "status": "recording",
        "message": "Recording started. Both parties have been notified."
    }


@router.post("/{call_id}/recording/stop")
async def stop_recording(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Stop recording a call"""
    user_id = current_user["user_id"]
    
    # Get call and current recording
    call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call["caller_id"], call["recipient_id"]]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    recording_id = call.get("current_recording_id")
    if not recording_id:
        raise HTTPException(status_code=400, detail="No active recording")
    
    now = datetime.now(timezone.utc)
    
    # Update recording
    recording = await db.call_recordings.find_one({"recording_id": recording_id})
    if recording:
        started_at = recording["started_at"]
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        duration = int((now - started_at).total_seconds())
        
        await db.call_recordings.update_one(
            {"recording_id": recording_id},
            {"$set": {
                "ended_at": now,
                "duration_seconds": duration,
                "status": "awaiting_upload"
            }}
        )
    
    # Update call
    await db.video_calls.update_one(
        {"call_id": call_id},
        {"$set": {"is_recording": False}}
    )
    
    # Notify other participant
    other_user_id = call["recipient_id"] if user_id == call["caller_id"] else call["caller_id"]
    other_ws = call_connections.get(call_id, {}).get(other_user_id)
    if other_ws:
        try:
            await other_ws.send_json({
                "type": "recording-stopped",
                "from": user_id,
                "recording_id": recording_id
            })
        except:
            pass
    
    logger.info(f"Recording {recording_id} stopped for call {call_id}")
    
    return {
        "recording_id": recording_id,
        "status": "awaiting_upload",
        "message": "Recording stopped. Ready to upload."
    }


@router.post("/{call_id}/recording/upload")
async def upload_recording(
    call_id: str,
    recording_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a call recording to S3"""
    user_id = current_user["user_id"]
    
    # Verify recording exists and user is participant
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update status to uploading
    await db.call_recordings.update_one(
        {"recording_id": recording_id},
        {"$set": {"status": "uploading"}}
    )
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"call_recording_{call_id}_{timestamp}.webm"
        
        if S3_ENABLED and s3_client:
            # Upload to S3
            s3_key = f"justice-recordings/{call_id}/{filename}"
            
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType='video/webm'
            )
            
            # Generate presigned URL (valid for 7 days)
            s3_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )
            
            # Update recording with S3 info
            await db.call_recordings.update_one(
                {"recording_id": recording_id},
                {"$set": {
                    "status": "completed",
                    "file_size_bytes": file_size,
                    "s3_key": s3_key,
                    "s3_url": s3_url,
                    "uploaded_at": datetime.now(timezone.utc)
                }}
            )
            
            logger.info(f"Recording {recording_id} uploaded to S3: {s3_key}")
            
            return {
                "recording_id": recording_id,
                "status": "completed",
                "file_size_bytes": file_size,
                "s3_key": s3_key,
                "download_url": s3_url,
                "message": "Recording uploaded to S3 successfully"
            }
        else:
            # Save locally if S3 not available
            recordings_dir = UPLOADS_DIR / "recordings"
            recordings_dir.mkdir(exist_ok=True)
            
            local_path = recordings_dir / filename
            with open(local_path, 'wb') as f:
                f.write(content)
            
            await db.call_recordings.update_one(
                {"recording_id": recording_id},
                {"$set": {
                    "status": "completed",
                    "file_size_bytes": file_size,
                    "local_path": str(local_path),
                    "uploaded_at": datetime.now(timezone.utc)
                }}
            )
            
            logger.info(f"Recording {recording_id} saved locally: {local_path}")
            
            return {
                "recording_id": recording_id,
                "status": "completed",
                "file_size_bytes": file_size,
                "local_path": str(local_path),
                "message": "Recording saved locally (S3 not configured)"
            }
            
    except Exception as e:
        logger.error(f"Recording upload failed: {e}")
        await db.call_recordings.update_one(
            {"recording_id": recording_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{call_id}/recordings")
async def get_call_recordings(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all recordings for a call"""
    user_id = current_user["user_id"]
    
    # Verify user was participant
    call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call["caller_id"], call["recipient_id"]]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    recordings = await db.call_recordings.find(
        {"call_id": call_id},
        {"_id": 0}
    ).sort("started_at", -1).to_list(length=50)
    
    # Convert datetime objects and refresh S3 URLs if needed
    for rec in recordings:
        for field in ["started_at", "ended_at", "uploaded_at"]:
            if rec.get(field) and hasattr(rec[field], 'isoformat'):
                rec[field] = rec[field].isoformat()
        
        # Refresh S3 URL if expired or close to expiring
        if rec.get("s3_key") and S3_ENABLED and s3_client:
            try:
                rec["download_url"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET_NAME, 'Key': rec["s3_key"]},
                    ExpiresIn=604800
                )
            except:
                pass
    
    return {"recordings": recordings}


@router.get("/recordings/my")
async def get_my_recordings(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get all recordings the user has access to"""
    user_id = current_user["user_id"]
    
    recordings = await db.call_recordings.find(
        {"participants": user_id, "status": "completed"},
        {"_id": 0}
    ).sort("started_at", -1).limit(limit).to_list(length=limit)
    
    # Enrich with call info and refresh URLs
    for rec in recordings:
        # Get call info
        call = await db.video_calls.find_one({"call_id": rec["call_id"]}, {"_id": 0})
        if call:
            rec["caller_name"] = call.get("caller_name")
            rec["recipient_name"] = call.get("recipient_name")
        
        # Convert datetime
        for field in ["started_at", "ended_at", "uploaded_at"]:
            if rec.get(field) and hasattr(rec[field], 'isoformat'):
                rec[field] = rec[field].isoformat()
        
        # Refresh S3 URL
        if rec.get("s3_key") and S3_ENABLED and s3_client:
            try:
                rec["download_url"] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET_NAME, 'Key': rec["s3_key"]},
                    ExpiresIn=604800
                )
            except:
                pass
    
    return {"recordings": recordings}
