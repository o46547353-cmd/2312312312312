FROM python:3.11-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY bot.py threads_api.py storage.py ai_gen.py threads_login.py ./

# Папка для storage.json и картинок
RUN mkdir -p /data

# storage.json и картинки хранятся в /data (монтируется как volume)
ENV STORAGE_PATH=/data/storage.json

CMD ["python", "bot.py"]
