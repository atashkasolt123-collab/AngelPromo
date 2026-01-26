import logging
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ТОКЕН БОТА - ЗАМЕНИ НА СВОЙ!
API_TOKEN = '8537643741:AAFDELd4DRCYOld43Ip36ewrfPBdyan-WnA'

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ТВОИ ПРЕМИУМ ЭМОДЗИ КАК В ТЗ
# Формат: {emoji_id: "emoji"}
PREMIUM_EMOJIS = {
    "rocket": "🛸\u200D5377336433692412420",
    "dollar": "💲\u200D5377852667286559564", 
    "dice": "🎯\u200D5377346496800786271",
    "transfer": "🔄\u200D5377720025811555309",
    "lightning": "⚡\u200D5375469677696815127",
    "casino": "🎰\u200D5969709082049779216",
    "balance": "💰\u200D5262509177363787445",
    "withdraw": "💸\u200D5226731292334235524",
    "deposit": "💳\u200D5226731292334235524",
    "game": "🎮\u200D5258508428212445001",
    "mine": "💣\u200D4979035365823219688",
    "win": "🏆\u200D5436386989857320953",
    "lose": "💥\u200D4979035365823219688",
    "prize": "🎁\u200D5323761960829862762",
    "user": "👤\u200D5168063997575956782",
    "stats": "📊\u200D5231200819986047254",
    "time": "🕒\u200D5258419835922030550",
    "min": "📌\u200D5447183459602669338",
    "card": "💳\u200D5902056028513505203",
    "rules": "📋\u200D5258328383183396223",
    "info": "ℹ️\u200D5258334872878980409",
    "back": "↩️\u200D5877629862306385808",
    "play": "▶️\u200D5467583879948803288",
    "bet": "🎯\u200D5893048571560726748",
    "multiplier": "📈\u200D5201691993775818138",
    "history": "📋\u200D5353025608832004653"
}

# Функция для отправки сообщения с премиум эмодзи
async def send_premium_message(chat_id, text, reply_markup=None):
    """Отправляет сообщение с премиум эмодзи"""
    try:
        # Telegram сам подставит премиум версии если у владельца бота есть Premium
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return message
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        # Fallback на обычные эмодзи
        fallback_text = text.replace("\u200D", "")
        return await bot.send_message(
            chat_id=chat_id,
            text=fallback_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

def get_emoji(name):
    """Получает ПРЕМИУМ эмодзи"""
    return PREMIUM_EMOJIS.get(name, "🎲")

# ЦИТАТЫ С ТВОИМИ ПРЕМИУМ ЭМОДЗИ
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
    """Клавиатура с ПРЕМИУМ эмодзи"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{get_emoji('dice')} Кинуть кубик снова",
            callback_data="roll_dice"
        )]
    ])
    return keyboard

async def send_dice_animation(chat_id):
    """Кидает настоящий кубик Telegram"""
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
    
    # Приветствие с ПРЕМИУМ эмодзи
    await send_premium_message(
        message.chat.id,
        f"{get_emoji('casino')} <b>Кубик Судьбы активирован!</b> {get_emoji('lightning')}\n\n"
        f"{get_emoji('game')} <i>Кидаю кубик...</i>"
    )
    
    # Кидаем кубик
    dice_value = await send_dice_animation(message.chat.id)
    
    # Формируем ответ с ПРЕМИУМ эмодзи
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
    
    # Отправляем результат с ПРЕМИУМ эмодзи
    await send_premium_message(
        message.chat.id,
        response,
        reply_markup=get_retry_keyboard()
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
    
    # Новый результат с ПРЕМИУМ эмодзи
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
    
    await send_premium_message(
        callback_query.message.chat.id,
        response,
        reply_markup=get_retry_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь с ПРЕМИУМ эмодзи"""
    help_text = (
        f"{get_emoji('info')} <b>Кубик Судьбы</b>\n\n"
        f"{get_emoji('rules')} <b>Правила:</b>\n"
        f"{get_emoji('min')} 🎲 4-6 = <b>УДАЧА</b> {get_emoji('win')}\n"
        f"{get_emoji('min')} 🎲 1-3 = <b>Следующий раз</b> {get_emoji('lose')}\n\n"
        f"{get_emoji('play')} <b>Команды:</b>\n"
        f"/start - Начать игру\n"
        f"/help - Помощь\n\n"
        f"{get_emoji('casino')} <i>Используй /start чтобы испытать удачу!</i>"
    )
    
    await send_premium_message(message.chat.id, help_text)

@dp.message()
async def echo_message(message: types.Message):
    """Обработка всех сообщений с ПРЕМИУМ эмодзи"""
    await send_premium_message(
        message.chat.id,
        f"{get_emoji('info')} <b>Используй /start чтобы бросить кубик!</b>\n\n"
        f"{get_emoji('dice')} <i>Или нажми кнопку ниже:</i>",
        reply_markup=get_retry_keyboard()
    )

async def main():
    """Запуск бота"""
    logger.info("🚀 Бот запускается с ПРЕМИУМ ЭМОДЗИ!")
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info(f"🆔 ID: {bot_info.id}")
    logger.info(f"💰 Премиум эмодзи: {'ДОСТУПНЫ' if bot_info.is_premium else 'НЕ ДОСТУПНЫ'}")
    
    if not bot_info.is_premium:
        logger.warning("⚠️ У владельца бота НЕТ Telegram Premium!")
        logger.warning("⚠️ Премиум эмодзи могут не работать!")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
