# Базовый образ
FROM python:3.12

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /superbank

# Копирование зависимостей
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы проекта в контейнер
COPY . /superbank

# Открываем порт для Django
EXPOSE 8000

# Команда запуска (может быть переопределена в docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "superbank.conf.wsgi:application"]
