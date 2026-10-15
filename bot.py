import asyncio
import json
import logging
import os
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path

import gspread
from flask import Flask, abort, request
from google.oauth2.service_account import Credentials
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ============================================================
#  ማዋቀር (Render Environment Variables)
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CREDS_FILE = BASE_DIR / "credentials.json"  # ኮምፒውተርህ ላይ ለሙከራ

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "10d8t6dysp3ig-bQ7HFEV-cP1oID-Fw7juVJOYeNVUYM")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")  # Render ላይ የ credentials.json ይዘት

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN አልተገኘም። Render ላይ Environment Variable ጨምር።")
if not PUBLIC_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL አልተገኘም። ቦቱ Web Service ሆኖ መሰራቱን አረጋግጥ።")

# ============================================================
#  ፒዲኤፎች (ፋይሎቹ bot.py ጎን መሆን አለባቸው)
# ============================================================
PDFS = {
    "peace": ("peace_army_regulation.pdf", "1. የሰላም ሰራዊት አደረጃጀት፣ አሰራር እና ተግባርና ኃላፊነት ደንብ"),
    "fee": ("loading_fee_directive.pdf", "2. የመጫንና ማውረድ አገልግሎት ክፍያ ተመን"),
    "loader": ("loader_directive.pdf", "3. ጫኝና አውራጅ መመሪያ"),
    "standards": ("service_standards.pdf", "4. የአገልግሎት ስታንዳርዶች ሰነድ"),
}

# ============================================================
#  ጽሁፎች
# ============================================================
WELCOME = (
    "እንኳን ወደ ልደታ ክ/ከተማ ሰላምና ጸጥታ ጽሕፈት ቤት ቴሌግራም ቦት በሰላም መጡ።\n"
    "ከታች ያሉትን ቁልፎች በመጠቀም የሚፈልጉትን አገልግሎት ማግኘት ይችላሉ።"
)

VISION_FULL = (
    "🌟 ራዕይ (Vision)\n"
    "በ2022 አዲስ አበባ ከተማችን በህዝብ ተሳትፎ ሠላምና ፀጥታ የሰፈነባት የህግ የበላይነት የተረጋገጠባት ለኑሮ፣ "
    "ለስራ እና ለመዝናኛ ተመራጭ የሆነች ከተማ ሆና ማየት፤\n\n"
    "🎯 ተልዕኮ\n"
    "የተቀናጀ የጸጥታ ጉዳዮች አስተዳደር እና የግጭት ቅድመ ማስጠንቀቂያና ፈጣን ምላሽ ስርዓትን ተግባራዊ በማድረግ ወንጀልን በመከላከል፤ "
    "የሰላም እሴቶችን በመገንባት፣ በሃይማኖትና እምነት ተከታዮች መካከል መከባበርና መቻቻል እንዲሰፍን በማድረግ፤ የክትትል፤ "
    "ቁጥጥር እና ቀልጣፋ አገልግሎት አሰጣጥ ስርዓት በመዘርጋት፣ ነዋሪውንና ባለድርሻ አካላትን ተሳትፎና ባለቤትነት በማረጋገጥ "
    "ሰላም፣ ጸጥታና ደህንነቷ የተጠበቀ እና ህግና ስርዓት የተከበረባት ከተማ ማድረግ ነው።\n\n"
    "💎 እሴቶች\n"
    "• ታማኝነትና ተጠያቂነት\n"
    "• ሚስጥር ጠባቂነት\n"
    "• ፍትሐዊነትና ሰብዓዊነት\n"
    "• ለላቀ ሰላም እና ጸጥታ መትጋት\n"
    "• ተቋማዊ አጋርነት\n"
    "• የህግ የበላይነትን ማክበርና ማስከበር"
)

# ============================================================
#  ቁልፎች
# ============================================================
BTN_TIP = "1/መረጃና ጥቆማ ለመስጠት"
BTN_VISION = "2/ስለ ፅ/ቤቱ ራዕይ ፤ተልዕኮ እና እሴቶች ለማወቅ"
BTN_COMPLAINT = "3/ቅሬታ ለማቅረብ"
BTN_GUIDES = "4/መመሪያዎችን ለመመልከት"
BTN_STANDARDS = "5/የአገልግሎት ስታንዳርዶች ለማየት"
BTN_FEEDBACK = "6/አገልግሎቶች ላይ አስተያየት ለመስጠት"
BTN_HOME = "🏠 ዋና ማውጫ"
BTN_PHOTO_YES = "📷 ፎቶ አለኝ"
BTN_PHOTO_NO = "❌ ፎቶ የለኝም"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_TIP], [BTN_VISION], [BTN_COMPLAINT], [BTN_GUIDES], [BTN_STANDARDS], [BTN_FEEDBACK], [BTN_HOME]],
    resize_keyboard=True,
)
FLOW_KEYBOARD = ReplyKeyboardMarkup([[BTN_HOME]], resize_keyboard=True)
PHOTO_KEYBOARD = ReplyKeyboardMarkup([[BTN_PHOTO_YES], [BTN_PHOTO_NO], [BTN_HOME]], resize_keyboard=True)

RATING_CHOICES = [("ሀ", "በጣም ከፍተኛ"), ("ለ", "ከፍተኛ"), ("ሐ", "መካከለኛ"), ("መ", "ዝቅተኛ")]
RATING_MAP = {}
for _i, (_letter, _name) in enumerate(RATING_CHOICES, 1):
    for _key in (f"{_letter}/ {_name}", _letter, _name, str(_i)):
        RATING_MAP[_key] = _name
RATING_KEYBOARD = ReplyKeyboardMarkup(
    [[f"{l}/ {n}"] for l, n in RATING_CHOICES] + [[BTN_HOME]], resize_keyboard=True
)

# ============================================================
#  Google Sheets
# ============================================================
_spreadsheet = None


def get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if GOOGLE_CREDS_JSON:
            creds = Credentials.from_service_account_info(json.loads(GOOGLE_CREDS_JSON), scopes=scopes)
        else:
            creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
        _spreadsheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    return _spreadsheet


def sheet(tab):
    return get_spreadsheet().worksheet(tab)


def add_row(tab, values):
    """አዲስ ረድፍ ይጨምራል፤ የረድፉን ID ይመልሳል (1 ጀምሮ)።"""
    ws = sheet(tab)
    ws.append_row(values, value_input_option="USER_ENTERED")
    return len(ws.col_values(1)) - 1  # ራስጌውን ሳይጨምር


def records(tab):
    """ሁሉም ረድፎች እንደ ዝርዝር (ID = ቦታ + 1)።"""
    return sheet(tab).get_all_records()


def last_records(tab, n=10):
    recs = records(tab)
    pairs = [(i + 1, r) for i, r in enumerate(recs)]
    return pairs[::-1][:n]


def get_record(tab, rid):
    recs = records(tab)
    if 1 <= rid <= len(recs):
        return recs[rid - 1]
    return None


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ============================================================
#  ማረጋገጫ ተግባራት
# ============================================================
def any_text(t):
    return t if t else None


def digits_only(t):
    return t if t.isdigit() else None


def phone_only(t):
    p = t.replace("+", "").replace(" ", "")
    return p if p.isdigit() and len(p) >= 9 else None


def rating_value(t):
    return RATING_MAP.get(t)


def comment_value(t):
    return "" if t == "-" else t


def photo_choice_value(t):
    if t == BTN_PHOTO_YES:
        return "yes"
    if t == BTN_PHOTO_NO:
        return "no"
    return None


def Q(key, prompt, check=any_text, error="እባክዎ እንደገና ይጻፉ።", markup=None):
    return {"key": key, "prompt": prompt, "check": check, "error": error, "markup": markup}


# ============================================================
#  የመጨረሻ ደረጃዎች (መረጃው ወደ Sheets ይገባል)
# ============================================================
async def finish_tip(update, context, d):
    add_row("suggestions", [now(), d["wereda"], d["zone"], d["place"], d["details"], d.get("photo") or ""])
    await update.message.reply_text("ለሰጡን መረጃና ጥቆማ እናመሰግናለን!", reply_markup=MAIN_KEYBOARD)


async def finish_complaint(update, context, d):
    cid = add_row("complaints", [
        now(), update.effective_chat.id, d["name"], d["wereda"], d["zone"],
        d["house"], d["details"], d["request"], d["phone"], "አዲስ", "",
    ])
    text = (
        f"🆕 አዲስ ቅሬታ #{cid}\n"
        f"ስም: {d['name']}\n"
        f"ወረዳ: {d['wereda']} | ቀጠና: {d['zone']} | ቤት ቁጥር: {d['house']}\n"
        f"ዝርዝር: {d['details']}\n"
        f"የሚጠይቁት: {d['request']}\n"
        f"ስልክ: {d['phone']}\n\n"
        f"ምላሽ ለመስጠት: /reply {cid} ምላሽዎ"
    )
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_message(aid, text)
        except Exception as e:
            log.warning("ለአስተዳዳሪ %s መላክ አልተቻለም: %s", aid, e)
    await update.message.reply_text(
        f"ቅሬታዎ ደርሶናል። የቅሬታ ቁጥርዎ፦ {cid}\nበአጭር ጊዜ ውስጥ ምላሽ እንሰጥዎታለን።",
        reply_markup=MAIN_KEYBOARD,
    )


async def finish_feedback(update, context, d):
    add_row("feedback", [now(), d["rating"], d["comment"]])
    await update.message.reply_text("ስለሰጡን አስተያየት እናመሰግናለን!", reply_markup=MAIN_KEYBOARD)


# ============================================================
#  ጥያቄዎች (flow) - በቅደም ተከተል ይጠየቃሉ
# ============================================================
FLOWS = {
    "tip": {
        "questions": [
            Q("wereda", "መረጃውን የሚሰጡበትን ወረዳ ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።"),
            Q("zone", "ቀጠናውን ይግለጹ (በቁጥርም ሆነ በፅሁፍ)።"),
            Q("place", "ልዩ ቦታውን ይግለጹ።"),
            Q("details", "የጥቆማውን ዝርዝር ሁኔታ ይግለጹ።"),
            Q("photo_choice",
              "ማስረጃ ፎቶ ካለዎት '📷 ፎቶ አለኝ' ይጫኑና ይላኩ፤ ከሌለ '❌ ፎቶ የለኝም' ይጫኑ።\n"
              "(ፎቶው የሚታየው ለአስተዳዳሪዎች ብቻ ነው)",
              photo_choice_value, "እባክዎ ከቁልፎቹ አንዱን ይጫኑ።", PHOTO_KEYBOARD),
        ],
        "finish": finish_tip,
    },
    "complaint": {
        "questions": [
            Q("name", "ሙሉ ስምዎን ያስገቡ።"),
            Q("wereda", "ወረዳዎን ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።"),
            Q("zone", "ቀጠናዎን ይጻፉ (በቁጥርም ሆነ በፅሁፍ)።"),
            Q("house", "የቤት ቁጥርዎን በቁጥር ብቻ ይጻፉ።", digits_only, "እባክዎ የቤት ቁጥርን በቁጥር ብቻ ይጻፉ።"),
            Q("details", "ቅሬታዎን በዝርዝር ይግለጹ።"),
            Q("request", "ጽ/ቤቱ እንዲያደርግልዎ የሚፈልጉትን ይግለጹ።"),
            Q("phone", "ለምላሽ እንድንደውልልዎ ስልክ ቁጥርዎን በቁጥር ብቻ ይጻፉ።",
              phone_only, "እባክዎ ትክክለኛ ስልክ ቁጥር በቁጥር ብቻ ይጻፉ።"),
        ],
        "finish": finish_complaint,
    },
    "feedback": {
        "questions": [
            Q("rating", "በጽ/ቤቱ ያገኙትን አገልግሎት እንዴት ይገልጹታል?",
              rating_value, "እባክዎ ከቁልፎቹ አንዱን ይምረጡ።", RATING_KEYBOARD),
            Q("comment", 'በቀጣይ ሊስተካከል ይገባዋል የሚሉት ካለ እዚህ ይጻፉ።\n(ከሌለ "-" ብለው ይላኩ)', comment_value),
        ],
        "finish": finish_feedback,
    },
}


async def start_flow(update, context, name):
    context.user_data.clear()
    context.user_data.update({"flow": name, "idx": 0, "data": {}})
    q = FLOWS[name]["questions"][0]
    await update.message.reply_text(q["prompt"], reply_markup=q["markup"] or FLOW_KEYBOARD)


async def run_finish(update, context, flow, data):
    try:
        await flow["finish"](update, context, data)
    except Exception:
        log.exception("መረጃ ወደ Sheets መጻፍ አልተቻለም")
        await update.message.reply_text(
            "ይቅርታ፣ መረጃውን አሁን ማስቀመጥ አልተቻለም። እባክዎ ጥቂት ቆይተው እንደገና ይሞክሩ።",
            reply_markup=MAIN_KEYBOARD,
        )


async def flow_answer(update, context, text):
    flow = FLOWS[context.user_data["flow"]]
    idx = context.user_data["idx"]
    q = flow["questions"][idx]

    value = q["check"](text)
    if value is None:
        return await update.message.reply_text(q["error"], reply_markup=q["markup"] or FLOW_KEYBOARD)

    context.user_data["data"][q["key"]] = value

    # ፎቶ አለኝ ከተባለ ፎቶው እስኪላክ እንጠብቃለን
    if q["key"] == "photo_choice" and value == "yes":
        context.user_data["awaiting_photo"] = True
        return await update.message.reply_text("እባክዎ ፎቶውን አሁን ይላኩ።", reply_markup=FLOW_KEYBOARD)

    idx += 1
    if idx < len(flow["questions"]):
        context.user_data["idx"] = idx
        nxt = flow["questions"][idx]
        return await update.message.reply_text(nxt["prompt"], reply_markup=nxt["markup"] or FLOW_KEYBOARD)

    data = context.user_data["data"]
    context.user_data.clear()
    await run_finish(update, context, flow, data)


async def finish_pending_tip(update, context, photo_id):
    data = context.user_data.get("data", {})
    data["photo"] = photo_id
    context.user_data.clear()
    await run_finish(update, context, FLOWS["tip"], data)


# ============================================================
#  ዋና ማውጫ እና ቁልፎች
# ============================================================
async def show_home(update, context):
    context.user_data.clear()
    await update.message.reply_text(WELCOME, reply_markup=MAIN_KEYBOARD)


async def send_pdf(update, key):
    fname, title = PDFS[key]
    path = BASE_DIR / fname
    if not path.exists():
        return await update.message.reply_text(
            f"ይቅርታ፣ '{title}' ፋይሉ ገና አልተጫነም። እባክዎ ለአስተዳዳሪው ያሳውቁ።",
            reply_markup=MAIN_KEYBOARD,
        )
    with path.open("rb") as f:
        await update.message.reply_document(document=f, filename=fname, caption=title)


async def on_text(update, context):
    text = update.message.text.strip()

    # ዋና ማውጫና ምናሌ ቁልፎች ሁልጊዜ ቅድሚያ አላቸው
    if text == BTN_HOME:
        return await show_home(update, context)
    if text == BTN_TIP:
        return await start_flow(update, context, "tip")
    if text == BTN_COMPLAINT:
        return await start_flow(update, context, "complaint")
    if text == BTN_FEEDBACK:
        return await start_flow(update, context, "feedback")

    # ቀጥታ ምላሽ የሚሰጡ ቁልፎች - የቀድሞው ውይይት ካለ ያጠፋሉ
    if text == BTN_VISION:
        context.user_data.clear()
        return await update.message.reply_text(VISION_FULL, reply_markup=MAIN_KEYBOARD)
    if text == BTN_GUIDES:
        context.user_data.clear()
        for key in ("peace", "fee", "loader"):
            await send_pdf(update, key)
        return await update.message.reply_text("ከላይ ያሉትን መመሪያዎች አውርደው ማየት ይችላሉ።", reply_markup=MAIN_KEYBOARD)
    if text == BTN_STANDARDS:
        context.user_data.clear()
        return await send_pdf(update, "standards")

    # ፎቶ እየተጠበቀ ከሆነ
    if context.user_data.get("awaiting_photo"):
        if text == BTN_PHOTO_NO:
            return await finish_pending_tip(update, context, None)
        return await update.message.reply_text(
            "እባክዎ ፎቶውን ይላኩ፤ ፎቶ ከሌለ '❌ ፎቶ የለኝም' ይጫኑ።", reply_markup=FLOW_KEYBOARD
        )

    # በውይይት ውስጥ ከሆነ መልሱን ያስቀምጣል
    if "flow" in context.user_data:
        return await flow_answer(update, context, text)

    await update.message.reply_text("እባክዎ ከታች ካሉት ቁልፎች አንዱን ይምረጡ።", reply_markup=MAIN_KEYBOARD)


async def on_photo(update, context):
    if not context.user_data.get("awaiting_photo"):
        return await update.message.reply_text("ፎቶ መላክ የሚቻለው ጥቆማ ሲሰጡ ብቻ ነው።", reply_markup=MAIN_KEYBOARD)
    await finish_pending_tip(update, context, update.message.photo[-1].file_id)


# ============================================================
#  የአስተዳዳሪ ትዕዛዞች (ከSheets ያነባሉ)
# ============================================================
async def is_admin(update):
    if update.effective_user.id in ADMIN_IDS:
        return True
    await update.message.reply_text("ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው።")
    return False


async def cmd_admin(update, context):
    if not await is_admin(update):
        return
    await update.message.reply_text(
        "የአስተዳዳሪ ትዕዛዞች፦\n"
        "/complaints - የቅሬታዎች ዝርዝር (የመጨረሻዎቹ 10)\n"
        "/complaint ቁጥር - የአንድ ቅሬታ ዝርዝር\n"
        "/reply ቁጥር ምላሽ - ለቅሬታ ምላሽ መስጠት\n"
        "/suggestions - የጥቆማዎች ዝርዝር (የመጨረሻዎቹ 10)\n"
        "/photo ቁጥር - የጥቆማ ፎቶ ማየት\n"
        "/feedbacks - የአስተያየቶች ማጠቃለያ"
    )


async def cmd_complaints(update, context):
    if not await is_admin(update):
        return
    rows = last_records("complaints", 10)
    if not rows:
        return await update.message.reply_text("ምንም ቅሬታ የለም።")
    lines = [f"#{rid} | {r['full_name']} | {r['wereda']} | {r['status']}" for rid, r in rows]
    await update.message.reply_text("\n".join(lines) + "\n\nዝርዝር ለማየት: /complaint ቁጥር")


async def cmd_complaint(update, context):
    if not await is_admin(update):
        return
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("አጠቃቀም: /complaint ቁጥር")
    rid = int(context.args[0])
    r = get_record("complaints", rid)
    if not r:
        return await update.message.reply_text("ይህ ቁጥር ያለው ቅሬታ የለም።")
    await update.message.reply_text(
        f"ቅሬታ #{rid} ({r['created']})\n"
        f"ስም: {r['full_name']}\n"
        f"ወረዳ: {r['wereda']} | ቀጠና: {r['zone']} | ቤት ቁጥር: {r['house_no']}\n"
        f"ስልክ: {r['phone']}\n"
        f"ዝርዝር: {r['detail']}\n"
        f"የሚጠይቁት: {r['request']}\n"
        f"ሁኔታ: {r['status']}\n"
        f"ምላሽ: {r['reply'] or '—'}"
    )


async def cmd_reply(update, context):
    if not await is_admin(update):
        return
    if len(context.args) < 2 or not context.args[0].isdigit():
        return await update.message.reply_text("አጠቃቀም: /reply ቁጥር ምላሽዎ")
    rid = int(context.args[0])
    answer = " ".join(context.args[1:])
    r = get_record("complaints", rid)
    if not r:
        return await update.message.reply_text("ይህ ቁጥር ያለው ቅሬታ የለም።")

    # ረድፉ = ID + 1 (ራስጌ ስላለ)። ሁኔታና ምላሹን ይጽፋል።
    ws = sheet("complaints")
    ws.update_cell(rid + 1, 10, "ምላሽ ተሰጥቷል")
    ws.update_cell(rid + 1, 11, answer)

    try:
        await context.bot.send_message(int(r["user_id"]), f"ለቅሬታ ቁጥር {rid} የተሰጠ ምላሽ፦\n\n{answer}")
        await update.message.reply_text("ምላሹ ለቅሬታ አቅራቢው ተልኳል ✅")
    except Exception as e:
        log.error("ምላሽ መላክ አልተቻለም: %s", e)
        await update.message.reply_text("ምላሹ ተመዝግቧል፤ ግን ለተጠቃሚው መላክ አልተቻለም።")


async def cmd_suggestions(update, context):
    if not await is_admin(update):
        return
    rows = last_records("suggestions", 10)
    if not rows:
        return await update.message.reply_text("ምንም ጥቆማ የለም።")
    parts = []
    for rid, r in rows:
        photo = "📷 አለ" if r.get("photo_file_id") else "የለም"
        parts.append(
            f"#{rid} ({r['created']})\n"
            f"ወረዳ: {r['wereda']} | ቀጠና: {r['zone']} | ቦታ: {r['place']}\n"
            f"{r['detail']}\nፎቶ: {photo}"
        )
    await update.message.reply_text("\n\n".join(parts)[:4000])


async def cmd_photo(update, context):
    if not await is_admin(update):
        return
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("አጠቃቀም: /photo ቁጥር")
    r = get_record("suggestions", int(context.args[0]))
    if not r or not r.get("photo_file_id"):
        return await update.message.reply_text("ለዚህ ጥቆማ ፎቶ የለም።")
    await update.message.reply_photo(r["photo_file_id"])


async def cmd_feedbacks(update, context):
    if not await is_admin(update):
        return
    recs = records("feedback")
    if not recs:
        return await update.message.reply_text("ምንም አስተያየት የለም።")
    counts = Counter(r["rating"] for r in recs)
    await update.message.reply_text(
        "የአስተያየቶች ማጠቃለያ፦\n" + "\n".join(f"{k}: {v}" for k, v in counts.items())
    )


async def on_error(update, context):
    log.error("ስህተት ተፈጥሯል: %s", context.error, exc_info=context.error)


# ============================================================
#  ቴሌግራም አፕሊኬሽን
# ============================================================
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", show_home))
application.add_handler(CommandHandler("admin", cmd_admin))
application.add_handler(CommandHandler("complaints", cmd_complaints))
application.add_handler(CommandHandler("complaint", cmd_complaint))
application.add_handler(CommandHandler("reply", cmd_reply))
application.add_handler(CommandHandler("suggestions", cmd_suggestions))
application.add_handler(CommandHandler("photo", cmd_photo))
application.add_handler(CommandHandler("feedbacks", cmd_feedbacks))
application.add_handler(MessageHandler(filters.PHOTO, on_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
application.add_error_handler(on_error)

# መልዕክቶች አንድ በአንድ በቅደም ተከተል የሚሰሩበት ወረፋ
bot_loop = asyncio.new_event_loop()
update_queue = None


async def update_worker():
    while True:
        update = await update_queue.get()
        try:
            await application.process_update(update)
        except Exception:
            log.exception("መልዕክት ማስኬድ አልተቻለም")
        finally:
            update_queue.task_done()


async def bot_startup():
    global update_queue
    update_queue = asyncio.Queue()

    # Sheets ተደራሽ መሆኑን ቀድሞ እናረጋግጣለን
    await asyncio.to_thread(get_spreadsheet)

    await application.initialize()
    await application.start()
    await application.bot.set_webhook(
        url=f"{PUBLIC_URL}/webhook",
        secret_token=WEBHOOK_SECRET or None,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    asyncio.create_task(update_worker())
    log.info("Webhook ተዘጋጅቷል: %s/webhook", PUBLIC_URL)


# ============================================================
#  Flask (Render ጤናማ መሆኑን እንዲያውቅና webhook እንዲቀበል)
# ============================================================
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Peace office bot is running"


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        abort(403)
    data = request.get_json(silent=True)
    if data:
        update = Update.de_json(data, application.bot)
        asyncio.run_coroutine_threadsafe(update_queue.put(update), bot_loop)
    return "OK", 200


if __name__ == "__main__":
    threading.Thread(target=bot_loop.run_forever, daemon=True).start()
    asyncio.run_coroutine_threadsafe(bot_startup(), bot_loop).result(timeout=90)
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
