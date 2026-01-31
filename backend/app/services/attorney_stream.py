"""
Attorney Live Stream Service
Provides real-time video streaming to attorneys during police encounters
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import secrets
import hashlib

from app.db.database import db

logger = logging.getLogger(__name__)


class AttorneyStreamService:
    """
    Service for managing live video streams from encounters to attorneys.
    Uses WebRTC signaling for peer-to-peer streaming.
    """
    
    # Stream session TTL (4 hours)
    STREAM_TTL_HOURS = 4
    
    async def create_stream_session(
        self,
        encounter_id: str,
        user_id: str,
        attorney_id: Optional[str] = None,
        attorney_email: Optional[str] = None
    ) -> Dict:
        """
        Create a new streaming session for an encounter.
        Generates secure access tokens for both user and attorney.
        """
        
        session_id = f"stream_{uuid.uuid4().hex[:12]}"
        
        # Generate secure access tokens
        user_token = secrets.token_urlsafe(32)
        attorney_token = secrets.token_urlsafe(32)
        
        # Create shareable link
        stream_code = secrets.token_urlsafe(8)
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.STREAM_TTL_HOURS)
        
        session = {
            "session_id": session_id,
            "encounter_id": encounter_id,
            "user_id": user_id,
            "attorney_id": attorney_id,
            "attorney_email": attorney_email,
            "user_token": user_token,
            "attorney_token": attorney_token,
            "stream_code": stream_code,
            "status": "pending",  # pending, active, ended
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "started_at": None,
            "ended_at": None,
            "messages": [],
            "attorney_connected": False,
            "user_connected": False,
            "recording_consent": True,
            "signaling_data": {
                "offers": [],
                "answers": [],
                "ice_candidates": []
            }
        }
        
        await db.attorney_streams.insert_one(session)
        
        # Generate stream URL
        base_url = "https://civil-rights-shield.preview.emergentagent.com"
        stream_url = f"{base_url}/live-stream/{stream_code}"
        
        return {
            "session_id": session_id,
            "stream_code": stream_code,
            "stream_url": stream_url,
            "user_token": user_token,
            "attorney_token": attorney_token,
            "expires_at": expires_at.isoformat(),
            "status": "pending"
        }
    
    async def get_session_by_code(self, stream_code: str) -> Optional[Dict]:
        """Get stream session by shareable code"""
        session = await db.attorney_streams.find_one(
            {"stream_code": stream_code},
            {"_id": 0}
        )
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get stream session by ID"""
        session = await db.attorney_streams.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        return session
    
    async def join_stream(
        self,
        stream_code: str,
        token: str,
        role: str  # "user" or "attorney"
    ) -> Dict:
        """
        Join a streaming session.
        Validates token and updates connection status.
        """
        
        session = await self.get_session_by_code(stream_code)
        
        if not session:
            return {"success": False, "error": "Stream session not found"}
        
        # Check expiration
        expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            return {"success": False, "error": "Stream session has expired"}
        
        # Validate token
        if role == "user":
            if token != session["user_token"]:
                return {"success": False, "error": "Invalid user token"}
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {"user_connected": True, "status": "active"}}
            )
        elif role == "attorney":
            if token != session["attorney_token"]:
                return {"success": False, "error": "Invalid attorney token"}
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$set": {
                    "attorney_connected": True,
                    "status": "active",
                    "started_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            return {"success": False, "error": "Invalid role"}
        
        # Get updated session
        updated_session = await self.get_session_by_code(stream_code)
        
        return {
            "success": True,
            "session_id": updated_session["session_id"],
            "stream_code": stream_code,
            "role": role,
            "status": updated_session["status"],
            "attorney_connected": updated_session["attorney_connected"],
            "user_connected": updated_session["user_connected"],
            "encounter_id": updated_session["encounter_id"]
        }
    
    async def send_signaling_data(
        self,
        stream_code: str,
        signal_type: str,  # "offer", "answer", "ice_candidate"
        data: Dict,
        sender_role: str
    ) -> Dict:
        """Store WebRTC signaling data for peer connection"""
        
        session = await self.get_session_by_code(stream_code)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        signal_entry = {
            "type": signal_type,
            "data": data,
            "sender": sender_role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if signal_type == "offer":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$push": {"signaling_data.offers": signal_entry}}
            )
        elif signal_type == "answer":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$push": {"signaling_data.answers": signal_entry}}
            )
        elif signal_type == "ice_candidate":
            await db.attorney_streams.update_one(
                {"stream_code": stream_code},
                {"$push": {"signaling_data.ice_candidates": signal_entry}}
            )
        
        return {"success": True, "signal_type": signal_type}
    
    async def get_signaling_data(
        self,
        stream_code: str,
        for_role: str
    ) -> Dict:
        """Get pending signaling data for a role"""
        
        session = await self.get_session_by_code(stream_code)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        signaling = session.get("signaling_data", {})
        
        # Return data meant for this role (from the other party)
        other_role = "attorney" if for_role == "user" else "user"
        
        return {
            "success": True,
            "offers": [s for s in signaling.get("offers", []) if s["sender"] == other_role],
            "answers": [s for s in signaling.get("answers", []) if s["sender"] == other_role],
            "ice_candidates": [s for s in signaling.get("ice_candidates", []) if s["sender"] == other_role]
        }
    
    async def send_message(
        self,
        stream_code: str,
        sender_role: str,
        message: str
    ) -> Dict:
        """Send a chat message during the stream"""
        
        session = await self.get_session_by_code(stream_code)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        msg = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "sender": sender_role,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.attorney_streams.update_one(
            {"stream_code": stream_code},
            {"$push": {"messages": msg}}
        )
        
        return {"success": True, "message": msg}
    
    async def get_messages(self, stream_code: str) -> List[Dict]:
        """Get all messages for a stream session"""
        
        session = await self.get_session_by_code(stream_code)
        if not session:
            return []
        
        return session.get("messages", [])
    
    async def end_stream(
        self,
        stream_code: str,
        ended_by: str
    ) -> Dict:
        """End a streaming session"""
        
        session = await self.get_session_by_code(stream_code)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        await db.attorney_streams.update_one(
            {"stream_code": stream_code},
            {"$set": {
                "status": "ended",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "ended_by": ended_by
            }}
        )
        
        return {
            "success": True,
            "session_id": session["session_id"],
            "status": "ended"
        }
    
    async def get_user_streams(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get user's stream history"""
        
        streams = await db.attorney_streams.find(
            {"user_id": user_id},
            {"_id": 0, "user_token": 0, "attorney_token": 0, "signaling_data": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return streams
    
    async def notify_attorney(
        self,
        session: Dict,
        encounter_location: Optional[str] = None,
        notification_method: str = "email"
    ) -> Dict:
        """Send notification to attorney about live stream via configured method"""
        
        from app.core.config import (
            SENDGRID_ENABLED, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL,
            TWILIO_ENABLED, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER,
            FRONTEND_URL
        )
        
        base_url = FRONTEND_URL or "https://civil-rights-shield.preview.emergentagent.com"
        stream_url = f"{base_url}/live-stream/{session['stream_code']}"
        
        notification = {
            "notification_id": f"notif_{uuid.uuid4().hex[:8]}",
            "type": "attorney_stream_invite",
            "attorney_email": session.get("attorney_email"),
            "attorney_id": session.get("attorney_id"),
            "stream_url": stream_url,
            "stream_code": session["stream_code"],
            "attorney_token": session["attorney_token"],
            "encounter_id": session["encounter_id"],
            "location": encounter_location,
            "notification_method": notification_method,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Your client is in a police encounter and has requested your presence via live stream. Join now: {stream_url}",
            "email_sent": False,
            "sms_sent": False
        }
        
        should_send_email = notification_method in ["email", "both"]
        should_send_sms = notification_method in ["sms", "both"]
        
        # Send email notification
        if should_send_email and SENDGRID_ENABLED and session.get("attorney_email"):
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail
                
                sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
                
                message = Mail(
                    from_email=SENDGRID_SENDER_EMAIL or "alerts@justice-app.com",
                    to_emails=session["attorney_email"],
                    subject="🚨 URGENT: Client Requesting Live Stream During Police Encounter",
                    html_content=f"""
                    <h2>Your client needs you NOW</h2>
                    <p>Your client has initiated a live stream during a police encounter and is requesting your presence.</p>
                    <p><strong>Location:</strong> {encounter_location or 'Not provided'}</p>
                    <p><a href="{stream_url}" style="background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">JOIN LIVE STREAM NOW</a></p>
                    <p>Stream Code: {session['stream_code']}</p>
                    <p><small>This link expires in {self.STREAM_TTL_HOURS} hours.</small></p>
                    """
                )
                
                response = sg.send(message)
                notification["email_sent"] = response.status_code == 202
                logger.info(f"Email notification sent to {session['attorney_email']}: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to send attorney notification email: {e}")
                notification["email_sent"] = False
        
        # Send SMS notification
        if should_send_sms and TWILIO_ENABLED:
            try:
                from twilio.rest import Client
                
                # Attorney phone could be stored in user profile or passed separately
                # For now, we'll try to extract from email domain or use a placeholder
                attorney_phone = session.get("attorney_phone")
                
                if attorney_phone:
                    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    
                    sms_body = f"🚨 URGENT: Your client needs you NOW! Police encounter in progress. Location: {encounter_location or 'Unknown'}. Join live stream: {stream_url}"
                    
                    message = client.messages.create(
                        body=sms_body,
                        from_=TWILIO_PHONE_NUMBER,
                        to=attorney_phone
                    )
                    
                    notification["sms_sent"] = message.status in ["queued", "sent"]
                    notification["sms_sid"] = message.sid
                    logger.info(f"SMS notification sent to attorney: {message.status}")
                else:
                    logger.warning("SMS requested but no attorney phone number available")
                    notification["sms_sent"] = False
                    notification["sms_error"] = "No attorney phone number configured"
            except Exception as e:
                logger.error(f"Failed to send attorney SMS notification: {e}")
                notification["sms_sent"] = False
                notification["sms_error"] = str(e)
        
        return notification


# Singleton instance
attorney_stream_service = AttorneyStreamService()
