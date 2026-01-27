import logging
import random
import re
import asyncio
from typing import Dict, List, Tuple, Set, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Dice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "8470278896:AAH5ALI5_TkogpE7neCD0mmF0oGAwSDR2hU"

# ID администратора
ADMIN_ID = 7313407194
ADMIN_USERNAME = "@qqlittle"

# Премиум эмодзи в HTML формате (только для текста)
PREMIUM_EMOJIS_HTML = {
    "rocket": '<tg-emoji emoji-id="5377336433692412420">🛸</tg-emoji>',
    "dollar": '<tg-emoji emoji-id="5377852667286559564">💲</tg-emoji>',
    "dice": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "transfer": '<tg-emoji emoji-id="5377720025811555309">🔄</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5375469677696815127">⚡</tg-emoji>',
    "casino": '<tg-emoji emoji-id="5969709082049779216">🎰</tg-emoji>',
    "balance": '<tg-emoji emoji-id="5262509177363787445">💰</tg-emoji>',
    "withdraw": '<tg-emoji emoji-id="5226731292334235524">💸</tg-emoji>',
    "deposit": '<tg-emoji emoji-id="5902056028513505203">💳</tg-emoji>',
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
    "history": '<tg-emoji emoji-id="5353025608832004653">📋</tg-emoji>',
    "fire": '<tg-emoji emoji-id="5445124005604368288">🔥</tg-emoji>',
    "star": '<tg-emoji emoji-id="5258463921982341676">⭐</tg-emoji>',
    "crown": '<tg-emoji emoji-id="5375757817856875637">👑</tg-emoji>',
    "gem": '<tg-emoji emoji-id="5447170525969141923">💎</tg-emoji>',
    "coin": '<tg-emoji emoji-id="5375256698515358018">🪙</tg-emoji>',
    "trophy": '<tg-emoji emoji-id="5375250732074737684">🏅</tg-emoji>',
    "medal": '<tg-emoji emoji-id="5258465977430624493">🎖️</tg-emoji>',
    "money": '<tg-emoji emoji-id="5226731292334235524">💵</tg-emoji>',
    "bank": '<tg-emoji emoji-id="5447203209511766728">🏦</tg-emoji>',
    "secure": '<tg-emoji emoji-id="5258418885282670157">🔒</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5323761960829862762">🎁</tg-emoji>',
    "flag": '<tg-emoji emoji-id="5447165412033893131">🏁</tg-emoji>',
    "target": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "luck": '<tg-emoji emoji-id="5377386804699168823">🍀</tg-emoji>',
    "jackpot": '<tg-emoji emoji-id="5262509177363787445">💰</tg-emoji>',
    "vip": '<tg-emoji emoji-id="5375757817856875637">👑</tg-emoji>'
}

def get_premium_emoji(name):
    """Получает премиум эмодзи в HTML формате (только для текста)"""
    return PREMIUM_EMOJIS_HTML.get(name, '🎲')

# Цитаты для игр с премиум эмодзи
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

# Минимальные суммы
MIN_DEPOSIT = 0.1  # Минимальное пополнение $
MIN_WITHDRAWAL = 3  # Минимальный вывод $
MIN_TRANSFER_AMOUNT = 0.1  # Минимальный перевод между пользователями $

# Глобальные счетчики
game_counter = 0
games_history: Dict[int, Dict] = {}

# Хранилище данных
user_data: Dict[int, Dict] = {
    ADMIN_ID: {  # Предварительно добавляем администратора
        "balance": 0,
        "username": ADMIN_USERNAME,
        "first_name": "Администратор",
        "deposits": [],
        "withdrawals": []
    }
}
game_data: Dict[int, Dict] = {}
user_bets: Dict[int, float] = {}

# Хранилище заявок на вывод
withdrawal_requests: Dict[int, Dict] = {}

# Константы игры
INITIAL_BALANCE = 0
MIN_BET = 0.1
GRID_SIZE = 5
TOTAL_CELLS = GRID_SIZE * GRID_SIZE
MIN_MINES = 2
MAX_MINES = 2

# Множители
MULTIPLIERS = {
    2: 1.12
}

# Множители для игры в кубы
DICE_MULTIPLIERS = {
    "even_odd": 2.0,  # Чет/Нечет
    "number": 6.0,    # Угадать число
    "high_low": 2.0   # Больше/Меньше
}

# Комиссия за перевод (в процентах)
TRANSFER_FEE_PERCENT = 0  # 0% комиссия

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с кнопками"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play_menu")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("💸 Вывести средства", callback_data="withdraw_menu")],
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
{get_premium_emoji('casino')} <b>Добро пожаловать в Stake Casino! {get_premium_emoji('vip')}</b>

{get_premium_emoji('fire')} Мы рады видеть вас в нашем премиум казино!

{get_premium_emoji('balance')} <b>Ваш баланс:</b> {user_data[user_id]['balance']:.2f}$

<u>Доступные команды:</u>
• <code>/balance</code> / <code>/bal</code> / <code>/b</code> - показать баланс
• <code>/pay сумма</code> - перевести другу (ответом на сообщение)
• <code>/pay ID сумма</code> - перевести по ID пользователя
• Напишите <code>мины</code> - игра в мины
• Напишите <code>кубы</code> - игра в кубы
• <code>/chet сумма</code> - ставка на чет (2,4,6) - x2
• <code>/nechet сумма</code> - ставка на нечет (1,3,5) - x2
• <code>/number число сумма</code> - ставка на число (1-6) - x6
• <code>/more сумма</code> - ставка на больше (4-6) - x2
• <code>/less сумма</code> - ставка на меньше (1-3) - x2
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Команда для проверки баланса
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает баланс пользователя"""
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    await show_balance_message(update.message, user_id)

async def show_balance_message(message, user_id: int):
    """Показывает баланс пользователя"""
    balance = user_data[user_id]["balance"]
    
    # Рассчитываем общие суммы
    total_deposits = sum(dep["amount"] for dep in user_data[user_id].get("deposits", []))
    total_withdrawals = sum(wd["amount"] for wd in user_data[user_id].get("withdrawals", []))
    
    saved_bet = user_bets.get(user_id, None)
    bet_info = f"\n{get_premium_emoji('history')} Сохраненная ставка: {saved_bet:.2f}$" if saved_bet else ""
    
    balance_text = f"""
{get_premium_emoji('balance')} <b>Ваш баланс</b>

{get_premium_emoji('stats')} Текущий баланс: <b>{balance:.2f}$</b>{bet_info}

{get_premium_emoji('stats')} <u>Статистика:</u>
• Всего пополнено: <b>{total_deposits:.2f}$</b>
• Всего выведено: <b>{total_withdrawals:.2f}$</b>

{get_premium_emoji('game')} <u>Минимальные суммы:</u>
• Все игры: {MIN_BET:.2f}$
• Переводы: {MIN_TRANSFER_AMOUNT:.2f}$
• Пополнение: от {MIN_DEPOSIT:.2f}$
• Вывод: от {MIN_WITHDRAWAL:.2f}$

🎲 <u>Доступные игры:</u>
• <b>Мины</b> - 2 мины, множитель 1.12x
• <b>Кубы</b> - несколько режимов игры

{get_premium_emoji('transfer')} <u>Переводы:</u>
Используйте <code>/pay сумма</code> для переводов друзьям!
    """
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("💸 Вывести средства", callback_data="withdraw_menu")],
        [InlineKeyboardButton("🎮 Меню игр", callback_data="play_menu")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        balance_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Команда для переводов /pay
async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перевод средств другому пользователю"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": username,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # Проверяем, является ли сообщение ответом на другое сообщение
    reply_to_message = update.message.reply_to_message
    
    if reply_to_message:
        # Перевод ответом на сообщение
        target_user = reply_to_message.from_user
        
        if target_user.id == user_id:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Нельзя переводить деньги самому себе!")
            return
        
        if not context.args:
            await update.message.reply_text(
                f"{get_premium_emoji('info')} Укажите сумму перевода.\n"
                "Используйте: <code>/pay сумма</code>\n"
                "Например: <code>/pay 10</code>",
                parse_mode='HTML'
            )
            return
        
        try:
            amount = float(context.args[0])
        except ValueError:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат суммы.")
            return
        
        # Получаем информацию о получателе
        target_id = target_user.id
        target_username = target_user.username or target_user.first_name
        
    else:
        # Перевод по ID
        if len(context.args) < 2:
            await update.message.reply_text(
                f"{get_premium_emoji('info')} Неправильный формат команды.\n\n"
                "<u>Способ 1 (ответом на сообщение):</u>\n"
                "Ответьте на сообщение друга: <code>/pay сумма</code>\n\n"
                "<u>Способ 2 (по ID):</u>\n"
                "<code>/pay ID_пользователя сумма</code>\n\n"
                "Например: <code>/pay 123456789 10</code>",
                parse_mode='HTML'
            )
            return
        
        # Пытаемся определить получателя
        target_arg = context.args[0]
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат суммы.")
            return
        
        # Пробуем получить ID из аргумента
        if target_arg.isdigit():
            # Это числовой ID
            target_id = int(target_arg)
            target_username = f"пользователь {target_id}"
        else:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат получателя. Используйте числовой ID.")
            return
        
        if target_id == user_id:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Нельзя переводить деньги самому себе!")
            return
        
        # Проверяем существование пользователя
        if target_id not in user_data:
            # Создаем запись о пользователе, если он не существует
            user_data[target_id] = {
                "balance": INITIAL_BALANCE, 
                "username": f"пользователь {target_id}",
                "first_name": f"Пользователь {target_id}",
                "deposits": [],
                "withdrawals": []
            }
    
    # Проверяем сумму перевода
    if amount < MIN_TRANSFER_AMOUNT:
        await update.message.reply_text(f"{get_premium_emoji('min')} Минимальная сумма перевода: {MIN_TRANSFER_AMOUNT:.2f}$")
        return
    
    # Проверяем баланс отправителя
    if user_data[user_id]["balance"] < amount:
        await update.message.reply_text(
            f"{get_premium_emoji('lose')} Недостаточно средств для перевода.\n"
            f"Ваш баланс: {user_data[user_id]['balance']:.2f}$\n"
            f"Сумма перевода: {amount:.2f}$",
            parse_mode='HTML'
        )
        return
    
    # Рассчитываем комиссию
    fee = amount * TRANSFER_FEE_PERCENT / 100
    net_amount = amount - fee
    
    # Выполняем перевод
    user_data[user_id]["balance"] -= amount
    user_data[target_id]["balance"] += net_amount
    
    # Сообщение об успешном переводе с премиум эмодзи
    transfer_text = f"""
{get_premium_emoji('transfer')} <b>Перевод выполнен успешно!</b>

📤 <u>Отправитель:</u>
{get_premium_emoji('user')} {username} (ID: {user_id})
💸 Списано: {amount:.2f}$
🔒 Комиссия: {fee:.2f}$ ({TRANSFER_FEE_PERCENT}%)
{get_premium_emoji('balance')} Новый баланс: {user_data[user_id]['balance']:.2f}$

📥 <u>Получатель:</u>
{get_premium_emoji('user')} {target_username} (ID: {target_id})
💰 Получено: {net_amount:.2f}$
{get_premium_emoji('balance')} Новый баланс: {user_data[target_id]['balance']:.2f}$

{get_premium_emoji('time')} Перевод мгновенный
    """
    
    await update.message.reply_text(
        transfer_text,
        parse_mode='HTML'
    )
    
    # Уведомляем получателя
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"{get_premium_emoji('gift')} <b>Вам поступил перевод!</b>\n\n"
                 f"📤 От: {username} (ID: {user_id})\n"
                 f"{get_premium_emoji('money')} Сумма: {net_amount:.2f}$\n"
                 f"🔒 Комиссия: {fee:.2f}$\n"
                 f"{get_premium_emoji('balance')} Ваш новый баланс: {user_data[target_id]['balance']:.2f}$\n\n"
                 f"{get_premium_emoji('fire')} Спасибо за использование нашего казино!",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить получателя {target_id}: {e}")

# Команды для быстрых ставок в кубы
async def dice_even_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ставка на чет в кубах"""
    user_id = update.effective_user.id
    await process_dice_quick_bet(update, context, user_id, "even")

async def dice_odd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ставка на нечет в кубах"""
    user_id = update.effective_user.id
    await process_dice_quick_bet(update, context, user_id, "odd")

async def dice_number_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ставка на число в кубах"""
    user_id = update.effective_user.id
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{get_premium_emoji('info')} Неправильный формат команды.\n"
            "Используйте: <code>/number число сумма</code>\n"
            "Например: <code>/number 3 10</code>\n\n"
            "<u>Доступные числа:</u> 1, 2, 3, 4, 5, 6",
            parse_mode='HTML'
        )
        return
    
    try:
        number = int(context.args[0])
        amount = float(context.args[1])
        
        if number < 1 or number > 6:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Число должно быть от 1 до 6.")
            return
        
        if amount < MIN_BET:
            await update.message.reply_text(f"{get_premium_emoji('min')} Минимальная ставка: {MIN_BET:.2f}$")
            return
        
        await process_dice_quick_bet(update, context, user_id, "number", number, amount)
        
    except ValueError:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат числа или суммы.")

async def dice_high_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ставка на больше (4-6) в кубах"""
    user_id = update.effective_user.id
    await process_dice_quick_bet(update, context, user_id, "high")

async def dice_low_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ставка на меньше (1-3) в кубах"""
    user_id = update.effective_user.id
    await process_dice_quick_bet(update, context, user_id, "low")

async def process_dice_quick_bet(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, 
                                 bet_type: str, number: int = None, amount: float = None) -> None:
    """Обрабатывает быстрые ставки в кубы"""
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # Если amount не передан, берем из аргументов
    if amount is None:
        if not context.args:
            await update.message.reply_text(
                f"{get_premium_emoji('info')} Укажите сумму ставки.\n"
                f"Например: <code>/{bet_type} 10</code>",
                parse_mode='HTML'
            )
            return
        try:
            amount = float(context.args[0])
        except ValueError:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат суммы.")
            return
    
    if amount < MIN_BET:
        await update.message.reply_text(f"{get_premium_emoji('min')} Минимальная ставка: {MIN_BET:.2f}$")
        return
    
    if user_data[user_id]["balance"] < amount:
        await update.message.reply_text(
            f"{get_premium_emoji('lose')} Недостаточно средств на балансе.\n"
            f"Ваш баланс: {user_data[user_id]['balance']:.2f}$",
            parse_mode='HTML'
        )
        return
    
    # Бросаем куб через Telegram Dice
    dice_message = await update.message.reply_dice(emoji="🎲")
    dice_result = dice_message.dice.value
    
    await asyncio.sleep(2)  # Ждем пока анимация куба завершится
    
    # Определяем выигрыш
    win = False
    multiplier = DICE_MULTIPLIERS["even_odd"]
    bet_name = ""
    
    if bet_type == "even":  # Чет
        bet_name = "чёт"
        win = dice_result in [2, 4, 6]
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif bet_type == "odd":  # Нечет
        bet_name = "нечёт"
        win = dice_result in [1, 3, 5]
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif bet_type == "number":  # Число
        bet_name = f"число {number}"
        win = dice_result == number
        multiplier = DICE_MULTIPLIERS["number"]
    elif bet_type == "high":  # Больше (4-6)
        bet_name = "больше (4-6)"
        win = dice_result in [4, 5, 6]
        multiplier = DICE_MULTIPLIERS["high_low"]
    elif bet_type == "low":  # Меньше (1-3)
        bet_name = "меньше (1-3)"
        win = dice_result in [1, 2, 3]
        multiplier = DICE_MULTIPLIERS["high_low"]
    
    # Добавляем случайную цитату
    quote = random.choice(LUCKY_QUOTES_HTML) if win else random.choice(UNLUCKY_QUOTES_HTML)
    
    # Обрабатываем результат
    if win:
        win_amount = amount * multiplier
        user_data[user_id]["balance"] += win_amount
        
        result_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Быстрая ставка</b>

{get_premium_emoji('bet')} Ваша ставка: <b>{bet_name}</b>
{get_premium_emoji('money')} Сумма: <b>{amount:.2f}$</b>
{get_premium_emoji('dice')} Результат: <b>{dice_result}</b>

{get_premium_emoji('win')} <b>ВЫИГРЫШ!</b>
{get_premium_emoji('trophy')} Выигрыш: <b>{win_amount:.2f}$</b> (x{multiplier})
{get_premium_emoji('balance')} Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{quote}

{get_premium_emoji('fire')} Поздравляем с выигрышем!
        """
    else:
        user_data[user_id]["balance"] -= amount
        
        result_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Быстрая ставка</b>

{get_premium_emoji('bet')} Ваша ставка: <b>{bet_name}</b>
{get_premium_emoji('money')} Сумма: <b>{amount:.2f}$</b>
{get_premium_emoji('dice')} Результат: <b>{dice_result}</b>

{get_premium_emoji('lose')} <b>ПРОИГРЫШ</b>
{get_premium_emoji('withdraw')} Ставка не возвращается
{get_premium_emoji('balance')} Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{quote}

{get_premium_emoji('play')} В следующий раз повезет!
        """
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("🎲 Играть в Кубы", callback_data="game_dice")],
        [InlineKeyboardButton("🎮 Меню игр", callback_data="play_menu")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        result_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Команда для администратора /game
async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает информацию об игре (только для администратора)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{get_premium_emoji('lose')} У вас нет прав для выполнения этой команды.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            f"{get_premium_emoji('info')} Неправильный формат команды.\n"
            "Используйте: <code>/game mines номер_игры</code>\n"
            "Например: <code>/game mines 1</code>\n\n"
            f"Всего сыграно игр: {game_counter}",
            parse_mode='HTML'
        )
        return
    
    game_type = context.args[0].lower()
    try:
        game_num = int(context.args[1])
    except ValueError:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный номер игры.")
        return
    
    if game_type != "mines":
        await update.message.reply_text(f"{get_premium_emoji('lose')} Доступен только тип 'mines'.")
        return
    
    if game_num not in games_history:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Игра №{game_num} не найдена.")
        return
    
    game_info = games_history[game_num]
    
    # Генерация поля с минами для администратора
    field_text = ""
    for row in range(GRID_SIZE):
        row_text = ""
        for col in range(GRID_SIZE):
            cell_idx = row * GRID_SIZE + col
            if cell_idx in game_info["mines"]:
                row_text += "💣"
            elif cell_idx in game_info["prizes"]:
                row_text += "🎁"
            else:
                row_text += "⬜"
        field_text += row_text + "\n"
    
    # Преобразуем индексы в координаты (строка, столбец)
    mine_positions = []
    for idx in sorted(game_info["mines"]):
        row = idx // GRID_SIZE + 1
        col = idx % GRID_SIZE + 1
        mine_positions.append(f"({row},{col})")
    
    prize_positions = []
    for idx in sorted(game_info["prizes"]):
        row = idx // GRID_SIZE + 1
        col = idx % GRID_SIZE + 1
        prize_positions.append(f"({row},{col})")
    
    game_details = f"""
{get_premium_emoji('game')} <b>Игра №{game_num} - Мины</b>

{get_premium_emoji('user')} Игрок: {game_info['user_id']} ({game_info.get('username', 'Неизвестно')})
{get_premium_emoji('money')} Ставка: {game_info['bet']:.2f}$
{get_premium_emoji('mine')} Количество мин: 2 (фиксировано)
{get_premium_emoji('stats')} Статус: {game_info.get('status', 'Завершена')}
{get_premium_emoji('time')} Время: {game_info.get('time', 'Неизвестно')}

<u>Поле с минами:</u>
{field_text}

<u>Позиции мин (координаты строка,столбец):</u>
{', '.join(mine_positions)}

<u>Позиции мин (индексы 0-24):</u>
{', '.join(map(str, sorted(game_info['mines'])))}

<u>Позиции призов:</u>
{', '.join(map(str, sorted(game_info['prizes'])))}
    """
    
    await update.message.reply_text(
        game_details,
        parse_mode='HTML'
    )

# Команда /givemoney для администратора
async def givemoney(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выдает баланс пользователю (только для администратора)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{get_premium_emoji('lose')} У вас нет прав для выполнения этой команды.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{get_premium_emoji('info')} Неправильный формат команды.\n"
            "Используйте: <code>/givemoney ID_пользователя сумма</code>\n"
            "Например: <code>/givemoney 123456789 100</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Сумма должна быть положительной.")
            return
        
        if target_id not in user_data:
            user_data[target_id] = {
                "balance": INITIAL_BALANCE, 
                "username": f"пользователь {target_id}",
                "first_name": f"Пользователь {target_id}",
                "deposits": [],
                "withdrawals": []
            }
        
        user_data[target_id]["balance"] += amount
        
        # Добавляем запись о пополнении
        deposit_record = {
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin_id": user_id,
            "type": "администратор"
        }
        user_data[target_id]["deposits"].append(deposit_record)
        
        await update.message.reply_text(
            f"{get_premium_emoji('deposit')} Баланс пользователя <code>{target_id}</code> пополнен на <b>{amount:.2f}$</b>.\n"
            f"Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>",
            parse_mode='HTML'
        )
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"{get_premium_emoji('gift')} Ваш баланс пополнен на <b>{amount:.2f}$</b> администратором!\n"
                     f"Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>",
                parse_mode='HTML'
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат ID или суммы.")

# Команда /delbalance для администратора
async def delbalance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Снимает баланс с пользователя (только для администратора)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{get_premium_emoji('lose')} У вас нет прав для выполнения этой команды.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{get_premium_emoji('info')} Неправильный формат команды.\n"
            "Используйте: <code>/delbalance ID_пользователя сумма</code>\n"
            "Например: <code>/delbalance 123456789 100</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Сумма должна быть положительной.")
            return
        
        if target_id not in user_data:
            await update.message.reply_text(f"{get_premium_emoji('lose')} Пользователь с ID {target_id} не найден.")
            return
        
        if user_data[target_id]["balance"] < amount:
            await update.message.reply_text(
                f"{get_premium_emoji('lose')} У пользователя недостаточно средств.\n"
                f"Баланс пользователя: {user_data[target_id]['balance']:.2f}$\n"
                f"Сумма списания: {amount:.2f}$",
                parse_mode='HTML'
            )
            return
        
        user_data[target_id]["balance"] -= amount
        
        await update.message.reply_text(
            f"{get_premium_emoji('withdraw')} С пользователя <code>{target_id}</code> списано <b>{amount:.2f}$</b>.\n"
            f"Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>",
            parse_mode='HTML'
        )
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"{get_premium_emoji('lose')} С вашего баланса списано <b>{amount:.2f}$</b> администратором!\n"
                     f"Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>",
                parse_mode='HTML'
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат ID или суммы.")

# Обработчик текстовых сообщений
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения"""
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()
    
    # Если пользователь написал "мины" - запускаем игру
    if text == "мины":
        await start_mines_from_chat(update, user_id)
        return
    
    # Если пользователь написал "кубы" или "кости" - запускаем игру в кубы
    if text in ["кубы", "кости", "dice"]:
        await start_dice_from_chat(update, user_id)
        return
    
    # Проверяем на наличие суммы для ставки
    pattern = r'(\d+\.?\d*)\s*(?:\$|usd|доллар|долларов)'
    match = re.search(pattern, text)
    
    if match:
        await handle_bet_message(update, user_id, match)
        return

# Запуск игры "Кубы" из чата
async def start_dice_from_chat(update: Update, user_id: int) -> None:
    """Запускает игру Кубы из текстового сообщения"""
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton("🎲 Чет/Нечет", callback_data="dice_even_odd"),
            InlineKeyboardButton("🎯 Число", callback_data="dice_number")
        ],
        [
            InlineKeyboardButton("⚖️ Больше/Меньше", callback_data="dice_high_low"),
            InlineKeyboardButton("↩️ Назад", callback_data="play_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Игра в Кубы</b>

{get_premium_emoji('user')} {update.effective_user.username or update.effective_user.first_name}
{get_premium_emoji('balance')} Баланс: {balance:.2f}$

<u>Выберите тип ставки:</u>

🎲 <b>Чет/Нечет</b>
• Чет (2,4,6): x{DICE_MULTIPLIERS["even_odd"]}
• Нечет (1,3,5): x{DICE_MULTIPLIERS["even_odd"]}

🎯 <b>Число</b>
• Угадать число (1-6): x{DICE_MULTIPLIERS["number"]}

⚖️ <b>Больше/Меньше</b>
• Больше (4-6): x{DICE_MULTIPLIERS["high_low"]}
• Меньше (1-3): x{DICE_MULTIPLIERS["high_low"]}

<u>Быстрые команды:</u>
• <code>/chet сумма</code> - ставка на чет
• <code>/nechet сумма</code> - ставка на нечет
• <code>/number число сумма</code> - ставка на число
• <code>/more сумма</code> - ставка на больше (4-6)
• <code>/less сумма</code> - ставка на меньше (1-3)
    """
    
    await update.message.reply_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Меню пополнения баланса
async def deposit_menu(query, user_id):
    """Меню пополнения баланса"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton(f"📞 Связаться с {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME[1:]}")],
        [InlineKeyboardButton("↩️ Назад", callback_data="balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    deposit_text = f"""
{get_premium_emoji('deposit')} <b>Пополнение баланса</b>

{get_premium_emoji('card')} Ваш текущий баланс: <b>{balance:.2f}$</b>

<u>Требования к пополнению:</u>
• {get_premium_emoji('min')} Минимальная сумма: <b>{MIN_DEPOSIT:.2f}$</b>
• {get_premium_emoji('user')} Пополнение через администратора: {ADMIN_USERNAME}

{get_premium_emoji('rules')} <b>Инструкция по пополнению:</b>
1. Нажмите кнопку ниже для связи с администратором
2. Укажите ваш ID: <code>{user_id}</code>
3. Укажите желаемую сумму пополнения
4. Дождитесь подтверждения от администратора

{get_premium_emoji('time')} Пополнение происходит в течение 5-15 минут после подтверждения.
    """
    
    await query.edit_message_text(
        text=deposit_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Меню вывода средств
async def withdraw_menu(query, user_id):
    """Меню вывода средств"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton(f"📞 Связаться с {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME[1:]}")],
        [InlineKeyboardButton("↩️ Назад", callback_data="balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    withdraw_text = f"""
{get_premium_emoji('withdraw')} <b>Вывод средств</b>

{get_premium_emoji('card')} Ваш текущий баланс: <b>{balance:.2f}$</b>

<u>Требования к выводу:</u>
• {get_premium_emoji('min')} Минимальная сумма вывода: <b>{MIN_WITHDRAWAL:.2f}$</b>
• {get_premium_emoji('user')} Вывод через администратора: {ADMIN_USERNAME}

{get_premium_emoji('rules')} <b>Инструкция по выводу:</b>
1. Нажмите кнопку ниже для связи с администратором
2. Укажите ваш ID: <code>{user_id}</code>
3. Укажите сумму вывода (от {MIN_WITHDRAWAL:.2f}$)
4. Укажите реквизиты для перевода
5. Дождитесь подтверждения и получения средств

{get_premium_emoji('time')} Вывод происходит в течение 5-30 минут после подтверждения.

{get_premium_emoji('secure')} <b>Внимание:</b> Средства выводятся только на карты РФ или через другие доступные способы, согласованные с администратором.
    """
    
    await query.edit_message_text(
        text=withdraw_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Меню игры в кубы
async def dice_menu(query, user_id):
    """Меню игры в кубы"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton("🎲 Чет/Нечет", callback_data="dice_even_odd"),
            InlineKeyboardButton("🎯 Число", callback_data="dice_number")
        ],
        [
            InlineKeyboardButton("⚖️ Больше/Меньше", callback_data="dice_high_low"),
            InlineKeyboardButton("↩️ Назад", callback_data="play_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Игра в Кубы</b>

{get_premium_emoji('user')} {query.from_user.username or query.from_user.first_name}
{get_premium_emoji('balance')} Баланс: {balance:.2f}$
🎲 Минимальная ставка: {MIN_BET:.2f}$

<u>Выберите тип ставки:</u>

🎲 <b>Чет/Нечет</b>
• Чет (2,4,6): x{DICE_MULTIPLIERS["even_odd"]}
• Нечет (1,3,5): x{DICE_MULTIPLIERS["even_odd"]}

🎯 <b>Число</b>
• Угадать число (1-6): x{DICE_MULTIPLIERS["number"]}

⚖️ <b>Больше/Меньше</b>
• Больше (4-6): x{DICE_MULTIPLIERS["high_low"]}
• Меньше (1-3): x{DICE_MULTIPLIERS["high_low"]}
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Чет/Нечет в кубах
async def dice_even_odd(query, user_id):
    """Ставка на чет/нечет в кубах"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton("🎲 Чет (2,4,6)", callback_data="dice_bet_even"),
            InlineKeyboardButton("🎲 Нечет (1,3,5)", callback_data="dice_bet_odd")
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="game_dice")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Чет/Нечет</b>

{get_premium_emoji('balance')} Баланс: {balance:.2f}$
🎯 Множитель: x{DICE_MULTIPLIERS["even_odd"]}

<u>Правила:</u>
• Выберите <b>Чет</b> - выигрываете, если выпадет 2, 4 или 6
• Выберите <b>Нечет</b> - выигрываете, если выпадет 1, 3 или 5

{get_premium_emoji('win')} Выигрыш: <b>ставка × {DICE_MULTIPLIERS["even_odd"]}</b>

<u>Быстрая команда:</u>
• <code>/chet сумма</code> - ставка на чет
• <code>/nechet сумма</code> - ставка на нечет
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Угадать число в кубах
async def dice_number(query, user_id):
    """Ставка на число в кубах"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="dice_bet_num_1"),
            InlineKeyboardButton("2", callback_data="dice_bet_num_2"),
            InlineKeyboardButton("3", callback_data="dice_bet_num_3")
        ],
        [
            InlineKeyboardButton("4", callback_data="dice_bet_num_4"),
            InlineKeyboardButton("5", callback_data="dice_bet_num_5"),
            InlineKeyboardButton("6", callback_data="dice_bet_num_6")
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="game_dice")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Угадать число</b>

{get_premium_emoji('balance')} Баланс: {balance:.2f}$
🎯 Множитель: x{DICE_MULTIPLIERS["number"]}

<u>Правила:</u>
• Выберите число от 1 до 6
• Если куб покажет выбранное число - вы выигрываете
• В противном случае - проигрыш

{get_premium_emoji('win')} Выигрыш: <b>ставка × {DICE_MULTIPLIERS["number"]}</b>

<u>Быстрая команда:</u>
• <code>/number число сумма</code>
• Например: <code>/number 3 10</code>
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Больше/Меньше в кубах
async def dice_high_low(query, user_id):
    """Ставка на больше/меньше в кубах"""
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton("📉 Меньше (1-3)", callback_data="dice_bet_low"),
            InlineKeyboardButton("📈 Больше (4-6)", callback_data="dice_bet_high")
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="game_dice")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Больше/Меньше</b>

{get_premium_emoji('balance')} Баланс: {balance:.2f}$
🎯 Множитель: x{DICE_MULTIPLIERS["high_low"]}

<u>Правила:</u>
• <b>Меньше</b> - выигрываете, если выпадет 1, 2 или 3
• <b>Больше</b> - выигрываете, если выпадет 4, 5 или 6

{get_premium_emoji('win')} Выигрыш: <b>ставка × {DICE_MULTIPLIERS["high_low"]}</b>

<u>Быстрая команда:</u>
• <code>/less сумма</code> - ставка на 1-3
• <code>/more сумма</code> - ставка на 4-6
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Обработка ставки в кубах
async def process_dice_bet(query, user_id, bet_type: str, bet_value: str = None):
    """Обрабатывает ставку в кубах"""
    # Сохраняем данные ставки
    saved_bet = user_bets.get(user_id, MIN_BET)
    game_data[user_id] = {
        "game_type": "dice",
        "bet_type": bet_type,
        "bet_value": bet_value,
        "amount": saved_bet
    }
    
    balance = user_data[user_id]["balance"]
    
    # Определяем описание ставки
    bet_description = ""
    if bet_type == "even":
        bet_description = "Чет (2,4,6)"
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif bet_type == "odd":
        bet_description = "Нечет (1,3,5)"
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif bet_type == "number":
        bet_description = f"Число {bet_value}"
        multiplier = DICE_MULTIPLIERS["number"]
    elif bet_type == "high":
        bet_description = "Больше (4-6)"
        multiplier = DICE_MULTIPLIERS["high_low"]
    elif bet_type == "low":
        bet_description = "Меньше (1-3)"
        multiplier = DICE_MULTIPLIERS["high_low"]
    else:
        bet_description = "Неизвестно"
        multiplier = 1.0
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton(f"🎯 Ставка: {saved_bet:.2f}$", callback_data="dice_change_bet"),
            InlineKeyboardButton("🎲 Играть", callback_data="dice_roll")
        ],
        [InlineKeyboardButton("📝 Изменить ставку", callback_data=f"dice_{bet_type}_{bet_value}" if bet_value else f"dice_{bet_type}")]
    ]
    
    # Добавляем кнопку "Назад" в зависимости от типа ставки
    if bet_type in ["even", "odd"]:
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="dice_even_odd")])
    elif bet_type == "number":
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="dice_number")])
    elif bet_type in ["high", "low"]:
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="dice_high_low")])
    else:
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="game_dice")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Подтверждение ставки</b>

{get_premium_emoji('bet')} Ставка: <b>{bet_description}</b>
{get_premium_emoji('money')} Сумма: <b>{saved_bet:.2f}$</b> (от {MIN_BET:.2f}$)
🎲 Множитель: <b>x{multiplier}</b>
{get_premium_emoji('win')} Потенциальный выигрыш: <b>{(saved_bet * multiplier):.2f}$</b>

{get_premium_emoji('balance')} Ваш баланс: <b>{balance:.2f}$</b>

<u>Нажмите "Играть" чтобы бросить куб!</u>
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Бросок куба
async def dice_roll(query, user_id):
    """Бросает куб и определяет результат"""
    if user_id not in game_data or "game_type" not in game_data[user_id]:
        await query.answer("Сначала сделайте ставку!")
        return
    
    game = game_data[user_id]
    bet_amount = game["amount"]
    
    # Проверяем баланс
    if user_data[user_id]["balance"] < bet_amount:
        await query.answer("Недостаточно средств!")
        return
    
    # Бросаем куб через Telegram Dice
    try:
        dice_message = await query.message.reply_dice(emoji="🎲")
        dice_result = dice_message.dice.value
        
        await asyncio.sleep(2)  # Ждем пока анимация куба завершится
        
    except Exception as e:
        logger.error(f"Ошибка при броске куба: {e}")
        # Если не удалось отправить анимацию, используем случайное число
        dice_result = random.randint(1, 6)
        await query.message.reply_text(f"🎲 Бросаем куб... Выпало: {dice_result}")
        await asyncio.sleep(1)
    
    # Определяем выигрыш
    win = False
    multiplier = 1.0
    bet_description = ""
    
    if game["bet_type"] == "even":
        bet_description = "Чет (2,4,6)"
        win = dice_result in [2, 4, 6]
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif game["bet_type"] == "odd":
        bet_description = "Нечет (1,3,5)"
        win = dice_result in [1, 3, 5]
        multiplier = DICE_MULTIPLIERS["even_odd"]
    elif game["bet_type"] == "number":
        bet_description = f"Число {game['bet_value']}"
        win = dice_result == int(game['bet_value'])
        multiplier = DICE_MULTIPLIERS["number"]
    elif game["bet_type"] == "high":
        bet_description = "Больше (4-6)"
        win = dice_result in [4, 5, 6]
        multiplier = DICE_MULTIPLIERS["high_low"]
    elif game["bet_type"] == "low":
        bet_description = "Меньше (1-3)"
        win = dice_result in [1, 2, 3]
        multiplier = DICE_MULTIPLIERS["high_low"]
    
    # Добавляем случайную цитату
    quote = random.choice(LUCKY_QUOTES_HTML) if win else random.choice(UNLUCKY_QUOTES_HTML)
    
    # Обрабатываем результат
    if win:
        win_amount = bet_amount * multiplier
        user_data[user_id]["balance"] += win_amount
        
        result_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Результат</b>

{get_premium_emoji('bet')} Ваша ставка: <b>{bet_description}</b>
{get_premium_emoji('money')} Сумма: <b>{bet_amount:.2f}$</b>
{get_premium_emoji('dice')} Выпало: <b>{dice_result}</b>

{get_premium_emoji('win')} <b>ВЫИГРЫШ!</b>
{get_premium_emoji('trophy')} Выигрыш: <b>{win_amount:.2f}$</b> (x{multiplier})
{get_premium_emoji('balance')} Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{quote}

{get_premium_emoji('fire')} Поздравляем с выигрышем!
        """
    else:
        user_data[user_id]["balance"] -= bet_amount
        
        result_text = f"""
{get_premium_emoji('dice')} <b>Кубы - Результат</b>

{get_premium_emoji('bet')} Ваша ставка: <b>{bet_description}</b>
{get_premium_emoji('money')} Сумма: <b>{bet_amount:.2f}$</b>
{get_premium_emoji('dice')} Выпало: <b>{dice_result}</b>

{get_premium_emoji('lose')} <b>ПРОИГРЫШ</b>
{get_premium_emoji('withdraw')} Ставка не возвращается
{get_premium_emoji('balance')} Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{quote}

{get_premium_emoji('play')} В следующий раз повезет!
        """
    
    # Клавиатура после игры с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("🎲 Играть снова", callback_data="game_dice")],
        [InlineKeyboardButton("🎮 Меню игр", callback_data="play_menu")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Изменение ставки в кубах
async def dice_change_bet(query, user_id):
    """Изменение ставки в кубах"""
    balance = user_data[user_id]["balance"]
    current_bet = game_data[user_id]["amount"] if user_id in game_data and "amount" in game_data[user_id] else MIN_BET
    
    saved_bet = user_bets.get(user_id, None)
    saved_bet_info = f"\n{get_premium_emoji('history')} Сохраненная ставка: {saved_bet:.2f}$" if saved_bet else ""
    
    keyboard = []
    bet_options = [0.1, 0.5, 1, 5, 10, 25, 50, 100]
    
    row = []
    for bet in bet_options:
        if bet <= balance:
            button_text = f"{bet:.1f}$"
            if saved_bet and abs(bet - saved_bet) < 0.01:
                button_text = f"💾{bet:.1f}$"
            row.append(InlineKeyboardButton(button_text, callback_data=f"dice_set_bet_{bet}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Определяем куда вернуться
    if user_id in game_data and "bet_type" in game_data[user_id]:
        bet_type = game_data[user_id]["bet_type"]
        bet_value = game_data[user_id].get("bet_value", "")
        if bet_value:
            keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data=f"dice_{bet_type}_{bet_value}")])
        else:
            keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data=f"dice_{bet_type}")])
    else:
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="game_dice")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"{get_premium_emoji('bet')} <b>Выберите ставку для Кубов</b>{saved_bet_info}\n\n"
             f"Текущая ставка: {current_bet:.2f}$\n"
             f"Ваш баланс: {balance:.2f}$",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Запуск игры "Мины" из чата
async def start_mines_from_chat(update: Update, user_id: int) -> None:
    """Запускает игру Мины из текстового сообщения"""
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    balance = user_data[user_id]["balance"]
    
    if balance < MIN_BET:
        await update.message.reply_text(
            f"{get_premium_emoji('lose')} Недостаточно средств для игры.\n"
            f"Минимальная ставка: {MIN_BET:.2f}$\n"
            f"Ваш баланс: {balance:.2f}$\n\n"
            f"Используйте <code>/start</code> для пополнения баланса.",
            parse_mode='HTML'
        )
        return
    
    # Используем сохраненную ставку или минимальную
    saved_bet = user_bets.get(user_id, MIN_BET)
    if saved_bet > balance:
        saved_bet = MIN_BET
    
    # Инициализируем игру
    if user_id not in game_data:
        game_data[user_id] = {
            "mines_count": 2,
            "bet": saved_bet,
            "revealed_cells": [],
            "game_active": False,
            "current_multiplier": 1.0,
            "prize_cells": set(),
            "game_number": 0,
            "mines": set(),
            "won_amount": 0
        }
    else:
        game_data[user_id]["bet"] = saved_bet
        game_data[user_id]["mines_count"] = 2
        game_data[user_id]["game_active"] = False
        game_data[user_id]["revealed_cells"] = []
        game_data[user_id]["current_multiplier"] = 1.0
        game_data[user_id]["prize_cells"] = set()
        game_data[user_id]["mines"] = set()
        game_data[user_id]["won_amount"] = 0
    
    mines_count = game_data[user_id]["mines_count"]
    multiplier = MULTIPLIERS[mines_count]
    potential_win = game_data[user_id]["bet"] * multiplier
    
    bet_source = f"{get_premium_emoji('history')} (сохраненная)" if user_bets.get(user_id) and abs(game_data[user_id]["bet"] - user_bets[user_id]) < 0.01 else ""
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton(f"🎯 Ставка: {game_data[user_id]['bet']:.2f}$", callback_data="change_bet"),
            InlineKeyboardButton("💣 Мины: 2", callback_data="mines_info")
        ],
        [InlineKeyboardButton(f"▶️ Играть ({multiplier}x)", callback_data="start_mines_game")],
        [InlineKeyboardButton("↩️ Назад в меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('game')} <b>Быстрый старт: Мины</b>

{get_premium_emoji('user')} {update.effective_user.username or update.effective_user.first_name}
{get_premium_emoji('balance')} Баланс — {balance:.2f} $
{get_premium_emoji('bet')} Ставка — {game_data[user_id]['bet']:.2f} $ {bet_source}(от {MIN_BET:.2f})

{get_premium_emoji('mine')} Количество мин — 2 (фиксировано)
{get_premium_emoji('multiplier')} Множитель — {multiplier}x
{get_premium_emoji('win')} Потенциальный выигрыш — {potential_win:.2f} $
    """
    
    await update.message.reply_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Информация о минах
async def mines_info(query, user_id):
    """Показывает информацию о фиксированном количестве мин"""
    mines_count = 2
    multiplier = MULTIPLIERS[mines_count]
    
    # Клавиатура с обычными эмодзи
    keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data="game_mines")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    info_text = f"""
{get_premium_emoji('info')} <b>Информация о минах</b>

{get_premium_emoji('game')} В игре "Мины" фиксированное количество мин: <b>2</b>
{get_premium_emoji('multiplier')} Множитель: <b>{multiplier}x</b>
{get_premium_emoji('stats')} Игровое поле: <b>5x5</b> (25 клеток)
{get_premium_emoji('mine')} Количество мин: <b>2</b>
{get_premium_emoji('prize')} Количество призов: <b>2</b>
    """
    
    await query.edit_message_text(
        text=info_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Обработка сообщений со ставками
async def handle_bet_message(update: Update, user_id: int, match: re.Match) -> None:
    """Обрабатывает сообщения со ставками"""
    try:
        amount = float(match.group(1))
    except ValueError:
        await update.message.reply_text(f"{get_premium_emoji('lose')} Неверный формат суммы.")
        return
    
    if amount < MIN_BET:
        await update.message.reply_text(
            f"{get_premium_emoji('min')} Минимальная ставка составляет {MIN_BET:.2f}$.\n"
            f"Вы указали: {amount:.2f}$"
        )
        return
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    user_bets[user_id] = amount
    
    await update.message.reply_text(
        f"{get_premium_emoji('bet')} Ставка сохранена!\n"
        f"Ваша ставка: <b>{amount:.2f}$</b>\n\n"
        f"Теперь при входе в игры эта ставка будет установлена автоматически.\n\n"
        f"<u>Доступные игры:</u>\n"
        f"• Напишите <code>мины</code> - игра в мины\n"
        f"• Напишите <code>кубы</code> - игра в кубы",
        parse_mode='HTML'
    )

# Показать баланс
async def show_balance(query, user_id):
    """Показывает баланс пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": query.from_user.username or query.from_user.first_name,
            "first_name": query.from_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    balance = user_data[user_id]["balance"]
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("💸 Вывести средства", callback_data="withdraw_menu")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    saved_bet = user_bets.get(user_id, None)
    bet_info = f"\n{get_premium_emoji('history')} Сохраненная ставка: {saved_bet:.2f}$" if saved_bet else ""
    
    # Рассчитываем общие суммы
    total_deposits = sum(dep["amount"] for dep in user_data[user_id].get("deposits", []))
    total_withdrawals = sum(wd["amount"] for wd in user_data[user_id].get("withdrawals", []))
    
    balance_text = f"""
{get_premium_emoji('balance')} <b>Ваш баланс</b>

{get_premium_emoji('money')} Баланс: {balance:.2f} ${bet_info}

{get_premium_emoji('stats')} <u>Статистика:</u>
• Всего пополнено: <b>{total_deposits:.2f}$</b>
• Всего выведено: <b>{total_withdrawals:.2f}$</b>

🎮 Минимальная ставка: {MIN_BET:.2f} $

<u>Доступные игры:</u>
• <b>Мины</b> - 2 мины, множитель 1.12x
• <b>Кубы</b> - несколько режимов игры

{get_premium_emoji('transfer')} <u>Переводы:</u>
Используйте <code>/pay сумма</code> для переводов друзьям!
    """
    
    await query.edit_message_text(
        text=balance_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Главный обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": query.from_user.username or query.from_user.first_name,
            "first_name": query.from_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # Сохраняем имя пользователя
    user_data[user_id]["username"] = query.from_user.username or query.from_user.first_name
    
    # Обработка основных команд
    if query.data == "play_menu":
        await play_menu(query, user_id)
        return
    
    elif query.data == "balance":
        await show_balance(query, user_id)
        return
    
    elif query.data == "deposit":
        await deposit_menu(query, user_id)
        return
    
    elif query.data == "withdraw_menu":
        await withdraw_menu(query, user_id)
        return
    
    elif query.data == "chats":
        # Клавиатура с обычными эмодзи
        keyboard = [
            [InlineKeyboardButton("💬 Перейти в чат", url="https://t.me/+fVJwoK3brgU0NmMy")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        chats_text = f"""
{get_premium_emoji('user')} <b>Игровые чаты</b>

Присоединяйтесь к нашему сообществу!
        """
        
        await query.edit_message_text(
            text=chats_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    elif query.data == "back_to_main":
        # Клавиатура с обычными эмодзи
        keyboard = [
            [InlineKeyboardButton("🎮 Играть", callback_data="play_menu")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton("💸 Вывести средства", callback_data="withdraw_menu")],
            [InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
{get_premium_emoji('casino')} <b>Добро пожаловать в Stake Casino! {get_premium_emoji('vip')}</b>

<u>Быстрые команды:</u>
• <code>/balance</code> / <code>/bal</code> / <code>/b</code> - показать баланс
• <code>/pay сумма</code> - перевести другу
• Напишите <code>мины</code> - игра в мины (2 мины)
• Напишите <code>кубы</code> - игра в кубы
• <code>/chet сумма</code> - ставка на чет (2,4,6) - x2
• <code>/nechet сумма</code> - ставка на нечет (1,3,5) - x2
• <code>/number число сумма</code> - ставка на число (1-6) - x6
• <code>/more сумма</code> - ставка на больше (4-6) - x2
• <code>/less сумма</code> - ставка на меньше (1-3) - x2
        """
        
        await query.edit_message_text(
            text=welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Игра в мины
    elif query.data == "game_mines":
        await mines_setup(query, user_id)
        return
    
    elif query.data == "change_bet":
        await change_bet(query, user_id)
        return
    
    elif query.data == "mines_info":
        await mines_info(query, user_id)
        return
    
    elif query.data.startswith("set_bet_"):
        bet = float(query.data.split("_")[2])
        if bet <= user_data[user_id]["balance"]:
            game_data[user_id]["bet"] = bet
            user_bets[user_id] = bet
        await mines_setup(query, user_id)
        return
    
    elif query.data == "start_mines_game":
        if user_data[user_id]["balance"] < game_data[user_id]["bet"]:
            await query.answer("Недостаточно средств на балансе!")
            return
        else:
            await play_mines_game(query, user_id)
            return
    
    elif query.data.startswith("cell_"):
        cell_idx = int(query.data.split("_")[1])
        await handle_cell_click(query, user_id, cell_idx)
        return
    
    elif query.data == "cashout":
        await handle_cashout(query, user_id)
        return
    
    elif query.data.startswith("cell_opened_"):
        await query.answer("Эта ячейка уже открыта!")
        return
    
    # Игра в кубы
    elif query.data == "game_dice":
        await dice_menu(query, user_id)
        return
    
    elif query.data == "dice_even_odd":
        await dice_even_odd(query, user_id)
        return
    
    elif query.data == "dice_number":
        await dice_number(query, user_id)
        return
    
    elif query.data == "dice_high_low":
        await dice_high_low(query, user_id)
        return
    
    elif query.data == "dice_bet_even":
        await process_dice_bet(query, user_id, "even")
        return
    
    elif query.data == "dice_bet_odd":
        await process_dice_bet(query, user_id, "odd")
        return
    
    elif query.data.startswith("dice_bet_num_"):
        number = query.data.split("_")[3]
        await process_dice_bet(query, user_id, "number", number)
        return
    
    elif query.data == "dice_bet_high":
        await process_dice_bet(query, user_id, "high")
        return
    
    elif query.data == "dice_bet_low":
        await process_dice_bet(query, user_id, "low")
        return
    
    elif query.data == "dice_change_bet":
        await dice_change_bet(query, user_id)
        return
    
    elif query.data.startswith("dice_set_bet_"):
        bet = float(query.data.split("_")[3])
        if bet <= user_data[user_id]["balance"]:
            # Сохраняем ставку для кубов
            user_bets[user_id] = bet
            if user_id in game_data and "bet_type" in game_data[user_id]:
                game_data[user_id]["amount"] = bet
                # Возвращаемся к соответствующему экрану
                bet_type = game_data[user_id]["bet_type"]
                bet_value = game_data[user_id].get("bet_value", "")
                if bet_value:
                    await process_dice_bet(query, user_id, bet_type, bet_value)
                else:
                    await process_dice_bet(query, user_id, bet_type)
            else:
                await dice_menu(query, user_id)
        return
    
    elif query.data == "dice_roll":
        await dice_roll(query, user_id)
        return

# Главное меню игр
async def play_menu(query, user_id):
    """Меню выбора игры"""
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": query.from_user.username or query.from_user.first_name,
            "first_name": query.from_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("💣 Мины (2 мины)", callback_data="game_mines")],
        [InlineKeyboardButton("🎲 Кубы", callback_data="game_dice")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    saved_bet = user_bets.get(user_id, None)
    bet_info = f"\n{get_premium_emoji('history')} Ваша сохраненная ставка: {saved_bet:.2f}$" if saved_bet else ""
    
    menu_text = f"""
{get_premium_emoji('game')} <b>Выберите игру</b>{bet_info}

🎮 <b>Мины</b>
• Фиксировано 2 мины на поле 5x5
• Множитель: 1.12x

🎲 <b>Кубы</b>
• Чет/Нечет - x{DICE_MULTIPLIERS["even_odd"]}
• Угадать число - x{DICE_MULTIPLIERS["number"]}
• Больше/Меньше - x{DICE_MULTIPLIERS["high_low"]}

<u>Быстрый старт:</u>
• Напишите в чат <code>мины</code> - игра в мины
• Напишите в чат <code>кубы</code> - игра в кубы
    """
    
    await query.edit_message_text(
        text=menu_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Настройка игры в мины
async def mines_setup(query, user_id):
    """Настройка игры в мины"""
    global game_counter
    
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE, 
            "username": query.from_user.username or query.from_user.first_name,
            "first_name": query.from_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    balance = user_data[user_id]["balance"]
    
    if user_id not in game_data:
        game_data[user_id] = {
            "mines_count": 2,
            "bet": MIN_BET,
            "revealed_cells": [],
            "game_active": False,
            "current_multiplier": 1.0,
            "prize_cells": set(),
            "game_number": game_counter + 1,
            "mines": set(),
            "won_amount": 0
        }
    
    saved_bet = user_bets.get(user_id)
    if saved_bet:
        if saved_bet <= balance:
            game_data[user_id]["bet"] = saved_bet
        else:
            game_data[user_id]["bet"] = min(saved_bet, balance)
            if balance < MIN_BET:
                game_data[user_id]["bet"] = MIN_BET
    else:
        game_data[user_id]["bet"] = MIN_BET
    
    mines_count = game_data[user_id]["mines_count"]
    multiplier = MULTIPLIERS[mines_count]
    potential_win = game_data[user_id]["bet"] * multiplier
    
    bet_source = f"{get_premium_emoji('history')} (сохраненная)" if saved_bet and abs(game_data[user_id]["bet"] - saved_bet) < 0.01 else ""
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [
            InlineKeyboardButton(f"🎯 Ставка: {game_data[user_id]['bet']:.2f}$", callback_data="change_bet"),
            InlineKeyboardButton("ℹ️ Инфо о минах", callback_data="mines_info")
        ],
        [InlineKeyboardButton(f"▶️ Играть ({multiplier}x)", callback_data="start_mines_game")],
        [InlineKeyboardButton("↩️ Назад", callback_data="play_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    setup_text = f"""
{get_premium_emoji('mine')} <b>Мины</b>

{get_premium_emoji('user')} {query.from_user.username or query.from_user.first_name}
{get_premium_emoji('balance')} Баланс — {balance:.2f} $
{get_premium_emoji('bet')} Ставка — {game_data[user_id]['bet']:.2f} $ {bet_source}(от {MIN_BET:.2f})

{get_premium_emoji('mine')} Количество мин — 2 (фиксировано)
{get_premium_emoji('multiplier')} Множитель — {multiplier}x
{get_premium_emoji('win')} Потенциальный выигрыш — {potential_win:.2f} $

<u>Номер игры:</u> #{game_data[user_id]['game_number']}
    """
    
    await query.edit_message_text(
        text=setup_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Инициализация игрового поля
def init_game_field(user_id):
    """Инициализирует игровое поле с минами и призами"""
    global game_counter
    
    game = game_data[user_id]
    
    all_cells = list(range(TOTAL_CELLS))
    
    # Всегда 2 мины
    mines_positions = random.sample(all_cells, 2)
    
    non_mine_cells = [cell for cell in all_cells if cell not in mines_positions]
    # Всегда 2 приза
    prize_positions = random.sample(non_mine_cells, 2)
    
    game["mines"] = set(mines_positions)
    game["prize_cells"] = set(prize_positions)
    game["revealed_cells"] = []
    game["game_active"] = True
    game["current_multiplier"] = 1.0
    game["won_amount"] = 0
    
    # Увеличиваем счетчик игр
    game_counter += 1
    game["game_number"] = game_counter
    
    # Сохраняем информацию об игре для администратора
    games_history[game_counter] = {
        "user_id": user_id,
        "username": user_data.get(user_id, {}).get("username", "Неизвестно"),
        "bet": game["bet"],
        "mines_count": 2,
        "mines": set(mines_positions),
        "prizes": set(prize_positions),
        "status": "Активна",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# Игровой процесс мин
async def play_mines_game(query, user_id):
    """Основной игровой процесс мин"""
    if user_id not in game_data or not game_data[user_id]["game_active"]:
        init_game_field(user_id)
    
    game = game_data[user_id]
    mines_count = game["mines_count"]
    bet = game["bet"]
    multiplier = MULTIPLIERS[mines_count]
    
    keyboard = []
    for row in range(GRID_SIZE):
        row_buttons = []
        for col in range(GRID_SIZE):
            cell_idx = row * GRID_SIZE + col
            if cell_idx in game["revealed_cells"]:
                if cell_idx in game["mines"]:
                    row_buttons.append(InlineKeyboardButton("💥", callback_data=f"cell_opened_{cell_idx}"))
                elif cell_idx in game["prize_cells"]:
                    row_buttons.append(InlineKeyboardButton("🎁", callback_data=f"cell_opened_{cell_idx}"))
                else:
                    row_buttons.append(InlineKeyboardButton("📦", callback_data=f"cell_opened_{cell_idx}"))
            else:
                row_buttons.append(InlineKeyboardButton("⬛", callback_data=f"cell_{cell_idx}"))
        keyboard.append(row_buttons)
    
    cashout_text = f"💰 Забрать {game['won_amount']:.2f}$" if game['won_amount'] > 0 else "💰 Забрать 0$"
    keyboard.append([
        InlineKeyboardButton(cashout_text, callback_data="cashout"),
        InlineKeyboardButton("↩️ Назад", callback_data="game_mines")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    field_text = generate_field_text(user_id)
    
    revealed_mines = len([c for c in game["revealed_cells"] if c in game["mines"]])
    
    game_text = f"""
{get_premium_emoji('mine')} <b>Мины · 2 мины</b>
<u>Номер игры:</u> #{game['game_number']}

{get_premium_emoji('bet')} Ставка {bet:.2f}$ x{game['current_multiplier']:.2f} ➡️ {get_premium_emoji('win')} Выигрыш {game['won_amount']:.2f}$

{field_text}

{get_premium_emoji('multiplier')} Текущий множитель: {game['current_multiplier']:.2f}x
{get_premium_emoji('multiplier')} Максимальный множитель: {multiplier}x
{get_premium_emoji('mine')} Осталось мин: {2 - revealed_mines}
    """
    
    await query.edit_message_text(
        text=game_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Генерация текста игрового поля
def generate_field_text(user_id):
    """Генерирует текстовое представление игрового поля"""
    game = game_data[user_id]
    revealed = set(game["revealed_cells"])
    mines = game["mines"]
    prizes = game["prize_cells"]
    
    field_text = ""
    for row in range(GRID_SIZE):
        row_text = ""
        for col in range(GRID_SIZE):
            cell_idx = row * GRID_SIZE + col
            
            if cell_idx in revealed:
                if cell_idx in mines:
                    row_text += "💥"
                elif cell_idx in prizes:
                    row_text += "🎁"
                else:
                    row_text += "📦"
            else:
                row_text += "⬛"
        
        field_text += row_text + "\n"
    
    return field_text

# Обработка нажатия на ячейку
async def handle_cell_click(query, user_id, cell_idx):
    """Обрабатывает нажатие на ячейку"""
    game = game_data[user_id]
    
    if cell_idx in game["revealed_cells"]:
        await query.answer("Эта ячейка уже открыта!")
        return
    
    game["revealed_cells"].append(cell_idx)
    
    if cell_idx in game["mines"]:
        game["game_active"] = False
        games_history[game["game_number"]]["status"] = "Проиграл"
        await end_game(query, user_id, win=False)
        return
    
    game["current_multiplier"] *= 1.12
    game["won_amount"] = game["bet"] * game["current_multiplier"]
    
    await play_mines_game(query, user_id)

# Завершение игры
async def end_game(query, user_id, win=True):
    """Завершает игру"""
    game = game_data[user_id]
    
    # Добавляем цитату
    quote = random.choice(LUCKY_QUOTES_HTML) if win else random.choice(UNLUCKY_QUOTES_HTML)
    
    if win:
        win_amount = game["won_amount"]
        user_data[user_id]["balance"] += win_amount
        games_history[game["game_number"]]["status"] = "Выиграл"
        
        # Клавиатура с обычными эмодзи
        keyboard = [
            [InlineKeyboardButton("🔄 Играть снова", callback_data="start_mines_game")],
            [InlineKeyboardButton("↩️ Назад в меню", callback_data="game_mines")]
        ]
        
        end_text = f"""
{get_premium_emoji('win')} <b>Поздравляем! Вы выиграли!</b>
<u>Номер игры:</u> #{game['game_number']}

{get_premium_emoji('fire')} Вы успешно собрали {win_amount:.2f}$!

{quote}

{get_premium_emoji('balance')} Ваш выигрыш добавлен на баланс.
{get_premium_emoji('money')} Новый баланс: {user_data[user_id]['balance']:.2f}$
        """
    else:
        user_data[user_id]["balance"] -= game["bet"]
        games_history[game["game_number"]]["status"] = "Проиграл"
        
        # Клавиатура с обычными эмодзи
        keyboard = [
            [InlineKeyboardButton("🔄 Играть снова", callback_data="start_mines_game")],
            [InlineKeyboardButton("↩️ Назад в меню", callback_data="game_mines")]
        ]
        
        end_text = f"""
{get_premium_emoji('lose')} <b>Игра окончена</b>
<u>Номер игры:</u> #{game['game_number']}

{get_premium_emoji('mine')} Вы наткнулись на мину!

{quote}

{get_premium_emoji('withdraw')} Ставка {game['bet']:.2f}$ не возвращается.
{get_premium_emoji('balance')} Новый баланс: {user_data[user_id]['balance']:.2f}$
        """
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    game["game_active"] = False
    
    await query.edit_message_text(
        text=end_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Обналичивание
async def handle_cashout(query, user_id):
    """Обрабатывает обналичивание выигрыша"""
    game = game_data[user_id]
    
    if not game["game_active"] or game["won_amount"] == 0:
        await query.answer("Нечего забирать!")
        return
    
    win_amount = game["won_amount"]
    user_data[user_id]["balance"] += win_amount
    game["game_active"] = False
    games_history[game["game_number"]]["status"] = "Забрал выигрыш"
    
    # Добавляем цитату
    quote = random.choice(LUCKY_QUOTES_HTML)
    
    # Клавиатура с обычными эмодзи
    keyboard = [
        [InlineKeyboardButton("🔄 Играть снова", callback_data="start_mines_game")],
        [InlineKeyboardButton("↩️ Назад в меню", callback_data="game_mines")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    cashout_text = f"""
{get_premium_emoji('win')} <b>Вы успешно забрали выигрыш!</b>
<u>Номер игры:</u> #{game['game_number']}

{get_premium_emoji('money')} Вы забрали: {win_amount:.2f}$
{get_premium_emoji('balance')} Ваш новый баланс: {user_data[user_id]['balance']:.2f}$

{quote}

{get_premium_emoji('fire')} Поздравляем с выигрышем!
    """
    
    await query.edit_message_text(
        text=cashout_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Изменение ставки
async def change_bet(query, user_id):
    """Изменение ставки"""
    balance = user_data[user_id]["balance"]
    current_bet = game_data[user_id]["bet"] if user_id in game_data and "bet" in game_data[user_id] else MIN_BET
    
    saved_bet = user_bets.get(user_id, None)
    saved_bet_info = f"\n{get_premium_emoji('history')} Сохраненная ставка: {saved_bet:.2f}$" if saved_bet else ""
    
    keyboard = []
    bet_options = [0.1, 0.5, 1, 5, 10, 25, 50, 100]
    
    row = []
    for bet in bet_options:
        if bet <= balance:
            button_text = f"{bet:.1f}$"
            if saved_bet and abs(bet - saved_bet) < 0.01:
                button_text = f"💾{bet:.1f}$"
            row.append(InlineKeyboardButton(button_text, callback_data=f"set_bet_{bet}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="game_mines")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"{get_premium_emoji('bet')} <b>Выберите ставку</b>{saved_bet_info}\n\n"
             f"Текущая ставка: {current_bet:.2f}$\n"
             f"Ваш баланс: {balance:.2f}$\n\n"
             f"<i>В игре всегда 2 мины с множителем 1.12x</i>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# Основная функция
def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("givemoney", givemoney))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("delbalance", delbalance))
    
    # Команды для баланса и переводов
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("bal", balance_command))
    application.add_handler(CommandHandler("b", balance_command))
    
    application.add_handler(CommandHandler("pay", pay_command))
    application.add_handler(CommandHandler("transfer", pay_command))
    application.add_handler(CommandHandler("send", pay_command))
    
    # Регистрируем команды для быстрых ставок в кубы (русские)
    application.add_handler(CommandHandler("chet", dice_even_command))
    application.add_handler(CommandHandler("nechet", dice_odd_command))
    application.add_handler(CommandHandler("number", dice_number_command))
    application.add_handler(CommandHandler("more", dice_high_command))
    application.add_handler(CommandHandler("less", dice_low_command))
    
    # Английские команды для совместимости
    application.add_handler(CommandHandler("even", dice_even_command))
    application.add_handler(CommandHandler("odd", dice_odd_command))
    application.add_handler(CommandHandler("high", dice_high_command))
    application.add_handler(CommandHandler("low", dice_low_command))
    
    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
    
    print("=" * 50)
    print("Бот запущен...")
    print("=" * 50)
    print(f"Администратор: {ADMIN_ID} ({ADMIN_USERNAME})")
    print(f"💰 Казино: Stake Casino {get_premium_emoji('vip')}")
    print("\n📊 Команды баланса:")
    print("• /balance / /bal / /b - показать баланс")
    print("• /pay сумма - перевести другу (ответом на сообщение)")
    print("• /pay ID сумма - перевести по ID пользователя")
    print(f"• Пополнение: от {MIN_DEPOSIT:.2f}$ через {ADMIN_USERNAME}")
    print(f"• Вывод: от {MIN_WITHDRAWAL:.2f}$ через {ADMIN_USERNAME}")
    print("\n🎮 Игры:")
    print("• Напишите 'мины' - игра в мины (2 мины, x1.12)")
    print("• Напишите 'кубы' - игра в кубы (анимированные кубики)")
    print("\n🎲 Быстрые ставки в Кубы:")
    print("• /chet сумма - ставка на чет (2,4,6) - x2")
    print("• /nechet сумма - ставка на нечет (1,3,5) - x2")
    print("• /number число сумма - ставка на число (1-6) - x6")
    print("• /more сумма - ставка на больше (4-6) - x2")
    print("• /less сумма - ставка на меньше (1-3) - x2")
    print("\n⚙️ Для админа:")
    print("• /givemoney ID сумма - выдать баланс")
    print("• /delbalance ID сумма - снять баланс")
    print("• /game mines номер - просмотр информации об игре")
    print("=" * 50)
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
