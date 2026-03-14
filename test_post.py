"""
python3 test_post.py
Тестирует публикацию reply — показывает полный ответ сервера.
"""
import os, time, json, random, uuid, requests
from dotenv import load_dotenv
load_dotenv()

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ["THREADS_CSRF_TOKEN"]
USERNAME   = os.environ["THREADS_USERNAME"]

def jazoest(s): return str(2 + sum(ord(c) for c in s))

def rnd(): return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))

def browser_headers():
    return {
        "User-Agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "X-CSRFToken":        CSRF_TOKEN,
        "X-IG-App-ID":        "238260118697367",
        "X-ASBD-ID":          "359341",
        "X-Bloks-Version-ID": "1363ee4ad31aa321b811ce30b2aacd0f644c2fb57f440040b43e585a4befa092",
        "X-Instagram-AJAX":   "0",
        "Cookie":             f"sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}",
        "Content-Type":       "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept":             "*/*",
        "Accept-Language":    "ru-RU,ru;q=0.9",
        "Origin":             "https://www.threads.com",
        "Referer":            f"https://www.threads.com/@{USERNAME}",
    }

def post(text, reply_to_id=None):
    upload_id = str(int(time.time() * 1000))
    app_info = {
        "entry_point":                "create_reply" if reply_to_id else "sidebar_navigation",
        "excluded_inline_media_ids":  "[]",
        "fediverse_composer_enabled": True,
        "is_reply_approval_enabled":  False,
        "is_spoiler_media":           False,
        "reply_control":              0,
        "self_thread_context_id":     str(uuid.uuid4()),
        "text_with_entities":         {"entities": [], "text": text},
    }
    if reply_to_id:
        app_info["reply_id"] = str(reply_to_id)

    payload = {
        "audience":                        "default",
        "caption":                         text,
        "creator_geo_gating_info":         json.dumps({"whitelist_country_codes": []}),
        "is_upload_type_override_allowed": "1",
        "jazoest":                         jazoest(upload_id),
        "publish_mode":                    "text_post",
        "should_include_permalink":        "true",
        "text_post_app_info":              json.dumps(app_info),
        "upload_id":                       upload_id,
        "web_session_id":                  f"{rnd()}:{rnd()}:{rnd()}",
    }
    if reply_to_id:
        payload["barcelona_source_reply_id"] = str(reply_to_id)

    url = "https://www.threads.com/api/v1/media/configure_text_only_post/"
    r = requests.post(url, headers=browser_headers(), data=payload, timeout=30)

    print(f"\n{'='*60}")
    print(f"reply_to={reply_to_id}")
    print(f"STATUS: {r.status_code}")
    print(f"RESPONSE: {r.text}")  # ПОЛНЫЙ ответ без обрезки
    print(f"{'='*60}")
    return r

# ШАГ 1: корневой пост
print("ШАГ 1 — корневой пост")
r1 = post("тест серии — шаг 1, удалю")
if r1.status_code != 200:
    print("❌ Корневой не прошёл, стоп")
    raise SystemExit(1)

pk1 = r1.json().get("media", {}).get("pk")
print(f"✅ pk1={pk1}")
time.sleep(10)

# ШАГ 2: reply на пост1
print("\nШАГ 2 — reply на пост1")
r2 = post("тест серии — шаг 2, удалю", reply_to_id=pk1)
if r2.status_code == 200:
    pk2 = r2.json().get("media", {}).get("pk")
    print(f"✅ pk2={pk2}")
else:
    print("❌ Reply не прошёл")
    raise SystemExit(1)
time.sleep(10)

# ШАГ 3: reply на пост2
print("\nШАГ 3 — reply на пост2")
r3 = post("тест серии — шаг 3, удалю", reply_to_id=pk2)
if r3.status_code == 200:
    print("✅ Всё работает! Серия из 3 постов опубликована.")
else:
    print("❌ Reply на пост2 не прошёл")
