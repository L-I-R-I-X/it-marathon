FROM gitverse.ru/hub/library/python:3.14-slim

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src/

# Открываем порт
EXPOSE 8000

# Запускаем сервер
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
