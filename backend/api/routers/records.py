import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import BrailleRecord, User
from schemas import BrailleRecordCreate, BrailleRecordRename, BrailleRecordResponse, BrailleRecordListResponse
from auth_utils import get_current_user

router = APIRouter(prefix="/api/records", tags=["盲文记录"])


@router.get("", response_model=BrailleRecordListResponse, summary="获取记录列表")
def list_records(
    search: str = Query(default="", description="按标题搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(BrailleRecord).filter(BrailleRecord.user_id == current_user.id)
    if search:
        q = q.filter(BrailleRecord.title.contains(search))
    total = q.count()
    records = q.order_by(BrailleRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return BrailleRecordListResponse(
        total=total,
        records=[
            BrailleRecordResponse(
                id=r.id, title=r.title, source_type=r.source_type,
                dot_matrix_width=r.dot_matrix_width, dot_matrix_height=r.dot_matrix_height,
                dot_matrix_data=r.dot_matrix_data or [], text_content=r.text_content,
                page_count=r.page_count, created_at=r.created_at,
            ) for r in records
        ],
    )


@router.get("/{record_id}", response_model=BrailleRecordResponse, summary="获取单条记录")
def get_record(record_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(BrailleRecord).filter(BrailleRecord.id == record_id, BrailleRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return BrailleRecordResponse(
        id=record.id, title=record.title, source_type=record.source_type,
        dot_matrix_width=record.dot_matrix_width, dot_matrix_height=record.dot_matrix_height,
        dot_matrix_data=record.dot_matrix_data or [], text_content=record.text_content,
        page_count=record.page_count, created_at=record.created_at,
    )


@router.post("", response_model=BrailleRecordResponse, status_code=status.HTTP_201_CREATED, summary="创建新记录")
def create_record(req: BrailleRecordCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = BrailleRecord(
        id=uuid.uuid4().hex[:16],
        user_id=current_user.id,
        title=req.title,
        source_type=req.source_type,
        dot_matrix_width=req.dot_matrix_width,
        dot_matrix_height=req.dot_matrix_height,
        dot_matrix_data=req.dot_matrix_data,
        text_content=req.text_content,
        page_count=req.page_count,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return BrailleRecordResponse(
        id=record.id, title=record.title, source_type=record.source_type,
        dot_matrix_width=record.dot_matrix_width, dot_matrix_height=record.dot_matrix_height,
        dot_matrix_data=record.dot_matrix_data or [], text_content=record.text_content,
        page_count=record.page_count, created_at=record.created_at,
    )


@router.put("/{record_id}", response_model=BrailleRecordResponse, summary="重命名记录")
def rename_record(record_id: str, req: BrailleRecordRename, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(BrailleRecord).filter(BrailleRecord.id == record_id, BrailleRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    record.title = req.title
    db.commit()
    db.refresh(record)
    return BrailleRecordResponse(
        id=record.id, title=record.title, source_type=record.source_type,
        dot_matrix_width=record.dot_matrix_width, dot_matrix_height=record.dot_matrix_height,
        dot_matrix_data=record.dot_matrix_data or [], text_content=record.text_content,
        page_count=record.page_count, created_at=record.created_at,
    )


@router.delete("/{record_id}", summary="删除记录")
def delete_record(record_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(BrailleRecord).filter(BrailleRecord.id == record_id, BrailleRecord.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"success": True, "message": "记录已删除"}
