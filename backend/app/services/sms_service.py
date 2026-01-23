"""
SMS Service - Send SMS alerts via Twilio
"""
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")


def is_twilio_configured() -> bool:
    """Check if Twilio is properly configured"""
    return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER])


async def send_sms(
    to_number: str,
    message: str,
    from_number: Optional[str] = None
) -> Dict:
    """
    Send an SMS message via Twilio.
    
    Args:
        to_number: Recipient phone number in E.164 format (+1234567890)
        message: Message content (max 1600 chars for concatenated SMS)
        from_number: Optional sender number (defaults to TWILIO_PHONE_NUMBER)
    
    Returns:
        Dict with success status, message_sid, and any errors
    """
    if not is_twilio_configured():
        logger.warning("Twilio not configured - SMS not sent")
        return {
            "success": False,
            "error": "Twilio not configured",
            "configured": False
        }
    
    # Validate phone number format
    if not to_number or not to_number.startswith("+"):
        return {
            "success": False,
            "error": "Invalid phone number format. Must be E.164 format (+1234567890)"
        }
    
    try:
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        sms = client.messages.create(
            body=message[:1600],  # Truncate to max SMS length
            from_=from_number or TWILIO_PHONE_NUMBER,
            to=to_number
        )
        
        logger.info(f"SMS sent to {to_number}: {sms.sid}")
        
        return {
            "success": True,
            "message_sid": sms.sid,
            "status": sms.status,
            "to": to_number
        }
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {e}")
        return {
            "success": False,
            "error": str(e),
            "to": to_number
        }


async def send_sos_alert_sms(
    to_number: str,
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict:
    """
    Send an SOS alert SMS to an emergency contact.
    
    Args:
        to_number: Recipient phone number
        user_name: Name of the person in distress
        location_address: Human-readable address
        share_url: URL to watch the live encounter
        latitude: Optional GPS latitude
        longitude: Optional GPS longitude
    
    Returns:
        Dict with send result
    """
    # Build Google Maps link if coordinates available
    maps_link = ""
    if latitude and longitude:
        maps_link = f"\n📍 Map: https://maps.google.com/?q={latitude},{longitude}"
    
    message = f"""🚨 EMERGENCY SOS ALERT 🚨

{user_name} is in a police encounter and needs help!

Location: {location_address}{maps_link}

Watch Live: {share_url}

This is an automated alert from JUSTICE - Civil Rights Defense System."""

    return await send_sms(to_number, message)


async def send_dead_mans_switch_sms(
    to_number: str,
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict:
    """
    Send a Dead Man's Switch alert SMS to an emergency contact.
    """
    maps_link = ""
    if latitude and longitude:
        maps_link = f"\n📍 Map: https://maps.google.com/?q={latitude},{longitude}"
    
    message = f"""⚠️ DEAD MAN'S SWITCH TRIGGERED ⚠️

{user_name} has become unresponsive during a police encounter!

Location: {location_address}{maps_link}

Watch Live: {share_url}

Please check on them immediately!

- JUSTICE Civil Rights Defense System"""

    return await send_sms(to_number, message)


async def send_witness_alert_sms(
    to_number: str,
    user_name: str,
    distance_miles: float,
    share_url: str
) -> Dict:
    """
    Send a witness alert SMS.
    """
    message = f"""👁️ WITNESS ALERT

{user_name} has started a police encounter {distance_miles} miles from your location.

Watch Live: {share_url}

Your presence as a witness can help protect civil rights.

- JUSTICE Witness Network"""

    return await send_sms(to_number, message)


async def send_bulk_sms(
    recipients: List[Dict],
    message_template: str,
    template_vars: Dict
) -> Dict:
    """
    Send SMS to multiple recipients.
    
    Args:
        recipients: List of dicts with 'phone' and 'name' keys
        message_template: Message with {placeholders}
        template_vars: Variables to substitute in template
    
    Returns:
        Dict with results summary
    """
    results = {
        "total": len(recipients),
        "sent": 0,
        "failed": 0,
        "details": []
    }
    
    for recipient in recipients:
        phone = recipient.get("phone")
        if not phone:
            results["failed"] += 1
            results["details"].append({
                "name": recipient.get("name"),
                "error": "No phone number"
            })
            continue
        
        # Personalize message
        vars_with_name = {**template_vars, "recipient_name": recipient.get("name", "Friend")}
        try:
            message = message_template.format(**vars_with_name)
        except KeyError:
            message = message_template
        
        result = await send_sms(phone, message)
        
        if result.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "name": recipient.get("name"),
            "phone": phone,
            **result
        })
    
    return results
