from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date


# --- Базовая схема задачи ---
class TaskBase(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание задачи"
    )
    is_important: bool = Field(
        ...,
        description="Важность задачи"
    )
    deadline_at: Optional[datetime] = Field(
        None,
        description="Плановый дедлайн задачи"
    )


# --- Схема для создания новой задачи ---
class TaskCreate(TaskBase):
    pass


# --- Схема для обновления задачи ---
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое название задачи"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Новое описание"
    )
    is_important: Optional[bool] = Field(
        None,
        description="Новая важность"
    )
    deadline_at: Optional[datetime] = Field(
        None,
        description="Новый дедлайн"
    )
    completed: Optional[bool] = Field(
        None,
        description="Статус выполнения"
    )


# --- Схема ответа ---
class TaskResponse(TaskBase):
    id: int = Field(
        ...,
        description="Уникальный ID задачи",
        examples=[1]
    )
    is_urgent: Optional[bool] = Field(
    default=False,
    description="Срочность задачи (вычисляемое поле)"
)
    quadrant: str = Field(
        ...,
        description="Квадрант матрицы Эйзенхауэра (Q1, Q2, Q3, Q4)"
    )
    completed: bool = Field(
        default=False,
        description="Статус выполнения задачи"
    )
    created_at: datetime = Field(
        ...,
        description="Дата создания"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Дата завершения"
    )
    days_until_deadline: Optional[int] = Field(
        None,
        description="Количество дней до дедлайна"
    )

    @validator('days_until_deadline', pre=True, always=True)
    def calculate_days_until_deadline(cls, v, values):
        if 'deadline_at' in values and values['deadline_at']:
            deadline = values['deadline_at']
            if isinstance(deadline, datetime):
                deadline_date = deadline.date()
            else:
                deadline_date = deadline
            today = date.today()
            delta = deadline_date - today
            return delta.days
        return None

    class Config:
        from_attributes = True


# --- Схема для статистики по дедлайнам ---
class DeadlineStatsResponse(BaseModel):
    title: str
    description: Optional[str]
    created_at: datetime
    days_until_deadline: Optional[int]

    class Config:
        from_attributes = True

