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
# 1. የ /start ትዕዛዝ እና ዋናው ሜኑ (Buttons)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ተጠቃሚው የሚመርጣቸው ዋና ዋና ቁልፎች
    keyboard = [
        ["🚨 ጥቆማ ለማድረስ", "ℹ️ ስለ ቢሮው"],
        ["📞 የእውቂያ ስልክ", "❓ አደጋ ጊዜ ጥሪ"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # የጠየቁት ትክክለኛ ሰላምታ እና መልእክት
    welcome_text = (
        "እንኳን ወደ ልደታ ክ/ከተማ ሰላምና ፀጥታ ፅ/ቤት ቦት በሰላም መጡ! "
        "የሚፈልጉትን አገልግሎት ከዝርዝሮቹ ውስጥ ይምረጡ"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

application.add_handler(CommandHandler("start", start))

# ==========================================
# 2. ተጠቃሚው ቁልፎቹን ሲነካ የሚሰጠው ምላሽ (Message Handler)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🚨 ጥቆማ ለማድረስ":
        await update.message.reply_text(
            "እባክዎ ስለሚፈልጉት ጥቆማ ዝርዝር መረጃ በጽሁፍ ይላኩልን። መረጃዎ ሚስጥሩ የተጠበቀ ነው።"
        )
    elif text == "ℹ️ ስለ ቢሮው":
        await update.message.reply_text(
            "የልደታ ክ/ከተማ ሰላምና ፀጥታ ፅ/ቤት በሰላም ማስከበር፣ በህግ ማክበር እና በህብረተሰቡ ደህንነት ዙሪያ የሚሰራ ተቋም ነው።"
        )
    elif text == "📞 የእውቂያ ስልክ":
        await update.message.reply_text(
            "📞 የቢሮው ዋና መስመር ስልክ ቁጥር:\n011-...\n\nለድንገተኛ ጊዜ ሁል ጊዜ ዝግጁ ነን!"
        )
    elif text == "❓ አደጋ ጊዜ ጥሪ":
        await update.message.reply_text(
            "🚨 አደጋ ወይም አጠራጣሪ ሁኔታ ሲያጋጥም ወዲያውኑ ለቁጥር 991 ወይም ለባለሙያዎቻችን ያሳውቁ።"
        )
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
    """ቴሌግራም የሚልካቸውን መረጃዎች የሚቀበልበት ዌብሁክ ኤንድፖይንት"""
    if request.method == 'POST':
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        
        async def process():
            await application.initialize()
            await application.process_update(update)
            
        asyncio.run(process())
    return 'OK', 200

# ሰርቨሩ ሲነሳ ዌብሁክን ከቴሌግራም ጋር ማያያዝ
def set_webhook():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def init_webhook():
        await application.initialize()
        await application.bot.set_webhook(url="https://llideta-security-bot.onrender.com/webhook")
    loop.run_until_complete(init_webhook())

# ዌብሁክን ማስጀመር
set_webhook()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
