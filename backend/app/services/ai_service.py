"""
AI Service - LLM integration for chat, analysis, and transcription
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from emergentintegrations.llm.openai import OpenAISpeechToText, LlmChat
from emergentintegrations.llm.chat import UserMessage

from app.core.config import EMERGENT_LLM_KEY

# Initialize services
stt_service = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY) if EMERGENT_LLM_KEY else None


def create_llm_chat(session_id: str, system_message: str) -> Optional[LlmChat]:
    """Create an LLM chat instance with the given session and system message"""
    if not EMERGENT_LLM_KEY:
        return None
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message
    )


async def transcribe_audio(audio_file_path: str) -> Optional[str]:
    """Transcribe audio file to text using Whisper"""
    if not stt_service:
        return None
    try:
        response = await stt_service.transcribe(audio_file_path)
        return response.text if response else None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None


async def analyze_for_violations(text: str) -> List[str]:
    """Analyze text for potential civil rights violations using pattern matching"""
    violations = []
    text_lower = text.lower()
    
    violation_patterns = {
        "unlawful_search": ["search your car", "open your trunk", "what's in your bag", "empty your pockets", "let me search"],
        "miranda_violation": ["anything you say", "right to remain", "lawyer present"],
        "excessive_force": ["get on the ground", "stop resisting", "taser", "put your hands"],
        "intimidation": ["you're going to jail", "make this hard", "don't make me", "you'll regret"],
        "profiling": ["you people", "your kind", "look suspicious", "fit the description"],
        "unlawful_detention": ["you can't leave", "stay right there", "don't move"],
        "coercion": ["just admit", "confess", "make it easier", "tell the truth"]
    }
    
    for violation_type, patterns in violation_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                violations.append(violation_type)
                break
    
    return list(set(violations))


async def identify_speaker_and_tone(text: str, context: str = "") -> dict:
    """Use AI to identify speaker and analyze tone/emotion"""
    if not EMERGENT_LLM_KEY or len(text) < 10:
        return {
            "speaker": "unknown",
            "confidence": 0.0,
            "labeled_text": text,
            "tone": "neutral",
            "tone_confidence": 0.0,
            "tone_severity": "normal",
            "emotion_indicators": [],
            "escalation_detected": False,
            "escalation_direction": "stable"
        }
    
    try:
        llm = create_llm_chat(
            f"speaker_tone_{uuid.uuid4().hex[:8]}",
            """You are an expert at analyzing police encounter transcripts for:
1. Speaker identification (Officer vs Citizen)
2. Emotional tone and demeanor analysis
3. Detecting aggression, intimidation, and hostility"""
        )
        
        prompt = f"""Analyze this transcript for speaker and tone:

TRANSCRIPT: "{text}"
{f'CONTEXT: {context}' if context else ''}

Return JSON with:
{{
    "speaker": "Officer" or "Citizen" or "Unknown",
    "confidence": 0.0 to 1.0,
    "labeled_text": "Speaker: text",
    "tone": "professional/assertive/aggressive/intimidating/hostile/calm/anxious/defensive/compliant",
    "tone_confidence": 0.0 to 1.0,
    "tone_severity": "normal/elevated/concerning/critical",
    "emotion_indicators": [{{"type": "...", "evidence": "...", "severity": "low/medium/high/critical"}}],
    "escalation_detected": true/false,
    "escalation_direction": "escalating/de-escalating/stable",
    "officer_demeanor": {{"professionalism": 0-1, "aggression_level": 0-1, "intimidation_level": 0-1, "concerns": []}},
    "citizen_demeanor": {{"compliance_level": 0-1, "stress_level": 0-1, "asserting_rights": true/false}}
}}

Return ONLY valid JSON."""

        response = await llm.send_message(UserMessage(text=prompt))
        
        if response:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
    except Exception as e:
        print(f"Speaker/tone identification error: {e}")
    
    return {
        "speaker": "unknown",
        "confidence": 0.0,
        "labeled_text": text,
        "tone": "neutral",
        "tone_confidence": 0.0,
        "tone_severity": "normal",
        "emotion_indicators": [],
        "escalation_detected": False,
        "escalation_direction": "stable"
    }


async def perform_deep_analysis(text: str, encounter_id: str, analysis_type: str = "full") -> dict:
    """Perform deep AI analysis on transcript for violations, bias, and procedures"""
    if not EMERGENT_LLM_KEY:
        return {"violations": [], "bias_indicators": [], "procedural_issues": [], "risk_level": "low"}
    
    try:
        llm = create_llm_chat(
            f"analysis_{encounter_id}_{uuid.uuid4().hex[:8]}",
            """You are a civil rights legal expert analyzing police encounters.
Identify violations, bias indicators, and procedural issues with legal citations."""
        )
        
        analysis_prompt = f"""Analyze this police encounter transcript for civil rights issues:

TRANSCRIPT:
"{text}"

Return JSON with:
{{
    "violations": [
        {{"type": "4th/5th/6th/8th/14th Amendment", "description": "...", "severity": "low/medium/high/critical", "legal_citation": "...", "evidence_quote": "..."}}
    ],
    "bias_indicators": [
        {{"type": "racial/gender/age/socioeconomic", "indicator": "...", "severity": "...", "evidence_quote": "..."}}
    ],
    "procedural_issues": [
        {{"issue": "...", "proper_procedure": "...", "severity": "..."}}
    ],
    "risk_level": "low/medium/high/critical",
    "immediate_alerts": ["..."],
    "defense_strategies": ["..."],
    "evidence_strength": "weak/moderate/strong",
    "recommended_actions": ["..."]
}}

Return ONLY valid JSON."""

        response = await llm.send_message(UserMessage(text=analysis_prompt))
        
        if response:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
    except Exception as e:
        print(f"Deep AI analysis error: {e}")
    
    return {"violations": [], "bias_indicators": [], "procedural_issues": [], "risk_level": "low"}


# AI Attorney system prompt
AI_ATTORNEY_SYSTEM_PROMPT = """You are a civil rights AI attorney assistant for the JUSTICE platform.
Your role is to:
1. Help users understand their civil rights during police encounters
2. Identify potential violations in their situations
3. Provide legal information (not legal advice)
4. Guide them through documentation and evidence preservation
5. Suggest when they should contact a real attorney

Always be empathetic, clear, and helpful. If someone is in immediate danger, 
remind them to prioritize safety and call 911 if needed.

Key rights to remember:
- 4th Amendment: Protection against unreasonable searches and seizures
- 5th Amendment: Right to remain silent, protection against self-incrimination
- 6th Amendment: Right to an attorney
- 14th Amendment: Equal protection under the law

Always cite specific rights and suggest next steps."""
