"""
python test_reply4.py POST_PK
Тестирует publish_mode для reply и альтернативные endpoint-ы.
"""
import sys, os, json, time, random, requests
from dotenv import load_dotenv
load_dotenv(r"C:\threads\.env")

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ["THREADS_CSRF_TOKEN"]
USER_ID    = os.environ["THREADS_USER_ID"]

H = {
    "User-Agent":      "Barcelona 289.0.0.77.109 Android",
    "X-CSRFToken":     CSRF_TOKEN,
    "X-IG-App-ID":     "238260118697367",
    "Cookie":          f"sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}",
    "Content-Type":    "application/x-www-form-urlencoded",
}

parent_pk  = sys.argv[1] if len(sys.argv) > 1 else input("post_id (pk): ").strip()
parent_full = f"{parent_pk}_{USER_ID}"
device_id   = f"android-{random.randint(0x100000000000, 0xffffffffffff):012x}"

def go(name, url, payload):
    print(f"\n{'─'*55}\n[{name}]")
    r = requests.post(url, headers=H, data=payload, timeout=20)
    print(f"  {r.status_code} → {r.text[:250]}")
    if r.status_code == 200:
        pk = r.json().get("media", {}).get("pk") or r.json().get("pk")
        print(f"  >>> post_id={pk}")
    time.sleep(4)
    return r.status_code == 200

BASE = {"_uid": USER_ID, "_csrftoken": CSRF_TOKEN, "device_id": device_id}

# 1. publish_mode = "reply_to_comment"
go("1: publish_mode=reply_to_comment",
   "https://www.threads.net/api/v1/media/configure_text_only_post/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 1",
    "publish_mode":        "reply_to_comment",
    "replied_to_post_id":  parent_pk})

# 2. publish_mode = "reply"  
go("2: publish_mode=reply",
   "https://www.threads.net/api/v1/media/configure_text_only_post/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 2",
    "publish_mode":        "reply",
    "replied_to_post_id":  parent_pk})

# 3. Без publish_mode, но с is_reply=1
go("3: no publish_mode + is_reply=1",
   "https://www.threads.net/api/v1/media/configure_text_only_post/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 3",
    "is_reply":            "1",
    "replied_to_post_id":  parent_pk})

# 4. text_feed reply endpoint
go("4: text_feed/replies endpoint",
   f"https://www.threads.net/api/v1/text_feed/{parent_pk}/add_reply/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 4",
    "publish_mode":        "text_post"})

# 5. configure_text_post_app_feed + upload_id + publish_mode=text_post + is_reply
upload_id = str(int(time.time() * 1000))
go("5: app_feed + upload_id + is_reply",
   "https://www.threads.net/api/v1/media/configure_text_post_app_feed/",
   {**BASE,
    "upload_id":           upload_id,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 5",
    "source_type":         "4",
    "is_reply":            "1",
    "replied_to_post_id":  parent_pk})

# 6. reply_to_post_id (без 'ied' — другое имя)
go("6: reply_to_post_id (без -ied)",
   "https://www.threads.net/api/v1/media/configure_text_only_post/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 6",
    "publish_mode":        "text_post",
    "reply_to_post_id":    parent_pk})

# 7. thread_id поле
go("7: thread_id field",
   "https://www.threads.net/api/v1/media/configure_text_only_post/",
   {**BASE,
    "text_post_app_info":  json.dumps({"reply_control": 0}),
    "caption":             "reply test 7",
    "publish_mode":        "text_post",
    "thread_id":           parent_pk})

print("\n\nКакие номера появились как REPLY в ветке (не отдельные посты)?")