from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description" : "Task not found"}},
)

# Временное хранилище (позже будет заменено на PostgreSQL)
tasks_db: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Сдать проект по FastAPI",
        "description": "Завершить разработку API и написать документацию",
        "is_important": True,
        "is_urgent": True,
        "quadrant": "Q1",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 2,
        "title": "Изучить SQLAlchemy",
        "description": "Прочитать документацию и попробовать примеры",
        "is_important": True,
        "is_urgent": False,
        "quadrant": "Q2",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 3,
        "title": "Сходить на лекцию",
        "description": None,
        "is_important": False,
        "is_urgent": True,
        "quadrant": "Q3",
        "completed": False,
        "created_at": datetime.now()
    },
    {
        "id": 4,
        "title": "Посмотреть сериал",
        "description": "Новый сезон любимого сериала",
        "is_important": False,
        "is_urgent": False,
        "quadrant": "Q4",
        "completed": True,
        "created_at": datetime.now()
    },
]


# --- Получить все задачи ---
@router.get("")
async def get_all_tasks() -> dict:
    return {
        "count": len(tasks_db),
        "tasks": tasks_db
    }

# --- Получить статистику по задачам ---
@router.get("/stats")
async def get_tasks_stats() -> dict:
    total_tasks = len(tasks_db)
    by_quadrant = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    by_status = {"completed": 0, "pending": 0}

    for task in tasks_db:
        # Статистика по квадрантам
        if task["quadrant"] in by_quadrant:
            by_quadrant[task["quadrant"]] += 1

        # Статистика по статусу
        if task["completed"]:
            by_status["completed"] += 1
        else:
            by_status["pending"] += 1

    return {
        "total_tasks": total_tasks,
        "by_quadrant": by_quadrant,
        "by_status": by_status
    }

# --- Фильтрация по статусу выполнения ---
@router.get("/status/{status}")
async def get_tasks_by_status(status: str) -> dict:
    if status not in ["completed", "pending"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный статус. Используйте: 'completed' или 'pending'"
        )

    filtered_tasks = [
        task for task in tasks_db
        if task["completed"] == (status == "completed")
    ]

    if not filtered_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Задачи со статусом '{status}' не найдены"
        )

    return {
        "status": status,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# --- Поиск задач по ключевому слову ---
@router.get("/search")
async def search_tasks(q: str = Query(..., min_length=2)) -> dict:
    keyword = q.lower()

    filtered_tasks = [
        task for task in tasks_db
        if keyword in task["title"].lower() or
           (task["description"] and keyword in task["description"].lower())
    ]

    if not filtered_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Задачи, содержащие '{q}', не найдены"
        )

    return {
        "query": q,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# --- Получить задачи по квадранту ---
@router.get("/quadrant/{quadrant}")
async def get_tasks_by_quadrant(quadrant: str) -> dict:
    if quadrant not in ["Q1", "Q2", "Q3", "Q4"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный квадрант. Используйте: Q1, Q2, Q3, Q4"
        )
    filtered_tasks = [
        task for task in tasks_db
        if task["quadrant"] == quadrant
    ]
    return {
        "quadrant": quadrant,
        "count": len(filtered_tasks),
        "tasks": filtered_tasks
    }

# --- Получить задачу по ID ---
@router.get("/{task_id}")
async def get_task_by_id(task_id: int) -> dict:
    for task in tasks_db:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=404,
        detail=f"Задача с ID {task_id} не найдена"
    )
