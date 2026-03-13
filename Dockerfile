FROM python:3.12.7


RUN pip install --no-cache-dir python-telegram-bot==21.9 apscheduler==3.10.4 python-dotenv==1.0.0 requests==2.31.0 openai httpx httpcore
COPY . .

CMD ["python", "bot.py"]