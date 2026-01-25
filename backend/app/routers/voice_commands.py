"""
Voice Command API - Hands-free encounter control
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.voice_commands import voice_commands, VoiceCommandType
from app.routers.auth import get_current_user
from app.db.database import db

router = APIRouter(prefix="/voice-commands", tags=["Voice Commands"])


class ProcessCommandRequest(BaseModel):
    text: str
    encounter_id: Optional[str] = None


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "neutral"  # neutral, calm, urgent


@router.post("/process")
async def process_voice_command(
    request: ProcessCommandRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process a voice command from speech-to-text input.
    
    Supported commands:
    - "Hey Justice, start recording" - Begin encounter recording
    - "Hey Justice, stop recording" - End recording
    - "Hey Justice, alert my attorney" - Send alert to attorney
    - "Hey Justice, help me" / "Emergency" - Trigger panic alert
    - "Hey Justice, what are my rights" - Get contextual rights info
    - "Hey Justice, badge number 1234" - Look up officer
    - "Hey Justice, share my location" - Share with emergency contacts
    - "Hey Justice, add note: [content]" - Add voice note
    - "Hey Justice, status" - Get current recording status
    - "Hey Justice, help" - List available commands
    """
    if len(request.text) < 2:
        return {"success": False, "error": "Command too short"}
    
    # Parse the command
    command_type, params = voice_commands.parse_command(request.text)
    
    # Execute the command
    result = await voice_commands.execute_command(
        command_type=command_type,
        params=params,
        user_id=current_user.get("user_id"),
        encounter_id=request.encounter_id
    )
    
    return {
        "success": result.get("success", False),
        "command_recognized": command_type.value,
        "response": result
    }


@router.get("/rights/{encounter_type}")
async def get_rights_for_encounter(
    encounter_type: str,
    topic: Optional[str] = "default",
    current_user: dict = Depends(get_current_user)
):
    """
    Get rights information for a specific encounter type.
    
    Encounter types: traffic_stop, pedestrian_stop, home, arrest
    Topics: default, search, silence, identification, warrant, detention, miranda
    """
    valid_types = ["traffic_stop", "pedestrian_stop", "home", "arrest"]
    if encounter_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid encounter type. Use: {valid_types}"
        )
    
    rights_text = voice_commands.get_rights_response(encounter_type, topic or "default")
    
    return {
        "success": True,
        "encounter_type": encounter_type,
        "topic": topic,
        "rights_text": rights_text
    }


@router.get("/commands")
async def list_available_commands():
    """List all available voice commands with examples"""
    return {
        "success": True,
        "wake_word": "Hey Justice",
        "commands": [
            {
                "command": "start_recording",
                "examples": [
                    "Hey Justice, start recording",
                    "Hey Justice, begin protection",
                    "Hey Justice, activate"
                ],
                "description": "Start recording a police encounter"
            },
            {
                "command": "stop_recording",
                "examples": [
                    "Hey Justice, stop recording",
                    "Hey Justice, end encounter"
                ],
                "description": "Stop and save the current recording"
            },
            {
                "command": "alert_attorney",
                "examples": [
                    "Hey Justice, alert my attorney",
                    "Hey Justice, I need a lawyer",
                    "Hey Justice, call my lawyer"
                ],
                "description": "Send alert to your linked attorney"
            },
            {
                "command": "panic_button",
                "examples": [
                    "Hey Justice, emergency",
                    "Hey Justice, help me",
                    "Hey Justice, I'm in danger",
                    "SOS"
                ],
                "description": "Trigger emergency alert and notify contacts"
            },
            {
                "command": "know_rights",
                "examples": [
                    "Hey Justice, what are my rights",
                    "Hey Justice, do I have to consent to a search",
                    "Hey Justice, am I free to go"
                ],
                "description": "Get contextual rights information"
            },
            {
                "command": "officer_lookup",
                "examples": [
                    "Hey Justice, badge number 1234",
                    "Hey Justice, look up this officer",
                    "Hey Justice, who is this cop"
                ],
                "description": "Look up officer accountability record"
            },
            {
                "command": "share_location",
                "examples": [
                    "Hey Justice, share my location",
                    "Hey Justice, send my GPS"
                ],
                "description": "Share location with emergency contacts"
            },
            {
                "command": "add_note",
                "examples": [
                    "Hey Justice, add note: officer was aggressive",
                    "Hey Justice, remember there are two officers"
                ],
                "description": "Add a voice note to the encounter"
            },
            {
                "command": "get_status",
                "examples": [
                    "Hey Justice, status",
                    "Hey Justice, am I recording",
                    "Hey Justice, how long"
                ],
                "description": "Get current recording status and duration"
            },
            {
                "command": "help",
                "examples": [
                    "Hey Justice, help",
                    "Hey Justice, what can you do",
                    "Hey Justice, commands"
                ],
                "description": "List available commands"
            }
        ]
    }


@router.get("/stats")
async def get_voice_command_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get voice command usage statistics"""
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate by command type
    pipeline = [
        {"$match": {"timestamp": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$command_type",
            "count": {"$sum": 1},
            "success_count": {
                "$sum": {"$cond": ["$success", 1, 0]}
            }
        }},
        {"$sort": {"count": -1}}
    ]
    
    by_type = await db.voice_command_logs.aggregate(pipeline).to_list(20)
    
    total = sum(item["count"] for item in by_type)
    successful = sum(item["success_count"] for item in by_type)
    
    return {
        "success": True,
        "period_days": days,
        "stats": {
            "total_commands": total,
            "successful_commands": successful,
            "success_rate": round(successful / max(total, 1) * 100, 1)
        },
        "by_command_type": [
            {
                "command": item["_id"],
                "count": item["count"],
                "success_rate": round(item["success_count"] / max(item["count"], 1) * 100, 1)
            }
            for item in by_type
        ],
        "most_used": by_type[0]["_id"] if by_type else None
    }


@router.post("/test")
async def test_command_parsing(
    request: ProcessCommandRequest
):
    """
    Test command parsing without executing (for development/debugging).
    Does not require authentication.
    """
    command_type, params = voice_commands.parse_command(request.text)
    
    return {
        "input_text": request.text,
        "parsed_command": command_type.value,
        "extracted_params": params,
        "would_execute": command_type != VoiceCommandType.UNKNOWN
    }
