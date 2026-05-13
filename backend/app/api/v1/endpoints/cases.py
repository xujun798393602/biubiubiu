"""Test case management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.task import Task
from app.models.test_case import CaseFolder, TaskCase, TestCase
from app.models.user import User
from app.schemas.case import (
    CaseCreate, CaseUpdate, CaseItem,
    FolderCreate, FolderUpdate, FolderItem, FolderTreeItem,
)
from app.schemas.common import ResponseModel


class CaseExecuteRequest(BaseModel):
    case_ids: List[str] = Field(..., min_length=1, max_length=100)


router = APIRouter()


# ── Helper: build folder tree ──────────────────────────────────────
def _build_tree(folders: list, case_counts: dict, cases_by_folder: dict, parent_id=None) -> list:
    tree = []
    for f in folders:
        if f.parent_id == parent_id:
            children = _build_tree(folders, case_counts, cases_by_folder, f.id)
            # Add cases as leaf nodes under this folder
            for c in cases_by_folder.get(f.id, []):
                children.append({
                    "id": str(c.id),
                    "name": c.name,
                    "type": "case",
                    "priority": c.priority,
                    "status": c.status,
                })
            # Count: direct cases + all descendant folder case counts
            total = case_counts.get(f.id, 0)
            for child in children:
                if child.get("type") == "folder":
                    total += child.get("case_count", 0)
            tree.append({
                "id": str(f.id),
                "name": f.name,
                "type": "folder",
                "parent_id": str(f.parent_id) if f.parent_id else None,
                "sort_order": f.sort_order,
                "case_count": total,
                "children": children,
            })
    tree.sort(key=lambda x: x.get("sort_order", 0))
    return tree


# ── Folder endpoints ───────────────────────────────────────────────

@router.get("/folders/tree", response_model=ResponseModel)
async def get_folder_tree(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    folders = (await db.execute(
        select(CaseFolder).where(CaseFolder.deleted_at.is_(None))
    )).scalars().all()

    # Count cases per folder
    count_result = (await db.execute(
        select(TestCase.folder_id, func.count())
        .where(TestCase.deleted_at.is_(None), TestCase.folder_id.isnot(None))
        .group_by(TestCase.folder_id)
    )).all()
    case_counts = {row[0]: row[1] for row in count_result}

    # Fetch all active cases grouped by folder
    all_cases = (await db.execute(
        select(TestCase).where(TestCase.deleted_at.is_(None), TestCase.folder_id.isnot(None))
    )).scalars().all()
    cases_by_folder: dict = {}
    for c in all_cases:
        cases_by_folder.setdefault(c.folder_id, []).append(c)

    tree = _build_tree(folders, case_counts, cases_by_folder)
    return ResponseModel(data=tree)


@router.post("/folders", response_model=ResponseModel, status_code=201)
async def create_folder(body: FolderCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if body.parent_id:
        parent = (await db.execute(
            select(CaseFolder).where(CaseFolder.id == body.parent_id, CaseFolder.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail={"code": "FOLDER_NOT_FOUND", "message": "父文件夹不存在"})

    folder = CaseFolder(name=body.name, parent_id=body.parent_id, creator_id=current_user.id)
    db.add(folder)
    await db.commit()
    return ResponseModel(data={"id": str(folder.id)})


@router.put("/folders/{folder_id}", response_model=ResponseModel)
async def update_folder(folder_id: str, body: FolderUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = (await db.execute(
        select(CaseFolder).where(CaseFolder.id == folder_id, CaseFolder.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail={"code": "FOLDER_NOT_FOUND", "message": "文件夹不存在"})

    if body.name is not None:
        folder.name = body.name
    if body.parent_id is not None:
        # Prevent circular reference
        if body.parent_id == folder_id:
            raise HTTPException(status_code=400, detail={"code": "CIRCULAR_REFERENCE", "message": "不能将文件夹移动到自身"})
        folder.parent_id = body.parent_id

    await db.commit()
    return ResponseModel(message="更新成功")


@router.delete("/folders/{folder_id}", response_model=ResponseModel)
async def delete_folder(folder_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = (await db.execute(
        select(CaseFolder).where(CaseFolder.id == folder_id, CaseFolder.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail={"code": "FOLDER_NOT_FOUND", "message": "文件夹不存在"})

    now = datetime.now(timezone.utc)

    # Cascade soft delete: collect all descendant folder ids
    folder_ids_to_delete = [folder.id]
    queue = [folder.id]
    while queue:
        parent = queue.pop(0)
        children = (await db.execute(
            select(CaseFolder.id).where(CaseFolder.parent_id == parent, CaseFolder.deleted_at.is_(None))
        )).scalars().all()
        for child_id in children:
            folder_ids_to_delete.append(child_id)
            queue.append(child_id)

    # Soft delete all folders
    for fid in folder_ids_to_delete:
        f = (await db.execute(select(CaseFolder).where(CaseFolder.id == fid))).scalar_one_or_none()
        if f:
            f.deleted_at = now

    # Soft delete all cases in these folders
    cases = (await db.execute(
        select(TestCase).where(TestCase.folder_id.in_(folder_ids_to_delete), TestCase.deleted_at.is_(None))
    )).scalars().all()
    for c in cases:
        c.deleted_at = now

    await db.commit()
    return ResponseModel(message="删除成功")


@router.post("/folders/{folder_id}/copy", response_model=ResponseModel, status_code=201)
async def copy_folder(folder_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    folder = (await db.execute(
        select(CaseFolder).where(CaseFolder.id == folder_id, CaseFolder.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail={"code": "FOLDER_NOT_FOUND", "message": "文件夹不存在"})

    # Recursive copy
    async def _copy_folder(src_folder, dest_parent_id):
        new_folder = CaseFolder(
            name=f"{src_folder.name}-复制",
            parent_id=dest_parent_id,
            sort_order=src_folder.sort_order,
            creator_id=current_user.id,
        )
        db.add(new_folder)
        await db.flush()

        # Copy cases in this folder
        src_cases = (await db.execute(
            select(TestCase).where(TestCase.folder_id == src_folder.id, TestCase.deleted_at.is_(None))
        )).scalars().all()
        for src_case in src_cases:
            data = {c.name: getattr(src_case, c.name) for c in src_case.__table__.columns if c.name not in ("id", "created_at", "updated_at")}
            data["folder_id"] = new_folder.id
            data["creator_id"] = current_user.id
            new_case = TestCase(**data)
            db.add(new_case)

        # Copy child folders recursively
        child_folders = (await db.execute(
            select(CaseFolder).where(CaseFolder.parent_id == src_folder.id, CaseFolder.deleted_at.is_(None))
        )).scalars().all()
        for child in child_folders:
            await _copy_folder(child, new_folder.id)

        return new_folder

    new_folder = await _copy_folder(folder, folder.parent_id)
    await db.commit()
    return ResponseModel(data={"id": str(new_folder.id)})


# ── Trash endpoints ────────────────────────────────────────────────

@router.get("/trash", response_model=ResponseModel)
async def get_trash(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    deleted_cases = (await db.execute(
        select(TestCase).where(TestCase.deleted_at.isnot(None))
    )).scalars().all()

    deleted_folders = (await db.execute(
        select(CaseFolder).where(CaseFolder.deleted_at.isnot(None))
    )).scalars().all()

    items = []
    for f in deleted_folders:
        items.append({"type": "folder", "id": str(f.id), "name": f.name, "deleted_at": str(f.deleted_at) if f.deleted_at else None})
    for c in deleted_cases:
        items.append({"type": "case", "id": str(c.id), "name": c.name, "deleted_at": str(c.deleted_at) if c.deleted_at else None})

    return ResponseModel(data=items)


@router.post("/trash/empty", response_model=ResponseModel)
async def empty_trash(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    # Hard delete all soft-deleted cases
    await db.execute(
        TestCase.__table__.delete().where(TestCase.deleted_at.isnot(None))
    )
    # Hard delete all soft-deleted folders
    await db.execute(
        CaseFolder.__table__.delete().where(CaseFolder.deleted_at.isnot(None))
    )
    await db.commit()
    return ResponseModel(message="垃圾桶已清空")


@router.post("/trash/restore/{item_type}/{item_id}", response_model=ResponseModel)
async def restore_trash_item(item_type: str, item_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if item_type == "case":
        item = (await db.execute(select(TestCase).where(TestCase.id == item_id, TestCase.deleted_at.isnot(None)))).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "用例不存在"})
        item.deleted_at = None
    elif item_type == "folder":
        folder = (await db.execute(select(CaseFolder).where(CaseFolder.id == item_id, CaseFolder.deleted_at.isnot(None)))).scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "文件夹不存在"})
        # Restore folder and all descendants
        folder_ids = [folder.id]
        queue = [folder.id]
        while queue:
            parent = queue.pop(0)
            children = (await db.execute(
                select(CaseFolder.id).where(CaseFolder.parent_id == parent, CaseFolder.deleted_at.isnot(None))
            )).scalars().all()
            for child_id in children:
                folder_ids.append(child_id)
                queue.append(child_id)

        for fid in folder_ids:
            f = (await db.execute(select(CaseFolder).where(CaseFolder.id == fid))).scalar_one_or_none()
            if f:
                f.deleted_at = None
            # Restore cases in this folder
            cases = (await db.execute(select(TestCase).where(TestCase.folder_id == fid, TestCase.deleted_at.isnot(None)))).scalars().all()
            for c in cases:
                c.deleted_at = None
    else:
        raise HTTPException(status_code=400, detail={"code": "INVALID_TYPE", "message": "类型必须是 case 或 folder"})

    await db.commit()
    return ResponseModel(message="恢复成功")


# ── Case copy endpoint ─────────────────────────────────────────────

@router.post("/{case_id}/copy", response_model=ResponseModel, status_code=201)
async def copy_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    src = (await db.execute(
        select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})

    data = {c.name: getattr(src, c.name) for c in src.__table__.columns if c.name not in ("id", "created_at", "updated_at")}
    data["name"] = f"{src.name}-复制"
    data["creator_id"] = current_user.id
    data["version"] = 1
    new_case = TestCase(**data)
    db.add(new_case)
    await db.commit()
    return ResponseModel(data={"id": str(new_case.id)})


# ── Existing case endpoints (modified) ─────────────────────────────

@router.get("", response_model=ResponseModel)
async def list_cases(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    type: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    author: str = Query(None),
    keyword: str = Query(None),
    folder_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TestCase).where(TestCase.deleted_at.is_(None))
    count_query = select(func.count()).select_from(TestCase).where(TestCase.deleted_at.is_(None))

    if folder_id:
        query = query.where(TestCase.folder_id == folder_id)
        count_query = count_query.where(TestCase.folder_id == folder_id)
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


@router.post("/execute", response_model=ResponseModel, status_code=201)
async def execute_cases(
    body: CaseExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate all case_ids exist
    existing = (await db.execute(
        select(TestCase.id).where(TestCase.id.in_(body.case_ids), TestCase.deleted_at.is_(None))
    )).scalars().all()
    if len(existing) != len(body.case_ids):
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "部分用例不存在"})

    # Create task
    task = Task(
        name=f"快速执行 {len(body.case_ids)} 个用例",
        description="从用例管理页面快速执行",
        priority="MEDIUM",
        execute_type="IMMEDIATE",
        creator_id=current_user.id,
        total_cases=len(body.case_ids),
    )
    db.add(task)
    await db.flush()

    # Add task-case associations
    for i, case_id in enumerate(body.case_ids):
        db.add(TaskCase(task_id=task.id, case_id=case_id, sort_order=i))

    await db.commit()
    return ResponseModel(data={"task_id": str(task.id), "message": f"已创建执行任务，共 {len(body.case_ids)} 个用例"})


@router.delete("/{case_id}", response_model=ResponseModel)
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    result = await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    case.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="删除成功")
