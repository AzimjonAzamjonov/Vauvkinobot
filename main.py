import logging
import json
import random
from typing import Dict, List
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo)
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters)

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_PASSWORD = "admin123"
CHANNELS = ["@YourChannel"]

# Fayllar
FILM_FILE = "kino.data.json"
USER_FILE = "users.json"
ADMINS = set()

# Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Yordamchi funksiya
async def check_subscription(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

async def force_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update.effective_user.id, context):
        keyboard = [[InlineKeyboardButton("🔔 Kanalga obuna bo‘lish", url=f"https://t.me/{ch[1:]}") for ch in CHANNELS]]
        await update.message.reply_text("Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=InlineKeyboardMarkup(keyboard))
        return False
    return True

# JSON bilan ishlovchilar

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_subscribe(update, context): return
    uid = str(update.effective_user.id)
    users = load_json(USER_FILE)
    users[uid] = users.get(uid, {"views": 0})
    save_json(USER_FILE, users)
    await update.message.reply_text("🎬 Vauv Kino botiga xush kelibsiz!\n\n🔍 Kino kodini yuboring yoki 🎲 Random tugmasini bosing.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Random kino", callback_data="random")]]))

# Kod yuborilganda kino
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_subscribe(update, context): return
    code = update.message.text.strip()
    kino = load_json(FILM_FILE)
    if code not in kino:
        await update.message.reply_text("❌ Bunday kod topilmadi.")
        return
    data = kino[code]
    if data["type"] == "film":
        await context.bot.forward_message(chat_id=update.effective_chat.id, from_chat_id=data["channel"], message_id=data["msg_id"])
    elif data["type"] == "serial":
        await send_serial_part(update, context, data, code, 1)

# Serial epizodlar
async def send_serial_part(update, context, data, code, part):
    if part < 1 or part > len(data["parts"]):
        await update.message.reply_text("❌ Bunday qism mavjud emas.")
        return
    await context.bot.forward_message(chat_id=update.effective_chat.id, from_chat_id=data["channel"], message_id=data["parts"][part - 1])
    btns = []
    start = ((part - 1) // 10) * 10 + 1
    end = min(start + 9, len(data["parts"]))
    for i in range(start, end + 1):
        btns.append(InlineKeyboardButton(str(i), callback_data=f"serial:{code}:{i}"))
    nav = []
    if start > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"serial:{code}:{start - 10}"))
    if end < len(data["parts"]):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"serial:{code}:{start + 10}"))
    keyboard = InlineKeyboardMarkup([btns[i:i + 5] for i in range(0, len(btns), 5)] + [nav] if nav else [])
    await update.message.reply_text("🧩 Qismni tanlang:", reply_markup=keyboard)

# CALLBACK
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "random":
        kino = load_json(FILM_FILE)
        if not kino:
            await query.edit_message_text("🎥 Hech qanday kino mavjud emas.")
            return
        code = random.choice(list(kino.keys()))
        msg = update.effective_message
        update.message = msg
        msg.text = code
        await handle_code(update, context)
    elif query.data.startswith("serial:"):
        _, code, part = query.data.split(":")
        kino = load_json(FILM_FILE)
        if code in kino:
            data = kino[code]
            await send_serial_part(update, context, data, code, int(part))

# Admin Login
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip().split(" ")[-1]
    if password == ADMIN_PASSWORD:
        ADMINS.add(update.effective_user.id)
        await update.message.reply_text("✅ Admin muvaffaqiyatli tasdiqlandi.")
    else:
        await update.message.reply_text("❌ Noto‘g‘ri admin parol.")

# MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler("login", login))
    app.run_polling()

if __name__ == '__main__':
    main()
