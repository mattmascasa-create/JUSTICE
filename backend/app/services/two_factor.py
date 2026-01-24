"""
Two-Factor Authentication Service
Supports TOTP (Authenticator Apps), SMS, and Email verification
"""
import os
import pyotp
import qrcode
import base64
import secrets
import hashlib
from io import BytesIO
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

from app.db.database import db


class TwoFactorMethod:
    TOTP = "totp"           # Authenticator app (Google Authenticator, Authy)
    SMS = "sms"             # SMS code via Twilio
    EMAIL = "email"         # Email code via SendGrid


class TwoFactorService:
    """Service for managing Two-Factor Authentication"""
    
    def __init__(self):
        self.app_name = "JUSTICE"
        self.code_length = 6
        self.code_validity_minutes = 10
        self.backup_codes_count = 10
    
    # ============== TOTP (Authenticator App) ==============
    
    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret for authenticator apps"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, email: str) -> str:
        """Get the URI for QR code generation"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.app_name)
    
    def generate_qr_code(self, secret: str, email: str) -> str:
        """Generate QR code as base64 string for authenticator setup"""
        uri = self.get_totp_uri(secret, email)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code from authenticator app"""
        totp = pyotp.TOTP(secret)
        # Allow 1 window before/after for clock drift
        return totp.verify(code, valid_window=1)
    
    # ============== SMS/Email Codes ==============
    
    def generate_verification_code(self) -> str:
        """Generate a random 6-digit verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.code_length)])
    
    async def store_verification_code(
        self, 
        user_id: str, 
        code: str, 
        method: str
    ) -> None:
        """Store a verification code with expiration"""
        # Hash the code for security
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        await db.two_factor_codes.delete_many({"user_id": user_id})  # Remove old codes
        await db.two_factor_codes.insert_one({
            "user_id": user_id,
            "code_hash": code_hash,
            "method": method,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.code_validity_minutes),
            "attempts": 0
        })
    
    async def verify_code(self, user_id: str, code: str) -> Tuple[bool, str]:
        """Verify a SMS/Email verification code"""
        code_doc = await db.two_factor_codes.find_one({"user_id": user_id})
        
        if not code_doc:
            return False, "No verification code found. Please request a new one."
        
        # Check expiration
        if datetime.now(timezone.utc) > code_doc["expires_at"].replace(tzinfo=timezone.utc):
            await db.two_factor_codes.delete_one({"user_id": user_id})
            return False, "Verification code expired. Please request a new one."
        
        # Check attempts (max 5)
        if code_doc["attempts"] >= 5:
            await db.two_factor_codes.delete_one({"user_id": user_id})
            return False, "Too many failed attempts. Please request a new code."
        
        # Verify code hash
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash != code_doc["code_hash"]:
            await db.two_factor_codes.update_one(
                {"user_id": user_id},
                {"$inc": {"attempts": 1}}
            )
            return False, "Invalid verification code."
        
        # Success - delete the code
        await db.two_factor_codes.delete_one({"user_id": user_id})
        return True, "Code verified successfully."
    
    # ============== Backup Codes ==============
    
    def generate_backup_codes(self) -> List[str]:
        """Generate a set of backup codes"""
        codes = []
        for _ in range(self.backup_codes_count):
            code = secrets.token_hex(4).upper()  # 8 character hex codes
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Hash backup codes for storage"""
        return [hashlib.sha256(code.replace("-", "").encode()).hexdigest() for code in codes]
    
    async def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code"""
        user = await db.users.find_one({"user_id": user_id})
        if not user or not user.get("two_factor", {}).get("backup_codes"):
            return False
        
        code_hash = hashlib.sha256(code.replace("-", "").encode()).hexdigest()
        backup_codes = user["two_factor"]["backup_codes"]
        
        if code_hash in backup_codes:
            # Remove the used code
            backup_codes.remove(code_hash)
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"two_factor.backup_codes": backup_codes}}
            )
            return True
        return False
    
    # ============== User 2FA Settings ==============
    
    async def get_2fa_status(self, user_id: str) -> Dict:
        """Get user's 2FA configuration status"""
        user = await db.users.find_one({"user_id": user_id}, {"two_factor": 1})
        
        if not user or not user.get("two_factor"):
            return {
                "enabled": False,
                "methods": [],
                "primary_method": None,
                "backup_codes_remaining": 0
            }
        
        tf = user["two_factor"]
        return {
            "enabled": tf.get("enabled", False),
            "methods": tf.get("methods", []),
            "primary_method": tf.get("primary_method"),
            "backup_codes_remaining": len(tf.get("backup_codes", [])),
            "phone_last_4": tf.get("phone", "")[-4:] if tf.get("phone") else None,
            "email_verified": tf.get("email_verified", False)
        }
    
    async def setup_totp(self, user_id: str, email: str) -> Dict:
        """Initialize TOTP setup - returns secret and QR code"""
        secret = self.generate_totp_secret()
        qr_code = self.generate_qr_code(secret, email)
        
        # Store pending secret (not yet verified)
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"two_factor.pending_totp_secret": secret}}
        )
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code}",
            "manual_entry_key": secret
        }
    
    async def confirm_totp_setup(self, user_id: str, code: str) -> Tuple[bool, Dict]:
        """Confirm TOTP setup by verifying a code"""
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return False, {"error": "User not found"}
        
        pending_secret = user.get("two_factor", {}).get("pending_totp_secret")
        if not pending_secret:
            return False, {"error": "No pending TOTP setup found"}
        
        if not self.verify_totp(pending_secret, code):
            return False, {"error": "Invalid verification code"}
        
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        hashed_codes = self.hash_backup_codes(backup_codes)
        
        # Enable TOTP
        methods = user.get("two_factor", {}).get("methods", [])
        if TwoFactorMethod.TOTP not in methods:
            methods.append(TwoFactorMethod.TOTP)
        
        await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "two_factor.enabled": True,
                    "two_factor.totp_secret": pending_secret,
                    "two_factor.methods": methods,
                    "two_factor.primary_method": TwoFactorMethod.TOTP,
                    "two_factor.backup_codes": hashed_codes,
                    "two_factor.setup_at": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {"two_factor.pending_totp_secret": ""}
            }
        )
        
        return True, {"backup_codes": backup_codes}
    
    async def setup_sms(self, user_id: str, phone: str) -> Tuple[bool, str]:
        """Setup SMS-based 2FA"""
        from app.services.sms_service import send_sms
        
        code = self.generate_verification_code()
        await self.store_verification_code(user_id, code, TwoFactorMethod.SMS)
        
        # Store phone number (pending verification)
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"two_factor.pending_phone": phone}}
        )
        
        # Send SMS
        success = await send_sms(
            to=phone,
            body=f"Your JUSTICE verification code is: {code}. Valid for {self.code_validity_minutes} minutes."
        )
        
        if success:
            return True, "Verification code sent to your phone."
        return False, "Failed to send SMS. Please check the phone number."
    
    async def confirm_sms_setup(self, user_id: str, code: str) -> Tuple[bool, Dict]:
        """Confirm SMS setup by verifying the code"""
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return False, {"error": "User not found"}
        
        pending_phone = user.get("two_factor", {}).get("pending_phone")
        if not pending_phone:
            return False, {"error": "No pending SMS setup found"}
        
        verified, message = await self.verify_code(user_id, code)
        if not verified:
            return False, {"error": message}
        
        # Generate backup codes if first 2FA method
        backup_codes = []
        hashed_codes = user.get("two_factor", {}).get("backup_codes", [])
        if not hashed_codes:
            backup_codes = self.generate_backup_codes()
            hashed_codes = self.hash_backup_codes(backup_codes)
        
        methods = user.get("two_factor", {}).get("methods", [])
        if TwoFactorMethod.SMS not in methods:
            methods.append(TwoFactorMethod.SMS)
        
        primary = user.get("two_factor", {}).get("primary_method") or TwoFactorMethod.SMS
        
        await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "two_factor.enabled": True,
                    "two_factor.phone": pending_phone,
                    "two_factor.methods": methods,
                    "two_factor.primary_method": primary,
                    "two_factor.backup_codes": hashed_codes
                },
                "$unset": {"two_factor.pending_phone": ""}
            }
        )
        
        result = {"message": "SMS 2FA enabled successfully"}
        if backup_codes:
            result["backup_codes"] = backup_codes
        return True, result
    
    async def setup_email(self, user_id: str) -> Tuple[bool, str]:
        """Setup Email-based 2FA"""
        from app.services.email_service import send_email
        
        user = await db.users.find_one({"user_id": user_id})
        if not user or not user.get("email"):
            return False, "User email not found"
        
        code = self.generate_verification_code()
        await self.store_verification_code(user_id, code, TwoFactorMethod.EMAIL)
        
        success = await send_email(
            to=user["email"],
            subject="JUSTICE - Email Verification Code",
            body=f"""
Your JUSTICE verification code is: {code}

This code is valid for {self.code_validity_minutes} minutes.

If you didn't request this code, please secure your account immediately.

- The JUSTICE Team
            """
        )
        
        if success:
            return True, "Verification code sent to your email."
        return False, "Failed to send email."
    
    async def confirm_email_setup(self, user_id: str, code: str) -> Tuple[bool, Dict]:
        """Confirm Email 2FA setup"""
        verified, message = await self.verify_code(user_id, code)
        if not verified:
            return False, {"error": message}
        
        user = await db.users.find_one({"user_id": user_id})
        
        # Generate backup codes if first 2FA method
        backup_codes = []
        hashed_codes = user.get("two_factor", {}).get("backup_codes", [])
        if not hashed_codes:
            backup_codes = self.generate_backup_codes()
            hashed_codes = self.hash_backup_codes(backup_codes)
        
        methods = user.get("two_factor", {}).get("methods", [])
        if TwoFactorMethod.EMAIL not in methods:
            methods.append(TwoFactorMethod.EMAIL)
        
        primary = user.get("two_factor", {}).get("primary_method") or TwoFactorMethod.EMAIL
        
        await db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "two_factor.enabled": True,
                    "two_factor.email_verified": True,
                    "two_factor.methods": methods,
                    "two_factor.primary_method": primary,
                    "two_factor.backup_codes": hashed_codes
                }
            }
        )
        
        result = {"message": "Email 2FA enabled successfully"}
        if backup_codes:
            result["backup_codes"] = backup_codes
        return True, result
    
    async def disable_2fa(self, user_id: str, password: str) -> Tuple[bool, str]:
        """Disable all 2FA methods (requires password verification)"""
        from app.core.security import verify_password
        
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return False, "User not found"
        
        if not verify_password(password, user.get("password_hash", "")):
            return False, "Invalid password"
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$unset": {"two_factor": ""}}
        )
        
        return True, "Two-factor authentication disabled"
    
    async def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """Regenerate backup codes (invalidates old ones)"""
        backup_codes = self.generate_backup_codes()
        hashed_codes = self.hash_backup_codes(backup_codes)
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"two_factor.backup_codes": hashed_codes}}
        )
        
        return backup_codes
    
    async def set_primary_method(self, user_id: str, method: str) -> bool:
        """Set the primary 2FA method"""
        user = await db.users.find_one({"user_id": user_id})
        if not user or method not in user.get("two_factor", {}).get("methods", []):
            return False
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"two_factor.primary_method": method}}
        )
        return True
    
    # ============== Login Verification ==============
    
    async def send_login_code(self, user_id: str, method: str = None) -> Tuple[bool, str]:
        """Send a verification code for login"""
        user = await db.users.find_one({"user_id": user_id})
        if not user or not user.get("two_factor", {}).get("enabled"):
            return False, "2FA not enabled"
        
        tf = user["two_factor"]
        method = method or tf.get("primary_method")
        
        if method == TwoFactorMethod.SMS:
            from app.services.sms_service import send_sms
            code = self.generate_verification_code()
            await self.store_verification_code(user_id, code, method)
            success = await send_sms(
                to=tf["phone"],
                body=f"Your JUSTICE login code is: {code}"
            )
            return success, "Code sent via SMS" if success else "Failed to send SMS"
        
        elif method == TwoFactorMethod.EMAIL:
            from app.services.email_service import send_email
            code = self.generate_verification_code()
            await self.store_verification_code(user_id, code, method)
            success = await send_email(
                to=user["email"],
                subject="JUSTICE - Login Verification Code",
                body=f"Your login code is: {code}\n\nValid for {self.code_validity_minutes} minutes."
            )
            return success, "Code sent via email" if success else "Failed to send email"
        
        elif method == TwoFactorMethod.TOTP:
            return True, "Enter code from your authenticator app"
        
        return False, "Invalid 2FA method"
    
    async def verify_login(self, user_id: str, code: str, method: str = None) -> bool:
        """Verify 2FA code during login"""
        user = await db.users.find_one({"user_id": user_id})
        if not user or not user.get("two_factor", {}).get("enabled"):
            return True  # 2FA not enabled, allow login
        
        tf = user["two_factor"]
        method = method or tf.get("primary_method")
        
        # Try TOTP first if it's the method
        if method == TwoFactorMethod.TOTP:
            if self.verify_totp(tf.get("totp_secret", ""), code):
                return True
        
        # Try SMS/Email code verification
        if method in [TwoFactorMethod.SMS, TwoFactorMethod.EMAIL]:
            verified, _ = await self.verify_code(user_id, code)
            if verified:
                return True
        
        # Try backup code as fallback
        if await self.verify_backup_code(user_id, code):
            return True
        
        return False


# Global service instance
two_factor_service = TwoFactorService()
