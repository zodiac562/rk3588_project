import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse, ProfileUpdateRequest
from auth_utils import hash_password, verify_password, create_access_token, generate_id, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])

UPLOAD_DIR = str(Path(__file__).resolve().parent.parent.parent / "uploads" / "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, email=user.email,
            avatar=user.avatar, bio=user.bio, created_at=user.created_at,
        ),
    )


@router.post("/register", response_model=TokenResponse, summary="用户注册")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

    user = User(
        id=generate_id(),
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, username=user.username, email=user.email,
            avatar=user.avatar, bio=user.bio, created_at=user.created_at,
        ),
    )


@router.get("/profile", response_model=UserResponse, summary="获取当前用户信息")
def get_profile(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id, username=current_user.username, email=current_user.email,
        avatar=current_user.avatar, bio=current_user.bio, created_at=current_user.created_at,
    )


@router.put("/profile", response_model=UserResponse, summary="更新用户信息")
def update_profile(req: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.username is not None and req.username != current_user.username:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用")
        current_user.username = req.username
    if req.avatar is not None:
        current_user.avatar = req.avatar
    if req.bio is not None:
        current_user.bio = req.bio
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id, username=current_user.username, email=current_user.email,
        avatar=current_user.avatar, bio=current_user.bio, created_at=current_user.created_at,
    )


@router.post("/avatar", response_model=UserResponse, summary="上传头像")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 PNG/JPG/GIF/WebP 格式")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    filename = f"{uuid.uuid4().hex}_{current_user.id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像大小不能超过 5MB")

    with open(filepath, "wb") as f:
        f.write(content)

    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar = avatar_url
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id, username=current_user.username, email=current_user.email,
        avatar=current_user.avatar, bio=current_user.bio, created_at=current_user.created_at,
    )


avatar_router = APIRouter()


@avatar_router.get("/uploads/avatars/{filename}")
async def serve_avatar(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(filepath)
