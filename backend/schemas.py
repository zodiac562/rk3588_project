from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ─── Auth ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None


# ─── Records ───────────────────────────────────────────

class BrailleRecordCreate(BaseModel):
    title: str
    source_type: str
    dot_matrix_width: int = 0
    dot_matrix_height: int = 0
    dot_matrix_data: List[List[int]] = []
    text_content: Optional[str] = None
    page_count: int = 1


class BrailleRecordRename(BaseModel):
    title: str


class BrailleRecordResponse(BaseModel):
    id: str
    title: str
    source_type: str
    dot_matrix_width: int
    dot_matrix_height: int
    dot_matrix_data: List[List[int]]
    text_content: Optional[str] = None
    page_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class BrailleRecordListResponse(BaseModel):
    total: int
    records: List[BrailleRecordResponse]


# ─── Device ────────────────────────────────────────────

class DeviceConnectRequest(BaseModel):
    device_id: str
    use_wifi: bool = False


class DeviceStatusResponse(BaseModel):
    status: str  # disconnected | connected | initializing | initialized | working | printing
    status_message: str
    device_id: Optional[str] = None
    use_wifi: bool = False


class DeviceCommandResponse(BaseModel):
    success: bool
    message: str


# ─── Logs ──────────────────────────────────────────────

class LogUploadRequest(BaseModel):
    logs: List[str]


class LogUploadResponse(BaseModel):
    success: bool
    uploaded_count: int
    message: str
