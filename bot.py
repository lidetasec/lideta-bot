import logging
import os
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# የሎጊንግ ማዋቀር (ስህተቶችን እና የቦቱን እንቅስቃሴዎች ለመከታተል)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# የ Flask ሰርቨር ማዋቀር (Gunicorn ከዚህ ጋር ይገናኛል: bot:app)
app = Flask(__name__)

# የቴሌግራም ቦት ቶከን ከሬንደር Environment Variables ማንበብ
TOKEN = os.environ.get("TELEGRAM_TOKEN") 

# የቴሌግራም አፕሊኬሽን ማዋቀር
application = Application.builder().token(TOKEN).build()

# ==========================================
# 1. የ /start ትዕዛዝ እና 6ቱ ዋና ዋና ሜኑ በተኖች
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # በምስሉ ላይ እንደሚታየው ትክክለኛ ምልክቶችን የያዙ ቁልፎች
    keyboard = [
        ["1/መረጃና ጥቆማ ለመስጠት"],
        ["2/ስለ ፅ/ቤቱ ራዕይ ፤ተልዕኮ እና እሴቶች ለማወቅ"],
        ["3/ቅሬታ ለማቅረብ"],
        ["4/መመሪያዎችን ለመመልከት"],
        ["5/የአገልግሎት ስታንዳርዶች ለማየት"],
        ["6/አገልግሎቶች ላይ አስተያየት ለመስጠት"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # የሰላምታ መልእክት
    welcome_text = (
        "እንኳን ወደ ልደታ ክ/ከተማ ሰላምና ጸጥታ ጽሕፈት ቤት ቴሌግራም ቦት በሰላም መጡ። "
        "ከታች ያሉትን ቁልፎች በመጠቀም የሚፈልጉትን አገልግሎት ማግኘት ይችላሉ።"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

# ==========================================
# 2. ተጠቃሚው በተኖቹን ሲነካ እና መልእክት ሲልክ የሚሰጠው ምላሽ
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "1/መረጃና ጥቆማ ለመስጠት":
        context.user_data['waiting_for'] = 'tip'
        await update.message.reply_text(
            "📍 **መረጃና ጥቆማ ለመስጠት**\n\n"
            "እባክዎ መረጃዎን በሚከተለው መልኩ በጽሁፍ ይላኩልን፦\n"
            "1. የሚሰጡበት ወረዳ\n"
            "2. መረጃውን የሚሰጡበት ቀጠና እና ልዩ ቦታ\n"
            "3. የጥቆማው ዝርዝር ሁኔታ\n\n"
            "መልእክትዎ በሚስጥር ይጠበቃል።"
        )
    elif text == "2/ስለ ፅ/ቤቱ ራዕይ ፤ተልዕኮ እና እሴቶች ለማወቅ":
        context.user_data['waiting_for'] = None
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
        
    elif text == "3/ቅሬታ ለማቅረብ":
        context.user_data['waiting_for'] = 'complaint'
        await update.message.reply_text(
            "📝 **ቅሬታ ለማቅረብ**\n\n"
            "እባክዎ ቅሬታዎን ለማስተናገድ የሚከተሉትን መረጃዎች ሙሉ በሙሉ ይጻፉልን፦\n"
            "1. ሙሉ ስምዎ\n"
            "2. ወረዳ\n"
            "3. ቀጠና\n"
            "4. የቤት ቁጥር\n"
            "5. ቅሬታ የሚያቀርቡበት ዝርዝር ሁኔታ\n"
            "6. ጽ/ቤቱ እንዲያደርግሎት የሚፈልጉት እገዛ/መፍትሄ\n"
            "7. ምላሽ ለመስጠት እንችል ዘንድ ስልክ ቁጥሮን ያስገቡ"
        )
    elif text == "4/መመሪያዎችን ለመመልከት":
        context.user_data['waiting_for'] = None
        directives_text = (
            "📂 **የጽ/ቤቱ መመሪያዎች እና ደንቦች**\n\n"
            "1️⃣ **ደንብ ቁጥር ፩፻፵/፪ሺ፲፬ (የሰላም ሰራዊት አደረጃጀት፣ አሰራር እና ተግባርና ኃላፊነት ደንብ)**\n"
            "• **ዓላማ፡** ነዋሪዎች በመንደር፣ በብሎክ እና በቀጠና አደረጃጀቶች ተደራጅተው ከፀጥታ ቋሚ ኃይሎች ጋር በመቀናጀት አካባቢያቸውን እንዲጠብቁ ማድረግ[cite: 38, 41]。\n"
            "• **አደረጃጀት፡** የመንደር፣ የብሎክ እና የቀጠና የሰላም ሰራዊት አመራር ኮሚቴዎች[cite: 41, 42, 43, 44]。\n"
            "• **ዋና ዋና ተግባራት፡** ሮንድ መውጣት፣ የፀጉረ-ልውጦች እና የሽብር እንቅስቃሴዎችን መከታተል፣ ህገ-ወጥ ግንባታዎችንና የመሬት ወረራዎችን መከላከል፣ የስነ-ምግባር ግንባታ መስራት[cite: 41, 42]。\n\n"
            "2️⃣ **የጫኝና አውራጅ ማህበራት አሰጣጥ ለመከታተልና ለመቆጣጠር የወጣ መመሪያ እና የዋጋ ተመን**\n"
            "• **ዓላማ፡** የጫኝና አውራጅ ማህበራትን አደረጃጀት፣ አሰራር እና የዋጋ ተመን በመወሰን የህብረተሰቡን እንግልት እና የተጋነነ ክፍያ ማስቀረት[cite: 72, 73, 79, 80]。\n"
            "• **አባልነት መስፈርት፡** የነዋሪነት መታወቂያ ያለው፣ ከ18 ዓመት በላይ፣ ስራ አጥ፣ ከወንጀል ንጹህ የሆነ፣ ስነ-ምግባር ያለው[cite: 85]。\n"
            "• **የዋጋ ተመን ማሻሻያ፡** የቤት እቃዎች፣ የኮንስትራክሽን እቃዎች፣ የቢሮ እቃዎች፣ ፍራፍሬዎች፣ አትክልቶች እና ጥራጥሬዎች መጫንና ማውረድ የተሻሻለ የዋጋ ተመን መመሪያ ተካትቷል።"
        )
        await update.message.reply_text(directives_text)
    elif text == "5/የአገልግሎት ስታንዳርዶች ለማየት":
        context.user_data['waiting_for'] = None
        standards_text = (
            "📊 **የልደታ ክ/ከተማ ሰላምና ጸጥታ ጽ/ቤት የአገልግሎት ስታንዳርዶች**\n\n"
            "1️⃣ **የሃይማኖትና የሰላም እሴት ግንባታ ስራሂደት**\n"
            "• የሃይማኖትና እምነት ተቋማት ድጋፍ፣ ክትትልና የምዝገባ ፈቃድ ማጣራት\n"
            "• ህገ-መንግስታዊ እና የሴኩላሪዝም መርሆች አፈጻጸም ክትትል\n"
            "• ህዝባዊና ሃይማኖታዊ ክብረ-በዓላት ሰላማዊ ክትትል\n"
            "• የሰላም ግንባታ ስልጠናዎች፣ ህዝብ ለህዝብ ትስስር እና የሰላም ኮንፍረንሶች\n"
            "• ባህላዊ የእርቅና ሽምግልና እሴቶች ግንባታ\n\n"
            "2️⃣ **የማህበረሰብ ፀጥታ ንቅናቄና የብዙሃን ማህበራት ድጋፍ ስራሂደት**\n"
            "• የማህበረሰብ ንቅናቄ፣ ፓናል ውይይቶች እና ኮንፍረንሶች ማስተባበር\n"
            "• በነዋሪዎች ተሳትፎ የህዝብ ቅጥር ጥበቃ አደረጃጀት እና ስምሪት\n"
            "• የማህበረሰብ ተኮር 7/24 ጸጥታ አጠባበቅ እና ምክክር መድረኮች\n"
            "• የሰላም ሰራዊት እና ጫኝና አውራጅ ማህበራት ምልመላ፣ ስልጠናና ስምሪት ክትትል\n\n"
            "3️⃣ **የፀጥታ መረጃ ግጭት ቅድመ ማስጠንቀቂያና ፈጣን ምላሽ ስራሂደት**\n"
            "• የ24 ሰዓት የፀጥታ መረጃ መሰብሰብ፣ ማጣራትና መተንተን\n"
            "• የማንነትና ቡድን ፀብ፣ ፀረ-ሰላም ሃይሎች እና ድንበር ተሻጋሪ ሽብርተኞች ክትትል\n"
            "• የተደራጁ ወንጀሎች፣ ሌብነት፣ ቅሚያ፣ ህገ-ወጥ የጦር መሳሪያና የገንዘብ ዝውውር ክትትል\n"
            "• የግጭት ቅድመ ማስጠንቀቂያ፣ ፈጣን ምላሽ እና የመሬት ወረራ/ህገወጥ ግንባታ ግጭቶች አፈታት\n\n"
            "4️⃣ **የፀጥታ ጉዳዮች ክትትል ቁጥጥርና ኦፕሬሽን ስራሂደት**\n"
            "• ህገ-ወጥ ተግባራትንና ወንጀል መከላከል፣ እርምጃ መውሰድና ማስወሰድ\n"
            "• ድንገተኛ የፀጥታ ኦፕሬሽን እና በዓላት/ኩነቶች ፀጥታ አስተባባሪነት\n"
            "• ግጭት መፍታትና ማስተዳደር እንዲሁም ቅሬታዎችን መፍታት\n"
            "• የማህበረሰብ አቀፍ ፖሊስ ማዕከላት፣ የግል ጥበቃ ኤጀንሲዎች እና የተቋማት ደህንነት ክትትል"
        )
        await update.message.reply_text(standards_text)
    elif text == "6/አገልግሎቶች ላይ አስተያየት ለመስጠት":
        context.user_data['waiting_for'] = 'feedback_rating'
        await update.message.reply_text(
            "⭐ **አገልግሎቶች ላይ አስተያየት ለመስጠት**\n\n"
            "በጽ/ቤቱ አገልግሎቶች ምን ያህል እረክተዋል? እባክዎን ከታች ካሉት አማራጮች አንዱን ይምረጡ፦\n\n"
            "ሀ) በጣም ከፍተኛ\n"
            "ለ) ከፍተኛ\n"
            "ሐ) መካከለኛ\n"
            "መ) ዝቅተኛ"
        )
    else:
        waiting_for = context.user_data.get('waiting_for')
        if waiting_for == 'tip':
            context.user_data['waiting_for'] = None
            await update.message.reply_text("ስለሰጡን መረጃና ጥቆማ እናመሰግናለን!")
        elif waiting_for == 'complaint':
            context.user_data['waiting_for'] = None
            await update.message.reply_text("ቅሬታዎ ደርሶናል በአጭር ግዜ ውስጥ ምላሽ እንሰጣለን")
        elif waiting_for == 'feedback_rating':
            context.user_data['waiting_for'] = 'feedback_comment'
            await update.message.reply_text("በቀጣይ ሊስተካከል ይገባዋል የሚሉትን አስተያየትዎን ይግለፁ")
        elif waiting_for == 'feedback_comment':
            context.user_data['waiting_for'] = None
            await update.message.reply_text("አስተያየትዎን ስለሰጡን እናመሰግናለን!")
        else:
            await update.message.reply_text(
                "መልእክትዎ ደርሷል። እናመሰግናለን!"
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
        
        async def process():
            await application.initialize()
            await application.process_update(update)
            
        asyncio.run(process())
    return 'OK', 200

def set_webhook():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def init_webhook():
        await application.initialize()
        await application.bot.set_webhook(url="https://llideta-security-bot.onrender.com/webhook")
    loop.run_until_complete(init_webhook())

set_webhook()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
