"""
AI Rights Coach Service - Real-time legal guidance during police encounters
Uses GPT-5.2 to analyze conversation and provide contextual rights guidance
"""
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Rights guidance templates by situation
RIGHTS_GUIDANCE = {
    "traffic_stop": [
        {"trigger": "license", "guidance": "You must provide license, registration, and insurance if driving.", "amendment": "4th"},
        {"trigger": "step out", "guidance": "You must exit if ordered, but can ask: 'Am I being detained?'", "amendment": "4th"},
        {"trigger": "search", "guidance": "Say: 'I do not consent to searches.' They need a warrant or probable cause.", "amendment": "4th"},
    ],
    "pedestrian_stop": [
        {"trigger": "id", "guidance": "In most states, you only need to identify if lawfully detained.", "amendment": "4th/5th"},
        {"trigger": "where are you going", "guidance": "You don't have to answer. Ask: 'Am I free to go?'", "amendment": "5th"},
        {"trigger": "what are you doing", "guidance": "You have the right to remain silent.", "amendment": "5th"},
    ],
    "arrest": [
        {"trigger": "arrest", "guidance": "Stay calm. Say: 'I invoke my right to remain silent and want a lawyer.'", "amendment": "5th/6th"},
        {"trigger": "handcuff", "guidance": "Do not resist. State clearly: 'I do not consent but will not resist.'", "amendment": "4th"},
        {"trigger": "miranda", "guidance": "After Miranda, say NOTHING without a lawyer present.", "amendment": "5th/6th"},
    ],
    "home_encounter": [
        {"trigger": "open the door", "guidance": "You don't have to open. Ask: 'Do you have a warrant?'", "amendment": "4th"},
        {"trigger": "warrant", "guidance": "Ask to see the warrant through a window. Verify the address.", "amendment": "4th"},
        {"trigger": "come inside", "guidance": "Say: 'I do not consent to entry.' They need a warrant.", "amendment": "4th"},
    ]
}

# Key phrases that indicate rights being violated
VIOLATION_INDICATORS = [
    {"phrase": "you have to", "type": "coercion", "response": "Ask: 'Is that a lawful order or a request?'"},
    {"phrase": "make this easy", "type": "intimidation", "response": "You have the right to assert your rights respectfully."},
    {"phrase": "nothing to hide", "type": "manipulation", "response": "Rights exist regardless. Say: 'I don't consent to searches.'"},
    {"phrase": "cooperate", "type": "pressure", "response": "Cooperation is voluntary. You can remain silent."},
    {"phrase": "we can do this the hard way", "type": "threat", "response": "Stay calm. This may be recorded as potential coercion."},
]


async def get_ai_rights_guidance(
    transcript: str,
    encounter_type: str = "general",
    current_context: Optional[Dict] = None
) -> Dict:
    """
    Analyze transcript and provide real-time rights guidance using AI.
    
    Args:
        transcript: Current conversation transcript
        encounter_type: Type of encounter (traffic_stop, pedestrian_stop, arrest, home_encounter)
        current_context: Additional context about the encounter
    
    Returns:
        Dict with guidance, warnings, and suggested responses
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid
    
    system_prompt = """You are a constitutional rights expert providing REAL-TIME guidance during a police encounter. 
Your role is to help citizens understand and exercise their constitutional rights lawfully and safely.

CRITICAL RULES:
1. SAFETY FIRST - Never suggest actions that could escalate danger
2. Be CONCISE - User is in a stressful situation, use short clear sentences
3. Cite the relevant Amendment when applicable
4. Suggest exact phrases to say
5. Flag potential rights violations immediately

Respond in JSON format:
{
    "immediate_guidance": "Short, actionable advice for right now",
    "suggested_response": "Exact phrase to say to the officer",
    "rights_applicable": ["4th Amendment", "5th Amendment"],
    "potential_violation": null or {"type": "...", "severity": 1-10, "explanation": "..."},
    "safety_warning": null or "Warning message if situation seems dangerous",
    "do_not": "What NOT to do right now"
}"""

    user_prompt = f"""ENCOUNTER TYPE: {encounter_type}
CURRENT TRANSCRIPT:
{transcript[-2000:]}  

CONTEXT: {current_context or 'None provided'}

Analyze the latest exchange and provide guidance. Focus on the most recent officer statement/question."""

    try:
        session_id = str(uuid.uuid4())
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(UserMessage(text=user_prompt))
        
        import json
        # Try to parse JSON from response
        content = str(response)
        # Extract JSON if wrapped in markdown code block
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
            
        guidance = json.loads(content)
        guidance["timestamp"] = datetime.now(timezone.utc).isoformat()
        guidance["encounter_type"] = encounter_type
        
        return guidance
        
    except Exception as e:
        logger.error(f"AI Rights Coach error: {e}")
        # Fallback to basic guidance
        return {
            "immediate_guidance": "Remember: You have the right to remain silent.",
            "suggested_response": "I respectfully invoke my right to remain silent.",
            "rights_applicable": ["5th Amendment"],
            "potential_violation": None,
            "safety_warning": None,
            "do_not": "Do not argue or physically resist.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "encounter_type": encounter_type,
            "fallback": True
        }


async def analyze_for_violations(
    transcript: str,
    officer_statements: List[str]
) -> List[Dict]:
    """
    Analyze officer statements for potential rights violations.
    
    Returns:
        List of potential violations with timestamps and legal analysis
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid
    
    system_prompt = """You are a constitutional law expert analyzing police conduct for rights violations.
Analyze the officer's statements and identify any potential constitutional violations.

For each violation found, provide:
{
    "violations": [
        {
            "statement": "The exact officer statement",
            "violation_type": "Type (e.g., 4th Amendment - Unreasonable Search)",
            "severity": 1-10,
            "legal_basis": "Brief legal explanation",
            "relevant_case_law": "Key case citation if applicable",
            "timestamp_marker": "Approximate position in transcript"
        }
    ],
    "overall_assessment": "Brief summary of encounter legality",
    "recommendation": "What the citizen should do"
}

Be conservative - only flag clear violations, not borderline conduct."""

    try:
        session_id = str(uuid.uuid4())
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id,
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        response = await chat.send_message(
            UserMessage(text=f"TRANSCRIPT:\n{transcript}\n\nOFFICER STATEMENTS TO ANALYZE:\n" + "\n".join(officer_statements))
        )
        
        import json
        content = str(response)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Violation analysis error: {e}")
        return {"violations": [], "overall_assessment": "Analysis unavailable", "recommendation": "Consult an attorney"}


def get_quick_guidance(phrase: str, encounter_type: str = "general") -> Optional[Dict]:
    """
    Get immediate guidance based on keyword matching (no AI latency).
    Used for instant responses while AI analysis runs in background.
    """
    phrase_lower = phrase.lower()
    
    # Check violation indicators first
    for indicator in VIOLATION_INDICATORS:
        if indicator["phrase"] in phrase_lower:
            return {
                "type": "warning",
                "indicator": indicator["type"],
                "guidance": indicator["response"],
                "immediate": True
            }
    
    # Check situation-specific guidance
    guidance_set = RIGHTS_GUIDANCE.get(encounter_type, [])
    for item in guidance_set:
        if item["trigger"] in phrase_lower:
            return {
                "type": "guidance",
                "guidance": item["guidance"],
                "amendment": item["amendment"],
                "immediate": True
            }
    
    return None
