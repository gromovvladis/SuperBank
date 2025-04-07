# Базовый образ
FROM python:3.12-slim

# Установка зависимостей
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /superbank

# Копирование зависимостей
COPY requirements.txt /superbank

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы ПОСЛЕ установки зависимостей
COPY . /superbank

# Открываем порт для Django
EXPOSE 8000

# Команда запуска по умолчанию. Будет переопределена в docker-compose для установки фикстур
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "superbank.conf.wsgi:application"]
