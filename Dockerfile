FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файлов requirements.txt
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всех файлов проекта
COPY . .

# Создание директории для базы данных
RUN mkdir -p /app/data

# Установка переменной окружения для Python
ENV PYTHONUNBUFFERED=1

# Экспонирование порта (если нужно)
EXPOSE 8000

# Команда запуска бота
CMD ["python", "bot.py"]
