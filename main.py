import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

# Премиум эмодзи с их ID
# Формат: "название": ("дефолтный_эмодзи", "emoji_id")
PREMIUM_EMOJIS = {
    "rocket": ("🛸", "5377336433692412420"),
    "dollar": ("💲", "5377852667286559564"),
    "multiplier": ("📈", "5201691993775818138"),
    "history": ("📋", "5353025608832004653")
}

def get_premium_emoji_html(name):
    """Получить премиум эмодзи в HTML формате"""
    if name in PREMIUM_EMOJIS:
        default_emoji, emoji_id = PREMIUM_EMOJIS[name]
        return f'<tg-emoji emoji-id="{emoji_id}">{default_emoji}</tg-emoji>'
    return ""

def generate_random_course():
    """Генерация случайного курса от 0.02 до 0.89$"""
    return round(random.uniform(0.02, 0.89), 5)

async def kurs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /kurs"""
    try:
        # Генерируем случайный курс
        random_course = generate_random_course()
        
        # Формируем сообщение с HTML разметкой
        message = (
            f"{get_premium_emoji_html('rocket')} Курс LBC {random_course}{get_premium_emoji_html('dollar')}\n"
            f"{get_premium_emoji_html('history')} Максимальный курс: 189$ | Минимальный курс: 0.00027$"
        )
        
        # Отправляем сообщение с parse_mode="HTML"
        await update.message.reply_text(message, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при получении курса")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    message = (
        "Привет! Я бот для отслеживания курса LBC.\n"
        f"{get_premium_emoji_html('rocket')} Используйте команду /kurs чтобы получить текущий курс."
    )
    await update.message.reply_text(message, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        f"{get_premium_emoji_html('history')} Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/kurs - Получить текущий курс LBC\n"
        "/help - Получить справку по командам"
    )
    await update.message.reply_text(message, parse_mode="HTML")

def main():
    """Основная функция запуска бота"""
    # ВАРИАНТ 1: Прямое указание токена (проще)
    TOKEN = "8115256081:AAH2Ze1oOhtTMF59FMlMza8p_80CVyx_iho"
    
    # ВАРИАНТ 2: Через переменную окружения (если используете на Bothost)
    # TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8115256081:AAH2Ze1oOhtTMF59FMlMza8p_80CVyx_iho")
    
    if not TOKEN or TOKEN.strip() == "":
        print("Ошибка: Токен бота не установлен!")
        return
    
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("kurs", kurs_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Запускаем бота
        print(f"Бот запущен с токеном: {TOKEN[:10]}...")
        print("Используются премиум эмодзи через HTML разметку")
        print("Бот работает...")
        print("Для остановки нажмите Ctrl+C")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
