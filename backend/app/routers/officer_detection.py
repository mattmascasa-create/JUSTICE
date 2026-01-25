"""
Officer Detection API - Automatic extraction of officer information from audio/text
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from pydantic import BaseModel
import os
import uuid
import aiofiles

from app.services.officer_detection import officer_detection
from app.routers.auth import get_current_user
from app.db.database import db

router = APIRouter(prefix="/officer-detection", tags=["Officer Detection"])


class DetectFromTextRequest(BaseModel):
    transcript: str
    encounter_id: Optional[str] = None


@router.post("/from-text")
async def detect_officers_from_text(
    request: DetectFromTextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detect officer information from transcript text.
    
    Uses pattern matching + AI to extract:
    - Badge numbers
    - Officer names
    - Department information
    - Unit/division numbers
    
    Automatically cross-references with accountability database.
    """
    if len(request.transcript) < 20:
        raise HTTPException(status_code=400, detail="Transcript too short for detection")
    
    result = await officer_detection.detect_from_transcript(
        request.transcript,
        request.encounter_id
    )
    
    return {"success": True, "detection": result}


@router.post("/from-audio")
async def detect_officers_from_audio(
    audio: UploadFile = File(...),
    encounter_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Detect officer information from audio file.
    
    Process:
    1. Transcribe audio using Whisper
    2. Extract officer info using patterns + AI
    3. Cross-reference with accountability database
    
    Supported formats: mp3, wav, m4a, webm, ogg
    """
    # Validate file type
    allowed_extensions = [".mp3", ".wav", ".m4a", ".webm", ".ogg", ".mp4"]
    file_ext = os.path.splitext(audio.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    temp_path = f"/tmp/officer_detect_{uuid.uuid4().hex}{file_ext}"
    
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await audio.read()
            await f.write(content)
        
        # Detect from audio
        result = await officer_detection.detect_from_audio(temp_path, encounter_id)
        
        return {"success": True, "detection": result}
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/encounter/{encounter_id}")
async def get_encounter_detections(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all officer detections for an encounter"""
    detections = await db.officer_detections.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(10)
    
    # Also get detected officers from encounter
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0, "detected_officers": 1}
    )
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "detections": detections,
        "current_detected_officers": encounter.get("detected_officers", []) if encounter else []
    }


@router.post("/encounter/{encounter_id}/redetect")
async def redetect_encounter_officers(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Re-run officer detection on an existing encounter's transcript.
    Useful when accountability database has been updated.
    """
    # Get encounter transcript
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0, "transcript": 1, "full_transcript": 1}
    )
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    transcript = encounter.get("full_transcript") or encounter.get("transcript", "")
    
    if len(transcript) < 20:
        raise HTTPException(status_code=400, detail="Encounter has insufficient transcript data")
    
    result = await officer_detection.detect_from_transcript(transcript, encounter_id)
    
    return {"success": True, "detection": result}


@router.get("/stats")
async def get_detection_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get officer detection statistics"""
    total_detections = await db.officer_detections.count_documents({})
    
    # Count detections with database matches
    pipeline = [
        {"$unwind": "$officers"},
        {"$group": {
            "_id": "$officers.database_match",
            "count": {"$sum": 1}
        }}
    ]
    match_stats = await db.officer_detections.aggregate(pipeline).to_list(10)
    
    db_matches = sum(s["count"] for s in match_stats if s["_id"] is True)
    no_matches = sum(s["count"] for s in match_stats if s["_id"] is False)
    
    return {
        "success": True,
        "stats": {
            "total_detections": total_detections,
            "officers_matched_to_database": db_matches,
            "officers_not_in_database": no_matches,
            "match_rate": round(db_matches / max(db_matches + no_matches, 1) * 100, 1)
        }
    }
