"""
Запусти на сервере: python3 test_upload.py
Покажет точный ответ Threads на каждом шаге загрузки картинки.
"""
import os, time, json, requests
from dotenv import load_dotenv
load_dotenv()

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ["THREADS_CSRF_TOKEN"]
USERNAME   = os.environ["THREADS_USERNAME"]
USER_ID    = os.environ.get("THREADS_USER_ID", "")

HEADERS = {
    "User-Agent":      "Barcelona 289.0.0.77.109 Android",
    "X-CSRFToken":     CSRF_TOKEN,
    "X-IG-App-ID":     "238260118697367",
    "Cookie":          f"sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

IMAGE_PATH = "slash_logo.jpg"

print("=" * 60)
print(f"Файл: {IMAGE_PATH}")
print(f"Существует: {os.path.exists(IMAGE_PATH)}")
if os.path.exists(IMAGE_PATH):
    print(f"Размер: {os.path.getsize(IMAGE_PATH)} байт")
print()

# ШАГ 1: upload
print("ШАГ 1 — Upload изображения")
upload_id = str(int(time.time() * 1000))
upload_url = f"https://www.threads.net/rupload_igphoto/fb_uploader_{upload_id}"

with open(IMAGE_PATH, "rb") as f:
    img_data = f.read()

rupload_params = json.dumps({
    "upload_id":         upload_id,
    "media_type":        1,
    "image_compression": json.dumps({"lib_name": "moz", "lib_version": "3.1.m", "quality": "87"}),
    "xsharing_user_ids": json.dumps([]),
    "retry_context":     json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
})

r = requests.post(upload_url, headers={
    **HEADERS,
    "Content-Type":               "application/octet-stream",
    "X-Entity-Type":              "image/jpeg",
    "X-Entity-Length":            str(len(img_data)),
    "X-Entity-Name":              f"fb_uploader_{upload_id}",
    "X-Instagram-Rupload-Params": rupload_params,
    "Offset":                     "0",
}, data=img_data, timeout=60)

print(f"Статус: {r.status_code}")
print(f"Ответ:  {r.text[:500]}")
print()

if r.status_code not in (200, 201):
    print("❌ Upload не прошёл. Дальше нет смысла.")
    raise SystemExit(1)

print("✅ Upload OK, upload_id =", upload_id)
print("Жду 12 секунд...")
time.sleep(12)

# ШАГ 2: configure с картинкой (корневой пост, без reply)
print("ШАГ 2 — Публикация поста с картинкой")

import random, uuid
device_id = f"android-{random.randint(0x100000000000, 0xffffffffffff):012x}"

app_info = {
    "reply_control":              0,
    "entry_point":                "text_post_new",
    "fediverse_composer_enabled": True,
    "is_reply_approval_enabled":  False,
    "is_spoiler_media":           False,
    "excluded_inline_media_ids":  "[]",
}

payload = {
    "upload_id":          upload_id,
    "text_post_app_info": json.dumps(app_info),
    "caption":            "тест загрузки картинки — удалю сразу",
    "_uid":               USER_ID,
    "_csrftoken":         CSRF_TOKEN,
    "device_id":          device_id,
    "source_type":        "4",
    "media_type":         "1",
    "audience":           "default",
    "publish_mode":       "text_post",
    "scene_type":         "1",
    "creation_logger_session_id": str(uuid.uuid4()),
}

r2 = requests.post(
    "https://www.threads.net/api/v1/media/configure_text_post_app_feed/",
    headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
    data=payload, timeout=30
)

print(f"Статус: {r2.status_code}")
print(f"Ответ:  {r2.text[:800]}")

if r2.status_code == 200:
    pk = r2.json().get("media", {}).get("pk") or r2.json().get("pk")
    print(f"\n✅ Пост с картинкой опубликован! pk={pk}")
    print("Зайди в Threads и проверь — потом удали тестовый пост.")
else:
    print(f"\n❌ Ошибка публикации. Статус {r2.status_code}")
