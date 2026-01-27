import logging
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ТОКЕН БОТА - ЗАМЕНИ!
API_TOKEN = '8537643741:AAFHrvTNcBkZP1lkvAbucMWlBs3_qQaP9O4'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ТВОИ ПРЕМИУМ ЭМОДЗИ С ID
PREMIUM_EMOJIS_HTML = {
    "rocket": '<tg-emoji emoji-id="5377336433692412420">🛸</tg-emoji>',
    "dollar": '<tg-emoji emoji-id="5377852667286559564">💲</tg-emoji>',
    "dice": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "transfer": '<tg-emoji emoji-id="5377720025811555309">🔄</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5375469677696815127">⚡</tg-emoji>',
    "casino": '<tg-emoji emoji-id="5969709082049779216">🎰</tg-emoji>',
    "balance": '<tg-emoji emoji-id="5262509177363787445">💰</tg-emoji>',
    "withdraw": '<tg-emoji emoji-id="5226731292334235524">💸</tg-emoji>',
    "deposit": '<tg-emoji emoji-id="5226731292334235524">💳</tg-emoji>',
    "game": '<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji>',
    "mine": '<tg-emoji emoji-id="4979035365823219688">💣</tg-emoji>',
    "win": '<tg-emoji emoji-id="5436386989857320953">🏆</tg-emoji>',
    "lose": '<tg-emoji emoji-id="4979035365823219688">💥</tg-emoji>',
    "prize": '<tg-emoji emoji-id="5323761960829862762">🎁</tg-emoji>',
    "user": '<tg-emoji emoji-id="5168063997575956782">👤</tg-emoji>',
    "stats": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "time": '<tg-emoji emoji-id="5258419835922030550">🕒</tg-emoji>',
    "min": '<tg-emoji emoji-id="5447183459602669338">📌</tg-emoji>',
    "card": '<tg-emoji emoji-id="5902056028513505203">💳</tg-emoji>',
    "rules": '<tg-emoji emoji-id="5258328383183396223">📋</tg-emoji>',
    "info": '<tg-emoji emoji-id="5258334872878980409">ℹ️</tg-emoji>',
    "back": '<tg-emoji emoji-id="5877629862306385808">↩️</tg-emoji>',
    "play": '<tg-emoji emoji-id="5467583879948803288">▶️</tg-emoji>',
    "bet": '<tg-emoji emoji-id="5893048571560726748">🎯</tg-emoji>',
    "multiplier": '<tg-emoji emoji-id="5201691993775818138">📈</tg-emoji>',
    "history": '<tg-emoji emoji-id="5353025608832004653">📋</tg-emoji>'
}

def get_premium_emoji(name):
    """Получает премиум эмодзи в HTML формате"""
    return PREMIUM_EMOJIS_HTML.get(name, '🎲')

# ЦИТАТЫ С ПРЕМИУМ ЭМОДЗИ В HTML
LUCKY_QUOTES_HTML = [
    f"{get_premium_emoji('rocket')} Взлетай к звездам! {get_premium_emoji('lightning')} Удача на твоей стороне!",
    f"{get_premium_emoji('dollar')} Богатство стучится в твою дверь! {get_premium_emoji('win')}",
    f"{get_premium_emoji('casino')} Джекпот приближается! {get_premium_emoji('prize')}",
    f"{get_premium_emoji('multiplier')} Твой успех множится! {get_premium_emoji('rocket')}",
    f"{get_premium_emoji('lightning')} Молниеносный успех! {get_premium_emoji('dice')} Кубик благоволит тебе!",
]

UNLUCKY_QUOTES_HTML = [
    f"{get_premium_emoji('lose')} Не падай духом! {get_premium_emoji('back')} Возвращайся сильнее!",
    f"{get_premium_emoji('mine')} Это лишь временное препятствие! {get_premium_emoji('win')} Победа близко!",
    f"{get_premium_emoji('game')} Игра только начинается! {get_premium_emoji('play')} Продолжай играть!",
    f"{get_premium_emoji('transfer')} Удача скоро переменится! {get_premium_emoji('lightning')}",
    f"{get_premium_emoji('time')} У каждого свое время! {get_premium_emoji('stats')} Статистика на твоей стороне!",
]

# Кнопка с обычным эмодзи (в кнопках нельзя использовать HTML)
def get_retry_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Кинуть кубик снова",
            callback_data="roll_dice"
        )
    ]])
    return keyboard

async def send_dice_animation(chat_id):
    dice = await bot.send_dice(chat_id=chat_id, emoji="🎲")
    await asyncio.sleep(3)
    return dice.dice.value

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    
    # Приветствие с ПРЕМИУМ ЭМОДЗИ В HTML
    await message.answer(
        f"{get_premium_emoji('casino')} <b>Кубик Судьбы</b> {get_premium_emoji('lightning')}\n\n"
        f"{get_premium_emoji('game')} <i>Кидаю кубик...</i>",
        parse_mode=ParseMode.HTML
    )
    
    dice_value = await send_dice_animation(message.chat.id)
    
    if dice_value in [4, 5, 6]:
        quote = random.choice(LUCKY_QUOTES_HTML)
        response = (
            f"{get_premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_premium_emoji('win')} <b>ЭТО УДАЧА!</b> {get_premium_emoji('rocket')}\n\n"
            f"{get_premium_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_premium_emoji('history')} <i>Сегодня твой день!</i>"
        )
    else:
        quote = random.choice(UNLUCKY_QUOTES_HTML)
        response = (
            f"{get_premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_premium_emoji('lose')} <b>Повезет в следующий раз!</b> {get_premium_emoji('mine')}\n\n"
            f"{get_premium_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_premium_emoji('time')} <i>Удачи в следующий раз!</i>"
        )
    
    await message.answer(
        response,
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "roll_dice")
async def process_retry(callback_query: types.CallbackQuery):
    await callback_query.answer("🎲 Кидаю кубик...")
    
    user = callback_query.from_user
    
    try:
        await bot.delete_message(
            callback_query.message.chat.id,
            callback_query.message.message_id
        )
    except:
        pass
    
    dice_value = await send_dice_animation(callback_query.message.chat.id)
    
    if dice_value in [4, 5, 6]:
        quote = random.choice(LUCKY_QUOTES_HTML)
        response = (
            f"{get_premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_premium_emoji('win')} <b>ЭТО УДАЧА!</b> {get_premium_emoji('rocket')}\n\n"
            f"{get_premium_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_premium_emoji('history')} <i>Везение продолжается!</i>"
        )
    else:
        quote = random.choice(UNLUCKY_QUOTES_HTML)
        response = (
            f"{get_premium_emoji('dice')} <b>Выпало: {dice_value}</b>\n\n"
            f"{get_premium_emoji('lose')} <b>Повезет в следующий раз!</b> {get_premium_emoji('mine')}\n\n"
            f"{get_premium_emoji('user')} <code>{user.first_name}</code>, {quote}\n\n"
            f"{get_premium_emoji('time')} <i>Не сдавайся!</i>"
        )
    
    await bot.send_message(
        callback_query.message.chat.id,
        response,
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        f"{get_premium_emoji('info')} <b>Кубик Судьбы</b>\n\n"
        f"{get_premium_emoji('rules')} <b>Правила:</b>\n"
        f"{get_premium_emoji('min')} 🎲 4-6 = <b>УДАЧА</b> {get_premium_emoji('win')}\n"
        f"{get_premium_emoji('min')} 🎲 1-3 = <b>Следующий раз</b> {get_premium_emoji('lose')}\n\n"
        f"{get_premium_emoji('play')} <b>Команды:</b>\n"
        f"/start - Начать игру\n"
        f"/help - Помощь\n\n"
        f"{get_premium_emoji('casino')} <i>Используй /start чтобы испытать удачу!</i>"
    )
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message()
async def echo_message(message: types.Message):
    await message.answer(
        f"{get_premium_emoji('info')} <b>Используй /start чтобы бросить кубик!</b>\n\n"
        f"{get_premium_emoji('dice')} <i>Или нажми кнопку ниже:</i>",
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def main():
    logger.info("🚀 Бот запускается с HTML ПРЕМИУМ ЭМОДЗИ!")
    
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот: @{bot_info.username}")
    logger.info(f"🆔 ID: {bot_info.id}")
    
    # Проверка - отправляем тестовое сообщение с премиум эмодзи
    test_emoji = get_premium_emoji('rocket')
    logger.info(f"💰 Тест премиум эмодзи: {test_emoji}")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
