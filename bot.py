import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "8181633106:AAH-3_auad582SBGFV_At3qXdyQgMYr41XY"
CLIENTS_FILE = "clients.txt"
LAST_SEEN_FILE = "last_seen.txt"

REMINDER_MESSAGE = (
    "👷 Напоминаем, что вы можете отправить заявку на стройматериалы.\n"
    "Мы всегда готовы уточнить цены и помочь с заказом! 📦"
)

def save_last_seen():
    with open(LAST_SEEN_FILE, 'w') as f:
        f.write(datetime.utcnow().isoformat())

def load_last_seen():
    if not os.path.exists(LAST_SEEN_FILE):
        return None
    with open(LAST_SEEN_FILE, 'r') as f:
        try:
            return datetime.fromisoformat(f.read().strip())
        except:
            return None

def save_client_id(user_id):
    if not os.path.exists(CLIENTS_FILE):
        open(CLIENTS_FILE, 'w').close()

    with open(CLIENTS_FILE, 'r') as f:
        ids = f.read().splitlines()

    if str(user_id) not in ids:
        with open(CLIENTS_FILE, 'a') as f:
            f.write(f"{user_id}\n")

def get_all_client_ids():
    if not os.path.exists(CLIENTS_FILE):
        return []
    with open(CLIENTS_FILE, 'r') as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_client_id(user_id)

    keyboard = [["📨 Отправить заявку", "📞 Связаться с нами"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = (
        "🏗️ *Добро пожаловать!*\n\n"
        "Мы — компания *Авабуд* 🧱\n"
        "Помогаем быстро и выгодно заказать стройматериалы.\n\n"
        "📞 Связь с нами: +380957347113"
    )

    await update.message.reply_text(welcome_message, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    save_client_id(user_id)

    last_seen = load_last_seen()
    if last_seen:
        time_diff = datetime.utcnow() - last_seen
        if time_diff > timedelta(minutes=30):
            await update.message.reply_text("🙏 Извините за задержку. Мы были временно недоступны, но снова на связи!")

    if "связаться" in text:
        await update.message.reply_text("📞 Наша связь: +380957347113")
    elif "заявку" in text or "отправить" in text:
        await update.message.reply_text("✍️ Пожалуйста, напишите список товаров, которые вас интересуют. Мы свяжемся с вами в ближайшее время.")
        # Также можно здесь переслать админу
    else:
        await update.message.reply_text("🤖 Спасибо за сообщение! Мы скоро вам ответим.")

async def send_reminders(app):
    client_ids = get_all_client_ids()
    now = datetime.utcnow()
    if now.weekday() >= 5 or not (9 <= now.hour < 17):
        return  # только в будни с 9:00 до 17:00

    for client_id in client_ids:
        try:
            await app.bot.send_message(chat_id=client_id, text=REMINDER_MESSAGE)
        except Exception as e:
            print(f"Ошибка при отправке клиенту {client_id}: {e}")

def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone='UTC')
    scheduler.add_job(lambda: asyncio.run(send_reminders(app)), 'cron', day_of_week='mon-fri', hour='9-16')
    scheduler.start()

if __name__ == '__main__':
    save_last_seen()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    start_scheduler(app)

    print("🤖 Бот запущен.")
    app.run_polling()
import os

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Получаем токен из переменной окружения (для безопасности)
    TOKEN = os.environ.get("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    start_scheduler(app)

    print("🤖 Бот запущен.")
    app.run_polling()
