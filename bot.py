# --- Загрузка переменных из .env ---
from dotenv import load_dotenv
load_dotenv()

import os
import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

# --- Функции для команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сообщение получено.")

async def send_reminder(app):
    # Здесь можно вставить свою функцию рассылки напоминаний
    pass

async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=7124318893,  # Замени на нужный user_id, если хочешь
            text="✅ Тестовая рассылка работает!"
        )
        await update.message.reply_text("📤 Сообщение отправлено пользователю 7124318893.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

async def post_init(app):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(send_reminder, "cron", hour="9-16", minute=0, day_of_week="mon-fri", args=[app])
    scheduler.start()
    logging.info("Планировщик запущен")

# --- Главная функция ---

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не найден. Убедитесь, что он указан в .env")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("testsend", test_send))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
