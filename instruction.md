# Инструкция по запуску решения

## Системные требования
- ОС: Linux / Windows / macOS
- Python 3.14
- Docker 24+ (для контейнеризации)

## Установка зависимостей
```bash
pip install -r requirements.txt
```

## Запуск сервера
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Сервер будет доступен по адресу `http://localhost:8000`.
Документация Swagger UI доступна по адресу `http://localhost:8000/docs`.

## Использование Docker

Сборка образа:
```bash
docker build -t digital-marathon-2026 .
```

Запуск через docker-compose:
```bash
GITVERSE_USER=ваш_пользователь docker-compose up
```
