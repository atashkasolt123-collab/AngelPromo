import logging
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен вашего бота
API_TOKEN = '8537643741:AAFDELd4DRCYOld43Ip36ewrfPBdyan-WnA'  # Токен вашего Spindja бота

# Инициализация бота с HTML парсингом
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ПРЕМИУМ ЭМОДЗИ с ID для Telegram API
PREMIUM_EMOJIS = {
    "rocket": "🛸\u200D5377336433692412420",
    "dollar": "💲\u200D5377852667286559564",
    "dice": "🎯\u200D5377346496800786271",
    "dice_roll": "🎲",
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

def premium_emoji(name):
    """Возвращает премиум эмодзи по имени"""
    return PREMIUM_EMOJIS.get(name, "🎲")

# Цитаты с ПРЕМИУМ эмодзи
LUCKY_QUOTES = [
    f"{premium_emoji('rocket')} Взлетай к звездам! {premium_emoji('lightning')} Удача на твоей стороне!",
    f"{premium_emoji('dollar')} Богатство стучится в твою дверь! {premium_emoji('win')}",
    f"{premium_emoji('casino')} Джекпот приближается! {premium_emoji('prize')}",
    f"{premium_emoji('multiplier')} Твой успех множится! {premium_emoji('rocket')}",
    f"{premium_emoji('lightning')} Молниеносный успех! {premium_emoji('dice')} Кубик благоволит тебе!",
]

UNLUCKY_QUOTES = [
    f"{premium_emoji('lose')} Не падай духом! {premium_emoji('back')} Возвращайся сильнее!",
    f"{premium_emoji('mine')} Это лишь временное препятствие! {premium_emoji('win')} Победа близко!",
    f"{premium_emoji('game')} Игра только начинается! {premium_emoji('play')} Продолжай играть!",
    f"{premium_emoji('transfer')} Удача скоро переменится! {premium_emoji('lightning')}",
    f"{premium_emoji('time')} У каждого свое время! {premium_emoji('stats')} Статистика на твоей стороне!",
]

def get_retry_keyboard():
    """Клавиатура для повторной попытки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{premium_emoji('dice')} Кинуть кубик снова",
            callback_data="roll_dice"
        )]
    ])
    return keyboard

async def send_dice_animation(chat_id):
    """Отправляет анимацию кубика и возвращает результат"""
    dice_message = await bot.send_dice(
        chat_id=chat_id,
        emoji="🎲"
    )
    
    # Ждем завершения анимации
    await asyncio.sleep(3)
    
    return dice_message.dice.value

async def format_result_message(user, dice_value):
    """Форматирует сообщение с результатом"""
    user_name = user.first_name or "Игрок"
    
    if dice_value in [4, 5, 6]:
        quote = random.choice(LUCKY_QUOTES)
        return (
            f"{premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{premium_emoji('win')} <b>🎉 ЭТО УДАЧА!</b> {premium_emoji('rocket')}\n\n"
            f"{premium_emoji('user')} <code>{user_name}</code>, {quote}\n\n"
            f"{premium_emoji('history')} <i>Этот день запомнится!</i>"
        )
    else:
        quote = random.choice(UNLUCKY_QUOTES)
        return (
            f"{premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{premium_emoji('lose')} <b>🌀 Повезет в следующий раз!</b> {premium_emoji('mine')}\n\n"
            f"{premium_emoji('user')} <code>{user_name}</code>, {quote}\n\n"
            f"{premium_emoji('time')} <i>Удачи в следующий раз!</i>"
        )

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started the bot")
    
    welcome_msg = await message.answer(
        f"{premium_emoji('casino')} <b>Кубик Судьбы</b> {premium_emoji('lightning')}\n\n"
        f"{premium_emoji('game')} Бросаю кубик..."
    )
    
    dice_value = await send_dice_animation(message.chat.id)
    logger.info(f"Dice roll: {dice_value} for user {message.from_user.id}")
    
    result_text = await format_result_message(message.from_user, dice_value)
    
    await welcome_msg.delete()
    await message.answer(
        result_text,
        reply_markup=get_retry_keyboard()
    )

@dp.callback_query(F.data == "roll_dice")
async def process_retry(callback_query: types.CallbackQuery):
    """Обработчик повторного броска"""
    await callback_query.answer("🎲 Бросаю кубик...")
    
    user = callback_query.from_user
    chat_id = callback_query.message.chat.id
    
    try:
        await bot.delete_message(chat_id, callback_query.message.message_id)
    except:
        pass
    
    dice_value = await send_dice_animation(chat_id)
    logger.info(f"Re-roll dice: {dice_value} for user {user.id}")
    
    result_text = await format_result_message(user, dice_value)
    
    await bot.send_message(
        chat_id=chat_id,
        text=result_text,
        reply_markup=get_retry_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь"""
    help_text = (
        f"{premium_emoji('info')} <b>Кубик Судьбы - Помощь</b>\n\n"
        f"{premium_emoji('rules')} <b>Правила:</b>\n"
        f"{premium_emoji('min')} 🎲 4, 5, 6 = <b>УДАЧА!</b> {premium_emoji('win')}\n"
        f"{premium_emoji('min')} 🎲 1, 2, 3 = <b>В следующий раз</b> {premium_emoji('lose')}\n\n"
        f"{premium_emoji('play')} <b>Команды:</b>\n"
        f"/start - Начать игру\n"
        f"/help - Эта справка\n\n"
        f"{premium_emoji('casino')} <i>Удачи в игре!</i>"
    )
    
    await message.answer(help_text)

@dp.message()
async def echo_message(message: types.Message):
    """Обработка всех остальных сообщений"""
    await message.answer(
        f"{premium_emoji('info')} Используйте /start чтобы бросить кубик!\n"
        f"{premium_emoji('dice')} Или нажмите на кнопку ниже:",
        reply_markup=get_retry_keyboard()
    )

async def main():
    """Основная функция запуска бота"""
    logger.info("🎰 Бот 'Кубик Судьбы' запускается...")
    logger.info("🚀 Версия для Bothost с aiogram 3.x")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info(f"🆔 ID бота: {bot_info.id}")
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
