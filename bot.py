import logging
import os
from datetime import datetime, timezone

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# ==== CONFIG ====
GROUP_CHAT_ID = -1002280657250  # <-- поменяй на id своей чат-группы!
CLIENTS_PATH = "/data/clients.txt"   # Использовать Persistent Disk Render!

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s: %(message)s'
)

# ==== LOAD ENV ====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def add_client(user_id: int):
    """Добавляет user_id в clients.txt, если такого ещё нет."""
    if not os.path.exists(CLIENTS_PATH):
        with open(CLIENTS_PATH, "w", encoding="utf-8"): pass
    with open(CLIENTS_PATH, encoding="utf-8", errors="replace") as f:
        existing = set(line.split("—")[0].strip() for line in f if line.strip())
    if str(user_id) not in existing:
        with open(CLIENTS_PATH, "a", encoding="utf-8") as f:
            f.write(f"{user_id} — {datetime.now(timezone.utc).isoformat()}\n")

# ==== ERROR HANDLER ====
async def error_handler(update, context):
    logging.error("Exception while handling an update:", exc_info=context.error)

# ==== TEST CMD ====
async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=7124318893,  # Замени на нужный user_id
            text="✅ Тестовая рассылка работает!"
        )
        await update.message.reply_text("📤 Сообщение отправлено пользователю 7124318893.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

# ==== START ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = user.language_code or 'ru'
    # Приветствие и кнопки
    if lang == "uk":
        text = (
            "🧱 Авабуд — твій помічник на будівництві! 🛠️\n"
            "Компанія Авабуд — надійний партнер для будівельників 👷‍♂️\n"
            "Власні склади 🏢, транспорт 🚚 та найкращі партнерські ціни 💰\n\n"
            "✅ У нас — дешевше, швидше та якісніше!\n"
            "📦 Будматеріали під замовлення — просто залиш заявку прямо в боті!\n\n"
            "📞 Зв’язок: +380957347113"
        )
        keyboard = [["📨 Надіслати заявку", "📞 Зв’язатися з нами"]]
    else:
        text = (
            "🧱 Авабуд — твой помощник на стройке! 🛠️\n"
            "Компания Авабуд — надежный партнёр для строителей 👷‍♂️\n"
            "Собственные склады 🏢, транспорт 🚚 и лучшие цены от партнёров 💰\n\n"
            "✅ У нас — дешевле, быстрее и качественнее!\n"
            "📦 Стройматериалы под заказ — просто оставь заявку прямо в боте!\n\n"
            "📞 Связь: +380957347113"
        )
        keyboard = [["📨 Отправить заявку", "📞 Связаться с нами"]]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup)
    add_client(user.id)

# ==== HANDLE ALL MESSAGES ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    message_text = update.message.text.lower()
    lang = user.language_code or "ru"
    # Пересылаем админам
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"📥 Заявка от @{user.username or user.first_name} ({user.id}):\n{update.message.text}"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки в группу: {e}")

    # Автоответ юзеру
    if "связ" in message_text or "зв’яз" in message_text:
        response = (
            "📞 Свяжитесь с нами: +380957347113"
            if lang != "uk"
            else "📞 Зв’яжіться з нами: +380957347113"
        )
    elif "заявк" in message_text or "надіслат" in message_text or "отправ" in message_text:
        response = (
            "📨 Пожалуйста, отправьте список необходимых стройматериалов."
            if lang != "uk"
            else "📨 Будь ласка, надішліть список необхідних будматеріалів."
        )
    else:
        response = (
            "🤖 Спасибо за сообщение! Мы скоро вам ответим."
            if lang != "uk"
            else "🤖 Дякуємо за повідомлення! Ми скоро вам відповімо."
        )
    await update.message.reply_text(response)

# ==== BROADCAST REMINDERS ====
async def send_reminder(app):
    logging.info("send_reminder вызван")
    try:
        if not os.path.exists(CLIENTS_PATH):
            logging.warning(f"Файл {CLIENTS_PATH} не найден для рассылки")
            return
        with open(CLIENTS_PATH, encoding="utf-8", errors="replace") as f:
            ids = set()
            for line in f:
                if line.strip():
                    parts = line.strip().split("—")
                    if parts and parts[0].strip().isdigit():
                        ids.add(parts[0].strip())
        sent_count = 0
        for user_id in ids:
            try:
                await app.bot.send_message(
                    chat_id=int(user_id),
                    text="👷 Напоминаем, что вы можете отправить заявку на стройматериалы.\nМы всегда готовы помочь! 📦"
                )
                sent_count += 1
            except Exception as e:
                logging.warning(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
        logging.info(f"Рассылка завершена. Всего сообщений отправлено: {sent_count}")
    except Exception as e:
        logging.error(f"Ошибка внутри send_reminder: {e}", exc_info=True)

# ==== SCHEDULER ====
async def post_init(app):
    logging.info("post_init вызван, запускаем планировщик")
    scheduler = AsyncIOScheduler(timezone="UTC")
    # Для теста: раскомментируй следующую строку, чтобы рассылка шла каждую минуту
    # scheduler.add_job(send_reminder, "interval", minutes=1, args=[app])
    # Рабочее расписание (с 9 до 16 часов UTC, по будням)
    scheduler.add_job(send_reminder, "cron", hour="9-16", minute=0, day_of_week="mon-fri", args=[app])
    scheduler.start()
    logging.info("Планировщик запущен")

# ==== COMMAND FOR MANUAL BROADCAST ====
async def testsendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_reminder(context.application)
    await update.message.reply_text("✔️ Рассылка выполнена вручную.")

# ==== MAIN ====
def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не найден. Убедитесь, что он указан в .env")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("testsend", test_send))
    app.add_handler(CommandHandler("testsendall", testsendall))  # добавлен хендлер для ручной рассылки
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_error_handler(error_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
