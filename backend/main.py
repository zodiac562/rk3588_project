"""
毕昇微光 (BiSheng Glimmer) — FastAPI 后端服务入口

启动命令:
    # 开发
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

    # 生产 (宝塔面板 -> Python 项目管理器 -> 启动方式: uvicorn)
    uvicorn main:app --host 0.0.0.0 --port 8001

数据库:
    首次启动前确保 MySQL 已创建数据库:
    CREATE DATABASE bisheng_glimmer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

    表结构由 SQLAlchemy 自动创建 (main.py 中 init_db())
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import init_db, SessionLocal
from models import User, BrailleRecord
from auth_utils import hash_password, generate_id
from api.routers import auth, records, device, logs
from api.routers.auth import avatar_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_demo_user()
    _seed_demo_record()
    yield


def _seed_demo_user():
    db: Session = SessionLocal()
    try:
        if db.query(User).filter(User.username == "test_admin").first() is None:
            db.add(User(
                id=generate_id(),
                username="test_admin",
                email="test@bisheng.com",
                password_hash=hash_password("123456"),
                bio="毕昇微光管理员",
            ))
            db.commit()
    finally:
        db.close()


_LIZU_TEXT = (
    "第四章 黎族船形屋文化源流与建筑特色"
    "海南岛的地形特点是中高四周低，形成了山地丘陵、台地和沿海平原等梯级。"
    "黎族主要聚居在海南岛的中南部，这里纬度低，雨量丰，阳光足，长夏而无冬，"
    "秋春相连，四季不分明。黎族村落就散落在海南岛中南部的丘陵、盆地、峡谷和一些滨海平原上。"
    "几千年的历史发展，孕育出了黎族丰富多彩的民族文化。"
    "黎族传统建筑的船形屋则是极具特色之一。"
)


def _seed_demo_record():
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "test_admin").first()
        if user is None:
            print("[seed] test_admin not found, skipping record seed")
            return
        print(f"[seed] found user: {user.username} (id={user.id})")
        existing = db.query(BrailleRecord).filter(
            BrailleRecord.user_id == user.id,
            BrailleRecord.title == "第四章 黎族船形屋文化源流与建筑特色",
        ).first()
        if existing is None:
            db.add(BrailleRecord(
                id=generate_id(),
                user_id=user.id,
                title="第四章 黎族船形屋文化源流与建筑特色",
                source_type="现场扫描",
                dot_matrix_width=40,
                dot_matrix_height=30,
                dot_matrix_data=[],
                text_content=_LIZU_TEXT,
                page_count=4,
            ))
            db.commit()
            print("[seed] 黎族船形屋 record inserted successfully")
        else:
            print("[seed] 黎族船形屋 record already exists, skipped")
    except Exception as e:
        print(f"[seed] ERROR: {e}")
    finally:
        db.close()


app = FastAPI(
    title="毕昇微光 API",
    description="面向视障阅读辅助的盲文扫描打印系统后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(records.router)
app.include_router(device.router)
app.include_router(logs.router)
app.include_router(avatar_router)

import os
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(os.path.join(uploads_dir, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/", tags=["健康检查"])
def root():
    return {"service": "毕昇微光 API", "version": "1.0.0", "status": "running"}


@app.get("/api/health", tags=["健康检查"])
def health_check():
    return {"status": "healthy"}


@app.get("/uploads/avatars/{filename}")
async def serve_avatar(filename: str):
    filepath = os.path.join(uploads_dir, "avatars", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(filepath)
