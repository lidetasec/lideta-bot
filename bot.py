import logging
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdfs"
DB_PATH = BASE_DIR / "bot_data.db"

# ---------- የውይይት ደረጃዎች ----------
(
    S_WEREDA, S_ZONE, S_PLACE, S_DETAIL,                              # ጥቆማ
    C_NAME, C_WEREDA, C_ZONE, C_HOUSE, C_DETAIL, C_REQUEST, C_PHONE,  # ቅሬታ
    F_RATING, F_IMPROVE,                                              # አስተያየት
) = range(13)

RATINGS = {
    "r_a": "በጣም ከፍተኛ",
    "r_b": "ከፍተኛ",
    "r_c": "መካከለኛ",
    "r_d": "ዝቅተኛ",
}

ALLOWED_PDFS = {f for f, _ in config.GUIDE_PDFS} | {config.STANDARD_PDF[0]}


# ---------- ዳታቤዝ (በኮምፒውተርህ ላይ) ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, wereda TEXT, zone TEXT, place TEXT, detail TEXT
        );
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, user_id INTEGER, full_name TEXT, wereda TEXT, zone TEXT,
            house_no TEXT, detail TEXT, request TEXT, phone TEXT,
            status TEXT DEFAULT 'አዲስ', reply TEXT
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT, rating TEXT, improve TEXT
        );
    """)
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- ምናሌዎች ----------
WELCOME = (
    "እንኳን ወደ ልደታ ክ/ከተማ ሰላምና ጸጥታ ጽሕፈት ቤት ቴሌግራም ቦት በሰላም መጡ።\n"
    "ከታች ያሉትን ቁልፎች በመጠቀም የሚፈልጉትን አገልግሎት ማግኘት ይችላሉ።"
)


def main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ መረጃና ጥቆማ ለመስጠት", callback_data="suggest")],
        [InlineKeyboardButton("2️⃣ ራዕይ፣ ተልዕኮና እሴቶች", callback_data="vision")],
        [InlineKeyboardButton("3️⃣ ቅሬታ ለማቅረብ", callback_data="complaint")],
        [InlineKeyboardButton("4️⃣ መመሪያዎችን ለመመልከት", callback_data="guides")],
        [InlineKeyboardButton("5️⃣ የአገልግሎት ስታንዳርዶች", callback_data="standards")],
        [InlineKeyboardButton("6️⃣ በአገልግሎቱ ላይ አስተያየት", callback_data="feedback")],
    ])


def back_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ወደ ዋና ምናሌ", callback_data="menu")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(WELCOME, reply_markup=main_menu_markup())
    return ConversationHandler.END


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.reply_text(WELCOME, reply_markup=main_menu_markup())
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("ተሰርዟል።", reply_markup=main_menu_markup())
    return ConversationHandler.END


# ---------- ራዕይ፣ ተልዕኮ፣ እሴቶች ----------
async def show_vision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        f"🌟 ራዕይ\n{config.VISION}\n\n"
        f"🎯 ተልዕኮ\n{config.MISSION}\n\n"
        f"💎 እሴቶች\n{config.VALUES}"
    )
    await q.message.reply_text(text, reply_markup=back_markup())


# ---------- መመሪያዎችና ስታንዳርዶች (PDF) ----------
async def send_pdf(chat_id, fname, context: ContextTypes.DEFAULT_TYPE):
    path = PDF_DIR / fname
    if not path.exists():
        await context.bot.send_message(
            chat_id, "ይቅርታ፣ ፋይሉ ገና አልተጫነም። እባክዎ ለአስተዳዳሪው ያሳውቁ።", reply_markup=back_markup()
        )
        return
    with path.open("rb") as f:
        await context.bot.send_document(chat_id, document=f, filename=fname)
    await context.bot.send_message(chat_id, "ሰነዱ ተልኳል።", reply_markup=back_markup())


async def show_guides(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [[InlineKeyboardButton(title, callback_data=f"pdf:{fname}")] for fname, title in config.GUIDE_PDFS]
    kb.append([InlineKeyboardButton("⬅️ ወደ ዋና ምናሌ", callback_data="menu")])
    await q.message.reply_text("ማየት የሚፈልጉትን መመሪያ ይምረጡ፦", reply_markup=InlineKeyboardMarkup(kb))


async def pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fname = q.data.split(":", 1)[1]
    if fname not in ALLOWED_PDFS:
        await q.message.reply_text("ይቅርታ፣ ይህ ፋይል አይገኝም።", reply_markup=back_markup())
        return
    await send_pdf(q.message.chat_id, fname, context)


async def show_standards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await send_pdf(q.message.chat_id, config.STANDARD_PDF[0], context)


# ---------- 1. መረጃና ጥቆማ ----------
async def suggest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.reply_text("ጥቆማዎን ለመስጠት የሚመለከተውን ወረዳ ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።")
    return S_WEREDA


async def s_wereda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wereda"] = update.message.text.strip()
    await update.message.reply_text("ቀጠናውን ይግለጹ (በቁጥርም ሆነ በፅሁፍ)።")
    return S_ZONE


async def s_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["zone"] = update.message.text.strip()
    await update.message.reply_text("ልዩ ቦታውን ይግለጹ።")
    return S_PLACE


async def s_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["place"] = update.message.text.strip()
    await update.message.reply_text("የጥቆማውን ዝርዝር ሁኔታ ይግለጹ።")
    return S_DETAIL


async def s_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    conn = get_conn()
    conn.execute(
        "INSERT INTO suggestions (created, wereda, zone, place, detail) VALUES (?, ?, ?, ?, ?)",
        (now(), d["wereda"], d["zone"], d["place"], update.message.text.strip()),
    )
    conn.commit()
    conn.close()
    context.user_data.clear()
    await update.message.reply_text("ለሰጡን መረጃና ጥቆማ እናመሰግናለን።", reply_markup=back_markup())
    return ConversationHandler.END


# ---------- 3. ቅሬታ ----------
async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.message.reply_text("ሙሉ ስምዎን ያስገቡ።")
    return C_NAME


async def c_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text("ወረዳዎን ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።")
    return C_WEREDA


async def c_wereda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wereda"] = update.message.text.strip()
    await update.message.reply_text("ቀጠናዎን ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።")
    return C_ZONE


async def c_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["zone"] = update.message.text.strip()
    await update.message.reply_text("የቤት ቁጥርዎን በቁጥር ብቻ ይጻፉ።")
    return C_HOUSE


async def c_house(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip().isdigit():
        await update.message.reply_text("እባክዎ የቤት ቁጥርን በቁጥር ብቻ ይጻፉ።")
        return C_HOUSE
    context.user_data["house_no"] = update.message.text.strip()
    await update.message.reply_text("ቅሬታዎን በዝርዝር ይግለጹ።")
    return C_DETAIL


async def c_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text.strip()
    await update.message.reply_text("ጽ/ቤቱ እንዲያደርግልዎ የሚፈልጉትን ይግለጹ።")
    return C_REQUEST


async def c_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["request"] = update.message.text.strip()
    await update.message.reply_text("ለምላሽ እንድንደውልልዎ ስልክ ቁጥርዎን በቁጥር ብቻ ይጻፉ።")
    return C_PHONE


async def c_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip().replace("+", "").replace(" ", "")
    if not phone.isdigit() or len(phone) < 9:
        await update.message.reply_text("እባክዎ ትክክለኛ ስልክ ቁጥር በቁጥር ብቻ ይጻፉ።")
        return C_PHONE

    d = context.user_data
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO complaints
           (created, user_id, full_name, wereda, zone, house_no, detail, request, phone)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (now(), update.effective_user.id, d["full_name"], d["wereda"], d["zone"],
         d["house_no"], d["detail"], d["request"], phone),
    )
    complaint_id = cur.lastrowid
    conn.commit()
    conn.close()

    text = (
        f"🆕 አዲስ ቅሬታ #{complaint_id}\n"
        f"ስም: {d['full_name']}\n"
        f"ወረዳ: {d['wereda']} | ቀጠና: {d['zone']} | ቤት ቁጥር: {d['house_no']}\n"
        f"ዝርዝር: {d['detail']}\n"
        f"የሚጠይቁት: {d['request']}\n"
        f"ስልክ: {phone}\n\n"
        f"ምላሽ ለመስጠት: /reply {complaint_id} ምላሽዎ"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text)
        except Exception as e:
            log.warning("ለአስተዳዳሪ %s መላክ አልተቻለም: %s", admin_id, e)

    context.user_data.clear()
    await update.message.reply_text(
        f"ቅሬታዎ ተቀብሏል። የቅሬታ ቁጥርዎ፦ {complaint_id}\nለቅሬታው ምላሽ እንሰጥዎታለን።",
        reply_markup=back_markup(),
    )
    return ConversationHandler.END


# ---------- 6. አስተያየት ----------
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("ሀ/ በጣም ከፍተኛ", callback_data="r_a")],
        [InlineKeyboardButton("ለ/ ከፍተኛ", callback_data="r_b")],
        [InlineKeyboardButton("ሐ/ መካከለኛ", callback_data="r_c")],
        [InlineKeyboardButton("መ/ ዝቅተኛ", callback_data="r_d")],
    ])
    await q.message.reply_text("በጽ/ቤቱ ያገኙትን አገልግሎት እንዴት ይገልጹታል?", reply_markup=kb)
    return F_RATING


async def f_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["rating"] = RATINGS[q.data]
    await q.message.reply_text('በቀጣይ መስተካከል ያለበት ነገር ካለ እዚህ ይፃፉ።\n(ከሌለ "-" ብለው ይላኩ)')
    return F_IMPROVE


async def f_improve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    improve = "" if text == "-" else text
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedback (created, rating, improve) VALUES (?, ?, ?)",
        (now(), context.user_data.get("rating", ""), improve),
    )
    conn.commit()
    conn.close()
    context.user_data.clear()
    await update.message.reply_text("ስለሰጡን አስተያየት እናመሰግናለን።", reply_markup=back_markup())
    return ConversationHandler.END


# ---------- የአስተዳዳሪ ክፍል ----------
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in config.ADMIN_IDS:
            await update.message.reply_text("ይቅርታ፣ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "የአስተዳዳሪ ትዕዛዞች፦\n"
        "/complaints - የቅሬታዎች ዝርዝር (የመጨረሻዎቹ 10)\n"
        "/complaint ቁጥር - የአንድ ቅሬታ ሙሉ ዝርዝር\n"
        "/reply ቁጥር ምላሽ - ለቅሬታ ምላሽ መስጠት\n"
        "/suggestions - የጥቆማዎች ዝርዝር (የመጨረሻዎቹ 10)\n"
        "/feedbacks - የአስተያየቶች ማጠቃለያ"
    )


@admin_only
async def admin_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("ምንም ቅሬታ የለም።")
        return
    lines = [f"#{r['id']} | {r['full_name']} | {r['wereda']} | {r['status']}" for r in rows]
    await update.message.reply_text("\n".join(lines) + "\n\nዝርዝር ለማየት: /complaint ቁጥር")


@admin_only
async def admin_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("አጠቃቀም: /complaint ቁጥር")
        return
    conn = get_conn()
    r = conn.execute("SELECT * FROM complaints WHERE id = ?", (int(context.args[0]),)).fetchone()
    conn.close()
    if not r:
        await update.message.reply_text("ይህ ቁጥር ያለው ቅሬታ አልተገኘም።")
        return
    await update.message.reply_text(
        f"ቅሬታ #{r['id']} ({r['created']})\n"
        f"ስም: {r['full_name']}\n"
        f"ወረዳ: {r['wereda']} | ቀጠና: {r['zone']} | ቤት ቁጥር: {r['house_no']}\n"
        f"ስልክ: {r['phone']}\n"
        f"ዝርዝር: {r['detail']}\n"
        f"የሚጠይቁት: {r['request']}\n"
        f"ሁኔታ: {r['status']}\n"
        f"ምላሽ: {r['reply'] or '—'}"
    )


@admin_only
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("አጠቃቀም: /reply ቁጥር ምላሽዎ")
        return
    complaint_id = int(context.args[0])
    answer = " ".join(context.args[1:])

    conn = get_conn()
    r = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not r:
        conn.close()
        await update.message.reply_text("ይህ ቁጥር ያለው ቅሬታ አልተገኘም።")
        return

    conn.execute(
        "UPDATE complaints SET reply = ?, status = 'ምላሽ ተሰጥቷል' WHERE id = ?",
        (answer, complaint_id),
    )
    conn.commit()
    conn.close()

    try:
        await context.bot.send_message(
            r["user_id"],
            f"ለቅሬታ ቁጥር {complaint_id} የተሰጠ ምላሽ፦\n\n{answer}",
        )
        await update.message.reply_text("ምላሹ ለቅሬታ አቅራቢው ተልኳል ✅")
    except Exception as e:
        log.error("ምላሽ መላክ አልተቻለም: %s", e)
        await update.message.reply_text("ምላሹ ተመዝግቧል፣ ግን ለተጠቃሚው መላክ አልተቻለም።")


@admin_only
async def admin_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM suggestions ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("ምንም ጥቆማ የለም።")
        return
    text = "\n\n".join(
        f"#{r['id']} ({r['created']})\nወረዳ: {r['wereda']} | ቀጠና: {r['zone']} | ቦታ: {r['place']}\n{r['detail']}"
        for r in rows
    )
    await update.message.reply_text(text[:4000])


@admin_only
async def admin_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    rows = conn.execute("SELECT rating, COUNT(*) AS n FROM feedback GROUP BY rating").fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("ምንም አስተያየት የለም።")
        return
    lines = [f"{r['rating']}: {r['n']}" for r in rows]
    await update.message.reply_text("የአስተያየቶች ማጠቃለያ፦\n" + "\n".join(lines))


# ---------- ዋና ----------
def main():
    init_db()
    PDF_DIR.mkdir(exist_ok=True)

    app = Application.builder().token(config.BOT_TOKEN).build()

    text_filter = filters.TEXT & ~filters.COMMAND

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(suggest_start, pattern="^suggest$"),
            CallbackQueryHandler(complaint_start, pattern="^complaint$"),
            CallbackQueryHandler(feedback_start, pattern="^feedback$"),
        ],
        states={
            S_WEREDA: [MessageHandler(text_filter, s_wereda)],
            S_ZONE: [MessageHandler(text_filter, s_zone)],
            S_PLACE: [MessageHandler(text_filter, s_place)],
            S_DETAIL: [MessageHandler(text_filter, s_detail)],
            C_NAME: [MessageHandler(text_filter, c_name)],
            C_WEREDA: [MessageHandler(text_filter, c_wereda)],
            C_ZONE: [MessageHandler(text_filter, c_zone)],
            C_HOUSE: [MessageHandler(text_filter, c_house)],
            C_DETAIL: [MessageHandler(text_filter, c_detail)],
            C_REQUEST: [MessageHandler(text_filter, c_request)],
            C_PHONE: [MessageHandler(text_filter, c_phone)],
            F_RATING: [CallbackQueryHandler(f_rating, pattern="^r_")],
            F_IMPROVE: [MessageHandler(text_filter, f_improve)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CallbackQueryHandler(menu_callback, pattern="^menu$"),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(show_vision, pattern="^vision$"))
    app.add_handler(CallbackQueryHandler(show_guides, pattern="^guides$"))
    app.add_handler(CallbackQueryHandler(pdf_callback, pattern="^pdf:"))
    app.add_handler(CallbackQueryHandler(show_standards, pattern="^standards$"))

    app.add_handler(CommandHandler("admin", admin_help))
    app.add_handler(CommandHandler("complaints", admin_complaints))
    app.add_handler(CommandHandler("complaint", admin_complaint))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(CommandHandler("suggestions", admin_suggestions))
    app.add_handler(CommandHandler("feedbacks", admin_feedbacks))

    log.info("ቦቱ ተነስቷል...")
    app.run_polling()


if __name__ == "__main__":
    main()
