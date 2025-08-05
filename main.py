from __future__ import annotations

import os
import json
import logging
from typing import Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# 🔧 Logging sozlamasi
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 📁 Fayl va baza sozlamalari
DATA_FILE = "kino_data.json"
BACKUP_FILE = "kino_data_backup.json"

# 👮 Admin ID ro'yxati
ADMIN_IDS: Set[int] = {7260661052}

# 📦 Kodlar bazasi
KINO_DB = {}

# 📤 Kanal manzili
CHANNEL_USERNAME = "-1002089704214"

# 🧩 Kodlar soni
KOD_COUNT = 0

# ======================== Fayl bilan ishlash ========================

def load_db():
    global KINO_DB
    try:
        with open(DATA_FILE, "r") as f:
            KINO_DB.update(json.load(f))
    except FileNotFoundError:
        pass

def save_db_with_backup():
    with open(DATA_FILE, "w") as f:
        json.dump(KINO_DB, f)
    with open(BACKUP_FILE, "w") as f:
        json.dump(KINO_DB, f)

# ======================== Komanda: /start ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Assalomu alaykum! Kod yuboring:")
    else:
        await update.message.reply_text("Salom Admin! Buyruqlarni yuboring.")

# ======================== Foydalanuvchi kod yuborganda ========================

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    code = update.message.text.strip()
    kino = KINO_DB.get(code)

    if not kino:
        await update.message.reply_text("❗ Kod topilmadi.")
        return

    if kino["type"] == "movie":
        await context.bot.send_video(update.effective_chat.id, kino["file_id"])
    elif kino["type"] == "serial":
        keyboard = [
            [InlineKeyboardButton(f"Part {i+1}", callback_data=f"{code}_{i+1}")]
            for i in range(kino["episodes"])
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Qaysi qismini ko‘rmoqchisiz?", reply_markup=reply_markup)

# ======================== Serial qismi tanlanganda ========================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    if len(data) != 2:
        return

    code, part_str = data
    part = int(part_str) - 1
    kino = KINO_DB.get(code)

    if not kino or "episodes_id" not in kino or part >= len(kino["episodes_id"]):
        await query.edit_message_text("❗ Qism topilmadi.")
        return

    file_id = kino["episodes_id"][part]
    await context.bot.send_video(query.message.chat.id, file_id)

# ======================== Admin komandasi: /addserial ========================

async def add_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Foydalanish: /addserial <kod> <post_id> <epizod_soni>")
        return

    code, post_id_str, episode_count_str = args
    try:
        post_id = int(post_id_str)
        episode_count = int(episode_count_str)
    except ValueError:
        await update.message.reply_text("Xatolik: ID va epizod soni raqam bo'lishi kerak.")
        return

    KINO_DB[code] = {
        "type": "serial",
        "post_id": post_id,
        "episodes": episode_count
    }
    save_db_with_backup()
    await update.message.reply_text(f"Serial qo‘shildi: {code}")

# ======================== Admin komandasi: /addpart ========================

async def add_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Foydalanish: /addpart <kod> <file_id>")
        return

    code, file_id = args
    if code not in KINO_DB:
        await update.message.reply_text("Kod topilmadi.")
        return

    kino = KINO_DB[code]
    if "episodes_id" not in kino:
        kino["episodes_id"] = []

    kino["episodes_id"].append(file_id)
    save_db_with_backup()
    await update.message.reply_text(f"{code} uchun qism qo‘shildi.")

# ======================== Botni ishga tushurish ========================

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN topilmadi. .env faylga yozing.")
        return

    application = Application.builder().token(token).build()

    load_db()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addserial", add_serial))
    application.add_handler(CommandHandler("addpart", add_episode))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    print("✅ Bot ishga tushdi.")
    application.run_polling()

if __name__ == "__main__":
    main()
