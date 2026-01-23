"""
JUSTICE Platform - Main Application Entry Point (Refactored)

This is the new modular entry point for the JUSTICE API.
It uses the organized router structure from /app/backend/app/

To use this instead of server.py, update the supervisor config to point here.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Import routers
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.cases import router as cases_router
from app.routers.evidence import router as evidence_router
from app.routers.analytics import router as analytics_router
from app.routers.sos import router as sos_router
from app.routers.attorneys import router as attorneys_router
from app.routers.ai_chat import router as ai_chat_router
from app.routers.encounters import router as encounters_router
from app.routers.community import router as community_router
from app.routers.rights import router as rights_router
from app.routers.attorney import router as attorney_collab_router
from app.routers.backup import router as backup_router
from app.routers.calls import router as calls_router
from app.routers.schedules import router as schedules_router
from app.routers.templates import router as templates_router

# Import config and services
from app.core.config import IPFS_ENABLED, S3_ENABLED, UPLOADS_DIR
from app.services.websocket import manager
from app.services.scheduled_reports import start_scheduler, stop_scheduler
from app.db.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    print("🚀 JUSTICE Platform Starting (Modular Architecture v5.16)...")
    print(f"   IPFS Enabled: {IPFS_ENABLED}")
    print(f"   S3 Enabled: {S3_ENABLED}")
    
    # Start the scheduler for automated reports
    try:
        start_scheduler()
        print("   📅 Scheduled Reports: Enabled")
    except Exception as e:
        print(f"   ⚠️ Scheduler failed to start: {e}")
    
    yield
    
    # Shutdown
    print("👋 JUSTICE Platform Shutting down...")
    stop_scheduler()


# Create FastAPI application
app = FastAPI(
    title="JUSTICE API",
    description="Civil Rights Defense System - Protecting citizens during police encounters",
    version="5.2.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
app.mount("/api/files", StaticFiles(directory=str(UPLOADS_DIR)), name="files")

# Include routers with /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(sos_router, prefix="/api")
app.include_router(attorneys_router, prefix="/api")
app.include_router(ai_chat_router, prefix="/api")
app.include_router(encounters_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(rights_router, prefix="/api")
app.include_router(attorney_collab_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(calls_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(templates_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "JUSTICE API",
        "version": "5.3.0",
        "status": "operational",
        "docs": "/docs"
    }


# WebSocket endpoint for authenticated user notifications
@app.websocket("/api/ws/{user_token}")
async def user_websocket(websocket: WebSocket, user_token: str):
    """
    WebSocket endpoint for real-time notifications to authenticated users.
    Token is the JWT auth token.
    """
    from app.core.security import decode_token
    
    try:
        # Validate the JWT token
        payload = decode_token(user_token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Connect the user
        await manager.connect(websocket, user_id)
        
        # Send connection confirmation
        await websocket.send_json({"type": "connected", "user_id": user_id})
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "typing":
                    # Forward typing indicator to recipient
                    recipient_id = data.get("recipient_id")
                    if recipient_id:
                        await manager.send_to_user(recipient_id, {
                            "type": "typing",
                            "from_user_id": user_id,
                            "conversation_id": data.get("conversation_id")
                        })
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except:
            pass


# WebSocket endpoint for shared encounter viewers
@app.websocket("/api/ws/shared/{encounter_id}")
async def shared_encounter_websocket(websocket: WebSocket, encounter_id: str, token: str):
    """
    WebSocket endpoint for real-time updates to shared encounter viewers.
    Validates share token before accepting connection.
    """
    # Validate encounter and share token
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not encounter or not encounter.get("share_active") or encounter.get("share_token") != token:
        await websocket.close(code=4003, reason="Invalid or expired share link")
        return
    
    await manager.add_share_viewer(encounter_id, websocket)
    
    # Update viewer count
    viewer_count = manager.get_share_viewer_count(encounter_id)
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {"share_viewer_count": viewer_count}}
    )
    
    # Notify encounter owner of new viewer
    await manager.send_to_user(encounter.get("user_id"), {
        "type": "viewer_joined",
        "encounter_id": encounter_id,
        "viewer_count": viewer_count
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            # Handle messages from viewers (like sending guidance)
            if data.get("type") == "guidance":
                from datetime import datetime, timezone
                import uuid
                
                now = datetime.now(timezone.utc)
                message_id = f"msg_{uuid.uuid4().hex[:12]}"
                
                message_doc = {
                    "message_id": message_id,
                    "encounter_id": encounter_id,
                    "sender_name": data.get("sender_name", "Anonymous")[:50],
                    "message": data.get("message", "")[:200],
                    "created_at": now.isoformat()
                }
                
                await db.encounter_messages.insert_one(message_doc)
                
                # Notify encounter owner
                await manager.send_to_user(encounter.get("user_id"), {
                    "type": "guidance_message",
                    "encounter_id": encounter_id,
                    "message_id": message_id,
                    "sender_name": data.get("sender_name", "Anonymous")[:50],
                    "message": data.get("message", "")[:200],
                    "timestamp": now.isoformat()
                })
                
                # Broadcast to all viewers
                await manager.broadcast_to_share_viewers(encounter_id, {
                    "type": "new_message",
                    "message_id": message_id,
                    "sender_name": data.get("sender_name", "Anonymous")[:50],
                    "message": data.get("message", "")[:200],
                    "timestamp": now.isoformat()
                })
                
    except WebSocketDisconnect:
        manager.remove_share_viewer(encounter_id, websocket)
        viewer_count = manager.get_share_viewer_count(encounter_id)
        await db.encounters.update_one(
            {"encounter_id": encounter_id},
            {"$set": {"share_viewer_count": viewer_count}}
        )
        # Notify owner
        await manager.send_to_user(encounter.get("user_id"), {
            "type": "viewer_left",
            "encounter_id": encounter_id,
            "viewer_count": viewer_count
        })


# For running with uvicorn directly (development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
