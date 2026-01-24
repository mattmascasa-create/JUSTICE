"""
Hardware Integration Service
Manages external device connections (GoPro, dash cams, RTSP cameras)
"""
import os
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from enum import Enum

from app.db.database import db


class DeviceType(str, Enum):
    GOPRO = "gopro"
    DASHCAM = "dashcam"
    RTSP_CAMERA = "rtsp_camera"
    SMARTPHONE = "smartphone"


class DeviceStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


class HardwareIntegrationService:
    """Service for managing external recording devices"""
    
    def __init__(self):
        self.active_devices: Dict[str, Dict] = {}
        self.rtmp_base_url = os.environ.get("RTMP_SERVER_URL", "rtmp://localhost:1935/live")
    
    async def register_device(
        self,
        user_id: str,
        device_type: DeviceType,
        device_name: str,
        device_id: Optional[str] = None,
        connection_info: Optional[Dict] = None
    ) -> Dict:
        """Register a new device for a user"""
        device_doc = {
            "device_id": device_id or f"dev_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "device_type": device_type,
            "device_name": device_name,
            "status": DeviceStatus.DISCONNECTED,
            "connection_info": connection_info or {},
            "stream_key": uuid.uuid4().hex[:16],
            "last_connected": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": self._get_default_settings(device_type)
        }
        
        await db.devices.insert_one(device_doc)
        return {k: v for k, v in device_doc.items() if k != "_id"}
    
    def _get_default_settings(self, device_type: DeviceType) -> Dict:
        """Get default settings for device type"""
        if device_type == DeviceType.GOPRO:
            return {
                "resolution": "720p",
                "bitrate": "4000",
                "stabilization": True,
                "auto_start": False
            }
        elif device_type == DeviceType.DASHCAM:
            return {
                "continuous_recording": True,
                "event_detection": True,
                "gps_overlay": True
            }
        elif device_type == DeviceType.RTSP_CAMERA:
            return {
                "rtsp_url": "",
                "username": "",
                "password": "",
                "reconnect_interval": 30
            }
        return {}
    
    async def get_user_devices(self, user_id: str) -> List[Dict]:
        """Get all devices for a user"""
        devices = await db.devices.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(50)
        return devices
    
    async def get_device(self, device_id: str, user_id: str) -> Optional[Dict]:
        """Get a specific device"""
        device = await db.devices.find_one(
            {"device_id": device_id, "user_id": user_id},
            {"_id": 0}
        )
        return device
    
    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        connection_info: Optional[Dict] = None
    ) -> bool:
        """Update device connection status"""
        update_data = {
            "status": status,
            "last_connected": datetime.now(timezone.utc).isoformat() if status == DeviceStatus.CONNECTED else None
        }
        if connection_info:
            update_data["connection_info"] = connection_info
        
        result = await db.devices.update_one(
            {"device_id": device_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def update_device_settings(
        self,
        device_id: str,
        user_id: str,
        settings: Dict
    ) -> bool:
        """Update device settings"""
        result = await db.devices.update_one(
            {"device_id": device_id, "user_id": user_id},
            {"$set": {"settings": settings}}
        )
        return result.modified_count > 0
    
    async def delete_device(self, device_id: str, user_id: str) -> bool:
        """Delete a device"""
        result = await db.devices.delete_one(
            {"device_id": device_id, "user_id": user_id}
        )
        return result.deleted_count > 0
    
    def get_rtmp_url(self, stream_key: str) -> str:
        """Get RTMP URL for device streaming"""
        return f"{self.rtmp_base_url}/{stream_key}"
    
    async def generate_gopro_config(self, device_id: str, user_id: str) -> Optional[Dict]:
        """Generate GoPro streaming configuration"""
        device = await self.get_device(device_id, user_id)
        if not device or device["device_type"] != DeviceType.GOPRO:
            return None
        
        return {
            "rtmp_url": self.get_rtmp_url(device["stream_key"]),
            "resolution": device["settings"].get("resolution", "720p"),
            "bitrate": device["settings"].get("bitrate", "4000"),
            "ble_commands": {
                "set_livestream": {
                    "feature_id": "0xF5",
                    "action_id": "0x73",
                    "url": self.get_rtmp_url(device["stream_key"])
                },
                "start_stream": {
                    "command": "set_shutter",
                    "value": 1
                },
                "stop_stream": {
                    "command": "set_shutter",
                    "value": 0
                }
            }
        }
    
    async def validate_rtsp_url(self, rtsp_url: str) -> Dict:
        """Validate RTSP camera URL format"""
        import re
        
        # Basic RTSP URL validation
        rtsp_pattern = r'^rtsp://(?:([^:@]+):([^@]+)@)?([^:/]+)(?::(\d+))?(/.*)?$'
        match = re.match(rtsp_pattern, rtsp_url)
        
        if not match:
            return {"valid": False, "error": "Invalid RTSP URL format"}
        
        return {
            "valid": True,
            "parsed": {
                "username": match.group(1),
                "password": match.group(2),
                "host": match.group(3),
                "port": match.group(4) or "554",
                "path": match.group(5) or "/"
            }
        }


# Stealth Recording Settings
class StealthRecordingService:
    """Service for stealth recording mode settings"""
    
    @staticmethod
    async def get_settings(user_id: str) -> Dict:
        """Get stealth recording settings for user"""
        settings = await db.stealth_settings.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not settings:
            # Return defaults
            return {
                "user_id": user_id,
                "enabled": False,
                "black_screen": True,
                "disable_flash": True,
                "silent_shutter": True,
                "volume_button_trigger": True,
                "auto_upload": True,
                "background_recording": False,
                "quick_launch_gesture": "triple_power"
            }
        return settings
    
    @staticmethod
    async def update_settings(user_id: str, settings: Dict) -> Dict:
        """Update stealth recording settings"""
        settings["user_id"] = user_id
        settings["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.stealth_settings.update_one(
            {"user_id": user_id},
            {"$set": settings},
            upsert=True
        )
        return settings


# Global service instance
hardware_service = HardwareIntegrationService()
stealth_service = StealthRecordingService()
