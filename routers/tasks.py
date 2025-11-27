# routers/tasks.py
from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from database import get_async_session
from models.task import Task
from models import User, UserRole
from typing import List, Optional
from schemas import TaskCreate, TaskUpdate, TaskResponse
from datetime import datetime, date
from dependencies import get_current_user

router = APIRouter(
    prefix="/api/v2/tasks",
    tags=["tasks"],
    responses={404: {"description": "Task not found"}},
)


def calculate_urgency_and_quadrant(deadline_at: Optional[datetime], is_important: bool) -> tuple[bool, str]:
    is_urgent = False

    if deadline_at:
        if isinstance(deadline_at, datetime):
            deadline_date = deadline_at.date()
        else:
            deadline_date = deadline_at

        today = date.today()
        days_until_deadline = (deadline_date - today).days
        is_urgent = days_until_deadline <= 3

    if is_important and is_urgent:
        quadrant = "Q1"
    elif is_important and not is_urgent:
        quadrant = "Q2"
    elif not is_important and is_urgent:
        quadrant = "Q3"
    else:
        quadrant = "Q4"

    return is_urgent, quadrant


def calculate_days_until_deadline(deadline_at: Optional[datetime]) -> Optional[int]:
    if not deadline_at:
        return None
    if isinstance(deadline_at, datetime):
        deadline_date = deadline_at.date()
    else:
        deadline_date = deadline_at
    today = date.today()
    return (deadline_date - today).days


# --- Получить все задачи (админ — все, user — свои) ---
@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Task))
    else:
        result = await db.execute(select(Task).where(Task.user_id == current_user.id))

    tasks = result.scalars().all()

    tasks_out = []
    for task in tasks:
        task_data = task.to_dict()
        task_data["days_until_deadline"] = calculate_days_until_deadline(task.deadline_at)

        tasks_out.append(TaskResponse(**task_data))

    return tasks_out


# --- Получить задачи сроком на сегодня ---
@router.get("/today", response_model=List[TaskResponse])
async def get_tasks_today(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    today = date.today()

    if current_user.role == UserRole.ADMIN:
        query = select(Task).where(func.date(Task.deadline_at) == today)
    else:
        query = select(Task).where(
            and_(
                Task.user_id == current_user.id,
                func.date(Task.deadline_at) == today
            )
        )

    result = await db.execute(query)
    tasks = result.scalars().all()

    tasks_out = []
    for task in tasks:
        task_data = task.to_dict()
        task_data["days_until_deadline"] = calculate_days_until_deadline(task.deadline_at)

        tasks_out.append(TaskResponse(**task_data))

    return tasks_out



# --- Фильтрация по статусу (проверяем права) ---
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Недопустимый статус. Используйте: completed или pending")

    is_completed = (status == "completed")

    if current_user.role == UserRole.ADMIN:
        query = select(Task).where(Task.completed == is_completed)
    else:
        query = select(Task).where(and_(Task.user_id == current_user.id, Task.completed == is_completed))

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)}) for task in tasks]


# --- Поиск задач (только свои, если не admin) ---
@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"

    if current_user.role == UserRole.ADMIN:
        query = select(Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    else:
        query = select(Task).where(
            and_(
                Task.user_id == current_user.id,
                (Task.title.ilike(keyword) | Task.description.ilike(keyword))
            )
        )

    result = await db.execute(query)
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")

    return [TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)}) for task in tasks]


# --- Получить задачи по квадранту ---
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(status_code=400, detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4")

    if current_user.role == UserRole.ADMIN:
        query = select(Task).where(Task.quadrant == quadrant)
    else:
        query = select(Task).where(and_(Task.quadrant == quadrant, Task.user_id == current_user.id))

    result = await db.execute(query)
    tasks = result.scalars().all()
    return [TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)}) for task in tasks]


# --- Получить задачу по ID (и проверить доступ) ---
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")

    return TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)})


# --- Создание новой задачи (привязываем к current_user) ---
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    is_urgent, quadrant = calculate_urgency_and_quadrant(task.deadline_at, task.is_important)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,
        quadrant=quadrant,
        deadline_at=task.deadline_at,
        completed=False,
        user_id=current_user.id
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return TaskResponse(**{**new_task.to_dict(), "days_until_deadline": calculate_days_until_deadline(new_task.deadline_at)})


# --- Обновление задачи (проверяем права) ---
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")

    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    if "is_important" in update_data or "deadline_at" in update_data:
        is_urgent, quadrant = calculate_urgency_and_quadrant(task.deadline_at, task.is_important)
        task.is_urgent = is_urgent
        task.quadrant = quadrant

    await db.commit()
    await db.refresh(task)

    return TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)})


# --- Удаление задачи ---
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")

    deleted_task_info = {"id": task.id, "title": task.title}

    await db.delete(task)
    await db.commit()

    return {"message": "Задача успешно удалена", "id": deleted_task_info["id"], "title": deleted_task_info["title"]}


# --- Отметить задачу выполненной ---
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> TaskResponse:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")

    task.completed = True
    task.completed_at = datetime.now()

    await db.commit()
    await db.refresh(task)

    return TaskResponse(**{**task.to_dict(), "days_until_deadline": calculate_days_until_deadline(task.deadline_at)})
