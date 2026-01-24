"""
Two-Factor Authentication Router
Endpoints for managing 2FA settings and verification
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.two_factor import two_factor_service, TwoFactorMethod

router = APIRouter(prefix="/2fa", tags=["Two-Factor Authentication"])


# ============== Request Models ==============

class VerifyCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class SetupSMSRequest(BaseModel):
    phone: str = Field(..., description="Phone number with country code")


class DisableRequest(BaseModel):
    password: str


class SetPrimaryMethodRequest(BaseModel):
    method: str = Field(..., description="totp, sms, or email")


# ============== Status Endpoints ==============

@router.get("/status")
async def get_2fa_status(current_user: dict = Depends(get_current_user)):
    """Get current 2FA configuration status"""
    status = await two_factor_service.get_2fa_status(current_user["user_id"])
    return status


# ============== TOTP (Authenticator App) ==============

@router.post("/totp/setup")
async def setup_totp(current_user: dict = Depends(get_current_user)):
    """Initialize TOTP setup - returns QR code and secret"""
    result = await two_factor_service.setup_totp(
        current_user["user_id"],
        current_user["email"]
    )
    return {
        "qr_code": result["qr_code"],
        "manual_entry_key": result["manual_entry_key"],
        "message": "Scan the QR code with your authenticator app, then verify with a code"
    }


@router.post("/totp/verify")
async def verify_totp_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify TOTP setup with a code from authenticator app"""
    success, result = await two_factor_service.confirm_totp_setup(
        current_user["user_id"],
        request.code
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result.get("error", "Verification failed"))
    
    return {
        "success": True,
        "message": "Authenticator app 2FA enabled successfully!",
        "backup_codes": result.get("backup_codes", []),
        "warning": "Save these backup codes in a safe place. You won't be able to see them again."
    }


# ============== SMS 2FA ==============

@router.post("/sms/setup")
async def setup_sms(
    request: SetupSMSRequest,
    current_user: dict = Depends(get_current_user)
):
    """Setup SMS-based 2FA - sends verification code to phone"""
    success, message = await two_factor_service.setup_sms(
        current_user["user_id"],
        request.phone
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/sms/verify")
async def verify_sms_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify SMS setup with the code sent to phone"""
    success, result = await two_factor_service.confirm_sms_setup(
        current_user["user_id"],
        request.code
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result.get("error", "Verification failed"))
    
    response = {
        "success": True,
        "message": result.get("message", "SMS 2FA enabled successfully!")
    }
    
    if result.get("backup_codes"):
        response["backup_codes"] = result["backup_codes"]
        response["warning"] = "Save these backup codes in a safe place. You won't be able to see them again."
    
    return response


# ============== Email 2FA ==============

@router.post("/email/setup")
async def setup_email(current_user: dict = Depends(get_current_user)):
    """Setup Email-based 2FA - sends verification code to email"""
    success, message = await two_factor_service.setup_email(current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/email/verify")
async def verify_email_setup(
    request: VerifyCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify Email setup with the code sent to email"""
    success, result = await two_factor_service.confirm_email_setup(
        current_user["user_id"],
        request.code
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result.get("error", "Verification failed"))
    
    response = {
        "success": True,
        "message": result.get("message", "Email 2FA enabled successfully!")
    }
    
    if result.get("backup_codes"):
        response["backup_codes"] = result["backup_codes"]
        response["warning"] = "Save these backup codes in a safe place. You won't be able to see them again."
    
    return response


# ============== Management ==============

@router.post("/disable")
async def disable_2fa(
    request: DisableRequest,
    current_user: dict = Depends(get_current_user)
):
    """Disable all 2FA methods (requires password)"""
    success, message = await two_factor_service.disable_2fa(
        current_user["user_id"],
        request.password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/backup-codes/regenerate")
async def regenerate_backup_codes(current_user: dict = Depends(get_current_user)):
    """Generate new backup codes (invalidates old ones)"""
    status = await two_factor_service.get_2fa_status(current_user["user_id"])
    if not status["enabled"]:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    codes = await two_factor_service.regenerate_backup_codes(current_user["user_id"])
    
    return {
        "backup_codes": codes,
        "warning": "Your old backup codes are now invalid. Save these new codes in a safe place."
    }


@router.put("/primary-method")
async def set_primary_method(
    request: SetPrimaryMethodRequest,
    current_user: dict = Depends(get_current_user)
):
    """Set the primary 2FA method"""
    if request.method not in [TwoFactorMethod.TOTP, TwoFactorMethod.SMS, TwoFactorMethod.EMAIL]:
        raise HTTPException(status_code=400, detail="Invalid method. Use: totp, sms, or email")
    
    success = await two_factor_service.set_primary_method(
        current_user["user_id"],
        request.method
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Method not available for this account")
    
    return {"success": True, "primary_method": request.method}


# ============== Login Verification (Used by Auth Router) ==============

@router.post("/send-code")
async def send_login_code(
    method: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Send a verification code for login (SMS or Email)"""
    success, message = await two_factor_service.send_login_code(
        current_user["user_id"],
        method
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"success": True, "message": message}


@router.post("/verify-login")
async def verify_login_code(
    request: VerifyCodeRequest,
    method: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Verify 2FA code during login"""
    success = await two_factor_service.verify_login(
        current_user["user_id"],
        request.code,
        method
    )
    
    if not success:
        raise HTTPException(status_code=401, detail="Invalid verification code")
    
    return {"success": True, "message": "Verification successful"}
