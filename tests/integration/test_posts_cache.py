import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.models.post import Post


@pytest.mark.asyncio
async def test_post_caching_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    """
    Интеграционный тест проверки жизненного цикла кеша.
    Проверяет, что данные берутся из кеша и инвалидируются при PUT/DELETE.
    """
    prefix = config.api.v1_prefix
    original_title = 'Оригинальный заголовок'
    original_content = 'Текст'

    create_payload = {'title': original_title, 'content': original_content}
    response = await async_client.post(f'{prefix}/posts', json=create_payload)
    assert response.status_code == 200
    post_id = response.json()['id']

    response = await async_client.get(f'{prefix}/posts/{post_id}')
    assert response.status_code == 200
    assert response.json()['title'] == original_title

    result = await db_session.execute(sa.select(Post).where(Post.id == post_id))
    db_post = result.scalar_one()
    db_post.title = 'Измененный в обход API заголовок'
    await db_session.commit()

    response = await async_client.get(f'{prefix}/posts/{post_id}')
    assert response.status_code == 200
    assert response.json()['title'] == original_title

    update_value = 'Обновлено через PUT'
    update_payload = {'title': update_value}
    response = await async_client.put(f'{prefix}/posts/{post_id}', json=update_payload)
    assert response.status_code == 200

    response = await async_client.get(f'{prefix}/posts/{post_id}')
    assert response.status_code == 200
    assert response.json()['title'] == update_value

    response = await async_client.delete(f'{prefix}/posts/{post_id}')
    assert response.status_code == 204

    response = await async_client.get(f'{prefix}/posts/{post_id}')
    assert response.status_code == 404
