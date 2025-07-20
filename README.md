# Superchromia.com Telegram Bot

Telegram бот для обработки и анализа сообщений с использованием FastAPI и PostgreSQL.

## Деплой на Render.com

### Автоматический деплой

1. **Подключите репозиторий к Render**
   - Зайдите на [render.com](https://render.com)
   - Создайте новый Web Service
   - Подключите ваш GitHub репозиторий

2. **Настройте переменные окружения в Render Dashboard:**
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELETHON_SESSION=anon
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   ```

3. **Настройки сервиса:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`

### Создание базы данных

1. Создайте PostgreSQL базу данных в Render
2. Скопируйте Connection String
3. Добавьте переменную окружения `DATABASE_URL` с этим значением

### Применение миграций

После деплоя примените миграции через Render Shell:

```bash
# В Render Dashboard -> ваш сервис -> Shell
alembic upgrade head
```

## Локальная разработка

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка переменных окружения

Создайте файл `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELETHON_SESSION=anon
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

### Запуск

```bash
# Запуск с Docker Compose
docker-compose up -d

# Или локально
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## API Endpoints

- `GET /health` - проверка здоровья сервиса
- `GET /api/v1/messages` - получение сообщений
- `POST /api/v1/summarize` - суммаризация сообщений

## Структура проекта

```
├── alembic/              # Миграции базы данных
├── api/                  # API endpoints
├── jobs/                 # Фоновые задачи
├── models/               # SQLAlchemy модели
├── repositories/         # Репозитории для работы с БД
├── storage/              # Хранилище файлов
├── app.py               # Основное приложение
├── render.yaml          # Конфигурация Render
└── requirements.txt     # Python зависимости
```

## Особенности для Render

- Приложение автоматически адаптируется к переменной `$PORT`
- Health check endpoint для мониторинга
- Безопасная инициализация Telegram клиента
- Оптимизированный Dockerfile для продакшена 