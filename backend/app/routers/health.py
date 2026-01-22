"""
Health Router - API health check endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from app.core.config import IPFS_ENABLED, S3_ENABLED

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Check API health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.5.0",
        "ipfs_enabled": IPFS_ENABLED,
        "s3_enabled": S3_ENABLED,
        "features": {
            "real_time_sharing": True,
            "live_guidance": True,
            "video_streaming": True,
            "screen_recording": True
        }
    }
