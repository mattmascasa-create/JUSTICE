"""
Attorney Live Stream Router - Real-time video streaming to attorneys during encounters
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
import json

from app.routers.auth import get_current_user
from app.services.attorney_stream import attorney_stream_service
from app.db.database import db

router = APIRouter(prefix="/attorney-stream", tags=["Attorney Live Stream"])


class CreateStreamRequest(BaseModel):
    encounter_id: str
    attorney_id: Optional[str] = None
    attorney_email: Optional[str] = None
    location: Optional[str] = None
    notification_method: Optional[str] = "email"  # email, sms, both, in-app


class JoinStreamRequest(BaseModel):
    stream_code: str
    token: str
    role: str  # "user" or "attorney"


class SignalingRequest(BaseModel):
    stream_code: str
    signal_type: str  # "offer", "answer", "ice_candidate"
    data: dict
    sender_role: str


class MessageRequest(BaseModel):
    stream_code: str
    message: str
    sender_role: str


@router.post("/create")
async def create_stream(
    request: CreateStreamRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new live stream session for an encounter.
    Returns stream URL and tokens for both user and attorney.
    """
    
    # Verify encounter exists and belongs to user
    encounter = await db.encounters.find_one(
        {"encounter_id": request.encounter_id, "user_id": current_user.get("user_id")},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Create stream session
    session = await attorney_stream_service.create_stream_session(
        encounter_id=request.encounter_id,
        user_id=current_user.get("user_id"),
        attorney_id=request.attorney_id,
        attorney_email=request.attorney_email
    )
    
    # Notify attorney if email provided
    if request.attorney_email:
        notification = await attorney_stream_service.notify_attorney(
            session=await attorney_stream_service.get_session(session["session_id"]),
            encounter_location=request.location
        )
        session["notification_sent"] = notification.get("email_sent", False)
    
    return {
        "success": True,
        "message": "Live stream session created",
        **session
    }


@router.post("/join")
async def join_stream(request: JoinStreamRequest):
    """
    Join an existing stream session.
    Validates token and updates connection status.
    No authentication required - uses stream token instead.
    """
    
    result = await attorney_stream_service.join_stream(
        stream_code=request.stream_code,
        token=request.token,
        role=request.role
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result.get("error", "Failed to join stream"))
    
    return result


@router.get("/session/{stream_code}")
async def get_stream_session(stream_code: str):
    """Get stream session details (public info only)"""
    
    session = await attorney_stream_service.get_session_by_code(stream_code)
    
    if not session:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Return only public info
    return {
        "success": True,
        "session_id": session["session_id"],
        "stream_code": stream_code,
        "status": session["status"],
        "attorney_connected": session["attorney_connected"],
        "user_connected": session["user_connected"],
        "created_at": session["created_at"],
        "expires_at": session["expires_at"]
    }


@router.post("/signal")
async def send_signaling_data(request: SignalingRequest):
    """
    Send WebRTC signaling data (offer, answer, or ICE candidate).
    Used for establishing peer-to-peer connection.
    """
    
    result = await attorney_stream_service.send_signaling_data(
        stream_code=request.stream_code,
        signal_type=request.signal_type,
        data=request.data,
        sender_role=request.sender_role
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send signal"))
    
    return result


@router.get("/signal/{stream_code}/{role}")
async def get_signaling_data(stream_code: str, role: str):
    """Get pending signaling data for a role"""
    
    result = await attorney_stream_service.get_signaling_data(
        stream_code=stream_code,
        for_role=role
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/message")
async def send_message(request: MessageRequest):
    """Send a chat message during the stream"""
    
    result = await attorney_stream_service.send_message(
        stream_code=request.stream_code,
        sender_role=request.sender_role,
        message=request.message
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/messages/{stream_code}")
async def get_messages(stream_code: str):
    """Get all messages for a stream session"""
    
    messages = await attorney_stream_service.get_messages(stream_code)
    
    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }


@router.post("/end/{stream_code}")
async def end_stream(stream_code: str, ended_by: str = "user"):
    """End a streaming session"""
    
    result = await attorney_stream_service.end_stream(
        stream_code=stream_code,
        ended_by=ended_by
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/history")
async def get_stream_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get user's stream history"""
    
    streams = await attorney_stream_service.get_user_streams(
        user_id=current_user.get("user_id"),
        limit=limit
    )
    
    return {
        "success": True,
        "streams": streams,
        "count": len(streams)
    }


# WebSocket endpoint for real-time signaling
@router.websocket("/ws/{stream_code}/{role}")
async def stream_websocket(
    websocket: WebSocket,
    stream_code: str,
    role: str
):
    """
    WebSocket endpoint for real-time signaling and messaging.
    Provides lower latency than HTTP polling.
    """
    
    await websocket.accept()
    
    try:
        # Verify stream exists
        session = await attorney_stream_service.get_session_by_code(stream_code)
        if not session:
            await websocket.close(code=4004, reason="Stream not found")
            return
        
        # Update connection status
        if role == "user":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {"user_connected": True}}
            )
        elif role == "attorney":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {"attorney_connected": True}}
            )
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "signal":
                # WebRTC signaling
                await attorney_stream_service.send_signaling_data(
                    stream_code=stream_code,
                    signal_type=message.get("signal_type"),
                    data=message.get("data"),
                    sender_role=role
                )
                
                # Broadcast to other party (in production, use proper pub/sub)
                await websocket.send_json({
                    "type": "signal_ack",
                    "signal_type": message.get("signal_type")
                })
            
            elif msg_type == "chat":
                # Chat message
                result = await attorney_stream_service.send_message(
                    stream_code=stream_code,
                    sender_role=role,
                    message=message.get("message")
                )
                
                await websocket.send_json({
                    "type": "chat_ack",
                    "message": result.get("message")
                })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "end":
                await attorney_stream_service.end_stream(stream_code, role)
                await websocket.send_json({"type": "ended"})
                break
    
    except WebSocketDisconnect:
        # Update connection status on disconnect
        if role == "user":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {"user_connected": False}}
            )
        elif role == "attorney":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {"attorney_connected": False}}
            )
    except Exception as e:
        await websocket.close(code=4000, reason=str(e))
