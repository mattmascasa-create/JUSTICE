"""
Health Router - API health check endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from app.core.config import IPFS_ENABLED, S3_ENABLED, TWILIO_ENABLED, SENDGRID_ENABLED

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Check API health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.9.0",
        "ipfs_enabled": IPFS_ENABLED,
        "s3_enabled": S3_ENABLED,
        "sms_enabled": TWILIO_ENABLED,
        "email_enabled": SENDGRID_ENABLED,
        "features": {
            "real_time_sharing": True,
            "live_guidance": True,
            "video_streaming": True,
            "screen_recording": True,
            "ai_evidence_highlights": True,
            "export_highlights_report": True,
            "sms_alerts": TWILIO_ENABLED,
            "email_alerts": SENDGRID_ENABLED,
            "ai_rights_coach": True,
            "dead_mans_switch": True,
            "witness_network": True
        }
    }
