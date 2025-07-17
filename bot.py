import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# ==== CONFIG ====
GROUP_CHAT_ID = -1002280657250  # ID вашей Telegram-группы

# ==== LOGGING ====
logging.basicConfig(level=logging.INFO)

# ==== ЗАГРУЗКА ТОКЕНА ====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


# ==== ОБРАБОТКА /start ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code

    if lang == "uk":
        text = "🏗️ Ласкаво просимо!\nМи — компанія Авабуд 🧱\n📞 Зв’язок: +380957347113"
        keyboard = [["📨 Надіслати заявку", "📞 Зв’язатися з нами"]]
    else:
        text = "🏗️ Добро пожаловать!\nМы — компания Авабуд 🧱\n📞 Связь: +380957347113"
        keyboard = [["📨 Отправить заявку", "📞 Связаться с нами"]]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup)

    # Сохраняем ID пользователя
    with open("clients.txt", "a") as f:
        f.write(f"{user.id} — {datetime.now(timezone.utc).isoformat()}\n")


# ==== ОБРАБОТКА СООБЩЕНИЙ ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text.lower()
    lang = user.language_code

    # Переслать сообщение администратору
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"📥 Заявка от @{user.username or user.first_name} ({user.id}):\n{update.message.text}"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки в группу: {e}")

    # Ответ пользователю
    if "связ" in message_text or "зв’яз" in message_text:
        response = "📞 Свяжитесь с нами: +380957347113" if lang != "uk" else "📞 Зв’яжіться з нами: +380957347113"
    elif "заявк" in message_text or "надіслат" in message_text or "отправ" in message_text:
        response = "📨 Пожалуйста, отправьте список необходимых стройматериалов." if lang != "uk" else "📨 Будь ласка, надішліть список необхідних будматеріалів."
    else:
        response = "🤖 Спасибо за сообщение! Мы скоро вам ответим." if lang != "uk" else "🤖 Дякуємо за повідомлення! Ми скоро вам відповімо."

    await update.message.reply_text(response)


# ==== РАССЫЛКА НАПОМИНАНИЙ ====
async def send_reminder(app):
    if not os.path.exists("clients.txt"):
        return

    with open("clients.txt") as f:
        ids = set()
        for line in f:
            if line.strip():
                parts = line.strip().split("—")
                if parts and parts[0].strip().isdigit():
                    ids.add(parts[0].strip())

    for user_id in ids:
        try:
            await app.bot.send_message(
                chat_id=int(user_id),
                text="👷 Напоминаем, что вы можете отправить заявку на стройматериалы.\nМы всегда готовы помочь! 📦"
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")


# ==== ЗАПУСК ====
async def post_init(app):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(send_reminder, "cron", hour="9-16", minute=0, day_of_week="mon-fri", args=[app])
    scheduler.start()
    logging.info("Планировщик запущен")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не найден. Убедитесь, что он указан в .env")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
