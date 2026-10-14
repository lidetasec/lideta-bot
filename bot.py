mport logging
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ሎጊንግ ማዋቀር
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask ሰርቨር ማዋቀር
app = Flask(__name__)

# ቴሌግራም ቦት ቶከን ከሬንደር ማንበብ
TOKEN = os.environ.get("TELEGRAM_TOKEN") 

# ቴሌግራም አፕሊኬሽን ማዋቀር
application = Application.builder().token(TOKEN).build()

# ቋሚ የኢቨንት ሉፕ ማዋቀር (ቦቱ በመሀል እንዳይቆም)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def setup_bot():
    await application.initialize()
    await application.bot.set_webhook(url="https://llideta-security-bot.onrender.com/webhook")

loop.run_until_complete(setup_bot())

# ፒዲኤፍ ፋይሎችን አስቀድሞ በሜሞሪ መጫን (ለፈጣን ምላሽ)
pdf_cache = {}
def load_pdfs():
    files = {
        'peace': 'peace_army_regulation.pdf',
        'fee': 'loading_fee_directive.pdf',
        'loader': 'loader_directive.pdf',
        'standards': 'service_standards.pdf'
    }
    for key, filename in files.items():
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                pdf_cache[key] = f.read()

load_pdfs()

# ==========================================
# 1. የ /start ትዕዛዝ እና 6ቱ ዋና ዋና ሜኑ በተኖች
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    
    keyboard = [
        ["1/መረጃና ጥቆማ ለመስጠት"],
        ["2/ስለ ፅ/ቤቱ ራዕይ ፤ተልዕኮ እና እሴቶች ለማወቅ"],
        ["3/ቅሬታ ለማቅረብ"],
        ["4/መመሪያዎችን ለመመልከት"],
        ["5/የአገልግሎት ስታንዳርዶች ለማየት"],
        ["6/አገልግሎቶች ላይ አስተያየት ለመስጠት"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        "እንኳን ወደ ልደታ ክ/ከተማ ሰላምና ጸጥታ ጽሕፈት ቤት ቴሌግራም ቦት በሰላም መጡ። "
        "ከታች ያሉትን ቁልፎች በመጠቀም የሚፈልጉትን አገልግሎት ማግኘት ይችላሉ።"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

# ==========================================
# 2. መልዕክቶችን እና የደረጃ በደረጃ ሂደቶችን ማስተዳደር
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = context.user_data.get('state')

    # ዋና ዋና ሜኑ በተኖች ሲጫኑ
    if text == "1/መረጃና ጥቆማ ለመስጠት":
        context.user_data.clear()
        context.user_data['state'] = 'TIP_WOREDA'
        context.user_data['tip_data'] = {}
        await update.message.reply_text(
            "📍 **መረጃና ጥቆማ ለመስጠት**\n\n"
            "እባክዎ መረጃውን የሚሰጡበትን **ወረዳ** ይምረጡ/ይጻፉ (በቁጥር ወይም በጽሁፍ)፦"
        )
        return

    elif text == "2/ስለ ፅ/ቤቱ ራዕይ ፤ተልዕኮ እና እሴቶች ለማወቅ":
        context.user_data.clear()
        vision_mission_text = (
            "🌟 **ራዕይ (Vision)**\n"
            "በ2022 አዲስ አበባ ከተማችን በህዝብ ተሳትፎ ሠላምና ፀጥታ የሰፈነባት የህግ የበላይነት የተረጋገጠባት ለኑሮ፣ "
            "ለስራ እና ለመዝናኛ ተመራጭ የሆነች ከተማ ሆና ማየት፤\n\n"
            "🎯 **ተልዕኮ**\n"
            "የተቀናጀ የጸጥታ ጉዳዮች አስተዳደር እና የግጭት ቅድመ ማስጠንቀቂያና ፈጣን ምላሽ ስርዓትን ተግባራዊ በማድረግ ወንጀልን በመከላከል፤ "
            "የሰላም እሴቶችን በመገንባት፣ በሃይማኖትና እምነት ተከታዮች መካከል መከባበርና መቻቻል እንዲሰፍን በማድረግ፤ የክትትል፤ "
            "ቁጥጥር እና ቀልጣፋ አገልግሎት አሰጣጥ ስርዓት በመዘርጋት፣ ነዋሪውንና ባለድርሻ አካላትን ተሳትፎና ባለቤትነት በማረጋገጥ "
            "ሰላም፣ ጸጥታና ደህንነቷ የተጠበቀ እና ህግና ስርዓት የተከበረባት ከተማ ማድረግ ነው፡፡\n\n"
            "💎 **እሴቶች**\n"
            "• ታማኝነትና ተጠያቂነት\n"
            "• ሚስጥር ጠባቂነት\n"
            "• ፍትሐዊነትና ሰብዓዊነት\n"
            "• ለላቀ ሰላም እና ጸጥታ መትጋት\n"
            "• ተቋማዊ አጋርነት\n"
            "• የህግ የበላይነትን ማክበርና ማስከበር"
        )
        await update.message.reply_text(vision_mission_text)
        return

    elif text == "3/ቅሬታ ለማቅረብ":
        context.user_data.clear()
        context.user_data['state'] = 'COMPLAINT_NAME'
        context.user_data['complaint_data'] = {}
        await update.message.reply_text(
            "📝 **ቅሬታ ለማቅረብ**\n\n"
            "እባክዎ **ሙሉ ስምዎን** ያስገቡ፦"
        )
        return

    elif text == "4/መመሪያዎችን ለመመልከት":
        context.user_data.clear()
        await update.message.reply_text(
            "📂 **የጽ/ቤቱ መመሪያዎች እና ደንቦች**\n\n"
            "እባክዎ ከዚህ በታች የተያያዙትን ሦስቱን ኦፊሴላዊ የፒዲኤፍ መመሪያዎች ማውረድ ይችላሉ፦"
        )
        
        if 'peace' in pdf_cache:
            await update.message.reply_document(document=pdf_cache['peace'], filename="peace_army_regulation.pdf", caption="📄 1. የሰላም ሰራዊት አደረጃጀት፣ አሰራር እና ተግባርና ኃላፊነት ደንብ")
        if 'fee' in pdf_cache:
            await update.message.reply_document(document=pdf_cache['fee'], filename="loading_fee_directive.pdf", caption="📄 2. የመጫንና ማውረድ አገልግሎት ክፍያ ተመን")
        if 'loader' in pdf_cache:
            await update.message.reply_document(document=pdf_cache['loader'], filename="loader_directive.pdf", caption="📄 3. ጫኝና አውራጅ መመሪያ")
        return

    elif text == "5/የአገልግሎት ስታንዳርዶች ለማየት":
        context.user_data.clear()
        await update.message.reply_text(
            "📊 **የልደታ ክ/ከተማ ሰላምና ጸጥታ ጽ/ቤት የአገልግሎት ስታንዳርዶች**\n\n"
            "እባክዎ የተሟላውን የስታንዳርድ ፒዲኤፍ ሰነድ ከዚህ በታች ያውርዱ፦"
        )
        if 'standards' in pdf_cache:
            await update.message.reply_document(document=pdf_cache['standards'], filename="service_standards.pdf", caption="📊 የአገልግሎት ስታንዳርዶች ሰነድ")
        return

    elif text == "6/አገልግሎቶች ላይ አስተያየት ለመስጠት":
        context.user_data.clear()
        context.user_data['state'] = 'FEEDBACK_RATING'
        context.user_data['feedback_data'] = {}
        await update.message.reply_text(
            "⭐ **አገልግሎቶች ላይ አስተያየት ለመስጠት**\n\n"
            "በጽ/ቤቱ ያገኙትን አገልግሎት እንዴት ይገልጹታል? (ለምሳሌ፦ ‹ሀ› ወይም ‹በጣም ከፍተኛ› ብለው መጻፍ ይችላሉ)\n\n"
            "ሀ) በጣም ከፍተኛ\n"
            "ለ) ከፍተኛ\n"
            "ሐ) መካከለኛ\n"
            "መ) ዝቅተኛ"
        )
        return

    # ==========================================
    # 3. የጥቆማ (Tip) የደረጃ በደረጃ አሰጣጥ ሂደት
    # ==========================================
    if state == 'TIP_WOREDA':
        context.user_data['tip_data']['woreda'] = text
        context.user_data['state'] = 'TIP_LOCATION'
        await update.message.reply_text("መረጃውን የሚሰጡበትን **ቀጠና እና ልዩ ቦታ** ይግለጹ (በቁጥር፣ በጽሁፍ ወይም በሁለቱም)፦")
        return

    elif state == 'TIP_LOCATION':
        context.user_data['tip_data']['location'] = text
        context.user_data['state'] = 'TIP_DETAILS'
        await update.message.reply_text("የጥቆማውን **ዝርዝር ሁኔታ** ይግለጹልን፦")
        return

    elif state == 'TIP_DETAILS':
        context.user_data['tip_data']['details'] = text
        context.user_data.clear()
        await update.message.reply_text("ለሰጡን መረጃና ጥቆማ እናመሰግናለን!")
        return

    # ==========================================
    # 4. የቅሬታ (Complaint) የደረጃ በደረጃ አሰጣጥ ሂደት
    # ==========================================
    elif state == 'COMPLAINT_NAME':
        context.user_data['complaint_data']['name'] = text
        context.user_data['state'] = 'COMPLAINT_WOREDA'
        await update.message.reply_text("እባክዎ **ወረዳ** ያስገቡ (በቁጥር ወይም በጽሁፍ)፦")
        return

    elif state == 'COMPLAINT_WOREDA':
        context.user_data['complaint_data']['woreda'] = text
        context.user_data['state'] = 'COMPLAINT_ZONE'
        await update.message.reply_text("እባክዎ **ቀጠና** ያስገቡ (በቁጥር ወይም በጽሁፍ)፦")
        return

    elif state == 'COMPLAINT_ZONE':
        context.user_data['complaint_data']['zone'] = text
        context.user_data['state'] = 'COMPLAINT_HOUSE'
        await update.message.reply_text("እባክዎ **የቤት ቁጥር** ያስገቡ (በቁጥር ብቻ)፦")
        return

    elif state == 'COMPLAINT_HOUSE':
        context.user_data['complaint_data']['house'] = text
        context.user_data['state'] = 'COMPLAINT_DETAILS'
        await update.message.reply_text("ቅሬታ የሚያቀርቡበትን **ዝርዝር ሁኔታ** ይግለጹ፦")
        return

    elif state == 'COMPLAINT_DETAILS':
        context.user_data['complaint_data']['details'] = text
        context.user_data['state'] = 'COMPLAINT_HELP'
        await update.message.reply_text("ጽ/ቤቱ እንዲያደርግሎት የሚፈልጉትን **እገዛ/መፍትሄ** ይግለጹ፦")
        return

    elif state == 'COMPLAINT_HELP':
        context.user_data['complaint_data']['help'] = text
        context.user_data['state'] = 'COMPLAINT_PHONE'
        await update.message.reply_text("ለቅሬታው ምላሽ እንድንሰጥዎ **ስልክ ቁጥርዎን** እዚህ ይጻፉ (በቁጥር ብቻ)፦")
        return

    elif state == 'COMPLAINT_PHONE':
        context.user_data['complaint_data']['phone'] = text
        context.user_data.clear()
        await update.message.reply_text("ቅሬታዎ ደርሶናል በአጭር ግዜ ውስጥ ምላሽ እንሰጣለን")
        return

    # ==========================================
    # 5. የአስተያየት (Feedback) ሂደት
    # ==========================================
    elif state == 'FEEDBACK_RATING':
        context.user_data['feedback_data']['rating'] = text
        context.user_data['state'] = 'FEEDBACK_COMMENT'
        await update.message.reply_text("በቀጣይ ሊስተካከል ይገባዋል የሚሉት ካለ እዚህ ይጻፉልን፦")
        return

    elif state == 'FEEDBACK_COMMENT':
        context.user_data['feedback_data']['comment'] = text
        context.user_data.clear()
        await update.message.reply_text("አስተያየትዎን ስለሰጡን እናመሰግናለን!")
        return

    else:
        await update.message.reply_text(
            "እባክዎ ከታች ካሉት ቁልፎች (Buttons) አንዱን በመምረጥ አገልግሎቱን ይጠቀሙ።"
        )

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==========================================
# 3. የ Flask እና Webhook ማዋቀሪያ ክፍሎች
# ==========================================
@app.route('/')
def home():
    return "Lideta Security Bot is live with Webhook!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        
        # ሉፑን ሳይለቁ በአስተማማኝ ሁኔታ ማካሄድ
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update), loop
        )
        try:
            future.result(timeout=10)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
