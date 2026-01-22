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



async def generate_evidence_highlights(
    transcriptions: List[dict], 
    encounter_id: str,
    existing_violations: List[dict] = None,
    existing_analysis: List[dict] = None
) -> List[dict]:
    """
    Generate AI-powered evidence highlights from encounter transcriptions.
    Identifies key moments: violations, escalations, important statements, cooperation attempts.
    Returns timestamped highlights for easy navigation.
    """
    if not EMERGENT_LLM_KEY or not transcriptions:
        return []
    
    # Build transcript text with timestamps
    transcript_with_times = []
    for t in transcriptions:
        timestamp = t.get("start_time", t.get("timestamp", "00:00"))
        speaker = t.get("speaker", "Unknown")
        text = t.get("text", t.get("labeled_text", ""))
        tone = t.get("tone", "neutral")
        transcript_with_times.append(f"[{timestamp}] {speaker} ({tone}): {text}")
    
    full_transcript = "\n".join(transcript_with_times)
    
    # Include existing analysis context
    context_parts = []
    if existing_violations:
        context_parts.append(f"Known violations: {json.dumps(existing_violations[:5])}")
    if existing_analysis:
        context_parts.append(f"Prior analysis: {json.dumps(existing_analysis[:3])}")
    context = "\n".join(context_parts) if context_parts else ""
    
    try:
        llm = create_llm_chat(
            f"highlights_{encounter_id}_{uuid.uuid4().hex[:8]}",
            """You are a legal evidence analyst specializing in police encounter documentation.
Your task is to identify key moments that would be important for legal review.
Focus on: rights violations, escalation points, important statements, and notable behaviors."""
        )
        
        prompt = f"""Analyze this police encounter transcript and identify KEY EVIDENCE HIGHLIGHTS.
Each highlight should be a significant moment that an attorney would want to review.

TRANSCRIPT WITH TIMESTAMPS:
{full_transcript}

{f'CONTEXT: {context}' if context else ''}

Return a JSON array of highlights. Each highlight must have:
- timestamp: The exact timestamp from the transcript (e.g., "00:45", "01:23")
- category: One of "violation", "escalation", "threat", "rights_assertion", "cooperation", "important_statement", "procedural_issue"
- severity: "critical", "high", "medium", or "low"
- title: Brief 5-10 word title
- description: 1-2 sentence explanation of why this is significant
- quote: The exact quote from the transcript
- legal_relevance: Brief note on legal significance
- speaker: "Officer" or "Citizen"

Return 5-15 highlights, prioritizing the most legally significant moments.
Return ONLY valid JSON array.

Example format:
[
  {{
    "timestamp": "00:45",
    "category": "violation",
    "severity": "critical",
    "title": "Unlawful Search Demand",
    "description": "Officer demanded to search vehicle without consent or probable cause.",
    "quote": "Open your trunk right now",
    "legal_relevance": "4th Amendment violation - requires consent or warrant",
    "speaker": "Officer"
  }}
]"""

        response = await llm.send_message(UserMessage(text=prompt))
        
        if response:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            
            highlights = json.loads(cleaned.strip())
            
            # Add IDs and normalize
            for i, highlight in enumerate(highlights):
                highlight["highlight_id"] = f"hl_{encounter_id}_{i}"
                highlight["generated_at"] = datetime.now(timezone.utc).isoformat()
                # Ensure required fields
                if "severity" not in highlight:
                    highlight["severity"] = "medium"
                if "category" not in highlight:
                    highlight["category"] = "important_statement"
            
            # Sort by severity (critical first) then timestamp
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            highlights.sort(key=lambda x: (severity_order.get(x.get("severity"), 2), x.get("timestamp", "")))
            
            return highlights
            
    except Exception as e:
        print(f"Evidence highlights generation error: {e}")
    
    return []


async def regenerate_highlights_with_feedback(
    encounter_id: str,
    transcriptions: List[dict],
    feedback: str,
    previous_highlights: List[dict] = None
) -> List[dict]:
    """
    Regenerate highlights with user/attorney feedback to improve relevance.
    """
    if not EMERGENT_LLM_KEY:
        return previous_highlights or []
    
    try:
        llm = create_llm_chat(
            f"regen_highlights_{encounter_id}_{uuid.uuid4().hex[:8]}",
            """You are refining evidence highlights based on feedback.
Improve the highlights to better serve legal review needs."""
        )
        
        transcript_with_times = []
        for t in transcriptions:
            timestamp = t.get("start_time", t.get("timestamp", "00:00"))
            speaker = t.get("speaker", "Unknown")
            text = t.get("text", t.get("labeled_text", ""))
            transcript_with_times.append(f"[{timestamp}] {speaker}: {text}")
        
        prompt = f"""TRANSCRIPT:
{chr(10).join(transcript_with_times)}

PREVIOUS HIGHLIGHTS:
{json.dumps(previous_highlights or [], indent=2)}

FEEDBACK TO ADDRESS:
{feedback}

Generate improved highlights addressing the feedback.
Return ONLY valid JSON array with same format as before.
Include timestamp, category, severity, title, description, quote, legal_relevance, speaker."""

        response = await llm.send_message(UserMessage(text=prompt))
        
        if response:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            
            highlights = json.loads(cleaned.strip())
            
            for i, highlight in enumerate(highlights):
                highlight["highlight_id"] = f"hl_{encounter_id}_{i}"
                highlight["generated_at"] = datetime.now(timezone.utc).isoformat()
                highlight["regenerated"] = True
            
            return highlights
            
    except Exception as e:
        print(f"Highlights regeneration error: {e}")
    
    return previous_highlights or []
