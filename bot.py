import logging
import os
from datetime import datetime, timezone

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from dotenv import load_dotenv

# ==== CONFIG ====
GROUP_CHAT_ID = -1002280657250  # <-- замените на id вашей группы
CLIENTS_PATH = "/data/clients.txt"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(name)s: %(message)s'
)

logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logging.getLogger('apscheduler.executors.default').setLevel(logging.DEBUG)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ==== Клиенты и состояния пользователей ====
user_states = dict()  # user_id: состояние
user_order_data = dict()  # user_id: данные заявки


def add_client(user_id: int):
    """Добавляет user_id в clients.txt, если такого ещё нет."""
    if not os.path.exists(CLIENTS_PATH):
        with open(CLIENTS_PATH, "w", encoding="utf-8"): pass
    with open(CLIENTS_PATH, encoding="utf-8", errors="replace") as f:
        existing = set(line.split("—")[0].strip() for line in f if line.strip())
    if str(user_id) not in existing:
        with open(CLIENTS_PATH, "a", encoding="utf-8") as f:
            f.write(f"{user_id} — {datetime.now(timezone.utc).isoformat()}\n")


# ==== Обработчик ошибок ====
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception while handling an update:", exc_info=context.error)


# ==== Клавиатуры ====
def get_main_keyboard():
    keyboard = [
        ["🏷️ Найдешевші будматеріали в Одесі, дізнатись ціни"],
        ["📝 Надіслати заявку", "📞 Зв’язатися з нами"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_order_keyboard():
    keyboard = [
        ["❌ Відмінити"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==== Команда /start ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "🧱 Авабуд — твій помічник на будівництві! 🛠️\n"
        "Компанія Авабуд — надійний партнер для будівельників 👷‍♂️\n"
        "Власні склади 🏢, транспорт 🚚 та найкращі партнерські ціни 💰\n\n"
        "✅ У нас — дешевше, швидше та якісніше!\n"
        "📦 Будматеріали під замовлення — просто залиш заявку прямо в боті!\n\n"
        "📞 Зв’язок: +380957347113"
    )
    reply_markup = get_main_keyboard()
    await update.message.reply_text(text, reply_markup=reply_markup)
    add_client(user.id)

    # Сбрасываем состояние пользователя при старте
    user_states.pop(user.id, None)
    user_order_data.pop(user.id, None)


# ==== Многошаговый сбор заявки и обработка всех сообщений ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id
    message_text = update.message.text.strip()
    lang = user.language_code or 'ru'

    add_client(user_id)
    state = user_states.get(user_id)

    # Если пользователь не в процессе
    if state is None:
        # Обработка кнопки запроса цен
        if message_text == "🏷️ Найдешевші будматеріали в Одесі, дізнатись ціни":
            user_states[user_id] = "waiting_for_price_request"
            prompt = (
                "Будь ласка, напишіть товар, ціни на який хочете дізнатись."
                if lang == "uk" else
                "Пожалуйста, напишите товар, цены на который хотите узнать."
            )
            await update.message.reply_text(prompt, reply_markup=get_order_keyboard())
            return

        # Кнопка начало заявки
        elif message_text in ["📝 Надіслати заявку", "📝 надiслати заявку"]:
            user_states[user_id] = "waiting_for_list"
            user_order_data[user_id] = dict()
            prompt = (
                "Будь ласка, напишіть список необхідних будматеріалів у зручному форматі."
                if lang == "uk" else
                "Пожалуйста, напишите список необходимых стройматериалов в удобном формате."
            )
            await update.message.reply_text(prompt, reply_markup=get_order_keyboard())
            return

        elif "зв’" in message_text.lower() or "связ" in message_text.lower():
            contact_msg = (
                "📞 Зв’яжіться з нами по телефону: +380957347113"
                if lang == "uk" else
                "📞 Свяжитесь с нами по телефону: +380957347113"
            )
            await update.message.reply_text(contact_msg, reply_markup=get_main_keyboard())
            return

        else:
            reply_text = (
                "🤖 Дякуємо за повідомлення! Ми скоро вам відповімо."
                if lang == "uk" else
                "🤖 Спасибо за сообщение! Мы скоро вам ответим."
            )
            await update.message.reply_text(reply_text, reply_markup=get_main_keyboard())
            return

    # --- В процессе заявки или запроса цен ---

    # Универсальная отмена
    if message_text == "❌ Відмінити" or message_text.lower() == "отменить":
        user_states.pop(user_id, None)
        user_order_data.pop(user_id, None)
        cancel_text = "Заявку/запит скасовано ❌" if lang == "uk" else "Заявку/запрос отменено ❌"
        await update.message.reply_text(cancel_text, reply_markup=get_main_keyboard())
        return

    # Обработка состояний
    if state == "waiting_for_price_request":
        # Пересылаем запрос в группу
        try:
            text_to_admin = (
                f"📢 Запит цін від @{user.username or user.first_name} ({user_id}):\n{message_text}"
            )
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text_to_admin)
            confirmation = (
                "Дякуємо! Ваш запит надіслано. Скоро ми з вами зв'яжемося."
                if lang == "uk" else
                "Спасибо! Ваш запрос отправлен. Скоро с вами свяжутся."
            )
            await update.message.reply_text(confirmation, reply_markup=get_main_keyboard())
        except Exception as e:
            logging.error(f"Помилка відправки запиту цін в групу: {e}")
            err_msg = (
                "Сталася помилка при відправці запиту. Спробуйте пізніше."
                if lang == "uk" else
                "Произошла ошибка при отправке запроса. Попробуйте позже."
            )
            await update.message.reply_text(err_msg, reply_markup=get_main_keyboard())
        user_states.pop(user_id, None)
        return

    if state == "waiting_for_list":
        user_order_data[user_id]["list"] = message_text
        prompt = (
            "Дякуємо! Тепер вкажіть, будь ласка, адресу доставки."
            if lang == "uk" else
            "Спасибо! Теперь укажите, пожалуйста, адрес доставки."
        )
        user_states[user_id] = "waiting_for_address"
        await update.message.reply_text(prompt, reply_markup=get_order_keyboard())
        return

    if state == "waiting_for_address":
        user_order_data[user_id]["address"] = message_text
        data = user_order_data[user_id]
        summary = (
            f"Ваша заявка:\n"
            f"📝 Будматеріали:\n{data['list']}\n\n"
            f"🏠 Адреса доставки:\n{data['address']}\n\n"
            "Підтверджуєте замовлення? (Так / Ні)"
            if lang == "uk" else
            f"Ваша заявка:\n"
            f"📝 Стройматериалы:\n{data['list']}\n\n"
            f"🏠 Адрес доставки:\n{data['address']}\n\n"
            "Подтверждаете заказ? (Да / Нет)"
        )
        user_states[user_id] = "waiting_for_confirmation"
        await update.message.reply_text(summary, reply_markup=get_order_keyboard())
        return

    if state == "waiting_for_confirmation":
        yes_vals = {"так", "yes", "да", "y"}
        no_vals = {"ні", "no", "нет", "n"}
        if message_text.lower() in yes_vals:
            data = user_order_data[user_id]
            # Посылаем заявку в группу
            order_text = (
                f"🆕 Нова заявка від @{user.username or user.first_name} ({user_id}):\n\n"
                f"📝 Будматеріали:\n{data['list']}\n\n"
                f"🏠 Адреса доставки:\n{data['address']}"
            )
            try:
                await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=order_text)
            except Exception as e:
                logging.error(f"Помилка відправки заявки в групу: {e}")

            thanks_msg = (
                "Дякуємо! Ваша заявка прийнята і буде оброблена найближчим часом."
                if lang == "uk" else
                "Спасибо! Ваш заказ принят и будет обработан в ближайшее время."
            )
            await update.message.reply_text(thanks_msg, reply_markup=get_main_keyboard())
            user_states.pop(user_id, None)
            user_order_data.pop(user_id, None)
            return

        elif message_text.lower() in no_vals:
            cancel_text = (
                "Заявку скасовано. Щоб почати спочатку, скористайтеся командою /start."
                if lang == "uk" else
                "Заявка отменена. Чтобы начать заново, используйте команду /start."
            )
            await update.message.reply_text(cancel_text, reply_markup=get_main_keyboard())
            user_states.pop(user_id, None)
            user_order_data.pop(user_id, None)
            return
        else:
            err_msg = (
                "Будь ласка, відповідайте 'Так' або 'Ні'."
                if lang == "uk" else
                "Пожалуйста, ответьте 'Да' или 'Нет'."
            )
            await update.message.reply_text(err_msg)
            return


# ==== Рассылка с маркетинговым текстом ====
async def send_reminder(app):
    logging.info("send_reminder запущений")
    try:
        if not os.path.exists(CLIENTS_PATH):
            logging.warning(f"Файл {CLIENTS_PATH} не знайдено для розсилки")
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
                    text=(
                        "🏗️ Компанія Авабуд нагадує: ваші будматеріали — понад усе! "
                        "Не відкладайте замовлення на потім, зробіть заявку вже сьогодні і "
                        "отримайте найкращі умови та ціни! 📦🔥"
                    )
                )
                sent_count += 1
            except Exception as e:
                logging.warning(f"Не вдалося надіслати нагадування користувачу {user_id}: {e}")
        logging.info(f"Розсилка завершена. Надіслано повідомлень: {sent_count}")
    except Exception as e:
        logging.error(f"Помилка в send_reminder: {e}", exc_info=True)


# ==== Планировщик ====
def job_listener(event):
    if event.exception:
        logging.error(f'Помилка при виконанні завдання {event.job_id}: {event.exception}', exc_info=True)
    else:
        logging.info(f'Завдання {event.job_id} виконано успішно')


async def post_init(app):
    logging.info("post_init викликаний, запускаємо планувальник")
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.add_job(send_reminder, "interval", minutes=10, args=[app])
    # Для бою можно использовать расписание:
    # scheduler.add_job(send_reminder, "cron", hour="6-16", minute=0, day_of_week="mon-fri", args=[app])
    scheduler.start()
    logging.info("Планувальник запущений")


# ==== Ручная рассылка ====
async def testsendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_reminder(context.application)
    await update.message.reply_text("✔️ Розсилка виконана вручну.")


# ==== Тестовая рассылка конкретному пользователю ====
async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=7124318893,  # замените на нужный user_id
            text="✅ Тестова розсилка працює!"
        )
        await update.message.reply_text("📤 Повідомлення надіслано користувачу 7124318893.")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка при надсиланні: {e}")


# ==== MAIN ====
def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN не знайдено. Перевірте файл .env")
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("testsend", test_send))
    app.add_handler(CommandHandler("testsendall", testsendall))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_error_handler(error_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
