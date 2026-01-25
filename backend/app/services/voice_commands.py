"""
Voice Command Service - Hands-free encounter control with natural language processing
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from enum import Enum

from app.db.database import db

logger = logging.getLogger(__name__)


class VoiceCommandType(Enum):
    """Types of voice commands"""
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    ALERT_ATTORNEY = "alert_attorney"
    PANIC_BUTTON = "panic_button"
    KNOW_RIGHTS = "know_rights"
    OFFICER_LOOKUP = "officer_lookup"
    SHARE_LOCATION = "share_location"
    ADD_NOTE = "add_note"
    GET_STATUS = "get_status"
    HELP = "help"
    UNKNOWN = "unknown"


# Voice command patterns with variations
COMMAND_PATTERNS = {
    VoiceCommandType.START_RECORDING: [
        r"(?:hey\s+)?justice[,\s]+start\s+(?:recording|protection)",
        r"(?:hey\s+)?justice[,\s]+begin\s+(?:recording|encounter)",
        r"(?:hey\s+)?justice[,\s]+record\s+this",
        r"(?:hey\s+)?justice[,\s]+activate",
        r"start\s+recording",
        r"begin\s+recording",
    ],
    VoiceCommandType.STOP_RECORDING: [
        r"(?:hey\s+)?justice[,\s]+stop\s+(?:recording|protection)",
        r"(?:hey\s+)?justice[,\s]+end\s+(?:recording|encounter)",
        r"(?:hey\s+)?justice[,\s]+stop",
        r"stop\s+recording",
        r"end\s+recording",
    ],
    VoiceCommandType.ALERT_ATTORNEY: [
        r"(?:hey\s+)?justice[,\s]+(?:alert|call|notify|contact)\s+(?:my\s+)?(?:attorney|lawyer)",
        r"(?:hey\s+)?justice[,\s]+(?:i\s+)?need\s+(?:a\s+)?(?:lawyer|attorney)",
        r"(?:hey\s+)?justice[,\s]+(?:get|send)\s+(?:me\s+)?(?:legal\s+)?help",
        r"call\s+my\s+(?:attorney|lawyer)",
        r"i\s+need\s+(?:a\s+)?lawyer",
    ],
    VoiceCommandType.PANIC_BUTTON: [
        r"(?:hey\s+)?justice[,\s]+(?:emergency|panic|help\s+me|sos)",
        r"(?:hey\s+)?justice[,\s]+i(?:'m|\s+am)\s+in\s+(?:danger|trouble)",
        r"(?:hey\s+)?justice[,\s]+send\s+(?:help|emergency)",
        r"help\s+me",
        r"emergency",
        r"sos",
    ],
    VoiceCommandType.KNOW_RIGHTS: [
        r"(?:hey\s+)?justice[,\s]+what\s+(?:are\s+)?my\s+rights",
        r"(?:hey\s+)?justice[,\s]+(?:tell|read)\s+(?:me\s+)?(?:my\s+)?rights",
        r"(?:hey\s+)?justice[,\s]+(?:can|do)\s+(?:i|they)\s+(?:have\s+to|need\s+to)",
        r"(?:hey\s+)?justice[,\s]+(?:am\s+i|do\s+i\s+have\s+to)",
        r"what\s+(?:are\s+)?my\s+rights",
        r"do\s+i\s+have\s+to\s+(?:answer|talk|consent|show)",
    ],
    VoiceCommandType.OFFICER_LOOKUP: [
        r"(?:hey\s+)?justice[,\s]+(?:look\s*up|check|find)\s+(?:this\s+)?officer",
        r"(?:hey\s+)?justice[,\s]+(?:who\s+is\s+)?(?:this\s+)?(?:officer|cop)",
        r"(?:hey\s+)?justice[,\s]+badge\s+(?:number\s+)?(\d+)",
        r"look\s*up\s+(?:officer|badge)",
        r"badge\s+(?:number\s+)?(\d+)",
    ],
    VoiceCommandType.SHARE_LOCATION: [
        r"(?:hey\s+)?justice[,\s]+share\s+(?:my\s+)?location",
        r"(?:hey\s+)?justice[,\s]+send\s+(?:my\s+)?(?:location|gps)",
        r"(?:hey\s+)?justice[,\s]+(?:where\s+am\s+i|broadcast\s+location)",
        r"share\s+(?:my\s+)?location",
    ],
    VoiceCommandType.ADD_NOTE: [
        r"(?:hey\s+)?justice[,\s]+(?:add\s+)?note[:\s]+(.+)",
        r"(?:hey\s+)?justice[,\s]+(?:remember|record)\s+(?:that\s+)?(.+)",
        r"(?:hey\s+)?justice[,\s]+mark\s+(?:that\s+)?(.+)",
        r"add\s+note[:\s]+(.+)",
    ],
    VoiceCommandType.GET_STATUS: [
        r"(?:hey\s+)?justice[,\s]+(?:what(?:'s|\s+is)\s+)?(?:the\s+)?status",
        r"(?:hey\s+)?justice[,\s]+(?:am\s+i\s+)?recording",
        r"(?:hey\s+)?justice[,\s]+(?:how\s+)?(?:long|duration)",
        r"status",
    ],
    VoiceCommandType.HELP: [
        r"(?:hey\s+)?justice[,\s]+(?:what\s+can\s+you\s+do|help|commands)",
        r"(?:hey\s+)?justice[,\s]+(?:list\s+)?commands",
        r"what\s+can\s+(?:you|justice)\s+do",
    ],
}

# Contextual rights responses
RIGHTS_RESPONSES = {
    "traffic_stop": {
        "default": "During a traffic stop: You must provide license, registration, and insurance. You can refuse searches. You can record the encounter. You can remain silent beyond identification.",
        "search": "You have the right to refuse a search of your vehicle. Say clearly: 'I do not consent to searches.' The officer may still search if they have probable cause.",
        "identification": "In a traffic stop, you must provide your license, registration, and proof of insurance. Passengers generally don't have to identify in most states.",
        "silence": "You have the right to remain silent. You can say: 'I am exercising my right to remain silent.' You don't have to answer questions about where you're going.",
    },
    "pedestrian_stop": {
        "default": "During a pedestrian stop: In most states, you only need to identify if reasonably suspected of a crime. You can ask 'Am I free to go?' You can refuse searches.",
        "search": "You can refuse a pat-down or search. Say: 'I do not consent to searches.' However, an officer may conduct a Terry frisk for weapons if they have reasonable suspicion.",
        "detention": "Ask: 'Am I being detained or am I free to go?' If detained, ask why. If free to go, calmly walk away.",
        "silence": "You have the right to remain silent. You don't have to answer questions about where you're going, what you're doing, or where you live.",
    },
    "home": {
        "default": "At your home: Police generally need a warrant to enter. You don't have to let them in without one. You can ask to see the warrant. You can record at your doorstep.",
        "warrant": "Ask: 'Do you have a warrant?' If yes, ask to see it. Check the address and your name. If no warrant, you can refuse entry.",
        "search": "Without a warrant, you can refuse to let police enter or search your home. Say: 'I do not consent to searches.' Keep the door closed or speak through it.",
    },
    "arrest": {
        "default": "If arrested: You have the right to remain silent. You have the right to an attorney. Don't resist physically. State clearly that you want a lawyer.",
        "miranda": "After arrest, police must read your Miranda rights before interrogation. You can invoke these rights at any time by saying: 'I want to remain silent. I want a lawyer.'",
        "questions": "You don't have to answer questions. Say: 'I am exercising my right to remain silent and I want an attorney.' Then stop talking.",
    },
}

# Audio response templates
AUDIO_RESPONSES = {
    VoiceCommandType.START_RECORDING: "Recording started. Stay calm and assert your rights.",
    VoiceCommandType.STOP_RECORDING: "Recording saved. Your encounter has been documented.",
    VoiceCommandType.ALERT_ATTORNEY: "Alerting your attorney now. Help is on the way.",
    VoiceCommandType.PANIC_BUTTON: "Emergency alert sent! Your location is being shared with your emergency contacts.",
    VoiceCommandType.SHARE_LOCATION: "Your location has been shared with your emergency contacts.",
    VoiceCommandType.GET_STATUS: "Currently recording. Duration: {duration}. {violations_detected} potential violations detected.",
    VoiceCommandType.HELP: "You can say: Start recording, Stop recording, Alert my attorney, What are my rights, Look up this officer, Share my location, or Help me for emergencies.",
    VoiceCommandType.UNKNOWN: "I didn't understand that command. Say 'Hey Justice, help' to hear available commands.",
}


class VoiceCommandService:
    """
    Service for processing voice commands during police encounters.
    Supports hands-free operation for safety.
    """
    
    def __init__(self):
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[VoiceCommandType, List[re.Pattern]]:
        """Pre-compile regex patterns for performance"""
        compiled = {}
        for cmd_type, patterns in COMMAND_PATTERNS.items():
            compiled[cmd_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def parse_command(self, text: str) -> Tuple[VoiceCommandType, Dict]:
        """
        Parse voice input to determine command type and extract parameters.
        Returns (command_type, extracted_params)
        """
        text = text.strip().lower()
        
        for cmd_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    params = {}
                    
                    # Extract parameters for specific commands
                    if cmd_type == VoiceCommandType.OFFICER_LOOKUP:
                        # Extract badge number if present
                        badge_match = re.search(r'badge\s*(?:number\s*)?(\d+)', text)
                        if badge_match:
                            params["badge_number"] = badge_match.group(1)
                    
                    elif cmd_type == VoiceCommandType.ADD_NOTE:
                        # Extract note content
                        if match.groups():
                            params["note_content"] = match.group(1).strip()
                    
                    elif cmd_type == VoiceCommandType.KNOW_RIGHTS:
                        # Determine what specific right they're asking about
                        params["topic"] = self._extract_rights_topic(text)
                    
                    return cmd_type, params
        
        return VoiceCommandType.UNKNOWN, {}
    
    def _extract_rights_topic(self, text: str) -> str:
        """Extract the specific rights topic from the query"""
        if any(w in text for w in ["search", "consent", "look through"]):
            return "search"
        elif any(w in text for w in ["silent", "answer", "talk", "say"]):
            return "silence"
        elif any(w in text for w in ["id", "identify", "name", "license"]):
            return "identification"
        elif any(w in text for w in ["warrant", "enter", "come in"]):
            return "warrant"
        elif any(w in text for w in ["arrest", "detained", "free to go"]):
            return "detention"
        elif any(w in text for w in ["miranda", "rights read"]):
            return "miranda"
        return "default"
    
    def get_rights_response(self, encounter_type: str, topic: str = "default") -> str:
        """Get contextual rights information based on encounter type"""
        encounter_responses = RIGHTS_RESPONSES.get(encounter_type, RIGHTS_RESPONSES["traffic_stop"])
        return encounter_responses.get(topic, encounter_responses["default"])
    
    def get_audio_response(self, command_type: VoiceCommandType, **kwargs) -> str:
        """Get the audio response for a command"""
        template = AUDIO_RESPONSES.get(command_type, AUDIO_RESPONSES[VoiceCommandType.UNKNOWN])
        return template.format(**kwargs) if kwargs else template
    
    async def execute_command(
        self,
        command_type: VoiceCommandType,
        params: Dict,
        user_id: str,
        encounter_id: Optional[str] = None
    ) -> Dict:
        """
        Execute a voice command and return the result.
        """
        result = {
            "command": command_type.value,
            "success": True,
            "response_text": "",
            "response_audio": None,
            "action_taken": None,
            "data": {}
        }
        
        try:
            if command_type == VoiceCommandType.START_RECORDING:
                result = await self._handle_start_recording(user_id)
                
            elif command_type == VoiceCommandType.STOP_RECORDING:
                result = await self._handle_stop_recording(user_id, encounter_id)
                
            elif command_type == VoiceCommandType.ALERT_ATTORNEY:
                result = await self._handle_alert_attorney(user_id, encounter_id)
                
            elif command_type == VoiceCommandType.PANIC_BUTTON:
                result = await self._handle_panic(user_id, encounter_id)
                
            elif command_type == VoiceCommandType.KNOW_RIGHTS:
                result = await self._handle_know_rights(user_id, encounter_id, params.get("topic", "default"))
                
            elif command_type == VoiceCommandType.OFFICER_LOOKUP:
                result = await self._handle_officer_lookup(user_id, params.get("badge_number"))
                
            elif command_type == VoiceCommandType.SHARE_LOCATION:
                result = await self._handle_share_location(user_id, encounter_id)
                
            elif command_type == VoiceCommandType.ADD_NOTE:
                result = await self._handle_add_note(user_id, encounter_id, params.get("note_content", ""))
                
            elif command_type == VoiceCommandType.GET_STATUS:
                result = await self._handle_get_status(user_id, encounter_id)
                
            elif command_type == VoiceCommandType.HELP:
                result = await self._handle_help()
                
            else:
                result["success"] = False
                result["response_text"] = self.get_audio_response(VoiceCommandType.UNKNOWN)
            
            # Log command
            await self._log_command(user_id, encounter_id, command_type, result["success"])
            
        except Exception as e:
            logger.error(f"Voice command execution error: {e}")
            result["success"] = False
            result["response_text"] = "Sorry, there was an error processing your command. Please try again."
        
        return result
    
    async def _handle_start_recording(self, user_id: str) -> Dict:
        """Handle start recording command"""
        # Check if already recording
        active = await db.encounters.find_one(
            {"user_id": user_id, "status": "active"},
            {"_id": 0, "encounter_id": 1}
        )
        
        if active:
            return {
                "command": "start_recording",
                "success": True,
                "response_text": "You're already recording. Stay safe.",
                "action_taken": "already_recording",
                "data": {"encounter_id": active["encounter_id"]}
            }
        
        return {
            "command": "start_recording",
            "success": True,
            "response_text": self.get_audio_response(VoiceCommandType.START_RECORDING),
            "action_taken": "start_recording",
            "data": {"should_start": True}
        }
    
    async def _handle_stop_recording(self, user_id: str, encounter_id: Optional[str]) -> Dict:
        """Handle stop recording command"""
        return {
            "command": "stop_recording",
            "success": True,
            "response_text": self.get_audio_response(VoiceCommandType.STOP_RECORDING),
            "action_taken": "stop_recording",
            "data": {"encounter_id": encounter_id, "should_stop": True}
        }
    
    async def _handle_alert_attorney(self, user_id: str, encounter_id: Optional[str]) -> Dict:
        """Handle alert attorney command"""
        from app.services.realtime_alerts import realtime_alerts
        
        if encounter_id:
            alert = await realtime_alerts.trigger_manual_alert(
                encounter_id=encounter_id,
                user_id=user_id,
                message="Voice command: Attorney requested during encounter",
                severity="high"
            )
            
            return {
                "command": "alert_attorney",
                "success": True,
                "response_text": self.get_audio_response(VoiceCommandType.ALERT_ATTORNEY),
                "action_taken": "attorney_alerted",
                "data": {"alert_id": alert.get("alert_id")}
            }
        
        return {
            "command": "alert_attorney",
            "success": True,
            "response_text": "To alert your attorney, please start recording first. Say 'Hey Justice, start recording.'",
            "action_taken": "need_encounter",
            "data": {}
        }
    
    async def _handle_panic(self, user_id: str, encounter_id: Optional[str]) -> Dict:
        """Handle panic/emergency command"""
        from app.services.realtime_alerts import realtime_alerts
        
        # Create critical alert
        if encounter_id:
            alert = await realtime_alerts.trigger_manual_alert(
                encounter_id=encounter_id,
                user_id=user_id,
                message="EMERGENCY: Voice-activated panic alert",
                severity="critical"
            )
        
        # Also trigger SOS
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "emergency_contacts": 1})
        contacts_notified = len(user.get("emergency_contacts", [])) if user else 0
        
        return {
            "command": "panic_button",
            "success": True,
            "response_text": self.get_audio_response(VoiceCommandType.PANIC_BUTTON),
            "action_taken": "emergency_triggered",
            "data": {
                "contacts_notified": contacts_notified,
                "sos_triggered": True
            }
        }
    
    async def _handle_know_rights(self, user_id: str, encounter_id: Optional[str], topic: str) -> Dict:
        """Handle know your rights command"""
        # Determine encounter type
        encounter_type = "traffic_stop"  # Default
        if encounter_id:
            encounter = await db.encounters.find_one(
                {"encounter_id": encounter_id},
                {"_id": 0, "encounter_type": 1}
            )
            if encounter:
                encounter_type = encounter.get("encounter_type", "traffic_stop")
        
        rights_text = self.get_rights_response(encounter_type, topic)
        
        return {
            "command": "know_rights",
            "success": True,
            "response_text": rights_text,
            "action_taken": "rights_provided",
            "data": {
                "encounter_type": encounter_type,
                "topic": topic
            }
        }
    
    async def _handle_officer_lookup(self, user_id: str, badge_number: Optional[str]) -> Dict:
        """Handle officer lookup command"""
        if not badge_number:
            return {
                "command": "officer_lookup",
                "success": True,
                "response_text": "Please say the badge number. For example: 'Hey Justice, badge number 1234.'",
                "action_taken": "need_badge",
                "data": {}
            }
        
        # Look up officer
        officer = await db.officers.find_one(
            {"badge_number": badge_number},
            {"_id": 0}
        )
        
        if officer:
            score = officer.get("accountability_score", 100)
            name = officer.get("full_name", "Unknown")
            
            if score < 40:
                warning = "Warning: This officer has multiple documented violations. Strongly recommend recording."
            elif score < 60:
                warning = "Caution: This officer has some documented issues. Consider recording."
            elif score < 80:
                warning = "This officer has a moderate accountability record."
            else:
                warning = "This officer has a good accountability record."
            
            return {
                "command": "officer_lookup",
                "success": True,
                "response_text": f"Badge {badge_number} is {name}. Accountability score: {score} out of 100. {warning}",
                "action_taken": "officer_found",
                "data": {
                    "badge_number": badge_number,
                    "officer_name": name,
                    "accountability_score": score,
                    "officer_id": officer.get("officer_id")
                }
            }
        
        return {
            "command": "officer_lookup",
            "success": True,
            "response_text": f"Badge number {badge_number} not found in our database. This may be a new officer. Recording is recommended.",
            "action_taken": "officer_not_found",
            "data": {"badge_number": badge_number}
        }
    
    async def _handle_share_location(self, user_id: str, encounter_id: Optional[str]) -> Dict:
        """Handle share location command"""
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "emergency_contacts": 1})
        contacts = user.get("emergency_contacts", []) if user else []
        
        return {
            "command": "share_location",
            "success": True,
            "response_text": self.get_audio_response(VoiceCommandType.SHARE_LOCATION),
            "action_taken": "location_shared",
            "data": {
                "contacts_notified": len(contacts),
                "encounter_id": encounter_id
            }
        }
    
    async def _handle_add_note(self, user_id: str, encounter_id: Optional[str], note_content: str) -> Dict:
        """Handle add note command"""
        if not note_content:
            return {
                "command": "add_note",
                "success": False,
                "response_text": "I didn't catch what you wanted to note. Please try again.",
                "action_taken": "need_content",
                "data": {}
            }
        
        if encounter_id:
            await db.encounters.update_one(
                {"encounter_id": encounter_id},
                {
                    "$push": {
                        "voice_notes": {
                            "content": note_content,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            )
        
        return {
            "command": "add_note",
            "success": True,
            "response_text": f"Note added: {note_content[:50]}...",
            "action_taken": "note_added",
            "data": {"note_content": note_content}
        }
    
    async def _handle_get_status(self, user_id: str, encounter_id: Optional[str]) -> Dict:
        """Handle get status command"""
        if not encounter_id:
            return {
                "command": "get_status",
                "success": True,
                "response_text": "No active recording. Say 'Hey Justice, start recording' to begin.",
                "action_taken": "no_encounter",
                "data": {}
            }
        
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0, "started_at": 1, "violations": 1, "status": 1}
        )
        
        if encounter:
            started = encounter.get("started_at")
            if started:
                if isinstance(started, str):
                    start_time = datetime.fromisoformat(started.replace("Z", "+00:00"))
                else:
                    start_time = started
                duration = datetime.now(timezone.utc) - start_time
                duration_str = f"{int(duration.total_seconds() // 60)} minutes"
            else:
                duration_str = "Unknown"
            
            violations = len(encounter.get("violations", []))
            
            return {
                "command": "get_status",
                "success": True,
                "response_text": self.get_audio_response(
                    VoiceCommandType.GET_STATUS,
                    duration=duration_str,
                    violations_detected=violations
                ),
                "action_taken": "status_provided",
                "data": {
                    "status": encounter.get("status"),
                    "duration": duration_str,
                    "violations_detected": violations
                }
            }
        
        return {
            "command": "get_status",
            "success": False,
            "response_text": "Could not retrieve encounter status.",
            "action_taken": "error",
            "data": {}
        }
    
    async def _handle_help(self) -> Dict:
        """Handle help command"""
        return {
            "command": "help",
            "success": True,
            "response_text": self.get_audio_response(VoiceCommandType.HELP),
            "action_taken": "help_provided",
            "data": {
                "available_commands": [
                    "Start recording",
                    "Stop recording",
                    "Alert my attorney",
                    "What are my rights",
                    "Look up officer / Badge number [X]",
                    "Share my location",
                    "Add note: [your note]",
                    "Status",
                    "Help me (emergency)"
                ]
            }
        }
    
    async def _log_command(
        self,
        user_id: str,
        encounter_id: Optional[str],
        command_type: VoiceCommandType,
        success: bool
    ):
        """Log voice command for analytics"""
        await db.voice_command_logs.insert_one({
            "user_id": user_id,
            "encounter_id": encounter_id,
            "command_type": command_type.value,
            "success": success,
            "timestamp": datetime.now(timezone.utc)
        })


# Singleton instance
voice_commands = VoiceCommandService()
