from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PostBase(BaseModel):
    """
    Базовая схема поста, содержащая общие поля.
    """
    title: str = Field(
            ...,
            min_length=3,
            max_length=255,
            description='Заголовок поста',
            examples=['Как я внедрил Redis в FastAPI'],
    )
    content: str = Field(
            ...,
            min_length=5,
            description='Основной текст публикации',
            examples=['В этой статье мы разберем процесс настройки кеширования'],
    )


class PostCreate(PostBase):
    """
    Схема для создания нового поста.
    Все поля обязательны (наследуются от PostBase).
    """


class PostUpdate(BaseModel):
    """
    Схема для частичного обновления поста.
    Все поля необязательны.
    """
    title: Optional[str] = Field(
            None,
            min_length=3,
            max_length=256,
            description='Новый заголовок поста',
            examples=['Обновленный заголовок'],
    )
    content: Optional[str] = Field(
            None,
            min_length=10,
            description='Обновленный текст публикации',
            examples=['Текст был дополнен новыми подробностями.'],
    )


class PostResponse(PostBase):
    """
    Схема для ответа API.
    Включает системные поля из БД.
    """
    id: int = Field(
            ...,
            description='Уникальный идентификатор поста',
            examples=[1]
    )
    created_at: datetime = Field(
            ...,
            description='Дата и время создания',
            examples=['2026-03-22T12:00:00'],
    )
    updated_at: datetime = Field(
            ...,
            description='Дата и время последнего обновления',
            examples=['2026-03-22T12:00:00'],
    )
