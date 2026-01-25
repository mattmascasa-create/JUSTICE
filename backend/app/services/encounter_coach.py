"""
AI Encounter Coach - Real-time guidance during police encounters
Provides whispered coaching based on situation analysis
"""
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from enum import Enum

from app.db.database import db
from app.core.config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)


class CoachingTone(Enum):
    """Tone of coaching messages"""
    CALM = "calm"           # Reassuring, de-escalation
    ALERT = "alert"         # Important information
    URGENT = "urgent"       # Immediate action needed
    INFORMATIVE = "info"    # Rights/procedure info


class CoachingCategory(Enum):
    """Categories of coaching advice"""
    DE_ESCALATION = "de_escalation"
    RIGHTS_REMINDER = "rights_reminder"
    RESPONSE_SUGGESTION = "response_suggestion"
    WARNING = "warning"
    DOCUMENTATION = "documentation"
    SAFETY = "safety"


# Pre-defined coaching responses for common situations (fast, no API needed)
INSTANT_COACHING = {
    # De-escalation
    "aggressive_language": {
        "triggers": ["calm down", "don't make me", "last warning", "you're making this worse"],
        "coaching": "Stay calm. Keep your hands visible. Speak slowly and clearly.",
        "tone": CoachingTone.CALM,
        "category": CoachingCategory.DE_ESCALATION
    },
    "raised_voices": {
        "triggers": ["yelling", "screaming", "shouting", "loud"],
        "coaching": "Keep your voice steady and low. Ask calmly: 'I want to cooperate. Can we talk calmly?'",
        "tone": CoachingTone.CALM,
        "category": CoachingCategory.DE_ESCALATION
    },
    
    # Rights reminders
    "search_request": {
        "triggers": ["search your", "look through", "open the trunk", "empty your pockets", "consent to search"],
        "coaching": "You can refuse. Say clearly: 'I do not consent to searches.'",
        "tone": CoachingTone.ALERT,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    "question_barrage": {
        "triggers": ["where are you going", "where are you coming from", "what are you doing", "why are you here"],
        "coaching": "You don't have to answer. You can say: 'I prefer not to answer questions.'",
        "tone": CoachingTone.INFORMATIVE,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    "detention_question": {
        "triggers": ["you're detained", "not free to go", "stay right there", "don't move"],
        "coaching": "Ask calmly: 'Am I being detained? What is the reason?' Remember this for your record.",
        "tone": CoachingTone.ALERT,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    "arrest_indication": {
        "triggers": ["under arrest", "you're arrested", "hands behind your back", "cuffs"],
        "coaching": "Do not resist physically. Say clearly: 'I am exercising my right to remain silent. I want an attorney.'",
        "tone": CoachingTone.URGENT,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    
    # Recording interference
    "recording_threat": {
        "triggers": ["stop recording", "put that phone", "turn that off", "delete that", "hand over your phone"],
        "coaching": "Recording is legal. Say: 'I have the right to record. I'm not interfering.'",
        "tone": CoachingTone.ALERT,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    
    # Miranda
    "miranda_rights": {
        "triggers": ["right to remain silent", "anything you say can", "right to an attorney"],
        "coaching": "Miranda rights are being read. STOP talking immediately. Say: 'I want a lawyer.'",
        "tone": CoachingTone.URGENT,
        "category": CoachingCategory.RIGHTS_REMINDER
    },
    
    # Safety
    "weapon_mention": {
        "triggers": ["gun", "weapon", "firearm", "taser", "pepper spray", "reach for"],
        "coaching": "Keep hands visible at all times. Move slowly. Announce any movements.",
        "tone": CoachingTone.URGENT,
        "category": CoachingCategory.SAFETY
    },
    "physical_threat": {
        "triggers": ["get on the ground", "hands up", "don't move", "stop resisting"],
        "coaching": "Comply with physical commands. Do not resist. Your safety is the priority.",
        "tone": CoachingTone.URGENT,
        "category": CoachingCategory.SAFETY
    },
    
    # Documentation reminders
    "officer_id": {
        "triggers": ["badge number", "officer", "my name is", "i'm officer"],
        "coaching": "Note the badge number and name. This is being recorded.",
        "tone": CoachingTone.INFORMATIVE,
        "category": CoachingCategory.DOCUMENTATION
    },
    "witness_present": {
        "triggers": ["witness", "bystander", "someone watching", "people around"],
        "coaching": "Witnesses are present. Their testimony may be valuable. Stay composed.",
        "tone": CoachingTone.INFORMATIVE,
        "category": CoachingCategory.DOCUMENTATION
    },
    
    # Response suggestions
    "id_request": {
        "triggers": ["show me your id", "license and registration", "identification"],
        "coaching": "In a traffic stop, provide license and registration. Otherwise, ask: 'Am I legally required to identify?'",
        "tone": CoachingTone.INFORMATIVE,
        "category": CoachingCategory.RESPONSE_SUGGESTION
    },
    "exit_vehicle": {
        "triggers": ["step out of the car", "exit the vehicle", "get out"],
        "coaching": "You must exit if ordered. Move slowly. Ask: 'May I know why I'm being asked to exit?'",
        "tone": CoachingTone.ALERT,
        "category": CoachingCategory.RESPONSE_SUGGESTION
    },
}

# Situation-specific coaching templates
SITUATION_TEMPLATES = {
    "traffic_stop": {
        "initial": "Keep hands on the wheel. Wait for the officer to approach. Have license and registration ready.",
        "search_request": "You can refuse a vehicle search. Say: 'I do not consent to searches of my vehicle.'",
        "prolonged_stop": "A traffic stop shouldn't take too long. Ask: 'Am I free to go?' after receiving your ticket.",
    },
    "pedestrian_stop": {
        "initial": "Stay calm. You can ask: 'Am I being detained or am I free to go?'",
        "id_request": "In most states, you only need to identify if reasonably suspected of a crime. Ask why you're being stopped.",
        "frisk": "A pat-down requires reasonable suspicion of weapons. Say: 'I do not consent to searches.'",
    },
    "home_encounter": {
        "initial": "You don't have to open the door. Speak through it or a window.",
        "entry_request": "Without a warrant, you can refuse entry. Ask: 'Do you have a warrant?' If not, say: 'I do not consent to entry.'",
        "warrant": "If they have a warrant, ask to see it. Check the address and your name. Note any discrepancies.",
    },
    "arrest": {
        "initial": "Do not resist physically. Stay calm. Your words and actions are being recorded.",
        "questioning": "You have the right to remain silent. Say: 'I am invoking my right to remain silent. I want an attorney.' Then STOP talking.",
        "booking": "You will be processed. Do not answer questions about the alleged crime. Wait for your attorney.",
    },
}


class EncounterCoachService:
    """
    AI-powered real-time coaching during police encounters.
    Provides contextual guidance based on what's being said.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}  # encounter_id -> session data
    
    def analyze_for_coaching(
        self,
        transcript_chunk: str,
        encounter_type: str = "general",
        encounter_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze a transcript chunk and return coaching suggestions.
        Uses instant pattern matching for speed.
        """
        coaching_messages = []
        chunk_lower = transcript_chunk.lower()
        
        # Check all instant coaching patterns
        for situation_key, situation_data in INSTANT_COACHING.items():
            for trigger in situation_data["triggers"]:
                if trigger in chunk_lower:
                    coaching_messages.append({
                        "coaching_id": f"coach_{uuid.uuid4().hex[:8]}",
                        "situation": situation_key,
                        "message": situation_data["coaching"],
                        "tone": situation_data["tone"].value,
                        "category": situation_data["category"].value,
                        "trigger_phrase": trigger,
                        "priority": self._get_priority(situation_data["tone"]),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break  # One coaching per situation type
        
        # Add situation-specific initial coaching if this is a new encounter
        if encounter_id and encounter_id not in self.active_sessions:
            self.active_sessions[encounter_id] = {
                "started_at": datetime.now(timezone.utc),
                "coaching_count": 0,
                "encounter_type": encounter_type
            }
            
            # Add initial situation coaching
            initial_coaching = SITUATION_TEMPLATES.get(encounter_type, {}).get("initial")
            if initial_coaching:
                coaching_messages.insert(0, {
                    "coaching_id": f"coach_{uuid.uuid4().hex[:8]}",
                    "situation": "initial",
                    "message": initial_coaching,
                    "tone": CoachingTone.INFORMATIVE.value,
                    "category": CoachingCategory.RESPONSE_SUGGESTION.value,
                    "trigger_phrase": None,
                    "priority": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        # Update session
        if encounter_id and encounter_id in self.active_sessions:
            self.active_sessions[encounter_id]["coaching_count"] += len(coaching_messages)
        
        # Sort by priority (urgent first)
        coaching_messages.sort(key=lambda x: x["priority"])
        
        return coaching_messages
    
    def _get_priority(self, tone: CoachingTone) -> int:
        """Get priority number (lower = higher priority)"""
        priority_map = {
            CoachingTone.URGENT: 0,
            CoachingTone.ALERT: 1,
            CoachingTone.CALM: 2,
            CoachingTone.INFORMATIVE: 3
        }
        return priority_map.get(tone, 3)
    
    async def get_ai_coaching(
        self,
        transcript: str,
        encounter_type: str,
        specific_question: Optional[str] = None
    ) -> Dict:
        """
        Get AI-generated coaching for complex situations.
        Used when instant coaching isn't sufficient.
        """
        if not EMERGENT_LLM_KEY:
            return {
                "success": False,
                "error": "AI coaching unavailable",
                "fallback": "Stay calm, assert your rights politely, and document everything."
            }
        
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            llm = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"coach_{uuid.uuid4().hex[:8]}",
                system_message="""You are a civil rights defense coach helping someone during a police encounter.
Your responses must be:
- BRIEF (1-2 sentences max)
- CALM and reassuring
- Legally accurate
- Focused on safety first, rights second
- Easy to understand under stress

Do NOT:
- Give lengthy explanations
- Use legal jargon
- Suggest confrontational actions
- Advise anything that could escalate the situation"""
            ).with_model("openai", "gpt-4o")
            
            if specific_question:
                prompt = f"""Someone in a {encounter_type} is asking: "{specific_question}"

Recent transcript: "{transcript[-500:]}"

Give ONE brief, calming response they can use or action they can take RIGHT NOW."""
            else:
                prompt = f"""Analyze this {encounter_type} encounter transcript and provide ONE brief coaching tip:

"{transcript[-500:]}"

What's the most important thing this person should do or say RIGHT NOW?"""
            
            response = await llm.send_message(UserMessage(text=prompt))
            
            return {
                "success": True,
                "coaching": str(response).strip(),
                "tone": "calm",
                "generated_by": "ai"
            }
            
        except Exception as e:
            logger.error(f"AI coaching error: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": "Stay calm and cooperative. Assert your rights politely."
            }
    
    def get_situation_coaching(self, encounter_type: str, situation: str) -> Optional[str]:
        """Get pre-defined coaching for a specific situation in an encounter type"""
        return SITUATION_TEMPLATES.get(encounter_type, {}).get(situation)
    
    def get_quick_response(self, scenario: str) -> Dict:
        """
        Get a quick response script for common scenarios.
        Returns what the person should say.
        """
        quick_responses = {
            "refuse_search": {
                "say": "I do not consent to any searches.",
                "note": "Say this clearly and calmly. Repeat if necessary."
            },
            "invoke_silence": {
                "say": "I am exercising my right to remain silent.",
                "note": "After saying this, stop talking. Do not answer any questions."
            },
            "request_attorney": {
                "say": "I want to speak with an attorney before answering any questions.",
                "note": "Once you request an attorney, questioning must stop."
            },
            "ask_if_detained": {
                "say": "Am I being detained, or am I free to go?",
                "note": "This clarifies your status. If free, you can leave."
            },
            "ask_reason": {
                "say": "May I ask why I'm being stopped?",
                "note": "You have the right to know why you're being detained."
            },
            "assert_recording": {
                "say": "I have the right to record this encounter. I am not interfering with your duties.",
                "note": "Recording police in public is protected by the First Amendment."
            },
            "refuse_entry": {
                "say": "I do not consent to you entering my home without a warrant.",
                "note": "Keep the door closed or speak through it."
            },
            "request_warrant": {
                "say": "Do you have a warrant? May I see it?",
                "note": "Check the address and your name on any warrant."
            },
        }
        
        return quick_responses.get(scenario, {
            "say": "I prefer not to answer questions without an attorney present.",
            "note": "This is a safe default response."
        })
    
    async def log_coaching_delivered(
        self,
        encounter_id: str,
        user_id: str,
        coaching_messages: List[Dict]
    ):
        """Log coaching messages for analytics and improvement"""
        if coaching_messages:
            await db.coaching_logs.insert_one({
                "encounter_id": encounter_id,
                "user_id": user_id,
                "coaching_messages": coaching_messages,
                "count": len(coaching_messages),
                "timestamp": datetime.now(timezone.utc)
            })
    
    def end_session(self, encounter_id: str) -> Optional[Dict]:
        """End a coaching session and return summary"""
        if encounter_id in self.active_sessions:
            session = self.active_sessions.pop(encounter_id)
            duration = datetime.now(timezone.utc) - session["started_at"]
            return {
                "encounter_id": encounter_id,
                "duration_seconds": duration.total_seconds(),
                "coaching_messages_delivered": session["coaching_count"],
                "encounter_type": session["encounter_type"]
            }
        return None


# Singleton instance
encounter_coach = EncounterCoachService()
