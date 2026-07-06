from fastapi import APIRouter, Depends

from models import User
from schemas import DeviceConnectRequest, DeviceStatusResponse, DeviceCommandResponse
from auth_utils import get_current_user

router = APIRouter(prefix="/api/device", tags=["设备管理"])

# In production, this state maps to the actual hardware manager singleton
_device_state = {
    "status": "disconnected",
    "status_message": "未连接",
    "device_id": None,
    "use_wifi": False,
}


@router.get("/status", response_model=DeviceStatusResponse, summary="获取设备状态")
def get_device_status(current_user: User = Depends(get_current_user)):
    return DeviceStatusResponse(**_device_state)


@router.post("/connect", response_model=DeviceCommandResponse, summary="连接/断开设备")
def connect_device(req: DeviceConnectRequest, current_user: User = Depends(get_current_user)):
    if req.device_id:
        _device_state["status"] = "connected"
        _device_state["status_message"] = "已连接"
        _device_state["device_id"] = req.device_id
        _device_state["use_wifi"] = req.use_wifi
        return DeviceCommandResponse(success=True, message=f"已连接到 {req.device_id}")
    else:
        _device_state.update(status="disconnected", status_message="未连接", device_id=None, use_wifi=False)
        return DeviceCommandResponse(success=True, message="已断开连接")


@router.post("/initialize", response_model=DeviceCommandResponse, summary="发送设备初始化指令")
def initialize_device(current_user: User = Depends(get_current_user)):
    if _device_state["status"] != "connected":
        return DeviceCommandResponse(success=False, message="请先连接设备")
    _device_state["status"] = "initialized"
    _device_state["status_message"] = "设备就绪，可以开始打印"
    return DeviceCommandResponse(success=True, message="设备初始化完成")


@router.post("/start", response_model=DeviceCommandResponse, summary="开始扫描打印")
def start_print(current_user: User = Depends(get_current_user)):
    if _device_state["status"] not in ("connected", "initialized"):
        return DeviceCommandResponse(success=False, message="请先连接并初始化设备")
    _device_state["status"] = "working"
    _device_state["status_message"] = "打印中..."
    return DeviceCommandResponse(success=True, message="打印作业已启动")


@router.post("/stop", response_model=DeviceCommandResponse, summary="紧急终止")
def stop_print(current_user: User = Depends(get_current_user)):
    _device_state["status"] = "connected"
    _device_state["status_message"] = "已终止"
    return DeviceCommandResponse(success=True, message="所有操作已终止")


@router.post("/paper-ready", response_model=DeviceCommandResponse, summary="换纸确认")
def paper_ready(current_user: User = Depends(get_current_user)):
    _device_state["status"] = "working"
    _device_state["status_message"] = "打印中..."
    return DeviceCommandResponse(success=True, message="已确认换纸，继续打印")
