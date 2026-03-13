import json
import os
from datetime import datetime, timedelta

FILE = "storage.json"

_DEFAULTS = {
    "queue":          [],
    "archive":        [],   # опубликованные серии с метаданными
    "settings":       {"interval_hours": 4, "active": False},
    "image_path":     None,
    "dm_text":        "Привет! Держи ссылку на SLASH VPN 👉 https://t.me/slash_vpn_bot",
    "dm_active":      False,
    "messaged_users": [],   # [{"user_id": "...", "username": "...", "ts": "..."}]
    "watched_posts":  [],   # post_id которые мониторим
    "pending_dm":     [],   # [{"user_id": "...", "username": "...", "post_id": "..."}]
                            # кто написал +, но DM ещё не получил
    "auto_topics":    [],   # список тем для авто-генерации
    "topic_index":    0,    # индекс следующей темы
}


def _load() -> dict:
    if not os.path.exists(FILE):
        return {k: v for k, v in _DEFAULTS.items()}
    with open(FILE, encoding="utf-8") as f:
        data = json.load(f)
    for k, v in _DEFAULTS.items():
        data.setdefault(k, v if not isinstance(v, list) else list(v))
    # Миграция: старый posted → archive
    if "posted" in data and data["posted"]:
        for item in data["posted"]:
            item.setdefault("posted_at", datetime.now().isoformat())
        data["archive"].extend(data.pop("posted"))
        _save(data)
    return data


def _save(d: dict):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ── Очередь ───────────────────────────────────────────────────────────────────

def add_series(series: dict):
    d = _load()
    d["queue"].append({"type": "series", "posts": series,
                        "added": datetime.now().isoformat()})
    _save(d)


def add(text: str):
    d = _load()
    d["queue"].append({"type": "single", "text": text,
                        "added": datetime.now().isoformat()})
    _save(d)


def pop() -> dict | None:
    d = _load()
    if not d["queue"]:
        return None
    item = d["queue"].pop(0)
    _save(d)
    return item


def count() -> int:
    return len(_load()["queue"])


# ── Архив ─────────────────────────────────────────────────────────────────────

def archive_item(item: dict, post_ids: list = None):
    """Кладёт опубликованный элемент в архив с временной меткой."""
    d = _load()
    d["archive"].append({
        **item,
        "posted_at":  datetime.now().isoformat(),
        "post_ids":   [str(x) for x in (post_ids or [])],
    })
    _save(d)


def get_archive(limit: int = 20) -> list:
    return _load()["archive"][-limit:]


# ── Настройки ─────────────────────────────────────────────────────────────────

def get_setting(key):
    return _load()["settings"].get(key)


def set_setting(key, value):
    d = _load()
    d["settings"][key] = value
    _save(d)


def set_image(path: str):
    d = _load()
    d["image_path"] = path
    _save(d)


def get_image() -> str | None:
    return _load().get("image_path")


# ── DM ────────────────────────────────────────────────────────────────────────

def set_dm_active(value: bool):
    d = _load()
    d["dm_active"] = value
    _save(d)


def get_dm_active() -> bool:
    return _load().get("dm_active", False)


def set_dm_text(text: str):
    d = _load()
    d["dm_text"] = text
    _save(d)


def get_dm_text() -> str:
    return _load().get("dm_text", "")


def was_messaged(user_id: str) -> bool:
    return any(str(u.get("user_id", u) if isinstance(u, dict) else u) == str(user_id)
               for u in _load().get("messaged_users", []))


def mark_messaged(user_id: str, username: str = ""):
    d = _load()
    if not was_messaged(user_id):
        d["messaged_users"].append({
            "user_id":  str(user_id),
            "username": username,
            "ts":       datetime.now().isoformat(),
        })
        # убираем из pending если был там
        d["pending_dm"] = [p for p in d["pending_dm"]
                           if str(p.get("user_id")) != str(user_id)]
        _save(d)


def get_messaged_count() -> int:
    return len(_load().get("messaged_users", []))


# ── Pending DM (написали +, но DM ещё не получили) ───────────────────────────

def add_pending_dm(user_id: str, username: str, post_id: str):
    d = _load()
    uid = str(user_id)
    already_pending  = any(str(p.get("user_id")) == uid for p in d["pending_dm"])
    already_messaged = was_messaged(uid)
    if not already_pending and not already_messaged:
        d["pending_dm"].append({
            "user_id":  uid,
            "username": username,
            "post_id":  str(post_id),
            "added":    datetime.now().isoformat(),
        })
        _save(d)


def get_pending_dm() -> list:
    return _load().get("pending_dm", [])


def get_pending_count() -> int:
    return len(_load().get("pending_dm", []))


def clear_pending_dm():
    d = _load()
    d["pending_dm"] = []
    _save(d)


# ── Мониторинг постов ─────────────────────────────────────────────────────────

def add_watched_post(post_id: str):
    d = _load()
    if str(post_id) not in [str(x) for x in d["watched_posts"]]:
        d["watched_posts"].append(str(post_id))
    _save(d)


def get_watched_posts() -> list:
    return [str(x) for x in _load().get("watched_posts", [])]


def remove_watched_post(post_id: str):
    d = _load()
    d["watched_posts"] = [x for x in d["watched_posts"] if str(x) != str(post_id)]
    _save(d)


# ── Авто-темы ─────────────────────────────────────────────────────────────────

def get_auto_topics() -> list:
    return _load().get("auto_topics", [])


def add_auto_topic(topic: str):
    d = _load()
    d.setdefault("auto_topics", [])
    if topic not in d["auto_topics"]:
        d["auto_topics"].append(topic)
    _save(d)


def remove_auto_topic(index: int):
    d = _load()
    topics = d.get("auto_topics", [])
    if 0 <= index < len(topics):
        topics.pop(index)
        if topics:
            d["topic_index"] = d.get("topic_index", 0) % len(topics)
        else:
            d["topic_index"] = 0
        d["auto_topics"] = topics
        _save(d)


def next_auto_topic() -> str | None:
    """Возвращает следующую тему по кругу и сдвигает индекс."""
    d = _load()
    topics = d.get("auto_topics", [])
    if not topics:
        return None
    idx = d.get("topic_index", 0) % len(topics)
    topic = topics[idx]
    d["topic_index"] = (idx + 1) % len(topics)
    _save(d)
    return topic


# ── Статистика ────────────────────────────────────────────────────────────────

def get_stats(hours: int = 24) -> dict:
    d     = _load()
    since = datetime.now() - timedelta(hours=hours)

    def after(ts_str):
        try:
            return datetime.fromisoformat(ts_str) >= since
        except Exception:
            return False

    posts_published = sum(1 for a in d["archive"] if after(a.get("posted_at", "")))
    dm_sent         = sum(1 for u in d["messaged_users"]
                          if isinstance(u, dict) and after(u.get("ts", "")))

    return {
        "period_hours":     hours,
        "posts_published":  posts_published,
        "dm_sent":          dm_sent,
        "queue_now":        len(d["queue"]),
        "total_published":  len(d["archive"]),
        "total_dm_sent":    len(d["messaged_users"]),
        "pending_dm":       len(d["pending_dm"]),
        "watched_posts":    len(d["watched_posts"]),
    }