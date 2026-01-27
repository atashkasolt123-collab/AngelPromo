import logging
import random
import re
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Dice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8470278896:AAH5ALI5_TkogpE7neCD0mmF0oGAwSDR2hU"
ADMIN_ID = 7313407194
ADMIN_USERNAME = "@qqlittle"

# Минимальные суммы ($)
MIN_DEPOSIT = 0.1
MIN_WITHDRAWAL = 3
MIN_TRANSFER = 0.1
MIN_BET = 0.1
INITIAL_BALANCE = 0.0

# Настройки игры
GRID_SIZE = 5
TOTAL_CELLS = 25
MINES_COUNT = 2
MINES_MULTIPLIER = 1.12

# Множители для кубов
DICE_MULTIPLIERS = {"even_odd": 2.0, "number": 6.0, "high_low": 2.0}

# Хранилища данных
user_data: Dict[int, Dict] = {}
game_data: Dict[int, Dict] = {}
user_bets: Dict[int, float] = {}
games_history: Dict[int, Dict] = {}
game_counter = 0

# ПРЕМИУМ ЭМОДЗИ В HTML (только для текста)
PREMIUM_EMOJIS = {
    "casino": '<tg-emoji emoji-id="5969709082049779216">🎰</tg-emoji>',
    "vip": '<tg-emoji emoji-id="5375757817856875637">👑</tg-emoji>',
    "fire": '<tg-emoji emoji-id="5445124005604368288">🔥</tg-emoji>',
    "balance": '<tg-emoji emoji-id="5262509177363787445">💰</tg-emoji>',
    "win": '<tg-emoji emoji-id="5436386989857320953">🏆</tg-emoji>',
    "lose": '<tg-emoji emoji-id="4979035365823219688">💥</tg-emoji>',
    "dice": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "transfer": '<tg-emoji emoji-id="5377720025811555309">🔄</tg-emoji>',
    "deposit": '<tg-emoji emoji-id="5902056028513505203">💳</tg-emoji>',
    "withdraw": '<tg-emoji emoji-id="5226731292334235524">💸</tg-emoji>',
    "game": '<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji>',
    "mine": '<tg-emoji emoji-id="4979035365823219688">💣</tg-emoji>',
    "trophy": '<tg-emoji emoji-id="5375250732074737684">🏅</tg-emoji>',
    "money": '<tg-emoji emoji-id="5226731292334235524">💵</tg-emoji>',
    "user": '<tg-emoji emoji-id="5168063997575956782">👤</tg-emoji>',
    "stats": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5377336433692412420">🛸</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5375469677696815127">⚡</tg-emoji>',
    "star": '<tg-emoji emoji-id="5258463921982341676">⭐</tg-emoji>',
    "gem": '<tg-emoji emoji-id="5447170525969141923">💎</tg-emoji>',
    "coin": '<tg-emoji emoji-id="5375256698515358018">🪙</tg-emoji>',
    "medal": '<tg-emoji emoji-id="5258465977430624493">🎖️</tg-emoji>',
    "bank": '<tg-emoji emoji-id="5447203209511766728">🏦</tg-emoji>',
    "secure": '<tg-emoji emoji-id="5258418885282670157">🔒</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5323761960829862762">🎁</tg-emoji>',
    "flag": '<tg-emoji emoji-id="5447165412033893131">🏁</tg-emoji>',
    "target": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "luck": '<tg-emoji emoji-id="5377386804699168823">🍀</tg-emoji>',
    "jackpot": '<tg-emoji emoji-id="5262509177363787445">💰</tg-emoji>',
    "dollar": '<tg-emoji emoji-id="5377852667286559564">💲</tg-emoji>',
    "time": '<tg-emoji emoji-id="5258419835922030550">🕒</tg-emoji>',
    "info": '<tg-emoji emoji-id="5258334872878980409">ℹ️</tg-emoji>',
    "multiplier": '<tg-emoji emoji-id="5201691993775818138">📈</tg-emoji>',
    "history": '<tg-emoji emoji-id="5353025608832004653">📋</tg-emoji>',
    "prize": '<tg-emoji emoji-id="5323761960829862762">🎁</tg-emoji>',
    "bet": '<tg-emoji emoji-id="5893048571560726748">🎯</tg-emoji>',
    "min": '<tg-emoji emoji-id="5447183459602669338">📌</tg-emoji>',
}

def emoji(name):
    """Возвращает премиум эмодзи в HTML формате (только для текста)"""
    return PREMIUM_EMOJIS.get(name, '<tg-emoji emoji-id="5377336433692412420">🛸</tg-emoji>')

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE,
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play_menu")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton("💸 Вывод", callback_data="withdraw_menu")],
        [InlineKeyboardButton("💳 Пополнение", callback_data="deposit")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('casino')} <b>Добро пожаловать в Stake Casino!</b> {emoji('vip')}

{emoji('fire')} <b>Премьем казино с эксклюзивными эмодзи!</b>

{emoji('balance')} <b>Ваш баланс:</b> {user_data[user_id]['balance']:.2f}$ {emoji('dollar')}

<u>{emoji('info')} Быстрые команды:</u>
• <code>/balance</code> - баланс
• <code>/pay сумма</code> - перевод
• напишите <b>мины</b> - игра в мины {emoji('mine')}
• напишите <b>кубы</b> - игра в кубы {emoji('dice')}

{emoji('star')} <b>Особенности:</b>
• Премьем эмодзи во всех сообщениях
• Мгновенные выплаты
• Поддержка 24/7 {emoji('time')}
"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE,
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    balance = user_data[user_id]["balance"]
    total_deposits = sum(d["amount"] for d in user_data[user_id].get("deposits", []))
    total_withdrawals = sum(w["amount"] for w in user_data[user_id].get("withdrawals", []))
    
    saved_bet = user_bets.get(user_id)
    bet_info = f"\n{emoji('history')} <b>Сохраненная ставка:</b> {saved_bet:.2f}$" if saved_bet else ""
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("💸 Вывести", callback_data="withdraw_menu")],
        [InlineKeyboardButton("🎮 Игры", callback_data="play_menu")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('balance')} <b>ВАШ БАЛАНС</b> {emoji('jackpot')}

{emoji('money')} <b>Текущий баланс:</b> {balance:.2f}$ {emoji('dollar')}{bet_info}

{emoji('stats')} <u>СТАТИСТИКА:</u>
{emoji('deposit')} Всего пополнено: <b>{total_deposits:.2f}$</b>
{emoji('withdraw')} Всего выведено: <b>{total_withdrawals:.2f}$</b>
{emoji('gem')} Чистая прибыль: <b>{(total_deposits - total_withdrawals):.2f}$</b>

{emoji('min')} <u>МИНИМАЛЬНЫЕ СУММЫ:</u>
🎯 Ставка в играх: {MIN_BET:.2f}$
🔄 Переводы: {MIN_TRANSFER:.2f}$
💳 Пополнение: от {MIN_DEPOSIT:.2f}$
💸 Вывод: от {MIN_WITHDRAWAL:.2f}$

{emoji('bank')} <b>Ваши средства в безопасности!</b> {emoji('secure')}
"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE,
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    reply_to = update.message.reply_to_message
    if reply_to:
        target_user = reply_to.from_user
        if target_user.id == user_id:
            await update.message.reply_text(f"{emoji('lose')} Нельзя переводить самому себе!")
            return
        if not context.args:
            await update.message.reply_text(f"{emoji('info')} Используйте: /pay сумма")
            return
        try:
            amount = float(context.args[0])
        except:
            await update.message.reply_text(f"{emoji('lose')} Неверная сумма!")
            return
        target_id = target_user.id
        target_username = target_user.username or target_user.first_name
    else:
        if len(context.args) < 2:
            await update.message.reply_text(
                f"{emoji('info')} <b>Используйте:</b>\n"
                f"<code>/pay ID_пользователя сумма</code>\n"
                f"Или ответьте на сообщение: <code>/pay сумма</code>",
                parse_mode='HTML'
            )
            return
        try:
            target_id = int(context.args[0])
            amount = float(context.args[1])
        except:
            await update.message.reply_text(f"{emoji('lose')} Неверный формат!")
            return
        if target_id == user_id:
            await update.message.reply_text(f"{emoji('lose')} Нельзя переводить самому себе!")
            return
        target_username = f"пользователь {target_id}"
    
    if amount < MIN_TRANSFER:
        await update.message.reply_text(f"{emoji('min')} Мин. сумма перевода: {MIN_TRANSFER:.2f}$")
        return
    
    if user_data[user_id]["balance"] < amount:
        await update.message.reply_text(f"{emoji('lose')} Недостаточно средств!")
        return
    
    if target_id not in user_data:
        user_data[target_id] = {
            "balance": INITIAL_BALANCE,
            "username": target_username,
            "first_name": target_username,
            "deposits": [],
            "withdrawals": []
        }
    
    user_data[user_id]["balance"] -= amount
    user_data[target_id]["balance"] += amount
    
    text = f"""{emoji('transfer')} <b>ПЕРЕВОД ВЫПОЛНЕН!</b> {emoji('rocket')}

{emoji('user')} <u>ОТПРАВИТЕЛЬ:</u>
👤 <b>{user_data[user_id]['username']}</b> (ID: {user_id})
💸 Списано: <b>{amount:.2f}$</b>
💰 Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{emoji('user')} <u>ПОЛУЧАТЕЛЬ:</u>
👤 <b>{target_username}</b> (ID: {target_id})
🎁 Получено: <b>{amount:.2f}$</b>
💰 Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

{emoji('time')} <b>Перевод мгновенный!</b> {emoji('lightning')}
"""
    
    await update.message.reply_text(text, parse_mode='HTML')
    
    # Уведомление получателю
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"""{emoji('gift')} <b>ВАМ ПОСТУПИЛ ПЕРЕВОД!</b> {emoji('fire')}

👤 От: <b>{user_data[user_id]['username']}</b>
💵 Сумма: <b>{amount:.2f}$</b>
💰 Ваш баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

{emoji('star')} Спасибо за использование нашего казино! {emoji('casino')}""",
            parse_mode='HTML'
        )
    except:
        pass

# ==================== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ====================

async def givemoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{emoji('lose')} Только для администратора! {emoji('secure')}")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{emoji('info')} <b>Используйте:</b>\n"
            f"<code>/givemoney ID_пользователя сумма</code>\n"
            f"Пример: <code>/givemoney 123456789 100</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text(f"{emoji('lose')} Сумма должна быть больше 0! {emoji('min')}")
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
        
        deposit_record = {
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin_id": user_id,
            "type": "администратор"
        }
        user_data[target_id]["deposits"].append(deposit_record)
        
        text = f"""{emoji('deposit')} <b>БАЛАНС ПОПОЛНЕН!</b> {emoji('fire')}

{emoji('user')} Пользователь: <code>{target_id}</code>
{emoji('money')} Сумма: <b>{amount:.2f}$</b>
{emoji('balance')} Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

{emoji('time')} Операция выполнена: {datetime.now().strftime('%H:%M:%S')}"""
        
        await update.message.reply_text(text, parse_mode='HTML')
        
        # Уведомление пользователю
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""{emoji('gift')} <b>ВАШ БАЛАНС ПОПОЛНЕН!</b> {emoji('star')}

💵 Сумма: <b>{amount:.2f}$</b>
👤 Администратор: {user_data[user_id]['username']}
💰 Ваш баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

🎰 Удачи в играх! 🎲""",
                parse_mode='HTML'
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text(f"{emoji('lose')} Неверный формат ID или суммы!")

async def delmoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{emoji('lose')} Только для администратора! {emoji('secure')}")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{emoji('info')} <b>Используйте:</b>\n"
            f"<code>/delmoney ID_пользователя сумма</code>\n"
            f"Пример: <code>/delmoney 123456789 100</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text(f"{emoji('lose')} Сумма должна быть больше 0! {emoji('min')}")
            return
        
        if target_id not in user_data:
            await update.message.reply_text(f"{emoji('lose')} Пользователь не найден! {emoji('user')}")
            return
        
        if user_data[target_id]["balance"] < amount:
            await update.message.reply_text(
                f"{emoji('lose')} Недостаточно средств у пользователя!\n"
                f"💰 Баланс: {user_data[target_id]['balance']:.2f}$\n"
                f"💸 Списание: {amount:.2f}$",
                parse_mode='HTML'
            )
            return
        
        user_data[target_id]["balance"] -= amount
        
        text = f"""{emoji('withdraw')} <b>БАЛАНС СПИСАН!</b> {emoji('lose')}

{emoji('user')} Пользователь: <code>{target_id}</code>
{emoji('money')} Сумма: <b>{amount:.2f}$</b>
{emoji('balance')} Новый баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

{emoji('time')} Операция выполнена: {datetime.now().strftime('%H:%M:%S')}"""
        
        await update.message.reply_text(text, parse_mode='HTML')
        
        # Уведомление пользователю
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"""{emoji('lose')} <b>С ВАШЕГО БАЛАНСА СПИСАНЫ СРЕДСТВА</b>

💸 Сумма: <b>{amount:.2f}$</b>
👤 Администратор: {user_data[user_id]['username']}
💰 Ваш баланс: <b>{user_data[target_id]['balance']:.2f}$</b>

ℹ️ По всем вопросам обращайтесь к администратору.""",
                parse_mode='HTML'
            )
        except:
            pass
            
    except ValueError:
        await update.message.reply_text(f"{emoji('lose')} Неверный формат ID или суммы!")

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text(f"{emoji('lose')} Только для администратора! {emoji('secure')}")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            f"{emoji('info')} <b>Используйте:</b>\n"
            f"<code>/game mines номер_игры</code>\n"
            f"Пример: <code>/game mines 1</code>\n\n"
            f"{emoji('history')} Всего игр: <b>{game_counter}</b>",
            parse_mode='HTML'
        )
        return
    
    game_type = context.args[0].lower()
    try:
        game_num = int(context.args[1])
    except ValueError:
        await update.message.reply_text(f"{emoji('lose')} Неверный номер игры!")
        return
    
    if game_type != "mines":
        await update.message.reply_text(f"{emoji('lose')} Только 'mines' доступны!")
        return
    
    if game_num not in games_history:
        await update.message.reply_text(f"{emoji('lose')} Игра №{game_num} не найдена!")
        return
    
    game_info = games_history[game_num]
    
    # Генерация поля
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
    
    # Координаты мин
    mine_positions = []
    for idx in sorted(game_info["mines"]):
        row = idx // GRID_SIZE + 1
        col = idx % GRID_SIZE + 1
        mine_positions.append(f"({row},{col})")
    
    game_details = f"""{emoji('game')} <b>ИНФОРМАЦИЯ ОБ ИГРЕ</b> {emoji('history')}

{emoji('user')} <b>Игрок:</b> {game_info['user_id']} ({game_info.get('username', 'Неизвестно')})
{emoji('money')} <b>Ставка:</b> {game_info['bet']:.2f}$
{emoji('mine')} <b>Количество мин:</b> {len(game_info['mines'])}
{emoji('stats')} <b>Статус:</b> {game_info.get('status', 'Завершена')}
{emoji('time')} <b>Время:</b> {game_info.get('time', 'Неизвестно')}

🎮 <u>ИГРОВОЕ ПОЛЕ:</u>
{field_text}

💣 <u>ПОЗИЦИИ МИН (ряд,столбец):</u>
{', '.join(mine_positions)}

ℹ️ <u>ИНДЕКСЫ МИН (0-24):</u>
{', '.join(map(str, sorted(game_info['mines'])))}
"""
    
    await update.message.reply_text(game_details, parse_mode='HTML')

# ==================== ИГРЫ ====================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()
    
    if text == "мины":
        await start_mines(update, user_id)
    elif text in ["кубы", "кости"]:
        await start_dice(update, user_id)
    elif re.search(r'(\d+\.?\d*)\s*\$', text):
        match = re.search(r'(\d+\.?\d*)\s*\$', text)
        amount = float(match.group(1))
        if amount >= MIN_BET:
            user_bets[user_id] = amount
            await update.message.reply_text(f"{emoji('bet')} <b>Ставка сохранена:</b> {amount:.2f}$")
        else:
            await update.message.reply_text(f"{emoji('min')} Мин. ставка: {MIN_BET:.2f}$")

async def start_mines(update, user_id):
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
        await update.message.reply_text(f"{emoji('lose')} Недостаточно средств! 📌 Мин. ставка: {MIN_BET:.2f}$")
        return
    
    saved_bet = user_bets.get(user_id, MIN_BET)
    if saved_bet > balance:
        saved_bet = MIN_BET
    
    game_data[user_id] = {
        "bet": saved_bet,
        "revealed": [],
        "active": False,
        "multiplier": 1.0,
        "prizes": set(),
        "mines": set(),
        "won": 0
    }
    
    potential = saved_bet * MINES_MULTIPLIER
    bet_source = f"💾" if user_bets.get(user_id) and saved_bet == user_bets[user_id] else ""
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(f"🎯 Ставка: {saved_bet:.2f}$", callback_data="change_bet"), InlineKeyboardButton("💣 Мины: 2", callback_data="mines_info")],
        [InlineKeyboardButton(f"▶️ Играть ({MINES_MULTIPLIER}x)", callback_data="start_mines_game")],
        [InlineKeyboardButton("↩️ Меню", callback_data="back_to_main")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('mine')} <b>ИГРА В МИНЫ</b> {emoji('game')}

{emoji('user')} Игрок: {update.effective_user.username or update.effective_user.first_name}
{emoji('balance')} Баланс: <b>{balance:.2f}$</b>
{emoji('bet')} Ставка: <b>{saved_bet:.2f}$</b> {bet_source}
{emoji('mine')} Количество мин: <b>2</b>
{emoji('multiplier')} Множитель: <b>{MINES_MULTIPLIER}x</b>
{emoji('win')} Потенциальный выигрыш: <b>{potential:.2f}$</b>"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def start_dice(update, user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE,
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("🎲 Чет/Нечет", callback_data="dice_even_odd"), InlineKeyboardButton("🎯 Число", callback_data="dice_number")],
        [InlineKeyboardButton("⚖️ Больше/Меньше", callback_data="dice_high_low"), InlineKeyboardButton("↩️ Меню", callback_data="play_menu")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('dice')} <b>ИГРА В КУБЫ</b> {emoji('game')}

{emoji('dice')} <b>Чет/Нечет</b> - x{DICE_MULTIPLIERS['even_odd']}
• Чет (2,4,6) или Нечет (1,3,5)

{emoji('target')} <b>Угадать число</b> - x{DICE_MULTIPLIERS['number']}
• Угадать выпавшее число (1-6)

⚖️ <b>Больше/Меньше</b> - x{DICE_MULTIPLIERS['high_low']}
• Больше (4-6) или Меньше (1-3)

{emoji('rules')} <u>Быстрые команды:</u>
• <code>/chet сумма</code> - чет (2,4,6)
• <code>/nechet сумма</code> - нечет (1,3,5)
• <code>/number число сумма</code> - угадать число
• <code>/more сумма</code> - больше (4-6)
• <code>/less сумма</code> - меньше (1-3)"""
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== МЕНЮ ====================

async def play_menu(query, user_id):
    saved_bet = user_bets.get(user_id)
    bet_info = f"\n{emoji('history')} <b>Ваша ставка:</b> {saved_bet:.2f}$" if saved_bet else ""
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("💣 Мины (2 мины)", callback_data="game_mines")],
        [InlineKeyboardButton("🎲 Кубы", callback_data="game_dice")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('game')} <b>ВЫБЕРИТЕ ИГРУ</b>{bet_info}

{emoji('mine')} <b>МИНЫ</b>
• Фиксировано 2 мины на поле 5x5
• Множитель: {MINES_MULTIPLIER}x
• Стратегическая игра на удачу

{emoji('dice')} <b>КУБЫ</b>
• Несколько режимов игры
• Множители до 6x
• Быстрые результаты

{emoji('lightning')} <b>Быстрый старт:</b>
Напишите в чат <b>мины</b> или <b>кубы</b>"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def deposit_menu(query, user_id):
    balance = user_data[user_id]["balance"]
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(f"📞 Связаться с {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME[1:]}")],
        [InlineKeyboardButton("↩️ Назад", callback_data="balance")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('deposit')} <b>ПОПОЛНЕНИЕ БАЛАНСА</b> {emoji('bank')}

{emoji('balance')} Текущий баланс: <b>{balance:.2f}$</b>

{emoji('min')} <u>ТРЕБОВАНИЯ:</u>
• Мин. сумма: <b>{MIN_DEPOSIT:.2f}$</b>
• Пополнение через: {ADMIN_USERNAME}

{emoji('rules')} <u>ИНСТРУКЦИЯ:</u>
1. Нажмите кнопку ниже для связи
2. Укажите ваш ID: <code>{user_id}</code>
3. Укажите желаемую сумму
4. Дождитесь подтверждения

{emoji('time')} Пополнение происходит за 5-15 минут

{emoji('secure')} <b>Ваши средства защищены!</b>"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def withdraw_menu(query, user_id):
    balance = user_data[user_id]["balance"]
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(f"📞 Связаться с {ADMIN_USERNAME}", url=f"https://t.me/{ADMIN_USERNAME[1:]}")],
        [InlineKeyboardButton("↩️ Назад", callback_data="balance")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('withdraw')} <b>ВЫВОД СРЕДСТВ</b> {emoji('money')}

{emoji('balance')} Текущий баланс: <b>{balance:.2f}$</b>

{emoji('min')} <u>ТРЕБОВАНИЯ:</u>
• Мин. сумма: <b>{MIN_WITHDRAWAL:.2f}$</b>
• Вывод через: {ADMIN_USERNAME}

{emoji('rules')} <u>ИНСТРУКЦИЯ:</u>
1. Нажмите кнопку ниже для связи
2. Укажите ваш ID: <code>{user_id}</code>
3. Укажите сумму (от {MIN_WITHDRAWAL:.2f}$)
4. Укажите реквизиты
5. Дождитесь получения

{emoji('time')} Вывод происходит за 5-30 минут

ℹ️ Средства выводятся на карты РФ или другие способы"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ОБРАБОТЧИК КНОПОК ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    
    data = query.data
    
    if data == "play_menu":
        await play_menu(query, user_id)
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "deposit":
        await deposit_menu(query, user_id)
    elif data == "withdraw_menu":
        await withdraw_menu(query, user_id)
    elif data == "back_to_main":
        # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
        keyboard = [
            [InlineKeyboardButton("🎮 Играть", callback_data="play_menu")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton("💸 Вывод", callback_data="withdraw_menu")],
            [InlineKeyboardButton("💳 Пополнение", callback_data="deposit")]
        ]
        # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
        text = f"""{emoji('casino')} <b>STAKE CASINO</b> {emoji('vip')}

{emoji('fire')} Добро пожаловать в лучшее казино!

Используйте кнопки ниже или команды:
• <code>/balance</code> - баланс
• <code>/pay сумма</code> - перевод
• напишите <b>мины</b> - игра в мины
• напишите <b>кубы</b> - игра в кубы

{emoji('star')} Эксклюзивные премиум эмодзи!
{emoji('lightning')} Мгновенные выплаты!
{emoji('secure')} Полная безопасность!"""
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "game_mines":
        await mines_setup(query, user_id)
    elif data == "game_dice":
        await dice_menu(query, user_id)
    elif data == "start_mines_game":
        if user_data[user_id]["balance"] < game_data[user_id]["bet"]:
            await query.answer("❌ Недостаточно средств!")
            return
        await play_mines(query, user_id)

async def show_balance(query, user_id):
    balance = user_data[user_id]["balance"]
    total_deposits = sum(d["amount"] for d in user_data[user_id].get("deposits", []))
    total_withdrawals = sum(w["amount"] for w in user_data[user_id].get("withdrawals", []))
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("💳 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("💸 Вывести", callback_data="withdraw_menu")],
        [InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('balance')} <b>ВАШ БАЛАНС</b> {emoji('jackpot')}

{emoji('money')} Текущий баланс: <b>{balance:.2f}$</b>

{emoji('stats')} <u>СТАТИСТИКА:</u>
💳 Всего пополнено: <b>{total_deposits:.2f}$</b>
💸 Всего выведено: <b>{total_withdrawals:.2f}$</b>
💎 Чистая прибыль: <b>{(total_deposits - total_withdrawals):.2f}$</b>

🎖️ Удачи в играх!"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def mines_setup(query, user_id):
    balance = user_data[user_id]["balance"]
    saved_bet = user_bets.get(user_id, MIN_BET)
    if saved_bet > balance:
        saved_bet = MIN_BET
    
    if user_id not in game_data:
        game_data[user_id] = {"bet": saved_bet, "revealed": [], "active": False, "multiplier": 1.0, "prizes": set(), "mines": set(), "won": 0}
    else:
        game_data[user_id]["bet"] = saved_bet
    
    potential = saved_bet * MINES_MULTIPLIER
    
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(f"🎯 Ставка: {saved_bet:.2f}$", callback_data="change_bet"), InlineKeyboardButton("ℹ️ Инфо", callback_data="mines_info")],
        [InlineKeyboardButton(f"▶️ Играть ({MINES_MULTIPLIER}x)", callback_data="start_mines_game")],
        [InlineKeyboardButton("↩️ Назад", callback_data="play_menu")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('mine')} <b>МИНЫ</b> {emoji('game')}

💰 Баланс: {balance:.2f}$
🎯 Ставка: {saved_bet:.2f}$
💣 Количество мин: 2
📈 Множитель: {MINES_MULTIPLIER}x
🏆 Потенциальный выигрыш: {potential:.2f}$"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def dice_menu(query, user_id):
    # КЛАВИАТУРА С ОБЫЧНЫМИ ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton("🎲 Чет/Нечет", callback_data="dice_even_odd"), InlineKeyboardButton("🎯 Число", callback_data="dice_number")],
        [InlineKeyboardButton("⚖️ Больше/Меньше", callback_data="dice_high_low"), InlineKeyboardButton("↩️ Назад", callback_data="play_menu")]
    ]
    
    # ТЕКСТ С ПРЕМИУМ ЭМОДЗИ
    text = f"""{emoji('dice')} <b>КУБЫ</b> {emoji('game')}

Выберите тип ставки:

🎲 <b>Чет/Нечет</b>
• Чет (2,4,6): x{DICE_MULTIPLIERS['even_odd']}
• Нечет (1,3,5): x{DICE_MULTIPLIERS['even_odd']}

🎯 <b>Число</b>
• Угадать число (1-6): x{DICE_MULTIPLIERS['number']}

⚖️ <b>Больше/Меньше</b>
• Больше (4-6): x{DICE_MULTIPLIERS['high_low']}
• Меньше (1-3): x{DICE_MULTIPLIERS['high_low']}"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ИГРА МИНЫ ====================

async def play_mines(query, user_id):
    global game_counter
    
    game = game_data[user_id]
    if not game["active"]:
        all_cells = list(range(TOTAL_CELLS))
        mines = random.sample(all_cells, MINES_COUNT)
        prizes = random.sample([c for c in all_cells if c not in mines], MINES_COUNT)
        game["mines"] = set(mines)
        game["prizes"] = set(prizes)
        game["revealed"] = []
        game["active"] = True
        game["multiplier"] = 1.0
        game["won"] = 0
        game_counter += 1
        game["game_number"] = game_counter
        
        # Сохраняем в историю
        games_history[game_counter] = {
            "user_id": user_id,
            "username": user_data[user_id]["username"],
            "bet": game["bet"],
            "mines": set(mines),
            "prizes": set(prizes),
            "status": "Активна",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # Генерация клавиатуры поля с обычными эмодзи
    keyboard = []
    for row in range(GRID_SIZE):
        row_buttons = []
        for col in range(GRID_SIZE):
            idx = row * GRID_SIZE + col
            if idx in game["revealed"]:
                if idx in game["mines"]:
                    row_buttons.append(InlineKeyboardButton("💥", callback_data=f"cell_opened_{idx}"))
                elif idx in game["prizes"]:
                    row_buttons.append(InlineKeyboardButton("🎁", callback_data=f"cell_opened_{idx}"))
                else:
                    row_buttons.append(InlineKeyboardButton("📦", callback_data=f"cell_opened_{idx}"))
            else:
                row_buttons.append(InlineKeyboardButton("⬛", callback_data=f"cell_{idx}"))
        keyboard.append(row_buttons)
    
    cashout_text = f"💰 Забрать {game['won']:.2f}$" if game['won'] > 0 else f"💰 Забрать 0$"
    keyboard.append([InlineKeyboardButton(cashout_text, callback_data="cashout"), InlineKeyboardButton("↩️ Назад", callback_data="game_mines")])
    
    # Текст с премиум эмодзи
    text = f"""{emoji('mine')} <b>МИНЫ · 2 МИНЫ</b> {emoji('game')}

🎯 Ставка {game['bet']:.2f}$ x{game['multiplier']:.2f} ➡️ {emoji('win')} Выигрыш {game['won']:.2f}$

📈 Текущий множитель: {game['multiplier']:.2f}x
💣 Осталось мин: {MINES_COUNT - len([c for c in game['revealed'] if c in game['mines']])}"""
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== КОМАНДЫ КУБОВ ====================

async def process_dice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, bet_type: str, number: int = None):
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": INITIAL_BALANCE,
            "username": update.effective_user.username or update.effective_user.first_name,
            "first_name": update.effective_user.first_name,
            "deposits": [],
            "withdrawals": []
        }
    
    if not context.args:
        await update.message.reply_text(f"{emoji('info')} Укажите сумму! Например: /{bet_type} 10")
        return
    
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text(f"{emoji('lose')} Неверная сумма!")
        return
    
    if amount < MIN_BET:
        await update.message.reply_text(f"{emoji('min')} Мин. ставка: {MIN_BET:.2f}$")
        return
    
    if user_data[user_id]["balance"] < amount:
        await update.message.reply_text(f"{emoji('lose')} Недостаточно средств!")
        return
    
    # Бросок куба
    dice_msg = await update.message.reply_dice(emoji="🎲")
    await asyncio.sleep(2)
    result = dice_msg.dice.value
    
    # Определение выигрыша
    win = False
    multiplier = 1.0
    bet_name = ""
    
    if bet_type == "even":
        bet_name = "Чет (2,4,6)"
        win = result in [2,4,6]
        multiplier = 2.0
    elif bet_type == "odd":
        bet_name = "Нечет (1,3,5)"
        win = result in [1,3,5]
        multiplier = 2.0
    elif bet_type == "number":
        bet_name = f"Число {number}"
        win = result == number
        multiplier = 6.0
    elif bet_type == "high":
        bet_name = "Больше (4-6)"
        win = result in [4,5,6]
        multiplier = 2.0
    elif bet_type == "low":
        bet_name = "Меньше (1-3)"
        win = result in [1,2,3]
        multiplier = 2.0
    
    if win:
        win_amount = amount * multiplier
        user_data[user_id]["balance"] += win_amount
        text = f"""{emoji('win')} <b>ВЫИГРЫШ!</b> {emoji('fire')}

{emoji('bet')} Ставка: <b>{bet_name}</b>
🎲 Результат: <b>{result}</b>
💵 Сумма: <b>{amount:.2f}$</b>
🏅 Выигрыш: <b>{win_amount:.2f}$</b> (x{multiplier})
💰 Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

{emoji('rocket')} Поздравляем! Удача на вашей стороне!"""
    else:
        user_data[user_id]["balance"] -= amount
        text = f"""{emoji('lose')} <b>ПРОИГРЫШ</b>

{emoji('bet')} Ставка: <b>{bet_name}</b>
🎲 Результат: <b>{result}</b>
💵 Сумма: <b>{amount:.2f}$</b>
💸 Потеряно: <b>{amount:.2f}$</b>
💰 Новый баланс: <b>{user_data[user_id]['balance']:.2f}$</b>

🍀 В следующий раз повезет больше!"""
    
    await update.message.reply_text(text, parse_mode='HTML')

async def process_dice_number_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) != 2:
        await update.message.reply_text(
            f"{emoji('info')} <b>Используйте:</b>\n"
            f"<code>/number число сумма</code>\n"
            f"Пример: <code>/number 3 10</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        number = int(context.args[0])
        amount = float(context.args[1])
        
        if number < 1 or number > 6:
            await update.message.reply_text(f"{emoji('lose')} Число должно быть от 1 до 6!")
            return
        
        await process_dice_bet(update, context, user_id, "number", number)
        
    except ValueError:
        await update.message.reply_text(f"{emoji('lose')} Неверный формат!")

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    
    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("pay", pay_command))
    
    # Административные команды
    app.add_handler(CommandHandler("givemoney", givemoney_command))
    app.add_handler(CommandHandler("delmoney", delmoney_command))
    app.add_handler(CommandHandler("game", game_command))
    
    # Быстрые команды кубов
    app.add_handler(CommandHandler("chet", lambda u,c: process_dice_bet(u,c,u.effective_user.id,"even")))
    app.add_handler(CommandHandler("nechet", lambda u,c: process_dice_bet(u,c,u.effective_user.id,"odd")))
    app.add_handler(CommandHandler("number", process_dice_number_bet))
    app.add_handler(CommandHandler("more", lambda u,c: process_dice_bet(u,c,u.effective_user.id,"high")))
    app.add_handler(CommandHandler("less", lambda u,c: process_dice_bet(u,c,u.effective_user.id,"low")))
    
    # Обработчики
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    print("=" * 60)
    print(f"🤖 БОТ ЗАПУЩЕН!")
    print(f"🔑 Токен: {TOKEN[:15]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"👤 Админ: {ADMIN_USERNAME}")
    print(f"🎰 Казино: Stake Casino 👑")
    print("\n📋 ОСНОВНЫЕ КОМАНДЫ:")
    print("• /start - запуск бота")
    print("• /balance - баланс")
    print("• /pay сумма - перевод")
    print("\n🎮 БЫСТРЫЕ ИГРЫ:")
    print("• Напишите 'мины' - игра в мины")
    print("• Напишите 'кубы' - игра в кубы")
    print("\n🎲 КОМАНДЫ КУБОВ:")
    print("• /chet сумма - ставка на чет (2,4,6)")
    print("• /nechet сумма - ставка на нечет (1,3,5)")
    print("• /number число сумма - угадать число")
    print("• /more сумма - больше (4-6)")
    print("• /less сумма - меньше (1-3)")
    print("\n⚙️ АДМИН КОМАНДЫ:")
    print("• /givemoney ID сумма - выдать баланс")
    print("• /delmoney ID сумма - снять баланс")
    print("• /game mines номер - информация об игре")
    print("=" * 60)
    
    app.run_polling()

if __name__ == '__main__':
    main()
