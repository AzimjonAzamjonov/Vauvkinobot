# ============================
#  FILMXONA BOT  —  FULL CODE
#  duplicate‑check + selective delete + reset‑all
#  python‑telegram‑bot v22  |  Replit keep_alive()
# ============================

import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from keep_alive import keep_alive

# === GLOBAL SETTINGS ===
import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@filmxona_kodlari"
ADMIN_CODE = "2299"
ADMIN_IDS: set[int] = set()

DATA_FILE = "kino_data.json"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        KINO_MA_LUMOTLAR: dict[str, dict] = json.load(f)
except FileNotFoundError:
    KINO_MA_LUMOTLAR = {}


def save_kino_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(KINO_MA_LUMOTLAR, f, ensure_ascii=False, indent=2)


# ---------- /start ----------
async def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    sub = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
    if sub.status in ("member", "administrator", "creator"):
        return await update.message.reply_text(
            "🎬 Kino kodini yuboring (masalan: 101)")
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔔 Kanalga obuna bo‘lish",
                url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}",
            )
        ],
        [InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")],
    ])
    await update.message.reply_text(
        "👋 Botdan foydalanish uchun avval kanalga obuna bo‘ling:",
        reply_markup=btn)


async def check_sub_cb(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    sub = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
    if sub.status in ("member", "administrator", "creator"):
        await q.edit_message_text("✅ Obuna tasdiqlandi. Kod yuboring.")
    else:
        await q.answer("❌ Hali obuna emassiz!", show_alert=True)


# ---------- handle_code ----------
async def handle_code(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if (await context.bot.get_chat_member(CHANNEL_USERNAME,
                                          uid)).status not in ("member",
                                                               "administrator",
                                                               "creator"):
        return await update.message.reply_text("❌ Avval kanalga obuna bo‘ling!"
                                               )

    kod = update.message.text.strip()
    kino = KINO_MA_LUMOTLAR.get(kod)
    if not kino:
        return await update.message.reply_text("❗ Kod topilmadi")

    # 1️⃣ Kanal postini to‘liq copy
    if "channel" in kino and "msg_id" in kino:
        return await context.bot.copy_message(update.effective_chat.id,
                                              kino["channel"],
                                              int(kino["msg_id"]))

    # 2️⃣ Oddiy video
    if kino.get("type") == "video":
        caption = (
            kino.get("caption")
            or f"🎬 {kino.get('title','')}\n\n📝 {kino.get('desc','')}".strip())
        return await context.bot.send_video(update.effective_chat.id,
                                            kino["file_id"],
                                            caption=caption or None)

    # 3️⃣ Serial
    if kino.get("type") == "serial":
        await update.message.reply_photo(
            photo=kino.get("photo", ""),
            caption=f"🎬 {kino.get('title','')}\n\n📝 {kino.get('desc','')}".
            strip(),
        )
        eps = kino["episodes"]
        btns = [[
            InlineKeyboardButton(eps[i]["text"], callback_data=f"ep|{kod}|{i}")
        ] for i in range(min(10, len(eps)))]
        if len(eps) > 10:
            btns.append([
                InlineKeyboardButton("▶️ Davomi",
                                     callback_data=f"next|{kod}|10")
            ])
        await update.message.reply_text(
            "📺 Qaysi qismini tanlaysiz?",
            reply_markup=InlineKeyboardMarkup(btns),
        )


# ---------- Serial epizodlari ----------
async def episode_cb(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    tag, kod, idx = q.data.split("|")
    idx = int(idx)
    kino = KINO_MA_LUMOTLAR.get(kod)
    if not kino:
        return

    if tag == "ep":
        return await context.bot.send_video(q.message.chat_id,
                                            kino["episodes"][idx]["file_id"])

    # next page
    start = idx
    eps = kino["episodes"]
    btns = [[
        InlineKeyboardButton(eps[i]["text"], callback_data=f"ep|{kod}|{i}")
    ] for i in range(start, min(len(eps), start + 10))]
    if start + 10 < len(eps):
        btns.append([
            InlineKeyboardButton("▶️ Davomi",
                                 callback_data=f"next|{kod}|{start+10}")
        ])
    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btns))


# ---------- /add (duplicate check) ----------
async def add(update: Update, context: CallbackContext):
    user = update.effective_user
    rows = update.message.text.strip().splitlines()

    # admin auth
    if user.id not in ADMIN_IDS:
        if len(rows) >= 2 and rows[1].strip() == ADMIN_CODE:
            ADMIN_IDS.add(user.id)
            return await update.message.reply_text("✅ Parol tasdiqlandi.")
        return await update.message.reply_text("❌ Parol noto‘g‘ri.")

    info, eps, kod = {}, [], ""
    dup = False
    for ln in rows:
        if ln.startswith("kod:"):
            kod = ln.split(":", 1)[1].strip()
            dup = kod in KINO_MA_LUMOTLAR
        elif ln.startswith((
                "type:",
                "title:",
                "desc:",
                "photo:",
                "file_id:",
                "caption:",
                "channel:",
                "msg_id:",
        )):
            k, v = ln.split(":", 1)
            info[k.strip()] = v.strip()
        elif ln.startswith("episodes:"):
            continue
        elif "=" in ln:
            k, v = ln.split("=", 1)
            eps.append({"text": f"{k.strip()}-qism", "file_id": v.strip()})
    if info.get("type") == "serial":
        info["episodes"] = eps
    if not kod:
        return await update.message.reply_text("❌ 'kod:' kiritilmadi")

    if dup and "pending" not in context.user_data:
        context.user_data["pending"] = (kod, info)
        btn = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("♻️ Almashtir",
                                     callback_data="confirm_add")
            ],
            [InlineKeyboardButton("❌ Bekor", callback_data="cancel_add")],
        ])
        return await update.message.reply_text(
            "⚠️ Bu kod band. Almashtirishni xohlaysizmi?",
            reply_markup=btn,
        )

    KINO_MA_LUMOTLAR[kod] = info
    save_kino_data()
    context.user_data.pop("pending", None)
    await update.message.reply_text("✅ Saqlandi / yangilandi.")


async def confirm_cb(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    if q.data == "confirm_add":
        kod, info = context.user_data.get("pending", (None, None))
        if kod:
            KINO_MA_LUMOTLAR[kod] = info
            save_kino_data()
            await q.edit_message_text("♻️ Kod yangilandi.")
    else:
        await q.edit_message_text("❌ Bekor qilindi.")
    context.user_data.pop("pending", None)


# ---------- /reset (all or single) ----------
async def reset_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = update.message.text.strip().split()
    if len(args) == 1:
        return await update.message.reply_text(
            "❗ Foydalanish:\n"
            "/reset all – barcha nuksonlarni o‘chirish\n"
            "/reset <kod> – bitta kodni o‘chirish")

    target = args[1]
    if target == "all":
        btn = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Ha, hammasini o‘chir",
                                     callback_data="reset_all")
            ],
            [InlineKeyboardButton("❌ Yo‘q", callback_data="cancel_reset")],
        ])
        return await update.message.reply_text(
            "⚠️ Barcha kino/seriallarni o‘chirishni tasdiqlaysizmi?",
            reply_markup=btn,
        )

    # single delete
    kod = target
    if kod not in KINO_MA_LUMOTLAR:
        return await update.message.reply_text("❗ Bu kod mavjud emas")
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Ha, o‘chir", callback_data=f"del|{kod}")],
        [InlineKeyboardButton("❌ Yo‘q", callback_data="cancel_reset")],
    ])
    await update.message.reply_text(
        f"⚠️ {kod} – kodli kinoni o‘chirishni tasdiqlaysizmi?",
        reply_markup=btn,
    )


async def reset_cb(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    if q.data == "reset_all":
        KINO_MA_LUMOTLAR.clear()
        save_kino_data()
        await q.edit_message_text("🗑️ Baza tozalandi.")
    elif q.data.startswith("del|"):
        _, kod = q.data.split("|", 1)
        if kod in KINO_MA_LUMOTLAR:
            KINO_MA_LUMOTLAR.pop(kod)
            save_kino_data()
            await q.edit_message_text(f"🗑️ {kod} o‘chirildi.")
        else:
            await q.edit_message_text("❗ Bu kod topilmadi.")
    else:
        await q.edit_message


# === main ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_cb, pattern="check_sub"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(
        CallbackQueryHandler(confirm_cb, pattern="^(confirm_add|cancel_add)$"))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(
        CallbackQueryHandler(reset_cb,
                             pattern="^(reset_all|cancel_reset|del\\|.+)$"))
    app.add_handler(CallbackQueryHandler(episode_cb, pattern="^(ep|next)\\|"))
    keep_alive()
    app.run_polling()


if __name__ == "__main__":
    main()
