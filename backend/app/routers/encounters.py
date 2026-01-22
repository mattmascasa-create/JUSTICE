"""
Encounters Router - Police encounter recording and management
Includes: start/end encounter, audio/video upload, transcription, AI analysis, reports
"""
import uuid
import json
import aiofiles
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.db.database import db
from app.core.config import ENCOUNTERS_DIR
from app.core.security import get_current_user
from app.services.websocket import manager
from app.services.ai_service import (
    transcribe_audio, analyze_for_violations, 
    identify_speaker_and_tone, perform_deep_analysis, stt_service
)
from app.models.schemas import EncounterStart, EncounterResponse

router = APIRouter(prefix="/encounters", tags=["Encounters"])


@router.post("/start", response_model=EncounterResponse)
async def start_encounter(encounter_data: EncounterStart, current_user: dict = Depends(get_current_user)):
    """Start a new police encounter recording session"""
    encounter_id = f"enc_{uuid.uuid4().hex[:12]}"
    stream_key = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    
    # Create encounter directory
    enc_dir = ENCOUNTERS_DIR / encounter_id
    enc_dir.mkdir(exist_ok=True)
    
    encounter_doc = {
        "encounter_id": encounter_id,
        "user_id": current_user["user_id"],
        "latitude": encounter_data.latitude,
        "longitude": encounter_data.longitude,
        "address": encounter_data.address,
        "encounter_type": encounter_data.encounter_type,
        "status": "active",
        "broadcast_mode": encounter_data.broadcast_mode,
        "stream_key": stream_key,
        "transcriptions": [],
        "violations": [],
        "officers": [],
        "manual_marks": [],
        "ai_analysis": [],
        "media_files": [],
        "started_at": now.isoformat(),
        "ended_at": None,
        "duration_seconds": 0
    }
    
    await db.encounters.insert_one(encounter_doc)
    
    # Notify emergency contacts if broadcasting
    if encounter_data.broadcast_mode in ["share_contacts", "all"]:
        contacts = await db.emergency_contacts.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0}
        ).to_list(10)
        
        for contact in contacts:
            if contact.get("contact_user_id"):
                await manager.send_to_user(contact["contact_user_id"], {
                    "type": "encounter_started",
                    "encounter_id": encounter_id,
                    "user_name": current_user.get("name"),
                    "location": {
                        "latitude": encounter_data.latitude,
                        "longitude": encounter_data.longitude,
                        "address": encounter_data.address
                    }
                })
    
    return EncounterResponse(
        encounter_id=encounter_id,
        user_id=current_user["user_id"],
        latitude=encounter_data.latitude,
        longitude=encounter_data.longitude,
        address=encounter_data.address,
        encounter_type=encounter_data.encounter_type,
        status="active",
        broadcast_mode=encounter_data.broadcast_mode,
        stream_key=stream_key,
        started_at=now,
        ended_at=None,
        duration_seconds=0
    )


@router.post("/{encounter_id}/audio")
async def upload_audio_chunk(
    encounter_id: str,
    chunk_index: int = Form(...),
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload an audio chunk for transcription"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Save audio chunk
    enc_dir = ENCOUNTERS_DIR / encounter_id
    enc_dir.mkdir(exist_ok=True)
    
    chunk_filename = f"audio_chunk_{chunk_index}.webm"
    chunk_path = enc_dir / chunk_filename
    
    async with aiofiles.open(chunk_path, 'wb') as f:
        content = await audio.read()
        await f.write(content)
    
    # Update encounter with media file
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"media_files": chunk_filename}}
    )
    
    transcription_result = None
    
    # Transcribe if STT service available
    if stt_service:
        try:
            response = await stt_service.transcribe(str(chunk_path))
            
            if response and response.text:
                segment_id = f"seg_{uuid.uuid4().hex[:12]}"
                now = datetime.now(timezone.utc)
                
                # Analyze for violations
                violations = await analyze_for_violations(response.text)
                
                # Get context from previous transcripts
                prev_transcripts = await db.transcriptions.find(
                    {"encounter_id": encounter_id}
                ).sort("start_time", -1).limit(3).to_list(length=3)
                context = " | ".join([f"{t.get('speaker', 'Unknown')}: {t.get('text', '')[:100]}" for t in prev_transcripts])
                
                # Identify speaker and tone
                speaker_result = await identify_speaker_and_tone(response.text, context)
                
                transcription_doc = {
                    "segment_id": segment_id,
                    "encounter_id": encounter_id,
                    "text": response.text,
                    "labeled_text": speaker_result.get("labeled_text", response.text),
                    "speaker": speaker_result.get("speaker", "unknown"),
                    "speaker_confidence": speaker_result.get("confidence", 0.0),
                    "speaker_changes": speaker_result.get("speaker_changes", []),
                    "tone": speaker_result.get("tone", "neutral"),
                    "tone_confidence": speaker_result.get("tone_confidence", 0.0),
                    "tone_severity": speaker_result.get("tone_severity", "normal"),
                    "emotion_indicators": speaker_result.get("emotion_indicators", []),
                    "escalation_detected": speaker_result.get("escalation_detected", False),
                    "escalation_direction": speaker_result.get("escalation_direction", "stable"),
                    "officer_demeanor": speaker_result.get("officer_demeanor", {}),
                    "citizen_demeanor": speaker_result.get("citizen_demeanor", {}),
                    "start_time": chunk_index * 10.0,
                    "end_time": (chunk_index + 1) * 10.0,
                    "confidence": 0.9,
                    "violations_detected": violations,
                    "audio_file": chunk_filename,
                    "created_at": now.isoformat()
                }
                
                await db.transcriptions.insert_one(transcription_doc)
                
                await db.encounters.update_one(
                    {"encounter_id": encounter_id},
                    {"$push": {"transcriptions": segment_id}}
                )
                
                transcription_result = {
                    "segment_id": segment_id,
                    "text": response.text,
                    "labeled_text": speaker_result.get("labeled_text", response.text),
                    "speaker": speaker_result.get("speaker", "unknown"),
                    "speaker_confidence": speaker_result.get("confidence", 0.0),
                    "tone": speaker_result.get("tone", "neutral"),
                    "tone_severity": speaker_result.get("tone_severity", "normal"),
                    "emotion_indicators": speaker_result.get("emotion_indicators", []),
                    "escalation_detected": speaker_result.get("escalation_detected", False),
                    "officer_demeanor": speaker_result.get("officer_demeanor", {}),
                    "violations_detected": violations
                }
                
                # Real-time alerts
                tone_severity = speaker_result.get("tone_severity", "normal")
                if tone_severity in ["concerning", "critical"] or speaker_result.get("escalation_detected"):
                    await manager.send_to_user(current_user["user_id"], {
                        "type": "tone_alert",
                        "encounter_id": encounter_id,
                        "tone": speaker_result.get("tone"),
                        "tone_severity": tone_severity,
                        "escalation_detected": speaker_result.get("escalation_detected"),
                        "text": response.text,
                        "speaker": speaker_result.get("speaker")
                    })
                
                if violations:
                    await manager.send_to_user(current_user["user_id"], {
                        "type": "violation_detected",
                        "encounter_id": encounter_id,
                        "violations": violations,
                        "text": response.text,
                        "speaker": speaker_result.get("speaker")
                    })
                
                # Broadcast to share viewers (if any)
                await manager.broadcast_to_share_viewers(encounter_id, {
                    "type": "transcription",
                    "segment_id": segment_id,
                    "text": response.text,
                    "labeled_text": speaker_result.get("labeled_text", response.text),
                    "speaker": speaker_result.get("speaker", "unknown"),
                    "tone": speaker_result.get("tone", "neutral"),
                    "tone_severity": speaker_result.get("tone_severity", "normal"),
                    "violations_detected": violations,
                    "timestamp": now.isoformat()
                })
        except Exception as e:
            print(f"Transcription error: {e}")
    
    return {
        "success": True,
        "chunk_index": chunk_index,
        "filename": chunk_filename,
        "transcription": transcription_result
    }


@router.post("/{encounter_id}/video")
async def upload_video_chunk(
    encounter_id: str,
    chunk_index: int = Form(...),
    video: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a video chunk"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    enc_dir = ENCOUNTERS_DIR / encounter_id
    enc_dir.mkdir(exist_ok=True)
    
    chunk_filename = f"video_chunk_{chunk_index}.webm"
    chunk_path = enc_dir / chunk_filename
    
    async with aiofiles.open(chunk_path, 'wb') as f:
        content = await video.read()
        await f.write(content)
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"media_files": chunk_filename}}
    )
    
    # Broadcast to viewers if streaming
    if encounter.get("broadcast_mode") in ["share_contacts", "livestream", "all"]:
        await manager.broadcast_to_viewers(encounter_id, content)
    
    return {
        "success": True,
        "chunk_index": chunk_index,
        "filename": chunk_filename
    }


@router.post("/{encounter_id}/analyze")
async def analyze_encounter_realtime(
    encounter_id: str,
    text: str = Form(...),
    analysis_type: str = Form("full"),
    current_user: dict = Depends(get_current_user)
):
    """Perform real-time AI analysis on transcript"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    analysis_result = await perform_deep_analysis(text, encounter_id, analysis_type)
    
    # Store analysis
    analysis_doc = {
        "analysis_id": f"anal_{uuid.uuid4().hex[:8]}",
        "encounter_id": encounter_id,
        "text_analyzed": text,
        "analysis_type": analysis_type,
        "result": analysis_result,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.encounter_analyses.insert_one(analysis_doc)
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"ai_analysis": analysis_doc["analysis_id"]}}
    )
    
    return {
        "analysis": analysis_result,
        "analysis_id": analysis_doc["analysis_id"],
        "encounter_context": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{encounter_id}/violations")
async def get_encounter_violations(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Get all detected violations for an encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get violations from transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id, "violations_detected": {"$ne": []}},
        {"_id": 0}
    ).to_list(100)
    
    all_violations = []
    for t in transcriptions:
        for v in t.get("violations_detected", []):
            all_violations.append({
                "violation_type": v,
                "detected_in_text": t.get("text", "")[:200],
                "timestamp": t.get("start_time", 0),
                "speaker": t.get("speaker", "unknown")
            })
    
    # Get AI analysis violations
    analyses = await db.encounter_analyses.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(50)
    
    ai_violations = []
    for a in analyses:
        result = a.get("result", {})
        for v in result.get("violations", []):
            ai_violations.append(v)
    
    return {
        "encounter_id": encounter_id,
        "pattern_violations": all_violations,
        "ai_violations": ai_violations,
        "total_count": len(all_violations) + len(ai_violations)
    }


@router.post("/{encounter_id}/mark-violation")
async def mark_violation(
    encounter_id: str,
    timestamp: float = Form(...),
    note: str = Form("Manual violation mark"),
    current_user: dict = Depends(get_current_user)
):
    """Mark a specific moment as a potential violation"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    mark_id = f"mark_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    source = "voice_command" if "voice" in note.lower() else "manual"
    
    mark_doc = {
        "mark_id": mark_id,
        "encounter_id": encounter_id,
        "timestamp_seconds": timestamp,
        "note": note,
        "created_at": created_at,
        "source": source
    }
    
    await db.encounter_marks.insert_one(mark_doc)
    
    clean_mark = {
        "mark_id": mark_id,
        "timestamp_seconds": timestamp,
        "note": note,
        "created_at": created_at,
        "source": source
    }
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"manual_marks": clean_mark}}
    )
    
    return {"success": True, "mark": clean_mark}


@router.post("/{encounter_id}/end")
async def end_encounter(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """End an encounter and generate report"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    now = datetime.now(timezone.utc)
    started_at = encounter.get("started_at")
    if isinstance(started_at, str):
        started_at = datetime.fromisoformat(started_at)
    
    duration = int((now - started_at).total_seconds()) if started_at else 0
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {
            "status": "completed",
            "ended_at": now.isoformat(),
            "duration_seconds": duration
        }}
    )
    
    # Notify contacts that encounter ended
    if encounter.get("broadcast_mode") in ["share_contacts", "all"]:
        contacts = await db.emergency_contacts.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0}
        ).to_list(10)
        
        for contact in contacts:
            if contact.get("contact_user_id"):
                await manager.send_to_user(contact["contact_user_id"], {
                    "type": "encounter_ended",
                    "encounter_id": encounter_id,
                    "user_name": current_user.get("name"),
                    "duration_seconds": duration
                })
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "duration_seconds": duration,
        "ended_at": now.isoformat()
    }


@router.get("")
async def list_encounters(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List all encounters for current user"""
    query = {"user_id": current_user["user_id"]}
    if status:
        query["status"] = status
    
    encounters = await db.encounters.find(query, {"_id": 0}).sort("started_at", -1).to_list(100)
    
    result = []
    for enc in encounters:
        for field in ["started_at", "ended_at"]:
            if enc.get(field) and isinstance(enc[field], str):
                enc[field] = datetime.fromisoformat(enc[field])
        result.append(enc)
    
    return result


@router.get("/{encounter_id}")
async def get_encounter(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific encounter details"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    for field in ["started_at", "ended_at"]:
        if encounter.get(field) and isinstance(encounter[field], str):
            encounter[field] = datetime.fromisoformat(encounter[field])
    
    return encounter


@router.get("/{encounter_id}/report")
async def get_encounter_report(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed report for an encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("start_time", 1).to_list(500)
    
    # Build full transcript
    full_transcript = " ".join([t.get("labeled_text") or t.get("text", "") for t in transcriptions])
    
    # Get violations
    all_violations = []
    for t in transcriptions:
        for v in t.get("violations_detected", []):
            all_violations.append({
                "type": v,
                "timestamp": t.get("start_time", 0),
                "text": t.get("text", "")[:100]
            })
    
    # Get AI analyses
    analyses = await db.encounter_analyses.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).to_list(20)
    
    ai_summary = []
    for a in analyses:
        result = a.get("result", {})
        ai_summary.extend(result.get("violations", []))
    
    # Get media files
    media_files = encounter.get("media_files", [])
    video_files = [f for f in media_files if f.startswith("video_")]
    audio_files = [f for f in media_files if f.startswith("audio_")]
    
    return {
        "encounter_id": encounter_id,
        "encounter_type": encounter.get("encounter_type"),
        "status": encounter.get("status"),
        "location": {
            "latitude": encounter.get("latitude"),
            "longitude": encounter.get("longitude"),
            "address": encounter.get("address")
        },
        "duration_seconds": encounter.get("duration_seconds", 0),
        "started_at": encounter.get("started_at"),
        "ended_at": encounter.get("ended_at"),
        "transcript": full_transcript,
        "transcription_segments": transcriptions,
        "violations": all_violations,
        "ai_analysis": ai_summary,
        "officers": encounter.get("officers", []),
        "manual_marks": encounter.get("manual_marks", []),
        "media": {
            "video_chunks": len(video_files),
            "audio_chunks": len(audio_files),
            "files": media_files
        }
    }


@router.get("/{encounter_id}/media/{filename}")
async def get_encounter_media(encounter_id: str, filename: str, current_user: dict = Depends(get_current_user)):
    """Stream encounter media file"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    file_path = ENCOUNTERS_DIR / encounter_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    
    media_type = "video/webm" if filename.startswith("video_") else "audio/webm"
    return FileResponse(file_path, media_type=media_type)


@router.get("/{encounter_id}/stream-token")
async def get_stream_token(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Get stream share token for encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    stream_key = encounter.get("stream_key") or uuid.uuid4().hex[:16]
    
    return {
        "stream_key": stream_key,
        "share_url": f"/live/{encounter_id}?key={stream_key}",
        "encounter_id": encounter_id
    }


@router.post("/{encounter_id}/officer")
async def add_officer_info(
    encounter_id: str,
    name: Optional[str] = Form(None),
    badge_number: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Add officer information to encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    officer_id = f"off_{uuid.uuid4().hex[:8]}"
    officer_doc = {
        "officer_id": officer_id,
        "name": name,
        "badge_number": badge_number,
        "department": department,
        "captured_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$push": {"officers": officer_doc}}
    )
    
    return {"success": True, "officer": officer_doc}



# ============== REAL-TIME SHARING ==============

@router.post("/{encounter_id}/share")
async def create_share_link(
    encounter_id: str,
    auto_notify: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a shareable link for real-time encounter viewing.
    Viewers can watch live and send guidance messages.
    """
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Generate unique share token
    share_token = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)
    
    # Update encounter with share info
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {
            "share_token": share_token,
            "share_created_at": now.isoformat(),
            "share_expires_at": expires_at.isoformat(),
            "share_active": True,
            "share_viewer_count": 0
        }}
    )
    
    share_url = f"/shared/{encounter_id}?token={share_token}"
    
    # Auto-notify emergency contacts if requested
    notified_contacts = []
    if auto_notify:
        contacts = await db.emergency_contacts.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0}
        ).to_list(10)
        
        for contact in contacts:
            contact_id = contact.get("contact_user_id")
            if contact_id:
                await manager.send_to_user(contact_id, {
                    "type": "encounter_share",
                    "encounter_id": encounter_id,
                    "share_url": share_url,
                    "share_token": share_token,
                    "user_name": current_user.get("name"),
                    "message": f"{current_user.get('name')} is sharing a live police encounter with you",
                    "location": {
                        "latitude": encounter.get("latitude"),
                        "longitude": encounter.get("longitude"),
                        "address": encounter.get("address")
                    }
                })
                notified_contacts.append(contact.get("name") or contact.get("email"))
    
    return {
        "success": True,
        "share_token": share_token,
        "share_url": share_url,
        "full_url": f"{share_url}",
        "expires_at": expires_at.isoformat(),
        "notified_contacts": notified_contacts
    }


@router.delete("/{encounter_id}/share")
async def revoke_share_link(encounter_id: str, current_user: dict = Depends(get_current_user)):
    """Revoke active share link for encounter"""
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    await db.encounters.update_one(
        {"encounter_id": encounter_id},
        {"$set": {"share_active": False, "share_token": None}}
    )
    
    # Notify all viewers that share was revoked
    await manager.broadcast_to_share_viewers(encounter_id, {
        "type": "share_revoked",
        "message": "The encounter owner has ended the share session"
    })
    
    return {"success": True, "message": "Share link revoked"}


@router.get("/shared/{encounter_id}")
async def get_shared_encounter(encounter_id: str, token: str):
    """
    Public endpoint - Get shared encounter data for viewers.
    No authentication required, only valid share token.
    """
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Validate share token
    if not encounter.get("share_active") or encounter.get("share_token") != token:
        raise HTTPException(status_code=403, detail="Invalid or expired share link")
    
    # Check expiration
    expires_at = encounter.get("share_expires_at")
    if expires_at:
        from datetime import datetime
        exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > exp_time:
            raise HTTPException(status_code=403, detail="Share link has expired")
    
    # Get owner info (limited)
    owner = await db.users.find_one(
        {"user_id": encounter.get("user_id")},
        {"_id": 0, "name": 1}
    )
    
    # Get recent transcriptions
    transcriptions = await db.transcriptions.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("start_time", -1).limit(50).to_list(50)
    transcriptions.reverse()  # Oldest first
    
    # Get guidance messages
    messages = await db.encounter_messages.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    return {
        "encounter_id": encounter_id,
        "owner_name": owner.get("name") if owner else "Unknown",
        "status": encounter.get("status"),
        "encounter_type": encounter.get("encounter_type"),
        "location": {
            "latitude": encounter.get("latitude"),
            "longitude": encounter.get("longitude"),
            "address": encounter.get("address")
        },
        "started_at": encounter.get("started_at"),
        "duration_seconds": encounter.get("duration_seconds", 0),
        "transcriptions": transcriptions,
        "violations": encounter.get("violations", []),
        "ai_analysis": encounter.get("ai_analysis", []),
        "manual_marks": encounter.get("manual_marks", []),
        "guidance_messages": messages,
        "share_active": True
    }


@router.post("/shared/{encounter_id}/message")
async def send_guidance_message(
    encounter_id: str,
    token: str,
    message: str,
    sender_name: str = "Anonymous Viewer"
):
    """
    Public endpoint - Send a guidance message to the encounter user.
    Limited to 200 characters for safety.
    """
    if len(message) > 200:
        raise HTTPException(status_code=400, detail="Message too long (max 200 characters)")
    
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Validate share token
    if not encounter.get("share_active") or encounter.get("share_token") != token:
        raise HTTPException(status_code=403, detail="Invalid or expired share link")
    
    # Check if encounter is still active
    if encounter.get("status") != "active":
        raise HTTPException(status_code=400, detail="Encounter has ended")
    
    now = datetime.now(timezone.utc)
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    
    message_doc = {
        "message_id": message_id,
        "encounter_id": encounter_id,
        "sender_name": sender_name[:50],  # Limit name length
        "message": message,
        "created_at": now.isoformat()
    }
    
    await db.encounter_messages.insert_one(message_doc)
    
    # Send real-time notification to encounter owner
    await manager.send_to_user(encounter.get("user_id"), {
        "type": "guidance_message",
        "encounter_id": encounter_id,
        "message_id": message_id,
        "sender_name": sender_name[:50],
        "message": message,
        "timestamp": now.isoformat()
    })
    
    # Broadcast to all share viewers
    await manager.broadcast_to_share_viewers(encounter_id, {
        "type": "new_message",
        "message_id": message_id,
        "sender_name": sender_name[:50],
        "message": message,
        "timestamp": now.isoformat()
    })
    
    return {
        "success": True,
        "message_id": message_id,
        "timestamp": now.isoformat()
    }


@router.get("/shared/{encounter_id}/updates")
async def get_shared_updates(encounter_id: str, token: str, since: str = None):
    """
    Polling endpoint for shared encounter updates.
    Returns new transcriptions and messages since the given timestamp.
    """
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if not encounter.get("share_active") or encounter.get("share_token") != token:
        raise HTTPException(status_code=403, detail="Invalid or expired share link")
    
    query = {"encounter_id": encounter_id}
    if since:
        query["created_at"] = {"$gt": since}
    
    # Get new transcriptions
    transcriptions = await db.transcriptions.find(
        query,
        {"_id": 0}
    ).sort("start_time", 1).to_list(50)
    
    # Get new messages
    messages = await db.encounter_messages.find(
        query,
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    
    return {
        "status": encounter.get("status"),
        "duration_seconds": encounter.get("duration_seconds", 0),
        "transcriptions": transcriptions,
        "messages": messages,
        "violations": encounter.get("violations", []),
        "manual_marks": encounter.get("manual_marks", []),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

