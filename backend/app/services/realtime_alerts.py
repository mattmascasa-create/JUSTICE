"""
Real-Time Violation Alert Service - Automatic attorney notifications during live encounters
"""
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from app.db.database import db
from app.services.websocket import manager as ws_manager

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"    # Immediate action required (excessive force, weapons drawn)
    HIGH = "high"            # Serious violation detected
    MEDIUM = "medium"        # Potential violation
    LOW = "low"              # Minor concern or pattern emerging


class AlertType(Enum):
    """Types of real-time alerts"""
    VIOLATION_DETECTED = "violation_detected"
    OFFICER_IDENTIFIED = "officer_identified"
    ESCALATION_WARNING = "escalation_warning"
    RIGHTS_VIOLATION = "rights_violation"
    RECORDING_ISSUE = "recording_issue"
    WITNESS_ALERT = "witness_alert"
    PANIC_BUTTON = "panic_button"
    ATTORNEY_NEEDED = "attorney_needed"


# Keywords that trigger immediate alerts
CRITICAL_KEYWORDS = {
    "excessive_force": ["taser", "tased", "pepper spray", "choking", "can't breathe", "stop hitting", 
                        "gun drawn", "weapon", "beating", "excessive", "brutality"],
    "miranda_violation": ["you have the right to remain silent", "anything you say can", 
                          "right to an attorney", "miranda"],
    "unlawful_search": ["search your car", "search your bag", "empty your pockets", 
                        "pat down", "frisk", "consent to search"],
    "detention": ["you're detained", "under arrest", "not free to go", "stop right there",
                  "hands up", "get on the ground", "don't move"],
    "first_amendment": ["stop recording", "turn that off", "put the phone down", "no filming",
                        "delete that", "hand over your phone"],
    "racial_profiling": ["you people", "your kind", "suspicious looking", "fit the description"]
}


class RealTimeAlertService:
    """
    Service for detecting and sending real-time violation alerts to attorneys
    during active police encounters.
    """
    
    def __init__(self):
        self.active_encounter_alerts: Dict[str, List[Dict]] = {}  # encounter_id -> alerts
        
    async def analyze_transcript_chunk(
        self,
        encounter_id: str,
        transcript_chunk: str,
        user_id: str,
        timestamp: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze a chunk of transcript in real-time for potential violations.
        Returns list of alerts that should be sent.
        """
        alerts = []
        chunk_lower = transcript_chunk.lower()
        
        # Check for critical keywords
        for violation_type, keywords in CRITICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in chunk_lower:
                    alert = await self._create_alert(
                        encounter_id=encounter_id,
                        user_id=user_id,
                        alert_type=AlertType.VIOLATION_DETECTED,
                        severity=self._get_severity_for_violation(violation_type),
                        violation_type=violation_type,
                        trigger_text=transcript_chunk,
                        trigger_keyword=keyword,
                        timestamp=timestamp or datetime.now(timezone.utc).isoformat()
                    )
                    alerts.append(alert)
                    break  # One alert per violation type per chunk
        
        # Check for escalation patterns
        if self._detect_escalation(chunk_lower):
            alert = await self._create_alert(
                encounter_id=encounter_id,
                user_id=user_id,
                alert_type=AlertType.ESCALATION_WARNING,
                severity=AlertSeverity.HIGH,
                violation_type="escalation",
                trigger_text=transcript_chunk,
                timestamp=timestamp or datetime.now(timezone.utc).isoformat()
            )
            alerts.append(alert)
        
        # Send alerts to connected attorneys
        if alerts:
            await self._broadcast_alerts(encounter_id, user_id, alerts)
        
        return alerts
    
    def _get_severity_for_violation(self, violation_type: str) -> AlertSeverity:
        """Map violation types to severity levels"""
        severity_map = {
            "excessive_force": AlertSeverity.CRITICAL,
            "miranda_violation": AlertSeverity.HIGH,
            "unlawful_search": AlertSeverity.HIGH,
            "detention": AlertSeverity.MEDIUM,
            "first_amendment": AlertSeverity.HIGH,
            "racial_profiling": AlertSeverity.HIGH
        }
        return severity_map.get(violation_type, AlertSeverity.MEDIUM)
    
    def _detect_escalation(self, text: str) -> bool:
        """Detect signs of situation escalation"""
        escalation_phrases = [
            "back up requested", "calling for backup", "resisting",
            "stop resisting", "get down", "on your knees",
            "don't make me", "last warning", "force will be used",
            "going to tase you", "reaching for", "screaming", "yelling"
        ]
        return any(phrase in text for phrase in escalation_phrases)
    
    async def _create_alert(
        self,
        encounter_id: str,
        user_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        violation_type: str,
        trigger_text: str,
        trigger_keyword: str = None,
        timestamp: str = None
    ) -> Dict:
        """Create and store an alert"""
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        
        alert = {
            "alert_id": alert_id,
            "encounter_id": encounter_id,
            "user_id": user_id,
            "alert_type": alert_type.value,
            "severity": severity.value,
            "violation_type": violation_type,
            "trigger_text": trigger_text[:500],  # Limit text length
            "trigger_keyword": trigger_keyword,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None
        }
        
        # Get user's linked attorney if any
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "linked_attorney_id": 1, "full_name": 1})
        if user:
            alert["citizen_name"] = user.get("full_name", "Unknown")
            alert["attorney_id"] = user.get("linked_attorney_id")
        
        # Store in database (copy to avoid _id mutation)
        await db.realtime_alerts.insert_one({**alert})
        
        # Track in active encounter alerts
        if encounter_id not in self.active_encounter_alerts:
            self.active_encounter_alerts[encounter_id] = []
        self.active_encounter_alerts[encounter_id].append(alert)
        
        return alert
    
    async def _broadcast_alerts(self, encounter_id: str, user_id: str, alerts: List[Dict]):
        """Send alerts via WebSocket and optionally email"""
        # Get encounter details
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0, "location": 1, "encounter_type": 1, "detected_officers": 1}
        )
        
        # Get user's linked attorneys
        user = await db.users.find_one(
            {"user_id": user_id},
            {"_id": 0, "linked_attorney_id": 1, "emergency_contacts": 1, "full_name": 1}
        )
        
        for alert in alerts:
            # Enrich alert with encounter details
            alert["encounter_location"] = encounter.get("location") if encounter else None
            alert["encounter_type"] = encounter.get("encounter_type") if encounter else None
            alert["detected_officers"] = encounter.get("detected_officers", []) if encounter else []
            
            # Send to citizen (the user recording)
            await ws_manager.send_to_user(user_id, {
                "type": "violation_alert",
                "alert": alert
            })
            
            # Send to linked attorney via WebSocket
            if user and user.get("linked_attorney_id"):
                attorney_id = user["linked_attorney_id"]
                await ws_manager.send_to_user(attorney_id, {
                    "type": "client_violation_alert",
                    "client_name": user.get("full_name", "Your client"),
                    "alert": alert
                })
                
                # For critical alerts, also send email
                if alert["severity"] == "critical":
                    await self._send_attorney_email_alert(attorney_id, user, alert, encounter)
            
            # Broadcast to encounter viewers (attorneys watching shared encounter)
            await self._notify_encounter_viewers(encounter_id, alert)
    
    async def _notify_encounter_viewers(self, encounter_id: str, alert: Dict):
        """Notify all attorneys viewing this encounter"""
        if encounter_id in ws_manager.encounter_viewers:
            message = {
                "type": "live_violation_alert",
                "alert": alert
            }
            for ws in ws_manager.encounter_viewers[encounter_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass
    
    async def _send_attorney_email_alert(
        self,
        attorney_id: str,
        user: Dict,
        alert: Dict,
        encounter: Dict
    ):
        """Send email alert to attorney for critical violations"""
        try:
            from app.services.email_service import send_simple_email
            
            attorney = await db.users.find_one(
                {"user_id": attorney_id},
                {"_id": 0, "email": 1, "full_name": 1}
            )
            
            if not attorney or not attorney.get("email"):
                return
            
            location = encounter.get("location", {}) if encounter else {}
            location_str = f"{location.get('address', 'Unknown location')}" if location else "Unknown location"
            
            subject = f"🚨 CRITICAL: Civil Rights Violation Alert - {user.get('full_name', 'Your Client')}"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #dc2626; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">⚠️ CRITICAL VIOLATION ALERT</h1>
                </div>
                
                <div style="padding: 20px; background: #fef2f2; border: 2px solid #dc2626;">
                    <h2 style="color: #dc2626; margin-top: 0;">Immediate Attorney Attention Required</h2>
                    
                    <p><strong>Client:</strong> {user.get('full_name', 'Unknown')}</p>
                    <p><strong>Time:</strong> {alert['timestamp']}</p>
                    <p><strong>Location:</strong> {location_str}</p>
                    
                    <div style="background: white; padding: 15px; border-left: 4px solid #dc2626; margin: 15px 0;">
                        <p style="margin: 0;"><strong>Violation Type:</strong> {alert['violation_type'].replace('_', ' ').title()}</p>
                        <p style="margin: 10px 0 0;"><strong>Trigger:</strong> "{alert.get('trigger_keyword', 'N/A')}"</p>
                    </div>
                    
                    <div style="background: #fee2e2; padding: 15px; border-radius: 8px;">
                        <p style="margin: 0; font-style: italic;">"{alert.get('trigger_text', 'N/A')}"</p>
                    </div>
                </div>
                
                <div style="padding: 20px; background: #f3f4f6;">
                    <p style="margin: 0;">
                        <a href="{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/attorney/live/{alert['encounter_id']}" 
                           style="background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                            View Live Encounter
                        </a>
                    </p>
                    <p style="margin: 15px 0 0; font-size: 12px; color: #6b7280;">
                        This alert was automatically generated by the JUSTICE Platform violation detection system.
                    </p>
                </div>
            </body>
            </html>
            """
            
            await send_simple_email(
                to_email=attorney["email"],
                subject=subject,
                body_html=body
            )
            
            logger.info(f"Critical alert email sent to attorney {attorney_id}")
            
        except Exception as e:
            logger.error(f"Failed to send attorney email alert: {e}")
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Mark an alert as acknowledged by attorney"""
        result = await db.realtime_alerts.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_by": user_id,
                    "acknowledged_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return result.modified_count > 0
    
    async def get_encounter_alerts(self, encounter_id: str) -> List[Dict]:
        """Get all alerts for an encounter"""
        alerts = await db.realtime_alerts.find(
            {"encounter_id": encounter_id},
            {"_id": 0}
        ).sort("timestamp", -1).to_list(100)
        return alerts
    
    async def get_user_alerts(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get alerts for a user (citizen or attorney)"""
        # Check if user is an attorney
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "role": 1})
        
        if user and user.get("role") == "attorney":
            # Get alerts for all linked clients
            alerts = await db.realtime_alerts.find(
                {"attorney_id": user_id},
                {"_id": 0}
            ).sort("timestamp", -1).to_list(limit)
        else:
            # Get alerts for this user's encounters
            alerts = await db.realtime_alerts.find(
                {"user_id": user_id},
                {"_id": 0}
            ).sort("timestamp", -1).to_list(limit)
        
        return alerts
    
    async def get_unacknowledged_alerts(self, attorney_id: str) -> List[Dict]:
        """Get unacknowledged alerts for an attorney"""
        alerts = await db.realtime_alerts.find(
            {
                "attorney_id": attorney_id,
                "acknowledged": False
            },
            {"_id": 0}
        ).sort("timestamp", -1).to_list(100)
        return alerts
    
    async def trigger_manual_alert(
        self,
        encounter_id: str,
        user_id: str,
        message: str,
        severity: str = "high"
    ) -> Dict:
        """Allow user to manually trigger an alert (panic/attorney needed)"""
        severity_enum = AlertSeverity[severity.upper()] if severity.upper() in AlertSeverity.__members__ else AlertSeverity.HIGH
        
        alert = await self._create_alert(
            encounter_id=encounter_id,
            user_id=user_id,
            alert_type=AlertType.ATTORNEY_NEEDED,
            severity=severity_enum,
            violation_type="manual_alert",
            trigger_text=message,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Broadcast immediately
        await self._broadcast_alerts(encounter_id, user_id, [alert])
        
        return alert


# Singleton instance
realtime_alerts = RealTimeAlertService()
