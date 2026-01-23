"""
Video Call Router - WebRTC signaling and call management with recording
"""
import uuid
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Form, WebSocket, WebSocketDisconnect, UploadFile, File, Body

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
        # Ensure started_at has timezone info
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
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

# ============== TRANSCRIPTION ENDPOINTS ==============

@router.post("/{recording_id}/transcribe")
async def transcribe_recording(
    recording_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Transcribe a recording using OpenAI Whisper with speaker identification"""
    user_id = current_user["user_id"]
    
    # Get recording
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if recording.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Recording not completed yet")
    
    # Check if already transcribed
    if recording.get("transcript"):
        return {
            "recording_id": recording_id,
            "status": "already_transcribed",
            "transcript": recording["transcript"],
            "speaker_transcript": recording.get("speaker_transcript"),
            "transcribed_at": recording.get("transcribed_at")
        }
    
    # Get call info for participant names
    call = await db.video_calls.find_one({"call_id": recording["call_id"]}, {"_id": 0})
    caller_name = call.get("caller_name", "Speaker 1") if call else "Speaker 1"
    recipient_name = call.get("recipient_name", "Speaker 2") if call else "Speaker 2"
    
    # Determine roles (attorney vs client)
    caller_user = await db.users.find_one({"user_id": call.get("caller_id")}, {"_id": 0, "role": 1}) if call else None
    caller_role = caller_user.get("role", "citizen") if caller_user else "citizen"
    
    if caller_role == "attorney":
        speaker1_label = f"Attorney ({caller_name})"
        speaker2_label = f"Client ({recipient_name})"
    else:
        speaker1_label = f"Client ({caller_name})"
        speaker2_label = f"Attorney ({recipient_name})"
    
    # Update status
    await db.call_recordings.update_one(
        {"recording_id": recording_id},
        {"$set": {"transcription_status": "processing"}}
    )
    
    try:
        import tempfile
        import httpx
        from emergentintegrations.llm.openai import transcribe_audio, chat
        
        audio_data = None
        
        # Download from S3 if available
        if recording.get("s3_key") and S3_ENABLED and s3_client:
            response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=recording["s3_key"])
            audio_data = response['Body'].read()
        elif recording.get("local_path"):
            with open(recording["local_path"], 'rb') as f:
                audio_data = f.read()
        elif recording.get("download_url") or recording.get("s3_url"):
            url = recording.get("download_url") or recording.get("s3_url")
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=120)
                audio_data = resp.content
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="Recording file not accessible")
        
        # Save to temp file for Whisper
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # Get API key from environment
            api_key = os.environ.get("EMERGENT_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="Transcription API key not configured")
            
            # Transcribe using Whisper
            transcript_result = await transcribe_audio(
                api_key=api_key,
                audio_file_path=tmp_path,
                response_format="verbose_json"
            )
            
            # Extract transcript text and segments with timestamps
            if isinstance(transcript_result, dict):
                transcript_text = transcript_result.get("text", "")
                whisper_segments = transcript_result.get("segments", [])
            else:
                transcript_text = str(transcript_result)
                whisper_segments = []
            
            # Use GPT to identify speakers and format transcript with timestamps
            speaker_transcript = None
            speaker_segments = []
            
            if transcript_text and len(transcript_text) > 50 and whisper_segments:
                try:
                    # Build segment info with timestamps for GPT
                    segments_with_time = []
                    for seg in whisper_segments:
                        start = seg.get("start", 0)
                        end = seg.get("end", 0)
                        text = seg.get("text", "").strip()
                        if text:
                            segments_with_time.append({
                                "start": start,
                                "end": end,
                                "text": text
                            })
                    
                    # Create a simpler prompt that preserves timestamps
                    segments_text = "\n".join([
                        f"[{s['start']:.1f}s - {s['end']:.1f}s]: {s['text']}" 
                        for s in segments_with_time
                    ])
                    
                    diarization_prompt = f"""Analyze this transcript of a video call between:
- {speaker1_label}
- {speaker2_label}

For each segment, identify the speaker (ATTORNEY or CLIENT) based on context:
- Attorneys: ask legal questions, give advice, explain procedures
- Clients: describe situations, ask for help, provide personal details

Input segments with timestamps:
{segments_text[:6000]}

Output format - for EACH segment output exactly:
SPEAKER|start_time|end_time|text

Example:
ATTORNEY|0.0|5.2|How can I help you today?
CLIENT|5.5|12.3|I was pulled over last week and...

Now process all segments:"""
                    
                    gpt_response = await chat(
                        api_key=api_key,
                        prompt=diarization_prompt,
                        model="gpt-4o-mini"
                    )
                    
                    if gpt_response:
                        # Parse GPT response into timestamped segments
                        lines = gpt_response.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            if '|' in line:
                                parts = line.split('|', 3)
                                if len(parts) >= 4:
                                    speaker_type = parts[0].strip().lower()
                                    try:
                                        start_time = float(parts[1].strip())
                                        end_time = float(parts[2].strip())
                                        text = parts[3].strip()
                                        
                                        if speaker_type in ['attorney', 'client'] and text:
                                            speaker_segments.append({
                                                "speaker": speaker_type,
                                                "start": start_time,
                                                "end": end_time,
                                                "text": text
                                            })
                                    except (ValueError, IndexError):
                                        continue
                        
                        # Build formatted speaker transcript
                        formatted_lines = []
                        for seg in speaker_segments:
                            speaker_name = transcript.speaker_labels.get(seg["speaker"], seg["speaker"].title()) if hasattr(transcript, 'speaker_labels') else seg["speaker"].title()
                            mins = int(seg["start"] // 60)
                            secs = int(seg["start"] % 60)
                            formatted_lines.append(f"[{mins}:{secs:02d}] **{seg['speaker'].title()}:** {seg['text']}")
                        
                        speaker_transcript = "\n\n".join(formatted_lines)
                        
                except Exception as e:
                    logger.warning(f"Speaker identification with timestamps failed: {e}")
                    # Fall back to segments without speaker ID but with timestamps
                    for seg in whisper_segments:
                        speaker_segments.append({
                            "speaker": "unknown",
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "text": seg.get("text", "").strip()
                        })
            elif whisper_segments:
                # No GPT processing, just use Whisper segments with timestamps
                for seg in whisper_segments:
                    speaker_segments.append({
                        "speaker": "unknown",
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "").strip()
                    })
            
            # Store transcript
            now = datetime.now(timezone.utc)
            await db.call_recordings.update_one(
                {"recording_id": recording_id},
                {"$set": {
                    "transcript": transcript_text,
                    "speaker_transcript": speaker_transcript or transcript_text,
                    "speaker_segments": speaker_segments,
                    "transcript_segments": whisper_segments,
                    "transcription_status": "completed",
                    "transcribed_at": now,
                    "speaker_labels": {
                        "attorney": caller_name if caller_role == "attorney" else recipient_name,
                        "client": recipient_name if caller_role == "attorney" else caller_name
                    }
                }}
            )
            
            logger.info(f"Transcription with speaker ID completed for recording {recording_id}")
            
            return {
                "recording_id": recording_id,
                "status": "completed",
                "transcript": transcript_text,
                "speaker_transcript": speaker_transcript or transcript_text,
                "speaker_segments": speaker_segments,
                "segments": whisper_segments,
                "transcribed_at": now.isoformat()
            }
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed for {recording_id}: {e}")
        await db.call_recordings.update_one(
            {"recording_id": recording_id},
            {"$set": {"transcription_status": "failed", "transcription_error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.get("/{recording_id}/transcript")
async def get_transcript(
    recording_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get transcript for a recording with speaker identification"""
    user_id = current_user["user_id"]
    
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not recording.get("transcript"):
        return {
            "recording_id": recording_id,
            "has_transcript": False,
            "transcription_status": recording.get("transcription_status", "not_started")
        }
    
    transcribed_at = recording.get("transcribed_at")
    if transcribed_at and hasattr(transcribed_at, 'isoformat'):
        transcribed_at = transcribed_at.isoformat()
    
    return {
        "recording_id": recording_id,
        "has_transcript": True,
        "transcript": recording["transcript"],
        "speaker_transcript": recording.get("speaker_transcript"),
        "speaker_segments": recording.get("speaker_segments", []),
        "speaker_labels": recording.get("speaker_labels", {}),
        "segments": recording.get("transcript_segments", []),
        "transcribed_at": transcribed_at
    }


@router.get("/transcripts/search")
async def search_transcripts(
    query: str,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Search across all transcripts the user has access to"""
    user_id = current_user["user_id"]
    
    # Find recordings with transcripts that match the query
    recordings = await db.call_recordings.find(
        {
            "participants": user_id,
            "transcript": {"$regex": query, "$options": "i"}
        },
        {"_id": 0}
    ).limit(limit).to_list(length=limit)
    
    results = []
    for rec in recordings:
        # Get call info
        call = await db.video_calls.find_one({"call_id": rec["call_id"]}, {"_id": 0})
        
        # Find matching excerpts
        transcript = rec.get("transcript", "")
        excerpts = []
        
        query_lower = query.lower()
        transcript_lower = transcript.lower()
        
        # Find all occurrences
        start = 0
        while True:
            idx = transcript_lower.find(query_lower, start)
            if idx == -1:
                break
            
            # Extract context around match
            excerpt_start = max(0, idx - 50)
            excerpt_end = min(len(transcript), idx + len(query) + 50)
            excerpt = transcript[excerpt_start:excerpt_end]
            
            if excerpt_start > 0:
                excerpt = "..." + excerpt
            if excerpt_end < len(transcript):
                excerpt = excerpt + "..."
            
            excerpts.append({
                "position": idx,
                "excerpt": excerpt
            })
            
            start = idx + 1
            if len(excerpts) >= 3:  # Max 3 excerpts per recording
                break
        
        results.append({
            "recording_id": rec["recording_id"],
            "call_id": rec["call_id"],
            "caller_name": call.get("caller_name") if call else None,
            "recipient_name": call.get("recipient_name") if call else None,
            "started_at": rec.get("started_at").isoformat() if rec.get("started_at") and hasattr(rec["started_at"], 'isoformat') else rec.get("started_at"),
            "duration_seconds": rec.get("duration_seconds"),
            "excerpts": excerpts,
            "match_count": len(excerpts)
        })
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }


# ============== AI TRANSCRIPT SUMMARY ==============

@router.post("/{recording_id}/summarize")
async def generate_transcript_summary(
    recording_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate an AI-powered summary of a call transcript with key points and action items"""
    user_id = current_user["user_id"]
    
    # Get the recording
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    transcript = recording.get("transcript") or recording.get("speaker_transcript")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript available. Please transcribe the recording first.")
    
    # Check if summary already exists and is recent
    existing_summary = recording.get("ai_summary")
    if existing_summary:
        summarized_at = recording.get("summarized_at")
        if summarized_at and hasattr(summarized_at, 'isoformat'):
            summarized_at = summarized_at.isoformat()
        return {
            "recording_id": recording_id,
            "status": "already_summarized",
            "summary": existing_summary,
            "summarized_at": summarized_at
        }
    
    try:
        from emergentintegrations.llm.openai import chat
        
        api_key = os.environ.get("EMERGENT_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="AI API key not configured")
        
        # Get call details
        call = await db.video_calls.find_one({"call_id": recording["call_id"]}, {"_id": 0})
        
        # Build context
        caller_name = call.get("caller_name", "Participant 1") if call else "Participant 1"
        recipient_name = call.get("recipient_name", "Participant 2") if call else "Participant 2"
        duration = recording.get("duration_seconds", 0)
        duration_mins = duration // 60 if duration else 0
        
        summary_prompt = f"""Analyze this transcript of a legal consultation call between {caller_name} and {recipient_name} ({duration_mins} minutes).

TRANSCRIPT:
{transcript[:8000]}

Generate a comprehensive summary with the following sections:

1. **OVERVIEW** (2-3 sentences describing the main topic and purpose of the call)

2. **KEY DISCUSSION POINTS** (bullet points of main topics discussed)
   - Topic and brief summary
   - Important details mentioned

3. **ACTION ITEMS** (specific tasks or follow-ups mentioned)
   - Task description
   - Who is responsible (if mentioned)
   - Deadline (if mentioned)

4. **LEGAL CONCERNS** (any legal issues, risks, or considerations mentioned)
   - Issue description
   - Potential implications

5. **RECOMMENDATIONS** (advice given during the call)
   - Recommendation
   - Context

6. **FOLLOW-UP NOTES** (anything requiring additional attention or research)

Format your response as clear, professional text that an attorney or client could use for case documentation. Use markdown formatting for sections and bullet points."""

        response = await chat(
            api_key=api_key,
            prompt=summary_prompt,
            model="gpt-4o-mini"
        )
        
        if not response:
            raise HTTPException(status_code=500, detail="Failed to generate summary")
        
        # Store the summary
        now = datetime.now(timezone.utc)
        await db.call_recordings.update_one(
            {"recording_id": recording_id},
            {"$set": {
                "ai_summary": response,
                "summarized_at": now
            }}
        )
        
        logger.info(f"AI summary generated for recording {recording_id}")
        
        return {
            "recording_id": recording_id,
            "status": "completed",
            "summary": response,
            "summarized_at": now.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation failed for {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@router.get("/{recording_id}/summary")
async def get_transcript_summary(
    recording_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the AI-generated summary for a recording"""
    user_id = current_user["user_id"]
    
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    summary = recording.get("ai_summary")
    if not summary:
        return {
            "recording_id": recording_id,
            "has_summary": False
        }
    
    summarized_at = recording.get("summarized_at")
    if summarized_at and hasattr(summarized_at, 'isoformat'):
        summarized_at = summarized_at.isoformat()
    
    return {
        "recording_id": recording_id,
        "has_summary": True,
        "summary": summary,
        "summarized_at": summarized_at
    }


@router.get("/{recording_id}/summary/pdf")
async def export_summary_pdf(
    recording_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Export AI summary as a professional PDF document"""
    from fastapi.responses import Response
    from fpdf import FPDF
    
    user_id = current_user["user_id"]
    
    # Get the recording
    recording = await db.call_recordings.find_one({"recording_id": recording_id}, {"_id": 0})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if user_id not in recording.get("participants", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    summary = recording.get("ai_summary")
    if not summary:
        raise HTTPException(status_code=400, detail="No summary available. Please generate a summary first.")
    
    # Get call details
    call = await db.video_calls.find_one({"call_id": recording.get("call_id")}, {"_id": 0})
    
    caller_name = call.get("caller_name", "Unknown") if call else "Unknown"
    recipient_name = call.get("recipient_name", "Unknown") if call else "Unknown"
    duration_seconds = recording.get("duration_seconds", 0)
    started_at = recording.get("started_at")
    summarized_at = recording.get("summarized_at")
    
    # Format dates
    if started_at and hasattr(started_at, 'strftime'):
        started_at_str = started_at.strftime('%B %d, %Y at %I:%M %p')
    else:
        started_at_str = str(started_at) if started_at else "Unknown"
    
    if summarized_at and hasattr(summarized_at, 'strftime'):
        summarized_at_str = summarized_at.strftime('%B %d, %Y at %I:%M %p')
    else:
        summarized_at_str = str(summarized_at) if summarized_at else "Unknown"
    
    duration_str = f"{duration_seconds // 60}m {duration_seconds % 60}s" if duration_seconds else "N/A"
    
    # Create PDF
    class SummaryPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 16)
            self.set_text_color(79, 70, 229)  # Indigo
            self.cell(0, 10, 'JUSTICE PLATFORM', 0, 1, 'C')
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0)
            self.cell(0, 8, 'Call Consultation Summary', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(128)
            self.cell(0, 5, 'AI-Generated Legal Consultation Summary', 0, 1, 'C')
            self.set_text_color(0)
            self.line(10, 35, 200, 35)
            self.ln(10)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Page {self.page_no()} | Generated by JUSTICE Platform | {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', 0, 0, 'C')
            self.set_text_color(0)
    
    pdf = SummaryPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # Call Information Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(79, 70, 229)  # Indigo
    pdf.set_text_color(255)
    pdf.cell(0, 8, '  CALL INFORMATION', 0, 1, 'L', fill=True)
    pdf.set_text_color(0)
    pdf.ln(3)
    
    info_items = [
        ('Recording ID:', recording_id),
        ('Participants:', f'{caller_name} and {recipient_name}'),
        ('Call Date:', started_at_str),
        ('Duration:', duration_str),
        ('Summary Generated:', summarized_at_str),
    ]
    
    for label, value in info_items:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(50, 6, label, 0, 0)
        pdf.set_font('Helvetica', '', 10)
        value_str = str(value)[:80] if len(str(value)) > 80 else str(value)
        pdf.cell(0, 6, value_str, 0, 1)
    
    pdf.ln(5)
    
    # Parse and render summary sections
    current_section = None
    section_colors = {
        'OVERVIEW': (147, 51, 234),      # Purple
        'KEY': (59, 130, 246),           # Blue
        'ACTION': (34, 197, 94),         # Green
        'LEGAL': (239, 68, 68),          # Red
        'RECOMMEND': (245, 158, 11),     # Amber
        'FOLLOW': (107, 114, 128),       # Gray
    }
    
    def get_section_color(section_name):
        for key, color in section_colors.items():
            if key in section_name.upper():
                return color
        return (79, 70, 229)  # Default indigo
    
    lines = summary.split('\n')
    for line in lines:
        # Check for page break
        if pdf.get_y() > 260:
            pdf.add_page()
        
        # Clean the line
        clean_line = line.strip()
        
        # Skip empty lines but add small space
        if not clean_line:
            pdf.ln(2)
            continue
        
        # Section headers (numbered like "1. **OVERVIEW**" or "**OVERVIEW**")
        is_section_header = False
        section_text = clean_line
        
        # Match patterns like "1. **OVERVIEW**" or "**OVERVIEW**"
        if clean_line.startswith('**') and clean_line.endswith('**'):
            is_section_header = True
            section_text = clean_line.replace('**', '')
        elif '**' in clean_line and clean_line[0].isdigit():
            # Pattern like "1. **OVERVIEW**"
            parts = clean_line.split('**')
            if len(parts) >= 2:
                is_section_header = True
                section_text = parts[1] if parts[1] else (parts[2] if len(parts) > 2 else clean_line)
        
        if is_section_header:
            pdf.ln(3)
            color = get_section_color(section_text)
            pdf.set_fill_color(*color)
            pdf.set_text_color(255)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 7, f'  {section_text.upper()}', 0, 1, 'L', fill=True)
            pdf.set_text_color(0)
            pdf.ln(2)
            current_section = section_text.upper()
            continue
        
        # Bullet points
        if clean_line.startswith('-') or clean_line.startswith('•'):
            content = clean_line[1:].strip().replace('**', '')
            pdf.set_font('Helvetica', '', 10)
            # Add bullet character
            pdf.cell(5, 5, '', 0, 0)
            pdf.cell(5, 5, chr(149), 0, 0)  # Bullet character
            # Handle long lines with multi_cell
            if len(content) > 90:
                pdf.set_x(20)
                pdf.multi_cell(0, 5, content)
            else:
                pdf.cell(0, 5, content, 0, 1)
            continue
        
        # Sub-bullet points (indented)
        if clean_line.startswith('  -') or clean_line.startswith('  •'):
            content = clean_line.strip()[1:].strip().replace('**', '')
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(15, 5, '', 0, 0)
            pdf.cell(5, 5, '-', 0, 0)
            if len(content) > 80:
                pdf.set_x(30)
                pdf.multi_cell(0, 5, content)
            else:
                pdf.cell(0, 5, content, 0, 1)
            continue
        
        # Regular paragraph text
        content = clean_line.replace('**', '')
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 5, content)
    
    # Confidentiality Notice
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 7, '  CONFIDENTIALITY NOTICE', 0, 1, 'L', fill=True)
    pdf.ln(2)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100)
    pdf.multi_cell(0, 5, 
        'This document contains confidential attorney-client communication summary. '
        'This AI-generated summary is provided for reference purposes and should be reviewed '
        'by qualified legal counsel. The original recording and transcript remain the authoritative sources.'
    )
    pdf.set_text_color(0)
    
    # Output PDF
    pdf_bytes = bytes(pdf.output())
    
    # Create filename
    safe_filename = f"call_summary_{recording_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        }
    )


@router.post("/batch-summary/pdf")
async def export_batch_summary_pdf(
    recording_ids: List[str] = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """Export multiple AI summaries as a single consolidated PDF document"""
    from fastapi.responses import Response
    from fpdf import FPDF
    
    user_id = current_user["user_id"]
    
    if not recording_ids:
        raise HTTPException(status_code=400, detail="No recording IDs provided")
    
    if len(recording_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 recordings per batch export")
    
    # Fetch all recordings
    recordings_data = []
    for rec_id in recording_ids:
        recording = await db.call_recordings.find_one({"recording_id": rec_id}, {"_id": 0})
        if not recording:
            continue
        
        if user_id not in recording.get("participants", []):
            continue
        
        summary = recording.get("ai_summary")
        if not summary:
            continue
        
        # Get call details
        call = await db.video_calls.find_one({"call_id": recording.get("call_id")}, {"_id": 0})
        
        recordings_data.append({
            "recording": recording,
            "call": call,
            "summary": summary
        })
    
    if not recordings_data:
        raise HTTPException(status_code=400, detail="No recordings with summaries found")
    
    # Create consolidated PDF
    class BatchSummaryPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 16)
            self.set_text_color(79, 70, 229)
            self.cell(0, 10, 'JUSTICE PLATFORM', 0, 1, 'C')
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0)
            self.cell(0, 8, 'Consolidated Call Summary Report', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(128)
            self.cell(0, 5, f'{len(recordings_data)} Consultation(s) | Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', 0, 1, 'C')
            self.set_text_color(0)
            self.line(10, 38, 200, 38)
            self.ln(12)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Page {self.page_no()} | JUSTICE Platform - Confidential', 0, 0, 'C')
            self.set_text_color(0)
    
    pdf = BatchSummaryPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    section_colors = {
        'OVERVIEW': (147, 51, 234),
        'KEY': (59, 130, 246),
        'ACTION': (34, 197, 94),
        'LEGAL': (239, 68, 68),
        'RECOMMEND': (245, 158, 11),
        'FOLLOW': (107, 114, 128),
    }
    
    def get_section_color(section_name):
        for key, color in section_colors.items():
            if key in section_name.upper():
                return color
        return (79, 70, 229)
    
    # Table of Contents page
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(79, 70, 229)
    pdf.set_text_color(255)
    pdf.cell(0, 10, '  TABLE OF CONTENTS', 0, 1, 'L', fill=True)
    pdf.set_text_color(0)
    pdf.ln(5)
    
    for idx, data in enumerate(recordings_data, 1):
        recording = data["recording"]
        call = data["call"]
        
        caller_name = call.get("caller_name", "Unknown") if call else "Unknown"
        recipient_name = call.get("recipient_name", "Unknown") if call else "Unknown"
        started_at = recording.get("started_at")
        
        if started_at and hasattr(started_at, 'strftime'):
            date_str = started_at.strftime('%b %d, %Y')
        else:
            date_str = str(started_at)[:10] if started_at else "Unknown"
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(10, 7, f'{idx}.', 0, 0)
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 7, f'{caller_name} & {recipient_name} - {date_str}', 0, 1)
    
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100)
    pdf.multi_cell(0, 5, 
        'This consolidated report contains AI-generated summaries of multiple attorney-client consultations. '
        'Each summary includes key discussion points, action items, and legal considerations. '
        'Original recordings remain the authoritative sources.'
    )
    pdf.set_text_color(0)
    
    # Individual summaries
    for idx, data in enumerate(recordings_data, 1):
        pdf.add_page()
        
        recording = data["recording"]
        call = data["call"]
        summary = data["summary"]
        
        caller_name = call.get("caller_name", "Unknown") if call else "Unknown"
        recipient_name = call.get("recipient_name", "Unknown") if call else "Unknown"
        duration_seconds = recording.get("duration_seconds", 0)
        started_at = recording.get("started_at")
        recording_id = recording.get("recording_id", "N/A")
        
        if started_at and hasattr(started_at, 'strftime'):
            started_at_str = started_at.strftime('%B %d, %Y at %I:%M %p')
        else:
            started_at_str = str(started_at) if started_at else "Unknown"
        
        duration_str = f"{duration_seconds // 60}m {duration_seconds % 60}s" if duration_seconds else "N/A"
        
        # Call header
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(59, 130, 246)
        pdf.set_text_color(255)
        pdf.cell(0, 8, f'  CONSULTATION #{idx}: {caller_name} & {recipient_name}', 0, 1, 'L', fill=True)
        pdf.set_text_color(0)
        pdf.ln(3)
        
        # Call info
        info_items = [
            ('Recording ID:', recording_id),
            ('Date:', started_at_str),
            ('Duration:', duration_str),
        ]
        
        for label, value in info_items:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(35, 5, label, 0, 0)
            pdf.set_font('Helvetica', '', 9)
            pdf.cell(0, 5, str(value)[:60], 0, 1)
        
        pdf.ln(3)
        
        # Parse and render summary
        lines = summary.split('\n')
        for line in lines:
            if pdf.get_y() > 260:
                pdf.add_page()
            
            clean_line = line.strip()
            
            if not clean_line:
                pdf.ln(2)
                continue
            
            # Section headers
            is_section_header = False
            section_text = clean_line
            
            if clean_line.startswith('**') and clean_line.endswith('**'):
                is_section_header = True
                section_text = clean_line.replace('**', '')
            elif '**' in clean_line and clean_line[0].isdigit():
                parts = clean_line.split('**')
                if len(parts) >= 2:
                    is_section_header = True
                    section_text = parts[1] if parts[1] else (parts[2] if len(parts) > 2 else clean_line)
            
            if is_section_header:
                pdf.ln(2)
                color = get_section_color(section_text)
                pdf.set_fill_color(*color)
                pdf.set_text_color(255)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, f'  {section_text.upper()}', 0, 1, 'L', fill=True)
                pdf.set_text_color(0)
                pdf.ln(1)
                continue
            
            # Bullet points
            if clean_line.startswith('-') or clean_line.startswith('•'):
                content = clean_line[1:].strip().replace('**', '')
                pdf.set_font('Helvetica', '', 9)
                pdf.cell(5, 4, '', 0, 0)
                pdf.cell(5, 4, chr(149), 0, 0)
                if len(content) > 90:
                    pdf.set_x(20)
                    pdf.multi_cell(0, 4, content)
                else:
                    pdf.cell(0, 4, content, 0, 1)
                continue
            
            # Sub-bullet points
            if clean_line.startswith('  -') or clean_line.startswith('  •'):
                content = clean_line.strip()[1:].strip().replace('**', '')
                pdf.set_font('Helvetica', '', 8)
                pdf.cell(15, 4, '', 0, 0)
                pdf.cell(5, 4, '-', 0, 0)
                if len(content) > 80:
                    pdf.set_x(30)
                    pdf.multi_cell(0, 4, content)
                else:
                    pdf.cell(0, 4, content, 0, 1)
                continue
            
            # Regular text
            content = clean_line.replace('**', '')
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 4, content)
        
        pdf.ln(3)
    
    # Final page - disclaimer
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(100, 100, 100)
    pdf.set_text_color(255)
    pdf.cell(0, 8, '  CONFIDENTIALITY & DISCLAIMER', 0, 1, 'L', fill=True)
    pdf.set_text_color(0)
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 10)
    disclaimers = [
        "This document contains confidential attorney-client communications.",
        "All summaries are AI-generated and should be reviewed by qualified legal counsel.",
        "Original recordings and transcripts remain the authoritative sources.",
        "This report is for professional use only and should not be distributed without authorization.",
        f"Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Total consultations: {len(recordings_data)}",
    ]
    
    for disclaimer in disclaimers:
        pdf.cell(5, 6, chr(149), 0, 0)
        pdf.cell(0, 6, disclaimer, 0, 1)
    
    # Output PDF
    pdf_bytes = bytes(pdf.output())
    
    safe_filename = f"consolidated_summary_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    
    logger.info(f"Batch PDF export: {len(recordings_data)} recordings for user {user_id}")
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}"
        }
    )


# ============== EMAIL DELIVERY ==============

from pydantic import BaseModel, EmailStr

class EmailSummaryRequest(BaseModel):
    recording_ids: List[str]
    recipient_emails: List[EmailStr]
    cc_emails: Optional[List[EmailStr]] = None
    custom_message: Optional[str] = None
    recipient_name: Optional[str] = None


@router.post("/email-summary")
async def email_summary_pdf(
    request: EmailSummaryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Email AI summary PDF to recipients"""
    from app.services.email_service import send_pdf_email, generate_summary_email_html, EmailDeliveryError
    from fpdf import FPDF
    
    user_id = current_user["user_id"]
    user_name = current_user.get("name", current_user.get("email", "A JUSTICE user"))
    
    if not request.recording_ids:
        raise HTTPException(status_code=400, detail="No recording IDs provided")
    
    if not request.recipient_emails:
        raise HTTPException(status_code=400, detail="No recipient emails provided")
    
    if len(request.recipient_emails) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 recipients per email")
    
    if len(request.recording_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 recordings per email")
    
    # Fetch all recordings with summaries
    recordings_data = []
    for rec_id in request.recording_ids:
        recording = await db.call_recordings.find_one({"recording_id": rec_id}, {"_id": 0})
        if not recording:
            continue
        
        if user_id not in recording.get("participants", []):
            continue
        
        summary = recording.get("ai_summary")
        if not summary:
            continue
        
        call = await db.video_calls.find_one({"call_id": recording.get("call_id")}, {"_id": 0})
        
        recordings_data.append({
            "recording": recording,
            "call": call,
            "summary": summary
        })
    
    if not recordings_data:
        raise HTTPException(status_code=400, detail="No recordings with summaries found")
    
    # Generate PDF (reuse batch PDF logic for single or multiple recordings)
    if len(recordings_data) == 1:
        # Single recording - use simpler PDF format
        data = recordings_data[0]
        recording = data["recording"]
        call = data["call"]
        summary = data["summary"]
        
        class SingleSummaryPDF(FPDF):
            def header(self):
                self.set_font('Helvetica', 'B', 16)
                self.set_text_color(79, 70, 229)
                self.cell(0, 10, 'JUSTICE PLATFORM', 0, 1, 'C')
                self.set_font('Helvetica', 'B', 14)
                self.set_text_color(0)
                self.cell(0, 8, 'Call Consultation Summary', 0, 1, 'C')
                self.line(10, 35, 200, 35)
                self.ln(10)
            
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Page {self.page_no()} | JUSTICE Platform', 0, 0, 'C')
        
        pdf = SingleSummaryPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Call info
        caller_name = call.get("caller_name", "Unknown") if call else "Unknown"
        recipient_name = call.get("recipient_name", "Unknown") if call else "Unknown"
        started_at = recording.get("started_at")
        duration = recording.get("duration_seconds", 0)
        
        if started_at and hasattr(started_at, 'strftime'):
            date_str = started_at.strftime('%B %d, %Y at %I:%M %p')
        else:
            date_str = str(started_at) if started_at else "Unknown"
        
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 7, f'Participants: {caller_name} & {recipient_name}', 0, 1)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Date: {date_str}', 0, 1)
        pdf.cell(0, 6, f'Duration: {duration // 60}m {duration % 60}s', 0, 1)
        pdf.ln(5)
        
        # Summary content
        for line in summary.split('\n'):
            if pdf.get_y() > 260:
                pdf.add_page()
            
            clean_line = line.strip()
            if not clean_line:
                pdf.ln(2)
                continue
            
            if '**' in clean_line:
                section = clean_line.replace('**', '')
                if clean_line[0].isdigit():
                    parts = section.split('. ', 1)
                    section = parts[1] if len(parts) > 1 else section
                pdf.ln(2)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_fill_color(79, 70, 229)
                pdf.set_text_color(255)
                pdf.cell(0, 7, f'  {section.upper()}', 0, 1, 'L', fill=True)
                pdf.set_text_color(0)
                pdf.ln(1)
                continue
            
            if clean_line.startswith('-') or clean_line.startswith('•'):
                content = clean_line[1:].strip()
                pdf.set_font('Helvetica', '', 10)
                pdf.cell(5, 5, '', 0, 0)
                pdf.cell(5, 5, chr(149), 0, 0)
                pdf.multi_cell(0, 5, content)
                continue
            
            pdf.set_font('Helvetica', '', 10)
            pdf.multi_cell(0, 5, clean_line)
        
        pdf_bytes = bytes(pdf.output())
        pdf_filename = f"call_summary_{recording.get('recording_id', 'report')}.pdf"
    else:
        # Multiple recordings - use consolidated format
        class BatchPDF(FPDF):
            def header(self):
                self.set_font('Helvetica', 'B', 16)
                self.set_text_color(79, 70, 229)
                self.cell(0, 10, 'JUSTICE PLATFORM', 0, 1, 'C')
                self.set_font('Helvetica', 'B', 14)
                self.set_text_color(0)
                self.cell(0, 8, 'Consolidated Summary Report', 0, 1, 'C')
                self.line(10, 35, 200, 35)
                self.ln(10)
            
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, f'Page {self.page_no()} | JUSTICE Platform - Confidential', 0, 0, 'C')
        
        pdf = BatchPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        
        # Table of contents
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, f'Contents: {len(recordings_data)} Consultation(s)', 0, 1)
        pdf.ln(3)
        
        for idx, data in enumerate(recordings_data, 1):
            rec = data["recording"]
            call = data["call"]
            caller = call.get("caller_name", "Unknown") if call else "Unknown"
            recipient = call.get("recipient_name", "Unknown") if call else "Unknown"
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f'{idx}. {caller} & {recipient}', 0, 1)
        
        # Individual summaries
        for idx, data in enumerate(recordings_data, 1):
            pdf.add_page()
            rec = data["recording"]
            call = data["call"]
            summary = data["summary"]
            
            caller = call.get("caller_name", "Unknown") if call else "Unknown"
            recipient = call.get("recipient_name", "Unknown") if call else "Unknown"
            
            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_fill_color(59, 130, 246)
            pdf.set_text_color(255)
            pdf.cell(0, 8, f'  Consultation #{idx}: {caller} & {recipient}', 0, 1, 'L', fill=True)
            pdf.set_text_color(0)
            pdf.ln(3)
            
            for line in summary.split('\n'):
                if pdf.get_y() > 260:
                    pdf.add_page()
                
                clean_line = line.strip()
                if not clean_line:
                    pdf.ln(2)
                    continue
                
                if '**' in clean_line:
                    section = clean_line.replace('**', '')
                    if clean_line[0].isdigit():
                        parts = section.split('. ', 1)
                        section = parts[1] if len(parts) > 1 else section
                    pdf.ln(2)
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.set_fill_color(79, 70, 229)
                    pdf.set_text_color(255)
                    pdf.cell(0, 6, f'  {section.upper()}', 0, 1, 'L', fill=True)
                    pdf.set_text_color(0)
                    continue
                
                if clean_line.startswith('-') or clean_line.startswith('•'):
                    content = clean_line[1:].strip()
                    pdf.set_font('Helvetica', '', 9)
                    pdf.cell(5, 4, '', 0, 0)
                    pdf.cell(5, 4, chr(149), 0, 0)
                    pdf.multi_cell(0, 4, content)
                    continue
                
                pdf.set_font('Helvetica', '', 9)
                pdf.multi_cell(0, 4, clean_line)
        
        pdf_bytes = bytes(pdf.output())
        pdf_filename = f"consolidated_summary_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    
    # Generate email HTML
    email_html = generate_summary_email_html(
        recording_count=len(recordings_data),
        sender_name=user_name,
        recipient_name=request.recipient_name,
        custom_message=request.custom_message
    )
    
    # Send email
    try:
        subject = f"Call Summary Report from {user_name} - JUSTICE Platform"
        
        result = await send_pdf_email(
            to_emails=request.recipient_emails,
            subject=subject,
            body_html=email_html,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
            cc_emails=request.cc_emails,
            sender_name=user_name
        )
        
        logger.info(f"Summary email sent to {request.recipient_emails} by user {user_id}")
        
        return {
            "status": "sent",
            "message": f"Summary emailed to {len(request.recipient_emails)} recipient(s)",
            "recipients": request.recipient_emails,
            "cc": request.cc_emails,
            "recording_count": len(recordings_data)
        }
        
    except EmailDeliveryError as e:
        logger.error(f"Email delivery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# ============== REAL-TIME TRANSCRIPTION ==============

# Store for live transcription sessions
live_transcription_sessions = {}  # call_id -> {segments: [], notes: []}


@router.post("/{call_id}/live-transcribe")
async def live_transcribe_chunk(
    call_id: str,
    audio_chunk: UploadFile = File(...),
    chunk_index: int = Form(0),
    current_user: dict = Depends(get_current_user)
):
    """Transcribe a live audio chunk during a call"""
    user_id = current_user["user_id"]
    
    # Verify call exists and user is participant
    call = active_calls.get(call_id)
    if not call:
        call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call.get("caller_id"), call.get("recipient_id")]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    # Initialize session if needed
    if call_id not in live_transcription_sessions:
        live_transcription_sessions[call_id] = {
            "segments": [],
            "notes": [],
            "started_at": datetime.now(timezone.utc)
        }
    
    try:
        import tempfile
        from emergentintegrations.llm.openai import transcribe_audio
        
        # Save audio chunk to temp file
        content = await audio_chunk.read()
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            api_key = os.environ.get("EMERGENT_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="Transcription API key not configured")
            
            # Transcribe chunk
            result = await transcribe_audio(
                api_key=api_key,
                audio_file_path=tmp_path,
                response_format="verbose_json"
            )
            
            transcript_text = ""
            if isinstance(result, dict):
                transcript_text = result.get("text", "").strip()
            else:
                transcript_text = str(result).strip()
            
            if transcript_text:
                # Calculate approximate timestamp based on chunk index
                # Assuming ~5 second chunks
                timestamp = chunk_index * 5.0
                
                segment = {
                    "index": chunk_index,
                    "timestamp": timestamp,
                    "text": transcript_text,
                    "speaker": "unknown",  # Will be identified by GPT if needed
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                live_transcription_sessions[call_id]["segments"].append(segment)
                
                # Broadcast to other participant via WebSocket
                other_user_id = call.get("recipient_id") if user_id == call.get("caller_id") else call.get("caller_id")
                other_ws = call_connections.get(call_id, {}).get(other_user_id)
                if other_ws:
                    try:
                        await other_ws.send_json({
                            "type": "live-transcript",
                            "segment": segment
                        })
                    except:
                        pass
                
                return {
                    "success": True,
                    "segment": segment
                }
            
            return {"success": True, "segment": None}
            
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Live transcription error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{call_id}/live-transcript")
async def get_live_transcript(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the current live transcript for a call"""
    user_id = current_user["user_id"]
    
    # Verify call exists and user is participant
    call = active_calls.get(call_id) or await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call.get("caller_id"), call.get("recipient_id")]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    session = live_transcription_sessions.get(call_id, {"segments": [], "notes": []})
    
    return {
        "call_id": call_id,
        "segments": session.get("segments", []),
        "notes": session.get("notes", [])
    }


@router.post("/{call_id}/live-note")
async def add_live_note(
    call_id: str,
    content: str = Form(...),
    timestamp: float = Form(0),
    note_type: str = Form("general"),  # general, important, action_item, question
    current_user: dict = Depends(get_current_user)
):
    """Add a note during a live call"""
    user_id = current_user["user_id"]
    
    # Verify call
    call = active_calls.get(call_id) or await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call.get("caller_id"), call.get("recipient_id")]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    # Initialize session if needed
    if call_id not in live_transcription_sessions:
        live_transcription_sessions[call_id] = {
            "segments": [],
            "notes": [],
            "started_at": datetime.now(timezone.utc)
        }
    
    note = {
        "note_id": f"note_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "user_name": current_user.get("name", "Unknown"),
        "content": content,
        "timestamp": timestamp,
        "note_type": note_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    live_transcription_sessions[call_id]["notes"].append(note)
    
    # Broadcast to other participant
    other_user_id = call.get("recipient_id") if user_id == call.get("caller_id") else call.get("caller_id")
    other_ws = call_connections.get(call_id, {}).get(other_user_id)
    if other_ws:
        try:
            await other_ws.send_json({
                "type": "live-note",
                "note": note
            })
        except:
            pass
    
    return {"success": True, "note": note}


@router.post("/{call_id}/save-live-transcript")
async def save_live_transcript(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Save the live transcript to the database when call ends"""
    user_id = current_user["user_id"]
    
    # Verify call
    call = await db.video_calls.find_one({"call_id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if user_id not in [call.get("caller_id"), call.get("recipient_id")]:
        raise HTTPException(status_code=403, detail="Not a participant")
    
    session = live_transcription_sessions.get(call_id)
    if not session:
        return {"success": True, "message": "No live transcript to save"}
    
    # Combine segments into full transcript
    segments = sorted(session.get("segments", []), key=lambda x: x.get("timestamp", 0))
    full_transcript = " ".join([s.get("text", "") for s in segments])
    
    # Save to database
    await db.live_transcripts.insert_one({
        "call_id": call_id,
        "segments": segments,
        "notes": session.get("notes", []),
        "full_transcript": full_transcript,
        "started_at": session.get("started_at"),
        "saved_at": datetime.now(timezone.utc),
        "participants": [call.get("caller_id"), call.get("recipient_id")]
    })
    
    # Clean up session
    del live_transcription_sessions[call_id]
    
    return {
        "success": True,
        "message": "Live transcript saved",
        "segment_count": len(segments),
        "note_count": len(session.get("notes", []))
    }
