"""
Subscription Service

Manages user subscription tiers and premium features.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# Feature access by tier
TIER_FEATURES = {
    SubscriptionTier.FREE: {
        "max_encounters_per_month": 5,
        "max_storage_mb": 500,
        "ai_analysis": True,
        "voice_commands": True,
        "emergency_sos": True,
        "evidence_export": True,
        "blockchain_anchoring": False,
        "premium_analytics": False,
        "attorney_streaming": False,
        "multi_cloud_backup": False,
        "3d_reconstruction": False,
        "class_action_finder": False,
        "priority_support": False,
    },
    SubscriptionTier.BASIC: {
        "max_encounters_per_month": 20,
        "max_storage_mb": 2000,
        "ai_analysis": True,
        "voice_commands": True,
        "emergency_sos": True,
        "evidence_export": True,
        "blockchain_anchoring": False,
        "premium_analytics": True,
        "attorney_streaming": True,
        "multi_cloud_backup": False,
        "3d_reconstruction": True,
        "class_action_finder": False,
        "priority_support": False,
    },
    SubscriptionTier.PREMIUM: {
        "max_encounters_per_month": 100,
        "max_storage_mb": 10000,
        "ai_analysis": True,
        "voice_commands": True,
        "emergency_sos": True,
        "evidence_export": True,
        "blockchain_anchoring": True,  # Premium feature!
        "premium_analytics": True,
        "attorney_streaming": True,
        "multi_cloud_backup": True,
        "3d_reconstruction": True,
        "class_action_finder": True,
        "priority_support": True,
    },
    SubscriptionTier.ENTERPRISE: {
        "max_encounters_per_month": -1,  # Unlimited
        "max_storage_mb": -1,  # Unlimited
        "ai_analysis": True,
        "voice_commands": True,
        "emergency_sos": True,
        "evidence_export": True,
        "blockchain_anchoring": True,
        "premium_analytics": True,
        "attorney_streaming": True,
        "multi_cloud_backup": True,
        "3d_reconstruction": True,
        "class_action_finder": True,
        "priority_support": True,
        "custom_integrations": True,
        "dedicated_support": True,
    }
}


# Pricing (monthly)
TIER_PRICING = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.BASIC: 9.99,
    SubscriptionTier.PREMIUM: 29.99,
    SubscriptionTier.ENTERPRISE: 99.99,
}


class SubscriptionService:
    """Service for managing user subscriptions"""
    
    def __init__(self, db):
        self.db = db
        self.users = db.users
        self.subscriptions = db.subscriptions
    
    async def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Get the user's current subscription tier"""
        user = await self.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return SubscriptionTier.FREE
        
        tier = user.get("subscription_tier", "free")
        try:
            return SubscriptionTier(tier)
        except ValueError:
            return SubscriptionTier.FREE
    
    async def get_user_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get full subscription details for a user"""
        tier = await self.get_user_tier(user_id)
        features = TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])
        
        # Get subscription record if exists
        subscription = await self.subscriptions.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        return {
            "tier": tier.value,
            "tier_name": tier.value.title(),
            "features": features,
            "price_monthly": TIER_PRICING.get(tier, 0),
            "subscription_active": subscription.get("active", True) if subscription else True,
            "expires_at": subscription.get("expires_at") if subscription else None,
            "created_at": subscription.get("created_at") if subscription else None
        }
    
    async def check_feature_access(self, user_id: str, feature: str) -> Dict[str, Any]:
        """Check if user has access to a specific feature"""
        tier = await self.get_user_tier(user_id)
        features = TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])
        
        has_access = features.get(feature, False)
        
        # Find which tier unlocks this feature
        required_tier = None
        for t, f in TIER_FEATURES.items():
            if f.get(feature, False):
                required_tier = t
                break
        
        return {
            "feature": feature,
            "has_access": has_access,
            "current_tier": tier.value,
            "required_tier": required_tier.value if required_tier else None,
            "upgrade_required": not has_access
        }
    
    async def upgrade_user_tier(
        self, 
        user_id: str, 
        new_tier: SubscriptionTier,
        payment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upgrade a user's subscription tier"""
        now = datetime.now(timezone.utc)
        
        # Update user record
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"subscription_tier": new_tier.value}}
        )
        
        # Create/update subscription record
        subscription_data = {
            "user_id": user_id,
            "tier": new_tier.value,
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "payment_id": payment_id
        }
        
        await self.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": subscription_data},
            upsert=True
        )
        
        return {
            "success": True,
            "new_tier": new_tier.value,
            "features": TIER_FEATURES.get(new_tier, {})
        }
    
    async def get_all_tiers(self) -> List[Dict[str, Any]]:
        """Get all available subscription tiers with features"""
        tiers = []
        for tier in SubscriptionTier:
            tiers.append({
                "tier": tier.value,
                "name": tier.value.title(),
                "price_monthly": TIER_PRICING.get(tier, 0),
                "features": TIER_FEATURES.get(tier, {}),
                "popular": tier == SubscriptionTier.PREMIUM
            })
        return tiers


# Singleton instance
_subscription_service = None


def get_subscription_service(db) -> SubscriptionService:
    """Get the subscription service instance"""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService(db)
    return _subscription_service
