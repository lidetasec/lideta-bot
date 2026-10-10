import logging
from flask import Flask
import threading
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==================== 🔑 ቶክን እና ID የሚገባበት ቦታ ====================
BOT_TOKEN = "8783351900:AAGNyRekcgyZH70Kx3n1PpdLtYxzOrKTGEI"
ADMIN_CHAT_ID = 1340095551

# የትእዛዝ ሁኔታዎች (States)
CHOOSING, TIP_WEREDA, TIP_LOCATION, TIP_DETAILS, COMPLAINT_NAME, COMPLAINT_OFFICE, COMPLAINT_DETAILS, FEEDBACK_TEXT = range(8)

# ዋና ሜኑ ቁልፎች
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🚨 መረጃና ጥቆማ ለመስጠት", "📝 ቅሬታ ለማቅረብ"],
        ["💡 አስተያየት ለመስጠት", "📋 የሚሰጡ አገልግሎቶች"],
        ["📞 ስለ እኛ / የእውቂያ መረጃ"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "እንኳን ወደ ልደታ ክፍለ ከተማ የሰላምና ፀጥታ አስተዳደር ጽህፈት ቤት አውቶሜትድ ቦት በሰላም መጡ! 👋\n\n"
        "እባክዎን ከታች ካሉት አማራጮች የሚፈልጉትን አገልግሎት ይምረጡ፦"
    )
    await update.message.reply_text(welcome_text, reply_markup=MAIN_KEYBOARD)
    return CHOOSING

# ==================== 1. መረጃና ጥቆማ ====================
async def tip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "እባክዎን መረጃውን ወይም ጥቆማውን የሚሰጡበትን ወረዳ ይጠቅሱ፦",
        reply_markup=ReplyKeyboardRemove()
    )
    return TIP_WEREDA

async def tip_wereda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tip_wereda'] = update.message.text
    await update.message.reply_text("እባክዎን መረጃውን ወይም ጥቆማውን የሚሰጡበትን ቀጠና እና ልዩ ቦታ ይጠቅሱ፦")
    return TIP_LOCATION

async def tip_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tip_location'] = update.message.text
    await update.message.reply_text("እባክዎን የሚሰጡንን መረጃ ወይም ጥቆማ ዝርዝር ሁኔታ ይግለጹልን፦")
    return TIP_DETAILS

async def tip_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tip_details'] = update.message.text
    user = update.message.from_user
    
    await update.message.reply_text(
        "ለሰጡን መረጃና ጥቆማ እናመሰግናለን! መረጃውን መርምረን በአጭር ጊዜ ውስጥ ምላሽ እንሰጣለን።",
        reply_markup=MAIN_KEYBOARD
    )
    
    admin_msg = (
        "🚨 **አዲስ የፀጥታ ጥቆማ ደርሷል!**\n\n"
        f"👤 **ላኪ:** {user.full_name} (@{user.username if user.username else 'የለውም'})\n"
        f"📍 **ወረዳ:** {context.user_data['tip_wereda']}\n"
        f"🏢 **ቀጠና/ቦታ:** {context.user_data['tip_location']}\n"
        f"📝 **የጥቆማው ዝርዝር:**\n{context.user_data['tip_details']}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
    return CHOOSING

# ==================== 2. ቅሬታ ማቅረቢያ ====================
async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "የቅሬታ አቅራቢውን ሙሉ ስም እና የስልክ ቁጥር ያስገቡ፦",
        reply_markup=ReplyKeyboardRemove()
    )
    return COMPLAINT_NAME

async def complaint_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['comp_name'] = update.message.text
    await update.message.reply_text("ቅሬታው የሚመለከተውን ወረዳ ወይም የቢሮ ክፍል ይጠቅሱ፦")
    return COMPLAINT_OFFICE

async def complaint_office(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['comp_office'] = update.message.text
    await update.message.reply_text("እባክዎን የቅሬታዎን ዝርዝር ምክንያት ይጻፉልን፦")
    return COMPLAINT_DETAILS

async def complaint_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['comp_details'] = update.message.text
    user = update.message.from_user
    
    await update.message.reply_text(
        "ቅሬታዎ በትክክል ተመዝግቧል። የሚመለከተው አካል መርምሮ ምላሽ የሚሰጥዎ ይሆናል። እናመሰግናለን!",
        reply_markup=MAIN_KEYBOARD
    )
    
    admin_msg = (
        "⚠️ **አዲስ ቅሬታ ደርሷል!**\n\n"
        f"👤 **አቅራቢ:** {context.user_data['comp_name']}\n"
        f"🔗 **Telegram:** @{user.username if user.username else 'የለውም'}\n"
        f"🏢 **የሚመለከተው ክፍል/ወረዳ:** {context.user_data['comp_office']}\n"
        f"📄 **የቅሬታው ዝርዝር:**\n{context.user_data['comp_details']}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
    return CHOOSING

# ==================== 3. አስተያየት መስጫ ====================
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ለጽህፈት ቤታችን አገልግሎት ማሻሻያ የሚሆን አስተያየትዎን ይጻፉልን፦",
        reply_markup=ReplyKeyboardRemove()
    )
    return FEEDBACK_TEXT

async def feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    
    await update.message.reply_text(
        "ለሰጡን አስተያየት እናመሰግናለን!",
        reply_markup=MAIN_KEYBOARD
    )
    
    admin_msg = (
        "💡 **አዲስ አስተያየት ደርሷል!**\n\n"
        f"👤 **ላኪ:** {user.full_name} (@{user.username if user.username else 'የለውም'})\n"
        f"💬 **አስተያየት:**\n{text}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
    return CHOOSING

# ==================== 4. አገልግሎቶች እና መረጃ ====================
async def services_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "📋 **የጽህፈት ቤቱ ዋና ዋና አገልግሎቶች፦**\n\n"
        "1. የህዝብና የአካባቢን ሰላምና ፀጥታ ማስጠበቅ\n"
        "2. የህብረተሰብ አቀፍ ፖሊስ አሰራርን ማጠናከር\n"
        "3. የፀጥታ ስጋቶችን እና የህግ መጣስ ጥቆማዎችን መቀበልና መፍትሄ መስጠት\n"
        "4. የህብረተሰብ ቅሬታዎችን ማስተናገድ\n\n"
        "🕒 **የስራ ሰዓት፦** ከሰኞ እስከ አርብ (ከጠዋቱ 2:30 - 11:30)"
    )
    await update.message.reply_text(info, reply_markup=MAIN_KEYBOARD, parse_mode='Markdown')
    return CHOOSING

async def about_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = (
        "📞 **ስለ እኛ / የእውቂያ መረጃ**\n\n"
        "🏢 **አድራሻ:** ልደታ ክፍለ ከተማ አስተዳደር ጽህፈት ቤት ህንፃ\n"
        "📍 **ቦታ:** አዲስ አበባ፣ ኢትዮጵያ\n"
        "☎️ **የአደጋ ጊዜ / የነፃ መስመር:** 930\n"
        "📧 **ኢሜይል:** info@lideta.gov.et"
    )
    await update.message.reply_text(info, reply_markup=MAIN_KEYBOARD, parse_mode='Markdown')
    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ሂደቱ ተቋርጧል።", reply_markup=MAIN_KEYBOARD)
    return CHOOSING

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(filters.Regex('^🚨 መረጃና ጥቆማ ለመስጠት$'), tip_start),
                MessageHandler(filters.Regex('^📝 ቅሬታ ለማቅረብ$'), complaint_start),
                MessageHandler(filters.Regex('^💡 አስተያየት ለመስጠት$'), feedback_start),
                MessageHandler(filters.Regex('^📋 የሚሰጡ አገልግሎቶች$'), services_info),
                MessageHandler(filters.Regex('^📞 ስለ እኛ / የእውቂያ መረጃ$'), about_info),
            ],
            TIP_WEREDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, tip_wereda)],
            TIP_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, tip_location)],
            TIP_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, tip_details)],
            COMPLAINT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_name)],
            COMPLAINT_OFFICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_office)],
            COMPLAINT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint_details)],
            FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
    )

    app.add_handler(conv_handler)
    print("ቦቱ ስራ ጀምሯል...")
    app.run_polling()
from flask import Flask, request
import asyncio
import os
from telegram import Update
from telegram.ext import Application

# የ Flask ሰርቨር (Gunicorn ከዚህ ጋር ይገናኛል: bot:app)
app = Flask(__name__)

# የቴሌግራም ቦት ቶከን
TOKEN = os.environ.get("TELEGRAM_TOKEN") 

# ከ Flask ሰርቨር ጋር ስም እንዳይጋጭ የቴሌግራም አፕሊኬሽኑን telegram_app ብለን እንሰርዘዋለን/እንፈጥረዋለን
telegram_app = Application.builder().token(TOKEN).build()

# --- (እዚህጋ የነበሩህን CommandHandler እና MessageHandler ሃንድለሮችህን ማስገባት ትችላለህ) ---
# ምሳሌ፦
# from telegram.ext import CommandHandler
# async def start(update, context):
#     await update.message.reply_text("ሰላም! የሊደታ ሰብ-ሲቲ ጸጥታ ቢሮ ቦት ነው።")
# telegram_app.add_handler(CommandHandler("start", start))
# ----------------------------------------------------------------------------------

@app.route('/')
def home():
    return "Lideta Security Bot is live with Webhook!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """ቴሌግራም የሚልካቸውን መረጃዎች የሚቀበልበት ዌብሁክ ኤንድፖይንት"""
    if request.method == 'POST':
        json_data = request.get_json()
        update = Update.de_json(json_data, telegram_app.bot)
        
        async def process():
            await telegram_app.initialize()
            await telegram_app.process_update(update)
            
        asyncio.run(process())
    return 'OK', 200

# ሰርቨሩ ሲነሳ ዌብሁክን ከቴሌግራም ጋር ማያያዝ
def set_webhook():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def init_webhook():
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(url="https://llideta-security-bot.onrender.com/webhook")
    loop.run_until_complete(init_webhook())

# ዌብሁክን ማስጀመር
set_webhook()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    from flask import Flask, request
import asyncio
import os

app = Flask(__name__)

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
