FROM python:3.12.7

WORKDIR /app


RUN pip install --no-cache-dir python-telegram-bot==20.7 apscheduler==3.10.4 python-dotenv==1.0.0 requests==2.31.0 openai httpx httpcore uvicorn==0.27.0 fastapi==0.109.2
COPY . .

CMD ["python", "bot.py"]