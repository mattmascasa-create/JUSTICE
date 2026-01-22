"""
JUSTICE Application - Services module
"""
from app.services.websocket import manager, ConnectionManager
from app.services.ai_service import (
    create_llm_chat,
    transcribe_audio,
    analyze_for_violations,
    identify_speaker_and_tone,
    perform_deep_analysis,
    AI_ATTORNEY_SYSTEM_PROMPT,
    stt_service
)
