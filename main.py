# ============================
#  vauvkino – ONE‑FILE  (aug 2025)  • python‑telegram‑bot v22
#  • /add  /reset  /stats  /send
#  • Kod bilan kino, serial, kanal‑post jo‘natish  + views
#  • Subscribe‑prompt  • Avto‑backup  • Users ro‘yxati
# ============================
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from __future__ import annotations
import json, logging, datetime, os, shutil
from typing import Any, Dict, List, Set
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
ADMIN_IDS = [7260661052]  # bu yerga o'z admin Telegram ID'ingizni yozing

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id in ADMIN_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            if update.message:
                await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
            elif update.callback_query:
                await update.callback_query.answer("❌ Bu amal faqat adminlar uchun.", show_alert=True)
    return wrapper


)

# ─── Logger ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


import os

BOT_TOKEN        = os.getenv("BOT_TOKEN", "7921810416:AAF2PRHSzam-Tne8C4ALKY3oc4-sjNnusDU").strip()
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@kinokodlarida").strip()
ADMIN_CODE       = os.getenv("ADMIN_CODE", "2299").strip()

DATA_FILE   = "/data1/kino_data.json"
USERS_FILE  = "/data1/users.json"
BACKUP_DIR  = "/data1/backups"

ADMIN_IDS: Set[int] = set()
USERS:     Set[int] = set()

# ─── Persistent data ─────────────────────────────────────────────────
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

# ─── Helpers ─────────────────────────────────────────────────────────
def save_db() -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(KINO_DB, f, ensure_ascii=False, indent=2)

def auto_backup() -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    shutil.copy2(DATA_FILE, f"{BACKUP_DIR}/kino_backup_{ts}.json")

def save_db_with_backup() -> None:
    save_db(); auto_backup()

def save_users() -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(USERS), f)

def sub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Obuna", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
        [InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")],
    ])

# ─── /start ──────────────────────────────────────────────────────────
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


# ─── CALLBACK HANDLER ─────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_subs":
        if await check_subscription(query.from_user.id, context):
            await query.message.edit_text("✅ Obuna tasdiqlandi. Endi kod yuboring.")
        else:
            await query.message.reply_text("❌ Hali ham obuna bo‘lmagansiz.")

    elif query.data.startswith("delete_"):
        # Kodni o‘chirish logikasi
        code = query.data.split("_")[1]
        await query.message.edit_text(f"🗑 Kod {code} o‘chirildi.")

    elif query.data.startswith("replace_"):
        # Kodni almashtirish logikasi
        code = query.data.split("_")[1]
        await query.message.edit_text(f"♻️ Kod {code} almashtirish rejimida.")

    elif query.data.startswith("ep_"):
        # Epizod sahifasi (masalan: ep_1)
        ep = query.data.split("_")[1]
        await query.message.edit_text(f"📺 Epizod: {ep}")

    elif query.data == "random_kino":
        await query.message.reply_text("🎲 Tasodifiy kino: (bu yerga random kino chiqadi)")

    elif query.data == "reset_kod":
        await query.message.reply_text("⚠️ Kodni o‘chirishni tasdiqlang:", reply_markup=confirm_reset_kb())

    elif query.data == "confirm_reset":
        await query.message.edit_text("✅ Kod o‘chirildi.")

    elif query.data == "cancel_reset":
        await query.message.edit_text("❌ Bekor qilindi.")

    else:
        await query.message.reply_text("❓ Noma'lum amal.")


# ─── /addserial ───────────────────────────────────────────────────────
@admin_only
async def add_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Foydalanish: /addserial <kod> <post_id> <epizod_soni>\n"
            "Masalan: /addserial 200 1234 10"
        )
        return

    code = args[0]
    try:
        post_id = int(args[1])
        episode_count = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ post_id va epizod soni butun son bo‘lishi kerak.")
        return

    data = load_data()
    data[code] = {
        "type": "serial",
        "post_id": post_id,
        "episodes": episode_count
    }
    save_data(data)

    await update.message.reply_text(
        f"✅ Serial qo‘shildi:\nKod: {code}\nEpizodlar: {episode_count}"
    )

# ─── /addepisode ──────────────────────────────────────────────────────
@admin_only
async def add_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "❌ Foydalanish: /addepisode <kod> <epizod_raqami> <post_id>\n"
            "Masalan: /addepisode 101 2 54321"
        )
        return

    code = args[0]
    try:
        ep_number = int(args[1])
        post_id = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ epizod raqami va post_id butun son bo‘lishi kerak.")
        return

    data = load_data()
    if code not in data:
        data[code] = {"type": "video", "episodes": {}}
    elif "episodes" not in data[code]:
        data[code]["episodes"] = {}

    data[code]["episodes"][str(ep_number)] = post_id
    save_data(data)

    await update.message.reply_text(
        f"✅ Epizod qo‘shildi:\nKod: {code}\nEpizod: {ep_number}\nPost ID: {post_id}"
    )


# ─── Delete button ───────────────────────────────────────────────────
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

#serial qoshish buyrugi
async def add_serial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Siz admin emassiz.")
        return

    lines = update.message.text.strip().splitlines()
    info = {"type": "serial"}
    for line in lines[1:]:
        if ":" not in line: continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key == "kod":
            kod = val
        elif key == "channel":
            info["channel"] = int(val)
        elif key == "parts":
            info["parts"] = [int(x.strip()) for x in val.split(",") if x.strip().isdigit()]

    if not kod or "channel" not in info or "parts" not in info:
        await update.message.reply_text("❌ Maʼlumotlar to‘liq emas.")
        return

    kino = load_json(FILM_FILE)
    kino[kod] = info
    save_json(FILM_FILE, kino)
    await update.message.reply_text(f"✅ Serial {kod} muvaffaqiyatli qo‘shildi.")

# ─── Serial epizodlari ───────────────────────────────────────────────
async def episode_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    tag, kod, idx_s = q.data.split("|", 2); idx = int(idx_s)
    kino = KINO_DB.get(kod)
    if not kino: return

    if tag == "ep":
        await context.bot.send_video(
            q.message.chat_id,
            kino["episodes"][idx]["file_id"],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌", callback_data="del")]])
        )
    else:  # next page
        start = idx; eps = kino["episodes"]
        kb = [[InlineKeyboardButton(eps[i]["text"], callback_data=f"ep|{kod}|{i}")]
               for i in range(start, min(len(eps), start+10))]
        if start+10 < len(eps):
            kb.append([InlineKeyboardButton("▶️ Davomi", callback_data=f"next|{kod}|{start+10}")])
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

# ─── Kino‑kodi xabarlari ─────────────────────────────────────────────
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id

    # obuna tekshirish
    try:
        m = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if m.status not in ("member","administrator","creator"):
            await update.message.reply_text("❌ Avval kanalga obuna bo‘ling:", reply_markup=sub_kb())
            return
    except Exception as e:
        logger.warning("get_chat_member xato: %s", e)

    USERS.add(uid); save_users()

    kod  = update.message.text.strip()
    kino = KINO_DB.get(kod)
    if not kino:
        await update.message.reply_text("❗ Kod topilmadi\n Aktual kodlar telegram kanalda:\n https://t.me/kinokodlarida")
        return

    # views
    kino["views"] = kino.get("views", 0) + 1; save_db_with_backup()
    views_txt = f"\n👁 {kino['views']} marta ko‘rilgan"

    # Channel post
    if kino.get("channel") and kino.get("msg_id"):
        cp = await context.bot.copy_message(
            update.effective_chat.id,
            kino["channel"],
            int(kino["msg_id"])
        )
        await context.bot.edit_message_reply_markup(
            cp.chat_id, cp.message_id,
            InlineKeyboardMarkup([[InlineKeyboardButton("❌", callback_data="del")]])
        )
        return

    # Video
    if kino.get("type") == "video":
        cap = (kino.get("caption") or
               f"🎬 {kino.get('title','')}\n\n📜 {kino.get('desc','')}") + views_txt
        await context.bot.send_video(
            update.effective_chat.id,
            kino["file_id"],
            caption=cap,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌", callback_data="del")]])
        )
        return

    # Serial preview
    if kino.get("type") == "serial":
        await update.message.reply_photo(
            kino.get("photo", ""),
            caption=f"🎬 {kino.get('title','')}\n\n📜 {kino.get('desc','')}{views_txt}"
        )
        eps = kino["episodes"]
        kb = [[InlineKeyboardButton(eps[i]["text"], callback_data=f"ep|{kod}|{i}")]
               for i in range(min(10, len(eps)))]
        if len(eps) > 10:
            kb.append([InlineKeyboardButton("▶️ Davomi", callback_data=f"next|{kod}|10")])
        await update.message.reply_text(
            "📺 Qaysi qismini tanlaysiz?", reply_markup=InlineKeyboardMarkup(kb)
        )

# ─── /stats ──────────────────────────────────────────────────────────
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    total   = len(KINO_DB)
    videos  = sum(1 for k in KINO_DB.values() if k.get("type") == "video")
    serials = sum(1 for k in KINO_DB.values() if k.get("type") == "serial")
    views   = sum(k.get("views",0) for k in KINO_DB.values())
    await update.message.reply_text(
        f"<b>Statistika</b>\n\n🎬 Jami: {total}\n📹 Video: {videos}\n🎞 Serial: {serials}\n👁 Ko‘rishlar: {views}",
        parse_mode="HTML"
    )
    # ─── /udump  ────────────────────────────────────────────────────────
async def udump_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    if not os.path.exists(USERS_FILE):
        await update.message.reply_text("❗ users.json topilmadi."); return
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

# ─── /urestore buyrug'i ───────────────────────────────────────────────
async def urestore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("📤 Yangi users.json faylini yuboring.")
    context.user_data["await_urestore"] = True

# ─── Hujjat qabul qilish (users.json)  ────────────────────────────────
async def urestore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("await_urestore"):
        return
    context.user_data.pop("await_urestore", None)

    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❗ Faqat .json hujjat qabul qilinadi."); return

    tmp = "/tmp/new_users.json"
    await doc.get_file().download_to_drive(tmp)

    try:
        with open(tmp, encoding="utf-8") as f:
            new_users = json.load(f)  # sintaksis tekshiruvi
    except Exception as e:
        await update.message.reply_text(f"❌ JSON xato: {e}"); return

    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"{BACKUP_DIR}/manual", exist_ok=True)
        shutil.copy2(USERS_FILE, f"{BACKUP_DIR}/manual/users_{ts}.bak")

        shutil.move(tmp, USERS_FILE)
        global USERS
        USERS = set(new_users)  # RAMdagi variableni yangilaymiz
        save_users()  # xavfsizlik uchun

        await update.message.reply_text("✅ users.json yangilandi.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Saqlashda xato: {e}")

# --- /dump  (admin – faylni yuborish) ------------------------------
async def dump_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    path = "/data/kino_data.json"   # volume ichidagi to‘liq yo‘l
    if not os.path.exists(path):
        await update.message.reply_text("❗ Fayl topilmadi."); return
    try:
        await context.bot.send_document(chat_id=update.effective_chat.id,
                                        document=open(path, "rb"),
                                        filename="kino_data.json",
                                        caption="📄 Hozirgi kino_data.json")
    except Exception as e:
        logger.error("dump send xato: %s", e)
        await update.message.reply_text(f"⚠️ Yuborib bo‘lmadi: {e}")


# --- /restore (1-bosqich) --------------------------------------------------
async def restore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(
        "📤 Yangi kino_data.json faylini hujjat (document) sifatida yuboring.")
    context.user_data["await_restore"] = True

# --- Hujjat qabul qilish ---------------------------------------------------
async def restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # faqat restore holati bo'lsa
    if not context.user_data.get("await_restore"):
        return
    context.user_data.pop("await_restore", None)

    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❗ Faqat .json fayl qabul qilinadi."); return

    # JSON’ni vaqtincha yuklab olamiz
    file_path = await doc.get_file()
    tmp = "/tmp/new_kino_data.json"
    await file_path.download_to_drive(custom_path=tmp)

    # Tekshiruv: JSON sintaksis
    try:
        with open(tmp, encoding="utf-8") as f:
            new_data = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"❌ JSON xato: {e}"); return

    try:
        # Eski faylni zaxira
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"{BACKUP_DIR}/manual", exist_ok=True)
        shutil.copy2(DATA_FILE, f"{BACKUP_DIR}/manual/kino_data_{ts}.bak")

        # Yangi faylni joylash
        shutil.move(tmp, DATA_FILE)

        # RAM’dagi bazani yangilash
        global KINO_DB
        KINO_DB = new_data

        await update.message.reply_text("✅ Fayl qabul qilindi va yuklandi.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Saqlashda xato: {e}")

# ─── /add ────────────────────────────────────────────────────────────
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

    info: Dict[str, Any] = {}; eps: List[Dict[str,str]] = []; kod=""
    for ln in lines:
        if ln.startswith("kod:"):  kod = ln.split(":",1)[1].strip()
        elif ln.startswith(("type:","title:","desc:","photo:","file_id:","caption:","channel:","msg_id:")):
            k,v = ln.split(":",1); info[k.strip()] = v.strip()
        elif "=" in ln:
            k,v = ln.split("=",1); eps.append({"text":f"{k.strip()}-qism","file_id":v.strip()})
    if info.get("type") == "serial":
        info["episodes"] = eps
    if not kod:
        await update.message.reply_text("❌ 'kod:' kiritilmadi")
        return

    KINO_DB[kod] = info; save_db_with_backup()
    await update.message.reply_text("✅ Saqlandi / yangilandi.")

# ─── /send (kanal‑postni global yuborish) ────────────────────────────
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
    q = update.callback_query; await q.answer()
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

# ─── /reset ──────────────────────────────────────────────────────────
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
    q = update.callback_query; await q.answer()
    if q.data == "reset_all":
        KINO_DB.clear(); save_db_with_backup()
        await q.edit_message_text("🗑️ Baza tozalandi.")
    elif q.data.startswith("del|"):
        _, kod = q.data.split("|",1)
        if kod in KINO_DB:
            KINO_DB.pop(kod); save_db_with_backup()
            await q.edit_message_text(f"🗑️ {kod} o‘chirildi.")
        else:
            await q.edit_message_text("❗ Topilmadi.")
    else:
        await q.edit_message_text("❌ Bekor qilindi.")

# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ---- Admin fayl zaxira / tiklash ----
    app.add_handler(CommandHandler("dump", dump_cmd))
    app.add_handler(CommandHandler("restore", restore_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, restore_file))
    #serial qoshish
    app.add_handler(CommandHandler("addserial", add_serial))
    # ---- /send channel‑post ----
    app.add_handler(CommandHandler("send", send_cmd))
    app.add_handler(CallbackQueryHandler(send_cb, pattern=r"^(send_now\|.+|cancel_send)$"))

    #--- Udump buyruq ---
    app.add_handler(CommandHandler("udump",    udump_cmd))
    app.add_handler(CommandHandler("urestore", urestore_cmd))
    # barcha hujjatlarni tutuvchi universal MessageHandler kerak:
    app.add_handler(MessageHandler(filters.Document.ALL, urestore_file))
    
    #yangi 001
    from telegram.ext import CommandHandler

    # boshqa handlerlar bilan birga quyidagini ham qo‘shing:
    app.add_handler(CommandHandler("addserial", add_serial))


    # ---- Core buyruqlar ----
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CommandHandler("stats",  stats_cmd))
    app.add_handler(CommandHandler("add",    add_cmd))
    app.add_handler(CommandHandler("reset",  reset_cmd))
    app.add_handler(CallbackQueryHandler(reset_cb, pattern=r"^(reset_all|cancel_reset|del\|.+)$"))

    # ---- Serial epizodlari va delete ----
    app.add_handler(CallbackQueryHandler(episode_cb, pattern=r"^(ep|next)\|"))
    app.add_handler(CallbackQueryHandler(del_msg_cb, pattern="^del$"))

    logger.info("🤖 Bot ishga tushdi   |   Kino DB: %s  |  USERS: %s", len(KINO_DB), len(USERS))
    app.run_polling()


if __name__ == "__main__":
    main()
