# BlogAPI

Спроектировать и частично реализовать API для блога с кешированием популярных постов.

### Что реализовано

* CRUD для постов:
  * создание поста
  * получение поста по ID
  * обновление поста
  * удаление поста
* Кеширование при `GET /posts/{id}`:
  * сначала проверка Redis
  * если кеша нет, данные берутся из PostgreSQL
  * затем пост сохраняется в Redis
* Инвалидация кеша при:
  * обновлении поста
  * удалении поста
* Интеграционный тест для проверки логики кеширования

### Логика кеширования реализована на основе компонентов библиотеки FastAPI-Cache (переписал под свой сценарий)


---

## Технологии

* Python 3.12
* FastAPI
* SQLAlchemy 2.x (async)
* PostgreSQL 
* Redis
* Alembic
* Pydantic v2
* Uvicorn
* Poetry 2.x
* Pytest

---

## Архитектура

Проект построен по слоистой архитектуре:

* `app` - пакет blog API микросервиса
* `api` - роутеры и точка входа приложения
* `dependencies` - зависимости FastAPI
* `models` - ORM-модели SQLAlchemy
* `schemas` - Pydantic-схемы
* `services` - бизнес-логика, кеширование, работа с данными
* `core` - конфигурация, подключение к БД и Redis
* `tests` - интеграционные тесты

### Схема запроса `GET /posts/{id}`

1. Клиент отправляет запрос в API
2. API проверяет Redis по ключу поста
3. Если кеш найден - возвращается значение из Redis
4. Если кеш не найден - выполняется запрос в PostgreSQL
5. Пост сохраняется в Redis
6. Данные возвращаются клиенту

### Какие выбраны подходы к кешированию

В ТЗ уже написано поведение, по которому осуществляется кеширование. В связи с этим были выбраны:

Используется стратегия **cache-aside**:
* приложение само управляет чтением из кеша
* Redis хранит только часто запрашиваемые данные
* при изменении данных кеш можно точечно инвалидировать

Преимущества:
* уменьшение нагрузки на PostgreSQL
* более быстрый ответ на повторные запросы


Так же используется стратегия **Client-side** кеширование (ETag):
* При первом запросе сервер возвращает ответ с заголовками:
  * ETag - хеш ответа
  * Cache-Control - время жизни
  * X-Cache: MISS
* Клиент сохраняет ETag.
* При повторном запросе клиент отправляет заголовок:
  * If-None-Match: <etag>
  * Сервер сравнивает ETag:
  * если данные не изменились → возвращает 304 Not Modified без тела
    если изменились → возвращает новые данные и новый ETag
* Что это даёт:
  * уменьшение трафика (нет тела ответа при 304)
  * ускорение ответов
  * снижение нагрузки на сервер


---

## Структура проекта

```text
blog_api/
├── app/
│   ├── api/
│   ├── core/
│   ├── dependencies/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── alembic/
│   ├── .env
│   └── Dockerfile
├── tests/
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── poetry.lock
└── README.md
```

---

## Требования

* Python 3.12+
* Docker и Docker Compose
* PostgreSQL
* Redis
* Poetry 2.x

---

## Переменные окружения

Настройки берутся из файла `app/.env`.

Пример:

```env
# ApiConfig
API_NAME='Blog API'
API_DEBUG=false

# RunConfig
RUN_HOST=0.0.0.0
RUN_PORT=8000

# DatabaseConfig
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=blog
POSTGRES_ECHO=false
POSTGRES_ECHO_POOL=false
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=10

# TestDatabaseConfig
POSTGRES_TEST_HOST=localhost
POSTGRES_TEST_PORT=5432
POSTGRES_TEST_USER=postgres
POSTGRES_TEST_PASSWORD=postgres
POSTGRES_TEST_DB=test_blog
POSTGRES_TEST_ECHO=true
POSTGRES_TEST_ECHO_POOL=true
POSTGRES_TEST_POOL_SIZE=5
POSTGRES_TEST_MAX_OVERFLOW=10

# RedisConfig
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# RedisDB
REDIS_DB_CACHE=0
REDIS_DB_TEST_CACHE=1
```

> Значения в вашем проекте могут отличаться. При необходимости обновите их под свой `.env`.

---

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Nekspert/BlogAPI.git
cd blog_api
```

### 2. Создать файл `.env`

Скопируйте `app/.env.example` в `app/.env` и заполните параметры.

### 3. Запуск через Docker

```bash
docker compose up -d --build
```

### 4. Проверить, что сервисы поднялись

* API: `http://localhost:8000`
* Swagger: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`

---

## Миграции

Применение миграций выполняется автоматически при старте контейнера API:

```bash
alembic upgrade head
```

Если нужно запустить вручную:

```bash
docker compose exec api alembic upgrade head
```

---

## Запуск локально без Docker

### 1. Установить зависимости

```bash
poetry install
```

### 2. Активировать окружение

```bash
poetry shell
```

### 3. Запустить приложение

```bash
uvicorn app.api.main:main_app --reload
```

---

## Тестирование

### Запуск всех тестов

```bash
poetry run pytest
```

### Запуск интеграционных тестов

```bash
poetry run pytest tests/integration
```

### Что проверяют тесты кеширования

* при первом запросе пост берётся из PostgreSQL и записывается в Redis
* при повторном запросе пост берётся из Redis
* после обновления кеш инвалидируется
* после удаления кеш удаляется

---

## REST API

### Посты

* `POST /posts` - создать пост
* `GET /posts/{id}` - получить пост по ID
* `PUT /posts/{id}` - обновить пост
* `DELETE /posts/{id}` - удалить пост

### Примеры

#### Создание поста

```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"title":"Hello","content":"My first post"}'
```

#### Получение поста

```bash
curl http://localhost:8000/posts/1
```

---

## Работа с кешем

В проекте используется Redis как быстрый слой хранения для часто запрашиваемых постов.

### Правила

* `GET /posts/{id}`:
  * сначала Redis
  * потом PostgreSQL
* `PUT/PATCH /posts/{id}`:
  * обновление в БД
  * удаление ключа из Redis
* `DELETE /posts/{id}`:
  * удаление из БД
  * удаление ключа из Redis

---


## Обработка ошибок

В проекте предусмотрена обработка ошибок:

* пост не найден - `404 Not Found`
* ошибка валидации - `422 Unprocessable Entity`
* ошибка сервера - `500 Internal Server Error`