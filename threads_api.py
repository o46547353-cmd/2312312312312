"""
Threads API — браузерный формат (из DevTools).
Публикация через threads.com с браузерными заголовками.
"""
import os, time, json, random, uuid, requests
from dotenv import load_dotenv
load_dotenv()

SESSION_ID         = os.environ["THREADS_SESSION_ID"]
CSRF_TOKEN         = os.environ["THREADS_CSRF_TOKEN"]
USERNAME           = os.environ["THREADS_USERNAME"]
_HARDCODED_USER_ID = os.environ.get("THREADS_USER_ID", "")

# Android HEADERS — только для чтения (replies, stats, DM)
HEADERS = {
    "User-Agent":      "Barcelona 289.0.0.77.109 Android",
    "X-CSRFToken":     CSRF_TOKEN,
    "X-IG-App-ID":     "238260118697367",
    "Cookie":          f"sessionid={SESSION_ID}; csrftoken={CSRF_TOKEN}",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_cached_user_id      = None
_write_backoff_until = 0.0; _write_429_count = 0
_read_backoff_until  = 0.0; _read_429_count  = 0

def _check_write_backoff():
    rem = _write_backoff_until - time.time()
    if rem > 0: raise Exception(f"429: пауза на запись ещё {int(rem//60)+1} мин.")

def _check_read_backoff():
    rem = _read_backoff_until - time.time()
    if rem > 0: raise Exception(f"429: пауза на чтение ещё {int(rem//60)+1} мин.")

def _handle_write_429():
    global _write_429_count, _write_backoff_until
    _write_429_count += 1
    m = [30, 60, 120][min(_write_429_count - 1, 2)]
    _write_backoff_until = time.time() + m * 60
    raise Exception(f"429: постинг. Пауза {m} мин.")

def _handle_read_429():
    global _read_429_count, _read_backoff_until
    _read_429_count += 1
    m = [10, 20, 40][min(_read_429_count - 1, 2)]
    _read_backoff_until = time.time() + m * 60
    raise Exception(f"429: чтение. Пауза {m} мин.")

def _reset_write_429():
    global _write_429_count, _write_backoff_until
    _write_429_count = 0; _write_backoff_until = 0.0

def _reset_read_429():
    global _read_429_count, _read_backoff_until
    _read_429_count = 0; _read_backoff_until = 0.0

def _get_user_id() -> str:
    global _cached_user_id
    if _cached_user_id: return _cached_user_id
    if _HARDCODED_USER_ID:
        _cached_user_id = _HARDCODED_USER_ID; return _cached_user_id
    r = requests.get(
        f"https://i.instagram.com/api/v1/users/web_profile_info/?username={USERNAME}",
        headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"user_id: {r.status_code} {r.text[:200]}")
    _cached_user_id = r.json()["data"]["user"]["id"]
    return _cached_user_id

def _jazoest(s: str) -> str:
    return str(2 + sum(ord(c) for c in s))

def _browser_headers() -> dict:
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

def _upload_image(image_path: str) -> str:
    upload_id  = str(int(time.time() * 1000))
    upload_url = f"https://www.threads.com/rupload_igphoto/fb_uploader_{upload_id}"
    with open(image_path, "rb") as f:
        img_data = f.read()
    rupload_params = json.dumps({
        "upload_id":         upload_id,
        "media_type":        1,
        "image_compression": json.dumps({"lib_name": "moz", "lib_version": "3.1.m", "quality": "87"}),
        "xsharing_user_ids": json.dumps([]),
        "retry_context":     json.dumps({"num_step_auto_retry": 0, "num_reupload": 0, "num_step_manual_retry": 0}),
    })
    hdrs = _browser_headers()
    hdrs.update({
        "Content-Type":               "application/octet-stream",
        "X-Entity-Type":              "image/jpeg",
        "X-Entity-Length":            str(len(img_data)),
        "X-Entity-Name":              f"fb_uploader_{upload_id}",
        "X-Instagram-Rupload-Params": rupload_params,
        "Offset":                     "0",
    })
    r = requests.post(upload_url, headers=hdrs, data=img_data, timeout=60)
    print(f"[upload] {r.status_code} → {r.text[:200]}")
    if r.status_code not in (200, 201):
        raise Exception(f"Картинка upload: {r.status_code} {r.text[:300]}")
    return upload_id


# ── ПУБЛИКАЦИЯ ────────────────────────────────────────────────────────────────

def _post_single(text: str, reply_to_id: str = None, image_path: str = None) -> str:
    _check_write_backoff()
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

    has_image = False
    if image_path and os.path.exists(image_path):
        try:
            upload_id = _upload_image(image_path)
            has_image = True
            print(f"[img] загружена upload_id={upload_id}, жду обработки...")
            time.sleep(10)
        except Exception as e:
            print(f"[img] не загружена: {e}, постим без картинки")

    def rnd():
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))

    # Payload точно по DevTools — лишних полей нет
    if has_image:
        # F12 DevTools: пост с картинкой — configure_text_post_app_feed, статус 200
        url = "https://www.threads.com/api/v1/media/configure_text_post_app_feed/"
        payload = {
            "caption":                   text,
            "creator_geo_gating_info":   json.dumps({"whitelist_country_codes": []}),
            "jazoest":                   _jazoest(upload_id),
            "should_include_permalink":  "true",
            "text_post_app_info":        json.dumps(app_info),
            "upload_id":                 upload_id,
            "web_session_id":            f"{rnd()}:{rnd()}:{rnd()}",
            "is_threads":                "true",
        }
    else:
        # F12 DevTools: reply — configure_text_only_post, статус 200
        url = "https://www.threads.com/api/v1/media/configure_text_only_post/"
        payload = {
            "audience":                        "default",
            "caption":                         text,
            "creator_geo_gating_info":         json.dumps({"whitelist_country_codes": []}),
            "is_upload_type_override_allowed": "1",
            "jazoest":                         _jazoest(upload_id),
            "publish_mode":                    "text_post",
            "should_include_permalink":        "true",
            "text_post_app_info":              json.dumps(app_info),
            "upload_id":                       upload_id,
            "web_session_id":                  f"{rnd()}:{rnd()}:{rnd()}",
        }

    if reply_to_id:
        payload["barcelona_source_reply_id"] = str(reply_to_id)

    r = requests.post(url, headers=_browser_headers(), data=payload, timeout=30)
    print(f"[post] {r.status_code} reply_to={reply_to_id} has_image={has_image} → {r.text[:400]}")

    if r.status_code == 200:
        _reset_write_429()
        d  = r.json()
        pk = (d.get("media", {}).get("pk") or d.get("media", {}).get("id")
              or d.get("pk") or d.get("id"))
        print(f"[post] OK pk={pk}")
        return str(pk)
    elif r.status_code == 401:
        raise Exception("401: cookies устарели. Обнови SESSION_ID и CSRF_TOKEN")
    elif r.status_code == 429:
        _handle_write_429()
    else:
        raise Exception(f"Threads {r.status_code}: {r.text[:500]}")


def post_series(posts: dict, image_path: str = None) -> list:
    ids = []
    id1 = _post_single(posts["post1"], image_path=image_path)
    ids.append(id1); time.sleep(random.uniform(8, 12))
    id2 = _post_single(posts["post2"], reply_to_id=id1)
    ids.append(id2); time.sleep(random.uniform(8, 12))
    id3 = _post_single(posts["post3"], reply_to_id=id2)
    ids.append(id3); time.sleep(random.uniform(8, 12))
    id4 = _post_single(posts["post4"], reply_to_id=id3)
    ids.append(id4)
    return ids


def post_single_text(text: str) -> str:
    return _post_single(text)


# ── REPLIES ───────────────────────────────────────────────────────────────────

def get_all_comments(post_id: str) -> list:
    _check_read_backoff()
    for url in [
        f"https://www.threads.net/api/v1/text_feed/{post_id}/replies/",
        f"https://www.threads.net/api/v1/media/{post_id}/replies/",
        f"https://i.instagram.com/api/v1/media/{post_id}/replies/",
    ]:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"[replies] {r.status_code} ← {url.split('/api/v1/')[-1]}")
        if r.status_code == 429: _handle_read_429()
        if r.status_code != 200: continue
        _reset_read_429()
        comments = []
        for c in (r.json().get("replies") or r.json().get("items") or []):
            user = c.get("user") or c.get("owner") or {}
            text = c.get("text") or (c.get("caption") or {}).get("text") or ""
            uid  = str(user.get("pk") or user.get("id") or "")
            if not uid or not text: continue
            comments.append({
                "comment_id": str(c.get("pk") or c.get("id", "")),
                "user_id":    uid,
                "username":   user.get("username", ""),
                "text":       text,
            })
        print(f"[replies] найдено {len(comments)} replies")
        return comments
    raise Exception("Replies: ни один endpoint не ответил 200")


# ── DM ────────────────────────────────────────────────────────────────────────

def send_dm(user_id: str, text: str) -> bool:
    _check_write_backoff()
    r = requests.post(
        "https://i.instagram.com/api/v1/direct_v2/threads/broadcast/text/",
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "recipient_users": f"[[{user_id}]]",
            "action":          "send_item",
            "text":            text,
            "_uid":            _get_user_id(),
            "_csrftoken":      CSRF_TOKEN,
        }, timeout=15)
    if r.status_code == 429: _handle_write_429()
    if r.status_code == 200: _reset_write_429(); return True
    raise Exception(f"DM {r.status_code}: {r.text[:200]}")


# ── СТАТИСТИКА ────────────────────────────────────────────────────────────────

def get_post_stats(post_id: str) -> dict:
    _check_read_backoff()
    r = requests.get(
        f"https://www.threads.net/api/v1/media/{post_id}/info/",
        headers=HEADERS, timeout=15)
    if r.status_code == 429: _handle_read_429()
    if r.status_code != 200: raise Exception(f"Stats {post_id}: {r.status_code}")
    _reset_read_429()
    items = r.json().get("items", [])
    if not items: return {"post_id": post_id, "likes": 0, "replies": 0,
                          "reposts": 0, "quotes": 0, "views": 0, "caption": ""}
    item = items[0]; tpa = item.get("text_post_app_info") or {}
    return {
        "post_id":  post_id,
        "likes":    item.get("like_count", 0),
        "replies":  tpa.get("direct_reply_count", 0) or item.get("comment_count", 0),
        "reposts":  tpa.get("repost_count", 0),
        "quotes":   tpa.get("quote_count", 0),
        "views":    item.get("view_count", 0),
        "caption":  (item.get("caption") or {}).get("text", "")[:80],
    }


def get_profile_stats() -> dict:
    _check_read_backoff()
    r = requests.get(
        f"https://i.instagram.com/api/v1/users/web_profile_info/?username={USERNAME}",
        headers=HEADERS, timeout=15)
    if r.status_code == 429: _handle_read_429()
    if r.status_code != 200: raise Exception(f"Профиль: {r.status_code}")
    _reset_read_429()
    user = r.json().get("data", {}).get("user", {})
    return {
        "followers":   user.get("follower_count", 0),
        "following":   user.get("following_count", 0),
        "posts_count": user.get("media_count", 0),
        "username":    user.get("username", USERNAME),
    }
