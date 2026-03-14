"""
python3 test_img_post.py
Тестирует все варианты публикации поста с картинкой.
"""
import os, time, json, random, uuid, requests
from dotenv import load_dotenv
load_dotenv()

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ["THREADS_CSRF_TOKEN"]
USERNAME   = os.environ["THREADS_USERNAME"]
IMAGE_PATH = "slash_logo.jpg"

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

def upload():
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
    hdrs = browser_headers()
    hdrs.update({
        "Content-Type":               "application/octet-stream",
        "X-Entity-Type":              "image/jpeg",
        "X-Entity-Length":            str(len(img_data)),
        "X-Entity-Name":              f"fb_uploader_{upload_id}",
        "X-Instagram-Rupload-Params": rupload_params,
        "Offset":                     "0",
    })
    r = requests.post(f"https://www.threads.com/rupload_igphoto/fb_uploader_{upload_id}",
                      headers=hdrs, data=img_data, timeout=60)
    print(f"  upload: {r.status_code} → {r.text[:100]}")
    assert r.status_code in (200, 201), f"upload failed: {r.status_code}"
    return upload_id

def try_post(label, url, payload):
    print(f"\n[{label}]")
    print(f"  url: {url.split('threads.com')[-1]}")
    r = requests.post(url, headers=browser_headers(), data=payload, timeout=30)
    print(f"  status: {r.status_code}")
    print(f"  response: {r.text[:300]}")
    if r.status_code == 200:
        pk = r.json().get("media", {}).get("pk")
        print(f"  ✅ УСПЕХ pk={pk}")
        return pk
    return None

def base_payload(upload_id, text, app_info):
    return {
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

def app_info_base(text):
    return {
        "entry_point":                "sidebar_navigation",
        "excluded_inline_media_ids":  "[]",
        "fediverse_composer_enabled": True,
        "is_reply_approval_enabled":  False,
        "is_spoiler_media":           False,
        "reply_control":              0,
        "self_thread_context_id":     str(uuid.uuid4()),
        "text_with_entities":         {"entities": [], "text": text},
    }

TEXT = "тест с картинкой — удалю"

# ── Вариант A: configure_text_only_post + source_type=4 (работал в старом тесте E)
print("=" * 60)
print("Загружаю картинку для варианта A...")
uid = upload()
time.sleep(10)
p = base_payload(uid, TEXT, app_info_base(TEXT))
p["source_type"] = "4"
pk = try_post("A: text_only_post + source_type=4",
              "https://www.threads.com/api/v1/media/configure_text_only_post/", p)
if pk:
    print(f"\n✅ ВАРИАНТ A РАБОТАЕТ. Используй text_only_post + source_type=4")
    raise SystemExit(0)

time.sleep(5)

# ── Вариант B: configure_text_post_app_feed без лишних полей
print("\n" + "=" * 60)
print("Загружаю картинку для варианта B...")
uid = upload()
time.sleep(10)
p = base_payload(uid, TEXT, app_info_base(TEXT))
pk = try_post("B: text_post_app_feed (без source_type/media_type)",
              "https://www.threads.com/api/v1/media/configure_text_post_app_feed/", p)
if pk:
    print(f"\n✅ ВАРИАНТ B РАБОТАЕТ.")
    raise SystemExit(0)

time.sleep(5)

# ── Вариант C: configure_text_post_app_feed + source_type + media_type
print("\n" + "=" * 60)
print("Загружаю картинку для варианта C...")
uid = upload()
time.sleep(10)
p = base_payload(uid, TEXT, app_info_base(TEXT))
p["source_type"] = "4"
p["media_type"]  = "1"
pk = try_post("C: text_post_app_feed + source_type=4 + media_type=1",
              "https://www.threads.com/api/v1/media/configure_text_post_app_feed/", p)
if pk:
    print(f"\n✅ ВАРИАНТ C РАБОТАЕТ.")
    raise SystemExit(0)

time.sleep(5)

# ── Вариант D: configure_text_post_app_feed + is_unified_inbox_post
print("\n" + "=" * 60)
print("Загружаю картинку для варианта D...")
uid = upload()
time.sleep(10)
p = base_payload(uid, TEXT, app_info_base(TEXT))
p["source_type"]             = "4"
p["media_type"]              = "1"
p["is_unified_inbox_post"]   = "0"
pk = try_post("D: + is_unified_inbox_post=0",
              "https://www.threads.com/api/v1/media/configure_text_post_app_feed/", p)
if pk:
    print(f"\n✅ ВАРИАНТ D РАБОТАЕТ.")
    raise SystemExit(0)

print("\n❌ Все варианты провалились.")
