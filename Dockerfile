FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочего пользователя
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Изменение владельца файлов
RUN chown -R app:app /app

# Переключение на пользователя app
USER app

EXPOSE 5000

# Команда для продакшена
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"] 