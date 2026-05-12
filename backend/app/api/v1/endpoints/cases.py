"""Test case management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.case import CaseCreate, CaseUpdate, CaseItem
from app.schemas.common import ResponseModel

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_cases(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    type: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    author: str = Query(None),
    keyword: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TestCase).where(TestCase.deleted_at.is_(None))
    count_query = select(func.count()).select_from(TestCase).where(TestCase.deleted_at.is_(None))

    if type:
        query = query.where(TestCase.type == type)
        count_query = count_query.where(TestCase.type == type)
    if status:
        query = query.where(TestCase.status == status)
        count_query = count_query.where(TestCase.status == status)
    if priority:
        query = query.where(TestCase.priority == priority)
        count_query = count_query.where(TestCase.priority == priority)
    if author:
        query = query.where(TestCase.author == author)
        count_query = count_query.where(TestCase.author == author)
    if keyword:
        from sqlalchemy import or_
        like = f"%{keyword}%"
        query = query.where(or_(TestCase.name.ilike(like), TestCase.id.cast(String).ilike(like)))
        count_query = count_query.where(or_(TestCase.name.ilike(like), TestCase.id.cast(String).ilike(like)))

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(query.offset((page - 1) * pageSize).limit(pageSize))).scalars().all()

    return ResponseModel(data={
        "list": [CaseItem.model_validate(i) for i in items],
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.post("", response_model=ResponseModel, status_code=201)
async def create_case(
    body: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "TESTER")),
):
    data = body.model_dump(exclude_unset=True)
    if not data.get("author"):
        data["author"] = current_user.real_name or current_user.username
    case = TestCase(**data, creator_id=current_user.id)
    db.add(case)
    await db.commit()
    return ResponseModel(data={"id": str(case.id)})


@router.get("/authors", response_model=ResponseModel)
async def list_authors(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(TestCase.author).where(TestCase.deleted_at.is_(None), TestCase.author.isnot(None)).distinct()
    )
    authors = [r[0] for r in result.all() if r[0]]
    return ResponseModel(data=authors)


@router.get("/{case_id}", response_model=ResponseModel)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    return ResponseModel(data=CaseItem.model_validate(case))


@router.put("/{case_id}", response_model=ResponseModel)
async def update_case(case_id: str, body: CaseUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    case.version += 1
    await db.commit()
    return ResponseModel(message="更新成功")


@router.delete("/{case_id}", response_model=ResponseModel)
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    from datetime import datetime, timezone
    case.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="删除成功")
