"""
python3 test_upload.py
Тестирует публикацию поста с картинкой через браузерный API.
"""
import os, time, json, random, uuid, requests
from dotenv import load_dotenv
load_dotenv()

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ["THREADS_CSRF_TOKEN"]
USERNAME   = os.environ["THREADS_USERNAME"]
USER_ID    = os.environ.get("THREADS_USER_ID", "")
IMAGE_PATH = "slash_logo.jpg"

def jazoest(s): return str(2 + sum(ord(c) for c in s))

HDRS_UPLOAD = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "X-CSRFToken":     CSRF_TOKEN,
    "X-IG-App-ID":     "238260118697367",
    "X-ASBD-ID":       "359341",
    "X-Bloks-Version-ID": "1363ee4ad31aa321b811ce30b2aacd0f644c2fb57f440040b43e585a4befa092",
    "X-Instagram-AJAX": "0",
    "Cookie":          f"sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}",
    "Origin":          "https://www.threads.com",
    "Referer":         f"https://www.threads.com/@{USERNAME}",
}

# ШАГ 1: Upload
print("ШАГ 1 — Upload")
upload_id = str(int(time.time() * 1000))
with open(IMAGE_PATH, "rb") as f:
    img_data = f.read()

rupload_params = json.dumps({
    "upload_id":         upload_id,
    "media_type":        1,
    "image_compression": json.dumps({"lib_name": "moz", "lib_version": "3.1.m", "quality": "87"}),
    "xsharing_user_ids": json.dumps([]),
    "retry_context":     json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
})

r = requests.post(
    f"https://www.threads.com/rupload_igphoto/fb_uploader_{upload_id}",
    headers={**HDRS_UPLOAD,
        "Content-Type":               "application/octet-stream",
        "X-Entity-Type":              "image/jpeg",
        "X-Entity-Length":            str(len(img_data)),
        "X-Entity-Name":              f"fb_uploader_{upload_id}",
        "X-Instagram-Rupload-Params": rupload_params,
        "Offset":                     "0",
    }, data=img_data, timeout=60)

print(f"Upload: {r.status_code} → {r.text[:200]}")
if r.status_code not in (200, 201):
    print("❌ Upload провалился"); raise SystemExit(1)

print(f"✅ Upload OK, ожидаю 10 сек...")
time.sleep(10)

# ШАГ 2: Publish
print("ШАГ 2 — Публикация с картинкой")
app_info = {
    "community_flair_id": None, "entry_point": "sidebar_navigation",
    "excluded_inline_media_ids": "[]", "fediverse_composer_enabled": True,
    "gif_media_id": None, "is_reply_approval_enabled": False, "is_spoiler_media": False,
    "link_attachment_url": None, "ranking_info_token": None, "reply_control": 0,
    "self_thread_context_id": str(uuid.uuid4()), "snippet_attachment": None,
    "special_effects_enabled_str": None, "tag_header": None,
    "text_with_entities": {"entities": [], "text": "тест с картинкой — удалю"},
}

def rnd_id(): return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
payload = {
    "caption":                  "тест с картинкой — удалю",
    "text_post_app_info":       json.dumps(app_info),
    "upload_id":                upload_id,
    "is_threads":               "true",
    "should_include_permalink": "true",
    "creator_geo_gating_info":  json.dumps({"whitelist_country_codes": []}),
    "web_session_id":           f"{rnd_id()}:{rnd_id()}:{rnd_id()}",
    "jazoest":                  jazoest(upload_id),
}

r2 = requests.post(
    "https://www.threads.com/api/v1/media/configure_text_post_app_feed/",
    headers={**HDRS_UPLOAD, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
             "Accept": "*/*"},
    data=payload, timeout=30)

print(f"Publish: {r2.status_code} → {r2.text[:500]}")
if r2.status_code == 200:
    pk = r2.json().get("media", {}).get("pk")
    print(f"✅ УСПЕХ! pk={pk} — проверь Threads, потом удали тестовый пост")
else:
    print("❌ Провал")