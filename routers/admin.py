# routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_async_session
from models import User, UserRole
from models.task import Task
from dependencies import get_current_user

router = APIRouter(prefix="/api/v2/admin", tags=["admin"])


@router.get("/users")
async def get_users_with_task_counts(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    query = (
        select(
            User.id,
            User.nickname,
            User.email,
            func.count(Task.id).label("task_count")
        )
        .join(Task, Task.user_id == User.id, isouter=True)
        .group_by(User.id)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {"id": r.id, "nickname": r.nickname, "email": r.email, "task_count": r.task_count}
        for r in rows
    ]
