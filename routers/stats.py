# routers/stats.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_async_session
from models.task import Task
from models import User, UserRole
from typing import List
from datetime import date, datetime
from schemas import DeadlineStatsResponse
from dependencies import get_current_user

router = APIRouter(
    prefix="/api/v2/stats",
    tags=["statistics"]
)


@router.get("/", response_model=dict)
async def get_tasks_stats(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Task))
    else:
        result = await db.execute(select(Task).where(Task.user_id == current_user.id))

    tasks = result.scalars().all()

    total_tasks = len(tasks)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    by_status = {"completed": 0, "pending": 0}

    for task in tasks:
        if task.quadrant in by_quadrant:
            by_quadrant[task.quadrant] += 1
        if task.completed:
            by_status["completed"] += 1
        else:
            by_status["pending"] += 1

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }


@router.get("/deadlines", response_model=List[DeadlineStatsResponse])
async def get_deadline_stats(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[DeadlineStatsResponse]:
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Task).where(Task.completed == False))
    else:
        result = await db.execute(select(Task).where(and_(Task.completed == False, Task.user_id == current_user.id)))

    tasks = result.scalars().all()

    deadline_stats = []
    for task in tasks:
        days_until_deadline = None
        if task.deadline_at:
            if isinstance(task.deadline_at, datetime):
                deadline_date = task.deadline_at.date()
            else:
                deadline_date = task.deadline_at

            today = date.today()
            delta = deadline_date - today
            days_until_deadline = delta.days

        deadline_stats.append({
            "title": task.title,
            "description": task.description,
            "created_at": task.created_at,
            "days_until_deadline": days_until_deadline
        })

    return deadline_stats








# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from models import Task
# from database import get_async_session
# from typing import List
# from datetime import date, datetime
# from schemas import DeadlineStatsResponse

# router = APIRouter(
#     prefix="/stats",
#     tags=["statistics"]
# )


# @router.get("/", response_model=dict)
# async def get_tasks_stats(db: AsyncSession = Depends(get_async_session)) -> dict:
#     result = await db.execute(select(Task))
#     tasks = result.scalars().all()
    
#     total_tasks = len(tasks)
#     by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
#     by_status = {"completed": 0, "pending": 0}

#     for task in tasks:
#         if task.quadrant in by_quadrant:
#             by_quadrant[task.quadrant] += 1
#         if task.completed:
#             by_status["completed"] += 1
#         else:
#             by_status["pending"] += 1

#     return {
#         "total_tasks": total_tasks,
#         "by_quadrant": by_quadrant,
#         "by_status": by_status
#     }


# @router.get("/deadlines", response_model=List[DeadlineStatsResponse])
# async def get_deadline_stats(db: AsyncSession = Depends(get_async_session)) -> List[DeadlineStatsResponse]:
#     """Получить статистику по дедлайнам для незавершенных задач"""
#     result = await db.execute(
#         select(Task).where(Task.completed == False)
#     )
#     tasks = result.scalars().all()
    
#     deadline_stats = []
#     for task in tasks:
#         days_until_deadline = None
#         if task.deadline_at:
#             if isinstance(task.deadline_at, datetime):
#                 deadline_date = task.deadline_at.date()
#             else:
#                 deadline_date = task.deadline_at
                
#             today = date.today()
#             delta = deadline_date - today
#             days_until_deadline = delta.days
        
#         deadline_stats.append({
#             "title": task.title,
#             "description": task.description,
#             "created_at": task.created_at,
#             "days_until_deadline": days_until_deadline
#         })
    
#     return deadline_stats

