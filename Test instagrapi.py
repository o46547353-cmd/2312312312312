"""
python test_instagrapi.py POST_PK
"""
import os, sys, json, time, random
from dotenv import load_dotenv
load_dotenv(r"C:\threads\.env")

SESSION_ID = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN = os.environ.get("THREADS_CSRF_TOKEN", "")
USER_ID    = os.environ["THREADS_USER_ID"]
USERNAME   = os.environ["THREADS_USERNAME"]

from instagrapi import Client
from instagrapi import extractors as _ext

# Патч
_orig_user_v1 = _ext.extract_user_v1
def _safe_user_v1(data):
    data.setdefault("pinned_channels_info", {"pinned_channels_list": []})
    data.setdefault("is_business", False)
    data.setdefault("broadcast_channel", None)
    try:
        return _orig_user_v1(data)
    except Exception:
        from instagrapi.types import User
        clean = {k: v for k, v in data.items() if k in User.__fields__}
        return _orig_user_v1(clean)
_ext.extract_user_v1 = _safe_user_v1

cl = Client()
cl.set_settings({
    "uuids": {
        "phone_id":          "12345678-1234-1234-1234-123456789abc",
        "uuid":              "12345678-1234-1234-1234-123456789abd",
        "client_session_id": "12345678-1234-1234-1234-123456789abe",
        "advertising_id":    "12345678-1234-1234-1234-123456789abf",
    },
    "cookies": {"sessionid": SESSION_ID, "csrftoken": CSRF_TOKEN},
    "authorization_data": {},
    "device_settings": cl.device,
    "user_agent":      cl.user_agent,
})
cl._user_id = str(USER_ID)
cl.username = USERNAME

# Смотрим доступные методы для threads
methods = [m for m in dir(cl) if 'thread' in m.lower() or 'reply' in m.lower()]
print("\nМетоды client с thread/reply:")
for m in methods:
    print(f"  {m}")

parent_pk = sys.argv[1] if len(sys.argv) > 1 else input("\npost_id для теста reply: ").strip()

# Пробуем опубликовать reply
print(f"\n[1] Пробую media_upload_to_threads с replied_to_media_id...")
try:
    m = cl.media_upload_to_threads("test reply через instagrapi", replied_to_media_id=parent_pk)
    print(f"    OK pk={m.pk}")
except Exception as e:
    print(f"    Ошибка: {e}")

time.sleep(3)

print(f"\n[2] Пробую через private_request напрямую...")
try:
    result = cl.private_request(
        "media/configure_text_only_post/",
        {
            "text_post_app_info": json.dumps({"reply_control": 0}),
            "caption":            "test reply via private_request",
            "_uid":               USER_ID,
            "_csrftoken":         CSRF_TOKEN,
            "device_id":          f"android-{random.randint(0x100000000000, 0xffffffffffff):012x}",
            "publish_mode":       "text_post",
            "replied_to_post_id": parent_pk,
        }
    )
    print(f"    OK: {json.dumps(result)[:200]}")
except Exception as e:
    print(f"    Ошибка: {e}")