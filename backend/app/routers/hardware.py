"""
Hardware Integration Router
Endpoints for managing external recording devices
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.hardware_integration import (
    hardware_service, stealth_service,
    DeviceType, DeviceStatus
)

router = APIRouter(prefix="/hardware", tags=["Hardware Integration"])


# ============== Request/Response Models ==============

class RegisterDeviceRequest(BaseModel):
    device_type: str = Field(..., description="Type: gopro, dashcam, rtsp_camera, smartphone")
    device_name: str = Field(..., description="User-friendly device name")
    connection_info: Optional[dict] = None


class UpdateDeviceSettingsRequest(BaseModel):
    settings: dict


class RTSPValidateRequest(BaseModel):
    rtsp_url: str


class StealthSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    black_screen: Optional[bool] = None
    disable_flash: Optional[bool] = None
    silent_shutter: Optional[bool] = None
    volume_button_trigger: Optional[bool] = None
    auto_upload: Optional[bool] = None
    background_recording: Optional[bool] = None
    quick_launch_gesture: Optional[str] = None


# ============== Device Management Endpoints ==============

@router.get("/devices")
async def get_user_devices(current_user: dict = Depends(get_current_user)):
    """Get all registered devices for the current user"""
    devices = await hardware_service.get_user_devices(current_user["user_id"])
    return {"devices": devices, "count": len(devices)}


@router.post("/devices")
async def register_device(
    request: RegisterDeviceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Register a new external device"""
    try:
        device_type = DeviceType(request.device_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device type. Must be one of: {[t.value for t in DeviceType]}"
        )
    
    device = await hardware_service.register_device(
        user_id=current_user["user_id"],
        device_type=device_type,
        device_name=request.device_name,
        connection_info=request.connection_info
    )
    return device


@router.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific device"""
    device = await hardware_service.get_device(device_id, current_user["user_id"])
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/devices/{device_id}/settings")
async def update_device_settings(
    device_id: str,
    request: UpdateDeviceSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update device settings"""
    success = await hardware_service.update_device_settings(
        device_id, current_user["user_id"], request.settings
    )
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a registered device"""
    success = await hardware_service.delete_device(device_id, current_user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}


@router.put("/devices/{device_id}/status")
async def update_device_status(
    device_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update device connection status"""
    try:
        device_status = DeviceStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {[s.value for s in DeviceStatus]}"
        )
    
    # Verify device belongs to user
    device = await hardware_service.get_device(device_id, current_user["user_id"])
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await hardware_service.update_device_status(device_id, device_status)
    return {"success": True, "status": status}


# ============== GoPro Specific Endpoints ==============

@router.get("/gopro/{device_id}/config")
async def get_gopro_config(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get GoPro streaming configuration including BLE commands"""
    config = await hardware_service.generate_gopro_config(device_id, current_user["user_id"])
    if not config:
        raise HTTPException(status_code=404, detail="GoPro device not found")
    return config


@router.get("/gopro/pairing-guide")
async def get_gopro_pairing_guide():
    """Get GoPro pairing instructions"""
    return {
        "steps": [
            {
                "step": 1,
                "title": "Enable Wireless on GoPro",
                "description": "On your GoPro, go to Preferences > Wireless Connections > Enable"
            },
            {
                "step": 2,
                "title": "Put GoPro in Pairing Mode",
                "description": "Go to Connections > Connect Device > GoPro App and wait for pairing mode"
            },
            {
                "step": 3,
                "title": "Connect via Bluetooth",
                "description": "Your phone will search for the GoPro. Select it when it appears."
            },
            {
                "step": 4,
                "title": "Join GoPro WiFi",
                "description": "Connect to the GoPro's WiFi network for streaming capabilities"
            },
            {
                "step": 5,
                "title": "Configure Streaming",
                "description": "The app will automatically configure RTMP streaming settings"
            }
        ],
        "supported_models": ["Hero 9", "Hero 10", "Hero 11", "Hero 12", "Hero 13"],
        "requirements": [
            "Bluetooth enabled on phone",
            "WiFi enabled on phone",
            "GoPro firmware up to date",
            "Stable internet connection for streaming"
        ]
    }


# ============== RTSP Camera Endpoints ==============

@router.post("/rtsp/validate")
async def validate_rtsp_url(
    request: RTSPValidateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Validate an RTSP camera URL"""
    result = await hardware_service.validate_rtsp_url(request.rtsp_url)
    return result


@router.get("/rtsp/setup-guide")
async def get_rtsp_setup_guide():
    """Get RTSP camera setup instructions"""
    return {
        "common_url_formats": [
            {
                "brand": "Generic",
                "format": "rtsp://username:password@ip:554/stream1"
            },
            {
                "brand": "Hikvision",
                "format": "rtsp://username:password@ip:554/Streaming/Channels/101"
            },
            {
                "brand": "Dahua",
                "format": "rtsp://username:password@ip:554/cam/realmonitor?channel=1&subtype=0"
            },
            {
                "brand": "Amcrest",
                "format": "rtsp://username:password@ip:554/cam/realmonitor?channel=1&subtype=0"
            },
            {
                "brand": "Reolink",
                "format": "rtsp://username:password@ip:554/h264Preview_01_main"
            }
        ],
        "troubleshooting": [
            "Ensure camera and phone are on the same network",
            "Check if camera supports RTSP (some WiFi-only cameras don't)",
            "Try both port 554 and 8554",
            "Disable firewall temporarily to test connection",
            "Update camera firmware to latest version"
        ]
    }


# ============== Stealth Recording Endpoints ==============

@router.get("/stealth/settings")
async def get_stealth_settings(current_user: dict = Depends(get_current_user)):
    """Get stealth recording settings"""
    settings = await stealth_service.get_settings(current_user["user_id"])
    return settings


@router.put("/stealth/settings")
async def update_stealth_settings(
    request: StealthSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update stealth recording settings"""
    # Build update dict from non-None values
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    # Get current settings and merge
    current = await stealth_service.get_settings(current_user["user_id"])
    current.update(update_data)
    
    settings = await stealth_service.update_settings(current_user["user_id"], current)
    return settings


# ============== Dash Cam Endpoints ==============

@router.get("/dashcam/setup-guide")
async def get_dashcam_setup_guide():
    """Get dash cam setup instructions"""
    return {
        "wifi_dashcams": {
            "description": "Dash cams with built-in WiFi can stream directly",
            "steps": [
                "Enable WiFi on your dash cam",
                "Connect your phone to the dash cam's WiFi network",
                "Find the RTSP URL in your dash cam's app or manual",
                "Add the camera in JUSTICE using the RTSP URL"
            ],
            "popular_models": [
                {"name": "Viofo A129", "has_rtsp": True},
                {"name": "BlackVue DR900X", "has_rtsp": True},
                {"name": "Thinkware U1000", "has_rtsp": True},
                {"name": "Garmin Dash Cam", "has_rtsp": False, "note": "Uses proprietary app"}
            ]
        },
        "smartphone_mount": {
            "description": "Use your smartphone as a dash cam with JUSTICE",
            "benefits": [
                "No additional hardware needed",
                "Direct integration with all JUSTICE features",
                "Automatic cloud backup",
                "GPS and audio already integrated"
            ],
            "recommended_mounts": [
                "Magnetic phone mount for dash",
                "Suction cup mount with adjustable arm",
                "Air vent mount for quick access"
            ]
        }
    }


# ============== Multi-Camera Support ==============

@router.get("/multi-camera/layout")
async def get_multicamera_layout(current_user: dict = Depends(get_current_user)):
    """Get recommended multi-camera layout for encounter recording"""
    devices = await hardware_service.get_user_devices(current_user["user_id"])
    
    connected_devices = [d for d in devices if d["status"] in ["connected", "streaming"]]
    
    layouts = {
        1: {"layout": "single", "grid": "1x1"},
        2: {"layout": "side-by-side", "grid": "2x1"},
        3: {"layout": "main-with-pip", "grid": "1+2"},
        4: {"layout": "quad", "grid": "2x2"}
    }
    
    device_count = len(connected_devices) + 1  # +1 for smartphone
    recommended_layout = layouts.get(min(device_count, 4), layouts[4])
    
    return {
        "device_count": device_count,
        "connected_devices": connected_devices,
        "recommended_layout": recommended_layout,
        "available_layouts": layouts
    }
