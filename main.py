from __future__ import annotations
import json, logging, datetime, os, shutil
from typing import Any, Dict, List, Set
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN        = os.getenv("BOT_TOKEN",        "YOUR_TOKEN_HERE")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@kinokodlarida")
ADMIN_CODE       = os.getenv("ADMIN_CODE",       "2299")

DATA_FILE   = "/data/kino_data.json"
USERS_FILE  = "users.json"
BACKUP_DIR  = "/data/backups"

ADMIN_IDS: Set[int] = set()
USERS:     Set[int] = set()

try:
    with open(DATA_FILE, encoding="utf-8") as f:
        KINO_DB: Dict[str, Dict[str, Any]] = json.load(f)
except FileNotFoundError:
    KINO_DB = {}

try:
    with open(USERS_FILE, encoding="utf-8") as f:
        USERS = set(json.load(f))
except FileNotFoundError:
    USERS = set()

def save_db() -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(KINO_DB, f, ensure_ascii=False, indent=2)

def auto_backup() -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    shutil.copy2(DATA_FILE, f"{BACKUP_DIR}/kino_backup_{ts}.json")

def save_db_with_backup() -> None:
    save_db()
    auto_backup()

def save_users() -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(USERS), f)

def sub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Obuna", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
        [InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    USERS.add(uid)
    save_users()

    try:
        m = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
    except Exception as e:
        logger.warning("get_chat_member xato: %s", e)
        m = None

    if m and m.status in ("member", "administrator", "creator"):
        await update.message.reply_text("🎬 Kino kodini yuboring (masalan: 101)")
    else:
        await update.message.reply_text(
            "👋 Avval kanalga obuna bo‘ling:", reply_markup=sub_kb()
        )

async def check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = await context.bot.get_chat_member(CHANNEL_USERNAME, q.from_user.id)
    if m.status in ("member", "administrator", "creator"):
        await q.edit_message_text("✅ Obuna tasdiqlandi. Endi kino kodini yuborishingiz mumkin.")
    else:
        await q.answer("❌ Hali obuna emassiz!", show_alert=True)

async def del_msg_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        try:
            await context.bot.delete_message(
                update.callback_query.message.chat_id,
                update.callback_query.message.message_id
            )
        except Exception as e:
            logger.warning("delete failed: %s", e)
        await update.callback_query.answer()

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id

    try:
        m = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if m.status not in ("member","administrator","creator"):
            await update.message.reply_text("❌ Avval kanalga obuna bo‘ling:", reply_markup=sub_kb())
            return
    except Exception as e:
        logger.warning(f"get_chat_member xato: {e}")

    USERS.add(uid)
    save_users()

    kod = update.message.text.strip()
    kino = KINO_DB.get(kod)

    if not kino:
        await update.message.reply_text(
            "❗ Kod topilmadi\nAktual kodlar telegram kanalda:\nhttps://t.me/kinokodlarida"
        )
        return

    try:
        if kino.get("channel") and kino.get("msg_id"):
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=kino["channel"],
                message_id=int(kino["msg_id"])
            )
            return

        # Agar yuqoridagi shartlarga mos kelmasa, xabar berish
        await update.message.reply_text("❗ Bu kod uchun ko‘rsatiladigan kontent mavjud emas.")

    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}")
        await update.message.reply_text(f"⚠️ Xatolik yuz berdi: {e}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    total   = len(KINO_DB)
    videos  = sum(1 for k in KINO_DB.values() if k.get("type") == "video")
    views   = sum(k.get("views",0) for k in KINO_DB.values())
    await update.message.reply_text(
        f"<b>Statistika</b>\n\n🎬 Jami: {total}\n📹 Video: {videos}\n👁 Ko‘rishlar: {views}",
        parse_mode="HTML"
    )

async def udump_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    if not os.path.exists(USERS_FILE):
        await update.message.reply_text("❗ users.json topilmadi.")
        return
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(USERS_FILE, "rb"),
            filename="users.json",
            caption="👥 Hozirgi users.json"
        )
    except Exception as e:
        logger.error("udump xato: %s", e)
        await update.message.reply_text(f"⚠️ Yuborib bo‘lmadi: {e}")

async def urestore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("📤 Yangi users.json faylini yuboring.")
    context.user_data["await_urestore"] = True

async def urestore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("await_urestore"):
        return
    context.user_data.pop("await_urestore", None)

    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❗ Faqat .json hujjat qabul qilinadi.")
        return

    tmp = "/tmp/new_users.json"
    await doc.get_file().download_to_drive(tmp)

    try:
        with open(tmp, encoding="utf-8") as f:
            new_users = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"❌ JSON xato: {e}")
        return

    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"{BACKUP_DIR}/manual", exist_ok=True)
        shutil.copy2(USERS_FILE, f"{BACKUP_DIR}/manual/users_{ts}.bak")

        shutil.move(tmp, USERS_FILE)
        global USERS
        USERS = set(new_users)
        save_users()

        await update.message.reply_text("✅ users.json yangilandi.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Saqlashda xato: {e}")

async def dump_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    path = "/data/kino_data.json"
    if not os.path.exists(path):
        await update.message.reply_text("❗ Fayl topilmadi.")
        return
    try:
        await context.bot.send_document(chat_id=update.effective_chat.id,
                                        document=open(path, "rb"),
                                        filename="kino_data.json",
                                        caption="📄 Hozirgi kino_data.json")
    except Exception as e:
        logger.error("dump send xato: %s", e)
        await update.message.reply_text(f"⚠️ Yuborib bo‘lmadi: {e}")

async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(
        "📤 Yangi kino_data.json faylini hujjat sifatida yuboring.")
    context.user_data["await_restore"] = True

async def restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("await_restore"):
        return
    context.user_data.pop("await_restore", None)

    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❗ Faqat .json fayl qabul qilinadi.")
        return

    file_path = await doc.get_file()
    tmp = "/tmp/new_kino_data.json"
    await file_path.download_to_drive(custom_path=tmp)

    try:
        with open(tmp, encoding="utf-8") as f:
            new_data = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"❌ JSON xato: {e}")
        return

    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"{BACKUP_DIR}/manual", exist_ok=True)
        shutil.copy2(DATA_FILE, f"{BACKUP_DIR}/manual/kino_data_{ts}.bak")

        shutil.move(tmp, DATA_FILE)

        global KINO_DB
        KINO_DB = new_data

        await update.message.reply_text("✅ Fayl qabul qilindi va yuklandi.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Saqlashda xato: {e}")

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    u = update.effective_user
    lines = update.message.text.strip().splitlines()
    if u.id not in ADMIN_IDS:
        if len(lines) >= 2 and lines[1].strip() == ADMIN_CODE:
            ADMIN_IDS.add(u.id)
            await update.message.reply_text("✅ Parol tasdiqlandi.")
            return
        await update.message.reply_text("❌ Parol noto‘g‘ri.")
        return

    info: Dict[str, Any] = {}
    kod = ""
    for ln in lines:
        if ln.startswith("kod:"):
            kod = ln.split(":",1)[1].strip()
        elif ln.startswith(("type:","title:","desc:","photo:","caption:","channel:","msg_id:","file_id:")):
            k,v = ln.split(":",1)
            info[k.strip()] = v.strip()

    if not kod:
        await update.message.reply_text("❌ 'kod:' kiritilmadi")
        return

    KINO_DB[kod] = info
    save_db_with_backup()
    await update.message.reply_text("✅ Saqlandi / yangilandi.")

async def send_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    parts = update.message.text.strip().split(maxsplit=3)
    if len(parts) != 3:
        await update.message.reply_text("❗ Foydalanish:\n/send -100123456789 42")
        return
    ch, msg_id = parts[1], parts[2]
    try:
        prev = await context.bot.copy_message(update.effective_chat.id, ch, int(msg_id))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Nusxa olinmadi: {e}")
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📤 Yuborish", callback_data=f"send_now|{ch}|{msg_id}"),
                               InlineKeyboardButton("❌ Bekor",    callback_data="cancel_send")]])
    await update.message.reply_text("Tasdiqlang:", reply_markup=kb, reply_to_message_id=prev.message_id)

async def send_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "cancel_send":
        await q.edit_message_text("❌ Bekor qilindi.")
        return
    _, ch, msg_id = q.data.split("|",2)
    sent = failed = 0
    for uid in USERS:
        try:
            await context.bot.copy_message(uid, ch, int(msg_id))
            sent += 1
        except Exception:
            failed += 1
    await q.edit_message_text(f"📤 Yuborildi: {sent}\n❌ Xato: {failed}")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    args = update.message.text.strip().split()
    if len(args) == 1:
        await update.message.reply_text("❗ Foydalanish:\n/reset all — hammasini tozalash\n/reset <kod> — bitta kodni o‘chirish")
        return
    target = args[1]
    if target == "all":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Ha", callback_data="reset_all")],
                                   [InlineKeyboardButton("❌ Yo‘q", callback_data="cancel_reset")]])
        await update.message.reply_text("Barchasini o‘chirilsinmi?", reply_markup=kb)
        return
    if target not in KINO_DB:
        await update.message.reply_text("❗ Bu kod topilmadi")
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Ha", callback_data=f"del|{target}")],
                               [InlineKeyboardButton("❌ Yo‘q", callback_data="cancel_reset")]])
    await update.message.reply_text(f"{target} kodli kinoni o‘chirilsinmi?", reply_markup=kb)

async def reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "reset_all":
        KINO_DB.clear()
        save_db_with_backup()
        await q.edit_message_text("🗑️ Baza tozalandi.")
    elif q.data.startswith("del|"):
        _, kod = q.data.split("|",1)
        if kod in KINO_DB:
            KINO_DB.pop(kod)
            save_db_with_backup()
            await q.edit_message_text(f"🗑️ {kod} o‘chirildi.")
        else:
            await q.edit_message_text("❗ Topilmadi.")
    else:
        await q.edit_message_text("❌ Bekor qilindi.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("dump", dump_cmd))
    app.add_handler(CommandHandler("restore", restore_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, restore_file))

    app.add_handler(CommandHandler("send", send_cmd))
    app.add_handler(CallbackQueryHandler(send_cb, pattern=r"^(send_now\|.+|cancel_send)$"))

    app.add_handler(CommandHandler("udump", udump_cmd))
    app.add_handler(CommandHandler("urestore", urestore_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, urestore_file))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_cb, pattern="^check_sub$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CallbackQueryHandler(reset_cb, pattern=r"^(reset_all|cancel_reset|del\|.+)$"))

    app.add_handler(CallbackQueryHandler(del_msg_cb, pattern="^del$"))

    logger.info("🤖 Bot ishga tushdi | Kino DB: %s | USERS: %s", len(KINO_DB), len(USERS))
    app.run_polling()

if __name__ == "__main__":
    main()
