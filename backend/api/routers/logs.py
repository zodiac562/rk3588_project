from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import DeviceLog, User
from schemas import LogUploadRequest, LogUploadResponse
from auth_utils import get_current_user

router = APIRouter(prefix="/api/logs", tags=["设备日志"])


@router.get("", summary="获取日志列表")
def get_logs(
    device_id: str = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DeviceLog).filter(DeviceLog.user_id == current_user.id)
    if device_id:
        q = q.filter(DeviceLog.device_id == device_id)
    logs = q.order_by(DeviceLog.created_at.desc()).limit(limit).all()
    return {
        "total": len(logs),
        "logs": [{"id": l.id, "device_id": l.device_id, "content": l.log_content, "created_at": l.created_at.isoformat()} for l in logs],
    }


@router.post("/upload", response_model=LogUploadResponse, summary="上传设备日志")
def upload_logs(
    req: LogUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = 0
    for content in req.logs:
        db.add(DeviceLog(user_id=current_user.id, device_id="ELF2", log_content=content))
        count += 1
    db.commit()
    return LogUploadResponse(success=True, uploaded_count=count, message=f"已上传 {count} 条日志")
