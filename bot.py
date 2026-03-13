import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import ai_gen, storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
load_dotenv()

BOT_TOKEN      = os.environ["BOT_TOKEN"]
OWNER_ID       = int(os.environ["OWNER_ID"])
scheduler      = AsyncIOScheduler()
_waiting_image = False


def owner_only(fn):
    async def wrap(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if upd.effective_user.id != OWNER_ID:
            return
        return await fn(upd, ctx)
    return wrap


# ─── /start ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_start(upd, ctx):
    await upd.message.reply_text("👋 Бот для постинга в Threads.\n/pomosch — полный гайд.")


# ─── /app — кнопка мини-аппа ─────────────────────────────────────────────────
@owner_only
async def cmd_app(upd, ctx):
    import os
    url = os.environ.get("MINIAPP_URL", "").strip()
    if not url:
        await upd.message.reply_text(
            "⚠️ MINIAPP_URL не задан в .env\n\n"
            "Добавь строку:\nMINIAPP_URL=https://твой-домен.com\n\n"
            "Для теста можно использовать ngrok:\n"
            "ngrok http 8000  →  скопируй HTTPS ссылку"
        )
        return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Открыть панель управления", web_app=WebAppInfo(url=url))
    ]])
    await upd.message.reply_text(
        "SLASH VPN — Control Panel", reply_markup=kb
    )


# ─── /pomosch ─────────────────────────────────────────────────────────────────
@owner_only
async def cmd_help(upd, ctx):
    await upd.message.reply_text("""📖 ГАЙД ПО БОТУ

🚀 Мини-апп: /app — вся панель управления в одном окне

━━━━━━━━━━━━━━━━
📝 ПУБЛИКАЦИЯ
━━━━━━━━━━━━━━━━

/seriya [тема]
  Генерирует серию из 4 постов и добавляет в очередь.
  Пример: /seriya жизнь без VPN

/post1 [тема]
  Генерирует и сразу публикует ОДИН пост.
  Пример: /post1 почему все используют VPN

/pokazat — посмотреть первую серию в очереди
/publikovat — опубликовать первую серию вручную
  ⏳ ~2 минуты. После публикации серия уходит в архив.
/ochered — сколько серий ждёт публикации
/arhiv — последние 10 опубликованных серий

━━━━━━━━━━━━━━━━
🤖 АВТОПОСТИНГ
━━━━━━━━━━━━━━━━

/avto vkl — включить автопостинг
/avto off — выключить
/interval [часы] — интервал между постами
  Пример: /interval 6 → публикация раз в 6 часов

Бот публикует из очереди. Если очередь пуста —
сам генерирует серию по следующей теме из списка.

━━━━━━━━━━━━━━━━
🎯 АВТО-ТЕМЫ
━━━━━━━━━━━━━━━━

/tema — список всех тем (и какая следующая)
/tema добавить <тема> — добавить тему
/tema удалить <номер> — удалить тему
/tema очистить — удалить все темы

Пример:
  /tema добавить жизнь без VPN
  /tema добавить зачем нужен VPN в 2025
  /tema добавить как защитить трафик

Темы используются по кругу автоматически.

━━━━━━━━━━━━━━━━
🖼 КАРТИНКА
━━━━━━━━━━━━━━━━

Картинка прикрепляется к 3-му посту каждой серии.

1. Напиши /kartinka
2. Отправь JPG как ФОТО (не файлом!)
3. Бот подтвердит сохранение

Картинка хранится и используется во всех следующих сериях.
Обновить в любой момент: снова /kartinka → новое фото.

━━━━━━━━━━━━━━━━
💬 АВТООТВЕТ НА +
━━━━━━━━━━━━━━━━

Бот каждые 30 мин сканирует все комментарии ко всем постам.
Кто написал + в комментарии — получает DM автоматически.
Каждый человек получает сообщение только один раз.

/avtootvet vkl — включить автоответ
/avtootvet off — выключить
/soobschenie [текст] — задать текст DM
  Пример: /soobschenie Привет! Вот ссылка: t.me/slash_vpn_bot
  Без аргумента — показывает текущий текст.

/check — вручную просканировать все комментарии прямо сейчас.
  Показывает всех, кто написал +, и кнопку для немедленной рассылки.

/razoslat — отправить DM тем, кто уже в очереди ожидания.
  (Попали туда если автоответ был выкл или DM не дошёл)

/status_dm — статистика: сколько DM отправлено, кто ждёт.

━━━━━━━━━━━━━━━━
📊 СТАТИСТИКА
━━━━━━━━━━━━━━━━

/stats — статистика бота за 24 ч и 7 дней:
  посты, DM, очередь, архив

/stats_threads — живая статистика из Threads за 24 ч:
  👁 просмотры, ❤️ лайки, 💬 ответы, 🔁 репосты
  по каждому посту серии + итого

/status — общее состояние бота одной строкой

━━━━━━━━━━━━━━━━
⚡️ БЫСТРЫЙ СТАРТ
━━━━━━━━━━━━━━━━

1. /kartinka → отправь фото логотипа
2. /soobschenie Привет! Вот ссылка: t.me/slash_vpn_bot
3. Нагенерируй серии: /seriya тема1, /seriya тема2...
4. /avto vkl + /interval 6
5. /avtootvet vkl
6. Готово — бот постит и отвечает на + сам 🚀""")


# ─── /seriya ──────────────────────────────────────────────────────────────────
@owner_only
async def cmd_series(upd, ctx):
    topic = " ".join(ctx.args) if ctx.args else ""
    if not topic:
        await upd.message.reply_text("Укажи тему. Пример: /seriya жизнь без VPN")
        return
    msg = await upd.message.reply_text(f"⏳ Генерирую: «{topic}»...")
    try:
        series = await asyncio.to_thread(ai_gen.generate_series, topic)
        storage.add_series(series)
        preview = (
            f"✅ Добавлено в очередь ({storage.count()} шт.)\n\n"
            f"📌 Пост 1:\n{series['post1']}\n\n"
            f"📌 Пост 2:\n{series['post2']}\n\n..."
        )
        await msg.edit_text(preview[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка генерации: {e}")


# ─── /post1 — одиночный пост ──────────────────────────────────────────────────
@owner_only
async def cmd_post1(upd, ctx):
    topic = " ".join(ctx.args) if ctx.args else ""
    if not topic:
        await upd.message.reply_text("Укажи тему. Пример: /post1 почему VPN необходим")
        return
    msg = await upd.message.reply_text(f"⏳ Генерирую пост: «{topic}»...")
    try:
        series = await asyncio.to_thread(ai_gen.generate_series, topic)
        text   = series["post1"]
        await msg.edit_text(f"📝 Текст поста:\n\n{text}\n\n⏳ Публикую...")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка генерации: {e}")
        return
    try:
        from threads_api import post_single_text
        post_id = await asyncio.to_thread(post_single_text, text)
        item = {"type": "single", "text": text}
        storage.archive_item(item, [post_id])
        storage.add_watched_post(post_id)
        await msg.edit_text(f"✅ Опубликовано!\n\n{text[:300]}")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка публикации: {e}")


# ─── /pokazat ─────────────────────────────────────────────────────────────────
@owner_only
async def cmd_showseries(upd, ctx):
    queue = storage._load().get("queue", [])
    if not queue:
        await upd.message.reply_text("📭 Очередь пуста")
        return
    item = queue[0]
    if item.get("type") == "series":
        s    = item["posts"]
        text = (f"📌 Пост 1:\n{s['post1']}\n\n"
                f"📌 Пост 2:\n{s['post2']}\n\n"
                f"📌 Пост 3:\n{s['post3']}\n\n"
                f"📌 Пост 4:\n{s['post4']}")
    else:
        text = item.get("text", "")
    await upd.message.reply_text(text[:4000])


# ─── /publikovat ──────────────────────────────────────────────────────────────
@owner_only
async def cmd_postseries(upd, ctx):
    item = storage.pop()
    if not item:
        await upd.message.reply_text("📭 Очередь пуста")
        return
    msg = await upd.message.reply_text("⏳ Публикую в Threads... (1–2 минуты)")
    try:
        from threads_api import post_series, post_single_text
        image    = storage.get_image()
        post_ids = []
        if item.get("type") == "series":
            post_ids = await asyncio.to_thread(post_series, item["posts"], image)
        else:
            pid = await asyncio.to_thread(post_single_text, item["text"])
            post_ids = [pid]
        storage.archive_item(item, post_ids)
        if post_ids:
            storage.add_watched_post(post_ids[0])
        await msg.edit_text(
            f"✅ Опубликовано! Осталось: {storage.count()} шт."
        )
    except Exception as e:
        if item.get("type") == "series":
            storage.add_series(item["posts"])
        else:
            storage.add(item.get("text", ""))
        try:
            await msg.edit_text(f"❌ Ошибка: {str(e)[:300]}")
        except Exception:
            await upd.message.reply_text(f"❌ Ошибка: {str(e)[:300]}")


# ─── /kartinka ────────────────────────────────────────────────────────────────
@owner_only
async def cmd_setimage(upd, ctx):
    global _waiting_image
    _waiting_image = True
    await upd.message.reply_text(
        "🖼 Жду картинку.\nОтправь JPG как ФОТО (не файлом!)."
    )


async def handle_photo(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _waiting_image
    if upd.effective_user.id != OWNER_ID or not _waiting_image:
        return
    photo = upd.message.photo[-1]
    file  = await ctx.bot.get_file(photo.file_id)
    path  = "slash_logo.jpg"
    await file.download_to_drive(path)
    storage.set_image(path)
    _waiting_image = False
    await upd.message.reply_text("✅ Картинка сохранена!")


# ─── /ochered ─────────────────────────────────────────────────────────────────
@owner_only
async def cmd_queue(upd, ctx):
    n = storage.count()
    await upd.message.reply_text(
        "📭 Очередь пуста" if n == 0 else f"📋 В очереди: {n} серий"
    )


# ─── /arhiv ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_archive(upd, ctx):
    items = storage.get_archive(10)
    if not items:
        await upd.message.reply_text("📂 Архив пуст")
        return
    lines = []
    for i, item in enumerate(reversed(items), 1):
        ts    = item.get("posted_at", "")[:16].replace("T", " ")
        label = (item.get("posts", {}).get("post1") or item.get("text") or "—")[:60]
        lines.append(f"{i}. [{ts}]\n{label}...")
    await upd.message.reply_text("📂 Последние 10 публикаций:\n\n" + "\n\n".join(lines))


# ─── /avto ────────────────────────────────────────────────────────────────────
@owner_only
async def cmd_auto(upd, ctx):
    if not ctx.args:
        await upd.message.reply_text("Используй: /avto vkl  или  /avto off")
        return
    state = ctx.args[0].lower()
    if state in ("vkl", "on", "вкл"):
        storage.set_setting("active", True)
        _start_post_scheduler(ctx.application)
        h = storage.get_setting("interval_hours") or 4
        await upd.message.reply_text(f"✅ Автопостинг вкл (каждые {h} ч.)")
    elif state in ("off", "выкл"):
        storage.set_setting("active", False)
        if scheduler.get_job("post_job"):
            scheduler.remove_job("post_job")
        await upd.message.reply_text("⏹ Автопостинг выкл")
    else:
        await upd.message.reply_text("Используй: /avto vkl  или  /avto off")


# ─── /interval ────────────────────────────────────────────────────────────────
@owner_only
async def cmd_interval(upd, ctx):
    if not ctx.args or not ctx.args[0].isdigit():
        await upd.message.reply_text("Пример: /interval 6")
        return
    h = int(ctx.args[0])
    storage.set_setting("interval_hours", h)
    if storage.get_setting("active"):
        scheduler.remove_all_jobs()
        _start_post_scheduler(ctx.application)
    await upd.message.reply_text(f"✅ Интервал: {h} ч.")


# ─── /avtootvet ───────────────────────────────────────────────────────────────
@owner_only
async def cmd_dm_toggle(upd, ctx):
    if not ctx.args:
        await upd.message.reply_text("Используй: /avtootvet vkl  или  /avtootvet off")
        return
    state = ctx.args[0].lower()
    if state in ("vkl", "on", "вкл"):
        storage.set_dm_active(True)
        _start_dm_scheduler(ctx.application)
        await upd.message.reply_text(
            f"✅ Автоответ вкл!\nТекст: «{storage.get_dm_text()}»\n"
            "Изменить: /soobschenie [текст]"
        )
    elif state in ("off", "выкл"):
        storage.set_dm_active(False)
        if scheduler.get_job("dm_job"):
            scheduler.remove_job("dm_job")
        await upd.message.reply_text("⏹ Автоответ выкл")
    else:
        await upd.message.reply_text("Используй: /avtootvet vkl  или  /avtootvet off")


# ─── /soobschenie ─────────────────────────────────────────────────────────────
@owner_only
async def cmd_set_dm_text(upd, ctx):
    if not ctx.args:
        await upd.message.reply_text(
            f"Текущий DM:\n«{storage.get_dm_text()}»\n\nИзменить: /soobschenie [текст]"
        )
        return
    text = " ".join(ctx.args)
    storage.set_dm_text(text)
    await upd.message.reply_text(f"✅ DM обновлён:\n«{text}»")


# ─── /checkraw — диагностика endpoint replies ────────────────────────────────
@owner_only
async def cmd_checkraw(upd, ctx):
    """Показывает сырой ответ от каждого endpoint для replies."""
    import requests as req
    from threads_api import HEADERS

    watched = storage.get_watched_posts()
    # Если передан post_id как аргумент — используем его
    if ctx.args:
        post_id = ctx.args[0]
    elif watched:
        post_id = watched[-1]
    else:
        await upd.message.reply_text(
            "Нет постов в мониторинге.\n"
            "Передай post_id вручную: /checkraw 3851610140369770444"
        )
        return

    msg = await upd.message.reply_text(f"🔍 Тестирую endpoints для:\n{post_id}")

    endpoints = [
        f"https://www.threads.net/api/v1/text_feed/{post_id}/replies/",
        f"https://www.threads.net/api/v1/media/{post_id}/replies/",
        f"https://i.instagram.com/api/v1/media/{post_id}/replies/",
        f"https://www.threads.net/api/v1/media/{post_id}/comments/",
        f"https://www.threads.net/api/v1/text_feed/{post_id}/text_replies/",
    ]

    lines = [f"Post: {post_id}"]
    for url in endpoints:
        try:
            r = await asyncio.to_thread(
                lambda u=url: req.get(u, headers=HEADERS, timeout=10)
            )
            short = url.split("/api/v1/")[-1]
            # Показываем ключи ответа если 200
            if r.status_code == 200:
                try:
                    keys = list(r.json().keys())
                    body = f"keys={keys}"
                    # Пробуем найти поле с комментами
                    d = r.json()
                    for k in ["replies","comments","items","threads","data"]:
                        if k in d:
                            count = len(d[k]) if isinstance(d[k], list) else "?"
                            body += f" | {k}={count} items"
                            if isinstance(d[k], list) and d[k]:
                                sample = d[k][0]
                                body += f" | sample_keys={list(sample.keys())[:6]}"
                            break
                except Exception:
                    body = r.text[:150]
                lines.append(f"\n✅ {r.status_code} /{short}\n   {body}")
            else:
                lines.append(f"\n❌ {r.status_code} /{short}")
        except Exception as e:
            short = url.split("/api/v1/")[-1]
            lines.append(f"\n💥 /{short}\n   {str(e)[:80]}")
        await asyncio.sleep(1)

    await msg.edit_text("\n".join(lines)[:4000])


# ─── /check — ручная проверка всех + в комментариях ──────────────────────────
@owner_only
async def cmd_check(upd, ctx):
    watched = storage.get_watched_posts()
    if not watched:
        await upd.message.reply_text(
            "📭 Нет постов для проверки.\n\n"
            "Посты добавляются в мониторинг автоматически после публикации."
        )
        return

    msg = await upd.message.reply_text(
        f"🔍 Сканирую {len(watched)} постов на + в комментариях..."
    )

    from threads_api import get_all_comments
    found    = []  # [(user_id, username, post_id)]
    errors   = []
    new_pending = 0

    for post_id in watched:
        try:
            comments = await asyncio.to_thread(get_all_comments, post_id)
            await asyncio.sleep(1)
            for c in comments:
                if "+" not in c["text"]:
                    continue
                uid  = c["user_id"]
                uname = c.get("username", "")
                if not uid:
                    continue
                found.append((uid, uname, post_id))
                if not storage.was_messaged(uid):
                    storage.add_pending_dm(uid, uname, post_id)
                    new_pending += 1
        except Exception as e:
            errors.append(f"пост {post_id}: {e}")

    pending = storage.get_pending_dm()

    # Формируем сообщение
    if not found:
        result = "🔍 Комментариев с + не найдено."
    else:
        already = len(found) - new_pending
        names   = ", ".join(
            f"@{u}" if u else f"id{uid}"
            for uid, u, _ in found[:15]
        )
        suffix  = f" и ещё {len(found)-15}..." if len(found) > 15 else ""
        result  = (
            f"✅ Найдено + : {len(found)} чел.\n"
            f"   Уже получили DM: {already}\n"
            f"   Ожидают DM: {len(pending)}\n\n"
            f"{names}{suffix}"
        )
    if errors:
        result += f"\n\n⚠️ Ошибки ({len(errors)}): {'; '.join(errors[:3])}"

    if pending:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"📨 Отправить DM {len(pending)} чел.", callback_data="blast_confirm"
            ),
            InlineKeyboardButton("❌ Отмена", callback_data="blast_cancel"),
        ]])
        await msg.edit_text(result, reply_markup=kb)
    else:
        await msg.edit_text(result)


# ─── /razoslat — принудительная рассылка ─────────────────────────────────────
@owner_only
async def cmd_blast(upd, ctx):
    pending = storage.get_pending_dm()
    if not pending:
        await upd.message.reply_text(
            "📭 Нет ожидающих рассылки.\n\nИспользуй /check чтобы найти всех, кто написал +"
        )
        return
    names  = ", ".join(
        f"@{p['username']}" if p.get("username") else f"id{p['user_id']}"
        for p in pending[:10]
    )
    suffix = f" и ещё {len(pending)-10}..." if len(pending) > 10 else ""
    kb     = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"📨 Отправить DM {len(pending)} чел.", callback_data="blast_confirm"
        ),
        InlineKeyboardButton("❌ Отмена", callback_data="blast_cancel"),
    ]])
    await upd.message.reply_text(
        f"📨 Ожидают DM: {len(pending)} чел.\n{names}{suffix}\n\n"
        f"Текст:\n«{storage.get_dm_text()}»",
        reply_markup=kb,
    )


async def callback_blast(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = upd.callback_query
    if upd.effective_user.id != OWNER_ID:
        await query.answer("Нет доступа")
        return
    await query.answer()

    if query.data == "blast_cancel":
        await query.edit_message_text("❌ Рассылка отменена")
        return

    pending = storage.get_pending_dm()
    if not pending:
        await query.edit_message_text("📭 Список уже пуст")
        return

    from threads_api import send_dm
    dm_text = storage.get_dm_text()
    await query.edit_message_text(f"⏳ Отправляю DM {len(pending)} чел....")

    sent = failed = 0
    for p in pending:
        try:
            await asyncio.to_thread(send_dm, p["user_id"], dm_text)
            storage.mark_messaged(p["user_id"], p.get("username", ""))
            sent += 1
            await asyncio.sleep(2)
        except Exception as e:
            logging.warning(f"Blast DM @{p.get('username')}: {e}")
            failed += 1

    await query.edit_message_text(
        f"✅ Рассылка завершена!\n📨 Отправлено: {sent}\n❌ Ошибок: {failed}"
    )


# ─── /status_dm ───────────────────────────────────────────────────────────────
@owner_only
async def cmd_dm_status(upd, ctx):
    active  = storage.get_dm_active()
    total   = storage.get_messaged_count()
    pending = storage.get_pending_count()
    watched = len(storage.get_watched_posts())
    await upd.message.reply_text(
        f"💬 Статус автоответа\n\n"
        f"Автоответ: {'✅ вкл' if active else '⏹ выкл'}\n"
        f"Постов в мониторинге: {watched}\n"
        f"Ожидают DM: {pending} чел. → /razoslat\n"
        f"DM отправлено всего: {total} чел.\n\n"
        f"Текст:\n«{storage.get_dm_text()}»\n\n"
        f"Ручная проверка комментариев: /check"
    )


# ─── /stats ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_stats(upd, ctx):
    s24  = storage.get_stats(24)
    s168 = storage.get_stats(24 * 7)
    await upd.message.reply_text(
        f"📊 СТАТИСТИКА\n\n"
        f"━━━━━━ За 24 часа ━━━━━━\n"
        f"📤 Опубликовано: {s24['posts_published']}\n"
        f"📨 DM отправлено: {s24['dm_sent']}\n\n"
        f"━━━━━━ За 7 дней ━━━━━━\n"
        f"📤 Опубликовано: {s168['posts_published']}\n"
        f"📨 DM отправлено: {s168['dm_sent']}\n\n"
        f"━━━━━━ Сейчас ━━━━━━\n"
        f"📋 В очереди: {s24['queue_now']}\n"
        f"📂 В архиве: {s24['total_published']}\n"
        f"📨 DM всего: {s24['total_dm_sent']} чел.\n"
        f"⏳ Ожидают DM: {s24['pending_dm']} чел.\n"
        f"👀 Постов в мониторинге: {s24['watched_posts']}\n\n"
        f"Принудительная рассылка: /razoslat\n"
        f"Ручная проверка: /check\n"
        f"Статистика Threads: /stats_threads"
    )


# ─── /stats_threads ───────────────────────────────────────────────────────────
@owner_only
async def cmd_stats_threads(upd, ctx):
    from threads_api import get_post_stats, get_profile_stats
    from datetime import datetime, timedelta

    msg = await upd.message.reply_text("⏳ Запрашиваю статистику из Threads...")
    lines = []

    # Профиль
    try:
        profile = await asyncio.to_thread(get_profile_stats)
        lines.append(
            "👤 @" + profile["username"] + "\n"
            "   Подписчики: " + f"{profile['followers']:,}" + "\n"
            "   Постов: " + f"{profile['posts_count']:,}"
        )
    except Exception as e:
        lines.append(f"👤 Профиль: {e}")

    # Посты за 24ч
    since_24h = datetime.now() - timedelta(hours=24)
    all_items = storage.get_archive(50)
    recent    = [
        item for item in all_items
        if item.get("post_ids")
        and datetime.fromisoformat(item.get("posted_at", "2000-01-01")) >= since_24h
    ]

    if recent:
        lines.append("")
        lines.append(f"📊 Серии за 24 ч ({len(recent)} шт.):")
        total_views = total_likes = total_replies = total_reposts = 0

        for item in recent:
            post_ids = item.get("post_ids", [])
            ts       = item.get("posted_at", "")[:16].replace("T", " ")
            caption  = ""
            s_views = s_likes = s_replies = s_reposts = 0
            errors  = 0

            for pid in post_ids:
                try:
                    await asyncio.sleep(0.8)
                    stat = await asyncio.to_thread(get_post_stats, pid)
                    s_views   += stat.get("views",   0)
                    s_likes   += stat.get("likes",   0)
                    s_replies += stat.get("replies", 0)
                    s_reposts += stat.get("reposts", 0)
                    if not caption:
                        caption = stat.get("caption", "")
                except Exception:
                    errors += 1

            total_views   += s_views
            total_likes   += s_likes
            total_replies += s_replies
            total_reposts += s_reposts

            err_note = f" ⚠️{errors}" if errors else ""
            lines.append(
                f"\n📌 [{ts}]{err_note}\n"
                f"   👁 {s_views:,}  ❤️ {s_likes}  💬 {s_replies}  🔁 {s_reposts}\n"
                f"   «{caption[:55]}...»"
            )

        lines.append("\n━━━━━━━━━━━━━━━━")
        lines.append(
            f"📈 ИТОГО за 24 ч:\n"
            f"   👁 Просмотры: {total_views:,}\n"
            f"   ❤️ Лайки: {total_likes:,}\n"
            f"   💬 Ответы: {total_replies:,}\n"
            f"   🔁 Репосты: {total_reposts:,}"
        )
    else:
        lines.append("\n📊 За последние 24 ч публикаций не было")

    await msg.edit_text("\n".join(lines)[:4000])


# ─── /status ──────────────────────────────────────────────────────────────────
@owner_only
async def cmd_status(upd, ctx):
    h      = storage.get_setting("interval_hours") or 4
    active = storage.get_setting("active")
    img    = storage.get_image() or "не установлена"
    dm_on  = storage.get_dm_active()
    s      = storage.get_stats(24 * 7)
    await upd.message.reply_text(
        f"📊 Состояние бота\n\n"
        f"📋 В очереди: {storage.count()} серий\n"
        f"🤖 Автопостинг: {'✅ вкл' if active else '⏹ выкл'} ({h} ч.)\n"
        f"🎯 Авто-темы: {len(storage.get_auto_topics())} шт. → /tema\n"
        f"🖼 Картинка: {img}\n"
        f"💬 Автоответ: {'✅ вкл' if dm_on else '⏹ выкл'}\n"
        f"📨 DM: {s['total_dm_sent']} чел. (ожидают: {s['pending_dm']})\n"
        f"📂 Архив: {s['total_published']} серий\n\n"
        f"/stats — подробная статистика\n"
        f"/tema — управление темами\n"
        f"/check — проверить + в комментариях"
    )


# ─── Авто-задача: проверка комментариев ───────────────────────────────────────
async def _dm_check_job(application: Application):
    if not storage.get_dm_active():
        return
    from threads_api import get_all_comments, send_dm

    watched  = storage.get_watched_posts()
    dm_text  = storage.get_dm_text()
    new_sent = 0

    for post_id in watched:
        try:
            comments = await asyncio.to_thread(get_all_comments, post_id)
            await asyncio.sleep(2)
        except Exception as e:
            logging.warning(f"Комментарии {post_id}: {e}")
            continue
        for c in comments:
            if "+" not in c["text"]:
                continue
            uid   = c["user_id"]
            uname = c.get("username", "")
            if not uid or storage.was_messaged(uid):
                continue
            try:
                await asyncio.to_thread(send_dm, uid, dm_text)
                storage.mark_messaged(uid, uname)
                new_sent += 1
                await asyncio.sleep(2)
            except Exception as e:
                logging.warning(f"DM @{uname}: {e}")
                storage.add_pending_dm(uid, uname, post_id)

    if new_sent > 0:
        await application.bot.send_message(
            OWNER_ID,
            f"📨 Автоответ: {new_sent} DM отправлено\n"
            f"Всего: {storage.get_messaged_count()} чел.\n"
            f"Ожидают: {storage.get_pending_count()} → /razoslat"
        )


# ─── Авто-задача: постинг ─────────────────────────────────────────────────────
async def _auto_job(application: Application):
    from threads_api import post_series, post_single_text
    if not storage.get_setting("active"):
        return

    # Берём из очереди или генерируем по теме
    item = storage.pop()
    generated_topic = None

    if not item:
        topic = storage.next_auto_topic()
        if not topic:
            try:
                topic = await asyncio.to_thread(ai_gen.generate_topic)
            except Exception as e:
                await application.bot.send_message(
                    OWNER_ID, f"❌ Авто: не могу придумать тему: {str(e)[:200]}"
                )
                return
        try:
            series = await asyncio.to_thread(ai_gen.generate_series, topic)
            item   = {"type": "series", "posts": series}
            generated_topic = topic
        except Exception as e:
            await application.bot.send_message(
                OWNER_ID, f"❌ Авто: ошибка генерации темы «{topic}»: {str(e)[:200]}"
            )
            return

    try:
        image    = storage.get_image()
        post_ids = []
        if item.get("type") == "series":
            post_ids = await asyncio.to_thread(post_series, item["posts"], image)
        else:
            pid = await asyncio.to_thread(post_single_text, item["text"])
            post_ids = [pid]
        storage.archive_item(item, post_ids)
        if post_ids:
            storage.add_watched_post(post_ids[0])

        source = f"тема «{generated_topic}»" if generated_topic else f"очередь (осталось: {storage.count()})"
        preview = ""
        if item.get("type") == "series":
            preview = "\n\n" + item["posts"].get("post1", "")[:200] + "..."
        await application.bot.send_message(
            OWNER_ID,
            f"✅ Авто: опубликовано из {source}{preview}"
        )
    except Exception as e:
        # Возвращаем в очередь только если взяли из очереди (не авто-генерация)
        if not generated_topic:
            if item.get("type") == "series":
                storage.add_series(item["posts"])
            else:
                storage.add(item.get("text", ""))
        await application.bot.send_message(OWNER_ID, f"❌ Авто ошибка: {str(e)[:300]}")




# ─── /tema — управление авто-темами ──────────────────────────────────────────
@owner_only
async def cmd_tema(upd, ctx):
    args = ctx.args

    # /tema  (без аргументов) — показать список
    if not args:
        topics = storage.get_auto_topics()
        if not topics:
            await upd.message.reply_text(
                "📋 Темы для авто-генерации не добавлены.\n\n"
                "Добавить: /tema добавить <тема>\n"
                "Пример: /tema добавить почему VPN нужен каждому"
            )
        else:
            idx = storage._load().get("topic_index", 0) % len(topics)
            lines = []
            for i, t in enumerate(topics):
                pointer = "→ " if i == idx else "   "
                lines.append(f"{pointer}{i+1}. {t}")
            await upd.message.reply_text(
                f"📋 Темы авто-генерации ({len(topics)} шт.):\n\n"
                + "\n".join(lines)
                + "\n\n→ следующая по очереди\n"
                  "Удалить: /tema удалить <номер>\n"
                  "Добавить: /tema добавить <текст>"
            )
        return

    subcmd = args[0].lower()

    if subcmd in ("добавить", "add", "+"):
        topic = " ".join(args[1:]).strip()
        if not topic:
            await upd.message.reply_text("Укажи тему. Пример: /tema добавить жизнь без VPN")
            return
        storage.add_auto_topic(topic)
        topics = storage.get_auto_topics()
        await upd.message.reply_text(f"✅ Тема добавлена: «{topic}»\nВсего тем: {len(topics)}")

    elif subcmd in ("удалить", "del", "delete", "-"):
        if len(args) < 2 or not args[1].isdigit():
            await upd.message.reply_text("Укажи номер. Пример: /tema удалить 2")
            return
        n = int(args[1]) - 1
        topics = storage.get_auto_topics()
        if 0 <= n < len(topics):
            removed = topics[n]
            storage.remove_auto_topic(n)
            await upd.message.reply_text(f"🗑 Удалено: «{removed}»")
        else:
            await upd.message.reply_text(f"❌ Нет темы с номером {n+1}")

    elif subcmd in ("очистить", "clear"):
        topics = storage.get_auto_topics()
        for _ in range(len(topics)):
            storage.remove_auto_topic(0)
        await upd.message.reply_text("🗑 Все темы удалены")

    else:
        # /tema текст напрямую без подкоманды — добавляем как тему
        topic = " ".join(args).strip()
        storage.add_auto_topic(topic)
        topics = storage.get_auto_topics()
        await upd.message.reply_text(f"✅ Тема добавлена: «{topic}»\nВсего тем: {len(topics)}")


# ─── Планировщики ─────────────────────────────────────────────────────────────
def _start_post_scheduler(application):
    h = storage.get_setting("interval_hours") or 4
    scheduler.add_job(
        _auto_job, "interval", hours=h,
        args=[application], id="post_job", replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()


def _start_dm_scheduler(application):
    scheduler.add_job(
        _dm_check_job, "interval", minutes=30,
        args=[application], id="dm_job", replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()


# ─── Запуск ───────────────────────────────────────────────────────────────────
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    cmds = [
        ("start",        cmd_start),
        ("app",          cmd_app),
        ("help",         cmd_help),
        ("pomosch",      cmd_help),
        ("seriya",       cmd_series),
        ("series",       cmd_series),
        ("post",         cmd_post1),
        ("post1",        cmd_post1),
        ("pokazat",      cmd_showseries),
        ("showseries",   cmd_showseries),
        ("publikovat",   cmd_postseries),
        ("postseries",   cmd_postseries),
        ("kartinka",     cmd_setimage),
        ("setimage",     cmd_setimage),
        ("ochered",      cmd_queue),
        ("queue",        cmd_queue),
        ("arhiv",        cmd_archive),
        ("avto",         cmd_auto),
        ("auto",         cmd_auto),
        ("tema",         cmd_tema),
        ("interval",     cmd_interval),
        ("avtootvet",    cmd_dm_toggle),
        ("soobschenie",  cmd_set_dm_text),
        ("check",        cmd_check),
        ("checkraw",     cmd_checkraw),
        ("razoslat",     cmd_blast),
        ("status_dm",    cmd_dm_status),
        ("stats",        cmd_stats),
        ("stats_threads",cmd_stats_threads),
        ("status",       cmd_status),
    ]
    for cmd, handler in cmds:
        application.add_handler(CommandHandler(cmd, handler))

    application.add_handler(CallbackQueryHandler(callback_blast, pattern="^blast_"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    if storage.get_setting("active"):
        _start_post_scheduler(application)
    if storage.get_dm_active():
        _start_dm_scheduler(application)

    print("Бот запущен...")
    application.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")