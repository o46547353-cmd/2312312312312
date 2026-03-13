
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ["AITUNNEL_API_KEY"],
    base_url="https://api.aitunnel.ru/v1/",
)

SYSTEM_PROMPT = """Ты пишешь конверсионные посты для Threads о SLASH VPN.
Продукт: SLASH VPN - Telegram-бот для защиты трафика.
Тарифы: 1 день 10р, 3 дня 30р, 7 дней 70р, 14 дней 150р, 30 дней 199р.
CTA всегда: напиши + в комментах - скину ссылку лично.

СТРУКТУРА - 4 поста:
ПОСТ 1 ХУК (до 450 символов): 3-4 коротких удара, каждая мысль отдельная строка, заканчивается стрелкой и CTA
ПОСТ 2 БОЛЬ (до 480 символов): раскрываешь проблему конкретно, заканчивается CTA
ПОСТ 3 РЕШЕНИЕ (до 450 символов): Telegram-бот 30 секунд без приложений, цена входа 10р, заканчивается CTA
ПОСТ 4 ДОЖИМ (до 220 символов): жесткий финальный призыв с триггером

ПРАВИЛА: от первого лица, без канцелярита, CTA в каждом посте, тарифы только в посте 3.

Отвечай СТРОГО только JSON без markdown:
{"post1": "текст", "post2": "текст", "post3": "текст", "post4": "текст"}

Переносы строк внутри текста заменяй на \\n"""

def generate_series(topic: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Тема: " + topic},
        ],
        max_tokens=1200,
        temperature=0.85,
    )
    text = resp.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    # Убираем реальные переносы строк внутри JSON-строк
    # Находим содержимое между кавычками и заменяем там \n на \\n
    def fix_newlines(m):
        return m.group(0).replace('\n', '\\n').replace('\r', '')
    text = re.sub(r'"(?:[^"\\]|\\.)*"', fix_newlines, text)
    data = json.loads(text)
    # Возвращаем реальные переносы строк обратно
    for key in data:
        data[key] = data[key].replace('\\n', '\n')
    return data

def generate_post(topic: str) -> str:
    return generate_series(topic)["post1"]

def generate_batch(topics: list) -> list:
    return [generate_post(t) for t in topics]
