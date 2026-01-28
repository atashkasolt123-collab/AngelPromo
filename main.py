import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Премиум эмодзи
PREMIUM_EMOJIS = {
    "rocket": "🛸",  # 5377336433692412420
    "dollar": "💲",  # 5377852667286559564
    "multiplier": "📈",  # 5201691993775818138
    "history": "📋"  # 5353025608832004653
}

def get_premium_emoji(name):
    """Получить премиум эмодзи по имени"""
    return PREMIUM_EMOJIS.get(name, "")

def generate_random_course():
    """Генерация случайного курса от 0.02 до 0.89$"""
    return round(random.uniform(0.02, 0.89), 5)

async def kurs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /kurs"""
    try:
        # Генерируем случайный курс
        random_course = generate_random_course()
        
        # Формируем сообщение
        message = (
            f"{get_premium_emoji('rocket')} Курс LBC {random_course}{get_premium_emoji('dollar')}\n"
            f"{get_premium_emoji('history')} Максимальный курс: 189$ | Минимальный курс: 0.00027$"
        )
        
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при получении курса")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для отслеживания курса LBC.\n"
        "Используйте команду /kurs чтобы получить текущий курс."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/kurs - Получить текущий курс LBC\n"
        "/help - Получить справку по командам"
    )

def main():
    """Основная функция запуска бота"""
    # ТОКЕН ВАШЕГО БОТА - ЗАМЕНИТЕ ЭТОТ ТОКЕН НА СВОЙ!
    # Получите токен у @BotFather в Telegram
    TOKEN = "8115256081:AAH2Ze1oOhtTMF59FMlMza8p_80CVyx_iho"
    
    # Пример токена (раскомментируйте и вставьте свой):
    # TOKEN = "8115256081:AAH2Ze1oOhtTMF59FMlMza8p_80CVyx_iho"
    
    if TOKEN == "8115256081:AAH2Ze1oOhtTMF59FMlMza8p_80CVyx_iho":
        print("=" * 60)
        print("ВНИМАНИЕ: Вы не установили токен бота!")
        print("=" * 60)
        print("Чтобы получить токен:")
        print("1. Найдите @BotFather в Telegram")
        print("2. Отправьте /newbot")
        print("3. Следуйте инструкциям")
        print("4. Получите токен и вставьте его в строку TOKEN")
        print("=" * 60)
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("kurs", kurs_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запускаем бота
    print(f"Бот запущен с токеном: {TOKEN[:10]}...")
    print("Бот работает...")
    print("Для остановки нажмите Ctrl+C")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
