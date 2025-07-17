# ... (весь твой код сверху остаётся без изменений)


# ==== ТЕСТОВАЯ КОМАНДА /testsend ====
async def test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=7124318893,  # Твой тестовый user_id
            text="✅ Тестовая рассылка работает!"
        )
        await update.message.reply_text("📤 Сообщение отправлено пользователю 7124318893.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")


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
    app.add_handler(CommandHandler("testsend", test_send))  # <--- добавлено
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
