import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Response, status

from app.api.tags import Tags
from app.core.config import config
from app.dependencies.db import SessionDep
from app.models.post import Post
from app.schemas.post import PostCreate, PostResponse, PostUpdate
from app.services.cache import Cache


router = APIRouter(prefix='/posts', tags=[Tags.POSTS.value])


@router.get('/{post_id}',
            response_model=PostResponse,
            summary='Получить пост по ID',
            description=(
                    'Возвращает данные публикации. Реализовано кеширование на уровне Redis: '
                    'при первом запросе данные берутся из БД, при последующих — из кеша. '
                    'Поддерживает проверку ETag для экономии трафика (304 Not Modified).'
            ))
@Cache.cache(expire=60, namespace=config.cache.namespace.blog_posts)
async def get_post(post_id: int, session: SessionDep):
    result = await session.execute(sa.select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    return post


@router.post('',
             response_model=PostResponse,
             summary='Создать новый пост',
             description='Создает новую запись в блоге.'
             )
async def create_post(data: PostCreate, session: SessionDep):
    post = Post(
            **data.model_dump(exclude_unset=True)
    )
    session.add(post)
    await session.commit()

    return post


@router.put('/{post_id}',
            response_model=PostResponse,
            summary='Обновить пост',
            description=(
                    'Частично или полностью обновляет данные существующего поста. '
                    'После успешного обновления в БД происходит автоматическая инвалидация (очистка) '
                    'всего кеша в пространстве имен блога, чтобы гарантировать актуальность данных.'
            ))
async def update_post(post_id: int, data: PostUpdate, session: SessionDep):
    result = await session.execute(sa.select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(post, key, value)

    await session.commit()
    await session.refresh(post)

    await Cache.clear(namespace=config.cache.namespace.blog_posts)

    return post


@router.delete('/{post_id}',
               summary='Удалить пост',
               description=(
                       'Удаляет запись из базы данных. При успешном удалении также очищает '
                       'соответствующий кеш в Redis, чтобы предотвратить отдачу удаленного контента.'
               ))
async def delete_post(post_id: int, session: SessionDep):
    result = await session.execute(sa.select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if post:
        await session.delete(post)
        await session.commit()
        await Cache.clear(namespace=config.cache.namespace.blog_posts)
        return Response(content=None, status_code=status.HTTP_204_NO_CONTENT)

    return Response(content=None, status_code=status.HTTP_404_NOT_FOUND)
