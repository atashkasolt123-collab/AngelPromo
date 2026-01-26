import logging
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ТОКЕН БОТА - ЗАМЕНИ!
API_TOKEN = '8054377794:AAF4cAzL4ariCvHlFE0AvEDpYWskMZUMRAI'  # Токен твоего @Testehdhabot

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ТВОИ ПРЕМИУМ ЭМОДЗИ - ПРОСТО СИМВОЛЫ
# Telegram САМ подставит премиум версии если у владельца есть Premium
PREMIUM_EMOJIS = {
    "rocket": "🚀",
    "dollar": "💲", 
    "dice": "🎯",
    "transfer": "🔄",
    "lightning": "⚡",
    "casino": "🎰",
    "balance": "💰",
    "withdraw": "💸",
    "deposit": "💳",
    "game": "🎮",
    "mine": "💣",
    "win": "🏆",
    "lose": "💥",
    "prize": "🎁",
    "user": "👤",
    "stats": "📊",
    "time": "🕒",
    "min": "📍",
    "card": "💳",
    "rules": "📋",
    "info": "ℹ️",
    "back": "↩️",
    "play": "▶️",
    "bet": "🎯",
    "multiplier": "📈",
    "history": "📜"
}

def get_emoji(name):
    """Получает эмодзи - Telegram сам сделает его премиум если нужно"""
    return PREMIUM_EMOJIS.get(name, "🎲")

# ЦИТАТЫ С ЭМОДЗИ
LUCKY_QUOTES = [
    f"{get_emoji('rocket')} Взлетай к звездам! {get_emoji('lightning')} Удача на твоей стороне!",
    f"{get_emoji('dollar')} Богатство стучится в твою дверь! {get_emoji('win')}",
    f"{get_emoji('casino')} Джекпот приближается! {get_emoji('prize')}",
    f"{get_emoji('multiplier')} Твой успех множится! {get_emoji('rocket')}",
    f"{get_emoji('lightning')} Молниеносный успех! {get_emoji('dice')} Кубик благоволит тебе!",
]

UNLUCKY_QUOTES = [
    f"{get_emoji('lose')} Не падай духом! {get_emoji('back')} Возвращайся сильнее!",
    f"{get_emoji('mine')} Это лишь временное препятствие! {get_emoji('win')} Победа близко!",
    f"{get_emoji('game')} Игра только начинается! {get_emoji('play')} Продолжай играть!",
    f"{get_emoji('transfer')} Удача скоро переменится! {get_emoji('lightning')}",
    f"{get_emoji('time')} У каждого свое время! {get_emoji('stats')} Статистика на твоей стороне!",
]

def get_retry_keyboard():
    """Клавиатура"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{get_emoji('dice')} Кинуть кубик снова",
            callback_data="roll_dice"
        )]
    ])
    return keyboard

async def send_dice_animation(chat_id):
    """Кидает кубик"""
    dice_message = await bot.send_dice(
        chat_id=chat_id,
        emoji="🎲"
    )
    await asyncio.sleep(3)
    return dice_message.dice.value

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик /start"""
    user = message.from_user
    
    # Приветствие
    await message.answer(
        f"{get_emoji('casino')} <b>🎰 Кубик Судьбы 🎰</b> {get_emoji('lightning')}\n\n"
        f"{get_emoji('game')} <i>Кидаю кубик...</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Кидаем кубик
    dice_value = await send_dice_animation(message.chat.id)
    
    # Результат
    if dice_value in [4, 5, 6]:
        quote = random.choice(LUCKY_QUOTES)
        response = (
            f"{get_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_emoji('win')} <b>🎯 ЭТО УДАЧА!</b> {get_emoji('rocket')}\n\n"
            f"{get_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_emoji('history')} <i>Сегодня твой день!</i>"
        )
    else:
        quote = random.choice(UNLUCKY_QUOTES)
        response = (
            f"{get_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_emoji('lose')} <b>💥 Повезет в следующий раз!</b> {get_emoji('mine')}\n\n"
            f"{get_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_emoji('time')} <i>Удачи в следующий раз!</i>"
        )
    
    await message.answer(
        response,
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "roll_dice")
async def process_retry(callback_query: types.CallbackQuery):
    """Повторный бросок"""
    await callback_query.answer("🎲 Кидаю кубик...")
    
    user = callback_query.from_user
    
    # Удаляем старое сообщение
    try:
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
    except:
        pass
    
    # Кидаем кубик снова
    dice_value = await send_dice_animation(callback_query.message.chat.id)
    
    # Новый результат
    if dice_value in [4, 5, 6]:
        quote = random.choice(LUCKY_QUOTES)
        response = (
            f"{get_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_emoji('win')} <b>🏆 ЭТО УДАЧА!</b> {get_emoji('rocket')}\n\n"
            f"{get_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_emoji('history')} <i>Везение продолжается!</i>"
        )
    else:
        quote = random.choice(UNLUCKY_QUOTES)
        response = (
            f"{get_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_emoji('lose')} <b>💣 Повезет в следующий раз!</b> {get_emoji('mine')}\n\n"
            f"{get_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_emoji('time')} <i>Не сдавайся!</i>"
        )
    
    await bot.send_message(
        callback_query.message.chat.id,
        response,
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь"""
    help_text = (
        f"{get_emoji('info')} <b>🎰 Кубик Судьбы 🎰</b>\n\n"
        f"{get_emoji('rules')} <b>📋 Правила:</b>\n"
        f"{get_emoji('min')} 🎲 4-6 = <b>🏆 УДАЧА</b>\n"
        f"{get_emoji('min')} 🎲 1-3 = <b>💥 Следующий раз</b>\n\n"
        f"{get_emoji('play')} <b>🎮 Команды:</b>\n"
        f"/start - Начать игру\n"
        f"/help - Помощь\n\n"
        f"{get_emoji('casino')} <i>✨ Используй /start чтобы испытать удачу! ✨</i>"
    )
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message()
async def echo_message(message: types.Message):
    """Обработка всех сообщений"""
    await message.answer(
        f"{get_emoji('info')} <b>🎲 Используй /start чтобы бросить кубик!</b>\n\n"
        f"{get_emoji('dice')} <i>🎯 Или нажми кнопку ниже:</i>",
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def main():
    """Запуск бота"""
    logger.info("🚀 Бот запускается...")
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info(f"🆔 ID: {bot_info.id}")
    logger.info("💰 Премиум эмодзи: Telegram сам решит")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
