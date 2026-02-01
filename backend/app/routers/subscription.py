"""
Subscription Router

API endpoints for managing user subscriptions and premium features.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.database import db
from app.core.security import get_current_user
from app.services.subscription import (
    get_subscription_service, 
    SubscriptionTier,
    TIER_FEATURES,
    TIER_PRICING
)


router = APIRouter(prefix="/subscription", tags=["Subscription"])


class UpgradeRequest(BaseModel):
    tier: str
    payment_id: Optional[str] = None


@router.get("/tiers")
async def get_available_tiers():
    """
    Get all available subscription tiers with features and pricing.
    Public endpoint - no authentication required.
    """
    service = get_subscription_service(db)
    tiers = await service.get_all_tiers()
    
    return {
        "success": True,
        "tiers": tiers
    }


@router.get("/current")
async def get_current_subscription(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current user's subscription details.
    """
    service = get_subscription_service(db)
    subscription = await service.get_user_subscription(current_user["user_id"])
    
    return {
        "success": True,
        "subscription": subscription
    }


@router.get("/feature/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if the current user has access to a specific feature.
    """
    service = get_subscription_service(db)
    access = await service.check_feature_access(current_user["user_id"], feature_name)
    
    return {
        "success": True,
        **access
    }


@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Upgrade the user's subscription tier.
    In production, this would integrate with a payment processor.
    """
    try:
        new_tier = SubscriptionTier(request.tier)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid tier: {request.tier}. Valid tiers: free, basic, premium, enterprise"
        )
    
    service = get_subscription_service(db)
    
    # Get current tier
    current_tier = await service.get_user_tier(current_user["user_id"])
    
    # Check if downgrade (not allowed through this endpoint)
    tier_order = [SubscriptionTier.FREE, SubscriptionTier.BASIC, SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE]
    if tier_order.index(new_tier) < tier_order.index(current_tier):
        raise HTTPException(
            status_code=400,
            detail="Downgrades must be processed through support"
        )
    
    # Process upgrade
    result = await service.upgrade_user_tier(
        current_user["user_id"],
        new_tier,
        request.payment_id
    )
    
    return {
        "success": True,
        "message": f"Successfully upgraded to {new_tier.value} tier",
        **result
    }


@router.get("/features")
async def get_feature_list(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of all features with the user's access status.
    """
    service = get_subscription_service(db)
    current_tier = await service.get_user_tier(current_user["user_id"])
    current_features = TIER_FEATURES.get(current_tier, {})
    
    # Build feature list with access info
    features = []
    for feature_name in TIER_FEATURES[SubscriptionTier.ENTERPRISE].keys():
        # Find which tier first unlocks this feature
        required_tier = None
        for tier in [SubscriptionTier.FREE, SubscriptionTier.BASIC, SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE]:
            if TIER_FEATURES[tier].get(feature_name, False):
                required_tier = tier
                break
        
        features.append({
            "feature": feature_name,
            "name": feature_name.replace("_", " ").title(),
            "has_access": current_features.get(feature_name, False),
            "required_tier": required_tier.value if required_tier else "enterprise",
            "is_premium": required_tier in [SubscriptionTier.PREMIUM, SubscriptionTier.ENTERPRISE] if required_tier else True
        })
    
    return {
        "success": True,
        "current_tier": current_tier.value,
        "features": features
    }


@router.get("/pricing")
async def get_pricing():
    """
    Get subscription pricing information.
    """
    pricing = []
    for tier in SubscriptionTier:
        pricing.append({
            "tier": tier.value,
            "name": tier.value.title(),
            "price_monthly": TIER_PRICING.get(tier, 0),
            "price_yearly": TIER_PRICING.get(tier, 0) * 10,  # 2 months free
            "features_count": sum(1 for v in TIER_FEATURES.get(tier, {}).values() if v is True),
            "popular": tier == SubscriptionTier.PREMIUM
        })
    
    return {
        "success": True,
        "pricing": pricing,
        "currency": "USD"
    }
