"""
Push Notification Service - Web Push API integration
"""
import os
import json
import logging
from typing import Optional
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

# VAPID configuration
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY_FILE = os.environ.get("VAPID_PRIVATE_KEY_FILE", "/app/backend/private_key.pem")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@justice-platform.com")


def get_vapid_claims():
    """Get VAPID claims for push notifications"""
    return {
        "sub": f"mailto:{VAPID_CLAIMS_EMAIL}"
    }


async def send_push_notification(
    subscription_info: dict,
    title: str,
    body: str,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    url: Optional[str] = None,
    tag: Optional[str] = None,
    data: Optional[dict] = None
) -> bool:
    """
    Send a push notification to a subscriber.
    
    Args:
        subscription_info: The push subscription object from the browser
        title: Notification title
        body: Notification body text
        icon: URL to notification icon
        badge: URL to badge icon (small icon for Android)
        url: URL to open when notification is clicked
        tag: Tag for notification grouping
        data: Additional data to include
    
    Returns:
        True if successful, False otherwise
    """
    if not VAPID_PUBLIC_KEY or not os.path.exists(VAPID_PRIVATE_KEY_FILE):
        logger.warning("VAPID keys not configured, skipping push notification")
        return False
    
    try:
        # Build notification payload
        payload = {
            "title": title,
            "body": body,
            "icon": icon or "/logo192.png",
            "badge": badge or "/badge-72x72.png",
            "tag": tag,
            "data": {
                "url": url or "/",
                **(data or {})
            },
            "requireInteraction": False,
            "silent": False
        }
        
        # Send the push notification
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY_FILE,
            vapid_claims=get_vapid_claims()
        )
        
        logger.info(f"Push notification sent: {title}")
        return True
        
    except WebPushException as e:
        logger.error(f"Push notification failed: {e}")
        # If subscription is invalid/expired, return False so caller can remove it
        if e.response and e.response.status_code in [404, 410]:
            logger.info("Subscription expired or invalid")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push: {e}")
        return False


async def send_push_to_user(db, user_id: str, title: str, body: str, **kwargs) -> int:
    """
    Send push notification to all subscriptions for a user.
    
    Returns:
        Number of successful notifications sent
    """
    # Get all push subscriptions for the user
    subscriptions = await db.push_subscriptions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    if not subscriptions:
        logger.debug(f"No push subscriptions for user {user_id}")
        return 0
    
    success_count = 0
    expired_ids = []
    
    for sub in subscriptions:
        subscription_info = sub.get("subscription")
        if not subscription_info:
            continue
            
        success = await send_push_notification(
            subscription_info=subscription_info,
            title=title,
            body=body,
            **kwargs
        )
        
        if success:
            success_count += 1
        else:
            # Mark for removal if subscription is invalid
            expired_ids.append(sub.get("subscription_id"))
    
    # Remove expired subscriptions
    if expired_ids:
        await db.push_subscriptions.delete_many({
            "subscription_id": {"$in": expired_ids}
        })
        logger.info(f"Removed {len(expired_ids)} expired push subscriptions")
    
    return success_count
