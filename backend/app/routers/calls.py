"""
Video Call Router - WebRTC signaling and call management
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Form, WebSocket, WebSocketDisconnect

from app.db.database import db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["Video Calls"])

# In-memory store for active calls and WebSocket connections
active_calls = {}  # call_id -> call_info
call_connections = {}  # call_id -> {user_id: websocket}


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
