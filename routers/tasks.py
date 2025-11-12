from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_async_session
from models import Task
from typing import List, Optional
from schemas import TaskCreate, TaskUpdate, TaskResponse
from datetime import datetime, date


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Task not found"}},
)


def calculate_urgency_and_quadrant(deadline_at: Optional[datetime], is_important: bool) -> tuple[bool, str]:
    """Вычисляет срочность и квадрант на основе дедлайна и важности"""
    is_urgent = False
    
    if deadline_at:
        if isinstance(deadline_at, datetime):
            deadline_date = deadline_at.date()
        else:
            deadline_date = deadline_at
            
        today = date.today()
        days_until_deadline = (deadline_date - today).days
        is_urgent = days_until_deadline <= 3
    
    # Определяем квадрант
    if is_important and is_urgent:
        quadrant = "Q1"
    elif is_important and not is_urgent:
        quadrant = "Q2"
    elif not is_important and is_urgent:
        quadrant = "Q3"
    else:
        quadrant = "Q4"
    
    return is_urgent, quadrant


# --- Получить все задачи ---
@router.get("", response_model=List[TaskResponse])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    return tasks


# --- Фильтрация по статусу выполнения ---
@router.get("/status/{status}", response_model=List[TaskResponse])
async def get_tasks_by_status(
    status: str,
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    if status not in ["completed", "pending"]:
        raise HTTPException(status_code=404, detail="Недопустимый статус. Используйте: completed или pending")

    is_completed = (status == "completed")
    result = await db.execute(
        select(Task).where(Task.completed == is_completed)
    )
    tasks = result.scalars().all()
    return tasks


# --- Поиск задач по ключевому слову ---
@router.get("/search", response_model=List[TaskResponse])
async def search_tasks(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    keyword = f"%{q.lower()}%"
    result = await db.execute(
        select(Task).where(
            (Task.title.ilike(keyword)) |
            (Task.description.ilike(keyword))
        )
    )
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=404, detail="По данному запросу ничего не найдено")

    return tasks


# --- Получить задачи по квадранту ---
@router.get("/quadrant/{quadrant}", response_model=List[TaskResponse])
async def get_tasks_by_quadrant(
    quadrant: str,
    db: AsyncSession = Depends(get_async_session)
) -> List[TaskResponse]:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    result = await db.execute(
        select(Task).where(Task.quadrant == quadrant)
    )
    tasks = result.scalars().all()
    return tasks


# --- Получить задачу по ID ---
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


# --- Создание новой задачи ---
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    # Вычисляем срочность и квадрант
    is_urgent, quadrant = calculate_urgency_and_quadrant(task.deadline_at, task.is_important)

    new_task = Task(
        title=task.title,
        description=task.description,
        is_important=task.is_important,
        is_urgent=is_urgent,  # Вычисляемое поле
        quadrant=quadrant,
        deadline_at=task.deadline_at,  # Новое поле
        completed=False
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


# --- Обновление задачи ---
@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    update_data = task_update.model_dump(exclude_unset=True)

    # Обновляем поля
    for field, value in update_data.items():
        setattr(task, field, value)

    # Пересчитываем срочность и квадрант если изменились важность или дедлайн
    if "is_important" in update_data or "deadline_at" in update_data:
        is_urgent, quadrant = calculate_urgency_and_quadrant(
            task.deadline_at, 
            task.is_important
        )
        task.is_urgent = is_urgent
        task.quadrant = quadrant

    await db.commit()
    await db.refresh(task)
    
    return task


# --- Удаление задачи ---
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> dict:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    deleted_task_info = {
        "id": task.id,
        "title": task.title
    }

    await db.delete(task)
    await db.commit()

    return {
        "message": "Задача успешно удалена",
        "id": deleted_task_info["id"],
        "title": deleted_task_info["title"]
    }


# --- Отметить задачу выполненной ---
@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task.completed = True
    task.completed_at = datetime.now()
    
    await db.commit()
    await db.refresh(task)
    
    return task
