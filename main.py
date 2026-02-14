import asyncio
import logging
import sqlite3
import random
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, DiceEmoji
import aiohttp

# ==================== ТОКЕНЫ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8216893084:AAFDDMLxgAJy-b5PlyM4fX250w03DH7ioE4")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7313407194"))
CRYPTOPAY_TOKEN = os.getenv("CRYPTOPAY_TOKEN", "531599:AAUMC694mv1R74W7olhV1Z1QpNGymqIXyVo")

# ==================== ПРЕМИУМ ЭМОДЗИ ====================
PREMIUM_EMOJIS = {
    "rocket": {"id": "5377336433692412420", "char": "🚀"},
    "dollar": {"id": "5377852667286559564", "char": "💲"},
    "dice": {"id": "5377346496800786271", "char": "🎯"},
    "transfer": {"id": "5377720025811555309", "char": "🔄"},
    "lightning": {"id": "5375469677696815127", "char": "⚡"},
    "casino": {"id": "5969709082049779216", "char": "🎰"},
    "balance": {"id": "5262509177363787445", "char": "💰"},
    "withdraw": {"id": "5226731292334235524", "char": "💸"},
    "deposit": {"id": "5226731292334235524", "char": "💳"},
}

def premium(name: str) -> str:
    e = PREMIUM_EMOJIS.get(name, PREMIUM_EMOJIS["rocket"])
    return f'<tg-emoji emoji-id="{e["id"]}">{e["char"]}</tg-emoji>'

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self, db_name="game_bot.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.0,
                    bet REAL DEFAULT 0.1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_admin INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mines_games (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    bet REAL,
                    field TEXT,
                    opened_cells TEXT,
                    game_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    invoice_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, is_admin) VALUES (?, ?, ?, ?)",
                          (ADMIN_ID, "admin", "Admin", 1))
            cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (ADMIN_ID,))
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "balance": row[3],
                    "bet": row[4],
                    "created_at": row[5],
                    "is_admin": row[6]
                }
            return None

    def create_user(self, user_id: int, username: str = "", first_name: str = ""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            conn.commit()

    def update_balance(self, user_id: int, amount: float) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ? RETURNING balance",
                (amount, user_id)
            )
            result = cursor.fetchone()
            new_balance = result[0] if result else 0
            conn.commit()
            return new_balance

    def set_balance(self, user_id: int, amount: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
            conn.commit()

    def get_balance(self, user_id: int) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0.0

    def set_bet(self, user_id: int, bet: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET bet = ? WHERE user_id = ?", (bet, user_id))
            conn.commit()

    def get_bet(self, user_id: int) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bet FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0.1

    def get_all_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

    def create_mines_game(self, user_id: int, bet: float, field: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO mines_games (user_id, bet, field, opened_cells) VALUES (?, ?, ?, ?)",
                (user_id, bet, field, "")
            )
            conn.commit()
            return cursor.lastrowid

    def get_mines_game(self, game_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM mines_games WHERE game_id = ?", (game_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "game_id": row[0],
                    "user_id": row[1],
                    "bet": row[2],
                    "field": row[3],
                    "opened_cells": row[4],
                    "game_active": row[5],
                    "created_at": row[6]
                }
            return None

    def update_mines_game(self, game_id: int, opened_cells: str, game_active: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE mines_games SET opened_cells = ?, game_active = ? WHERE game_id = ?",
                (opened_cells, game_active, game_id)
            )
            conn.commit()

    def save_payment(self, invoice_id: str, user_id: int, amount: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO payments (invoice_id, user_id, amount) VALUES (?, ?, ?)",
                (invoice_id, user_id, amount)
            )
            conn.commit()

    def confirm_payment(self, invoice_id: str) -> Optional[Tuple[int, float]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, amount FROM payments WHERE invoice_id = ? AND status = 'pending'",
                (invoice_id,)
            )
            result = cursor.fetchone()
            if result:
                cursor.execute(
                    "UPDATE payments SET status = 'paid' WHERE invoice_id = ?",
                    (invoice_id,)
                )
                conn.commit()
                return result
            return None

# ==================== CRYPTO BOT API ====================
class CryptoPayClient:
    def __init__(self, token: str, testnet: bool = True):
        self.token = token
        self.base_url = "https://testnet-pay.crypt.bot" if testnet else "https://pay.crypt.bot"
        self.headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(self, amount: float, asset: str = "USDT") -> Optional[Dict]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/createInvoice"
                params = {
                    "asset": asset,
                    "amount": str(amount),
                    "description": "Пополнение игрового баланса",
                    "paid_btn_name": "openBot",
                    "paid_btn_url": "https://t.me/Pllays_Bot"
                }
                async with session.post(url, headers=self.headers, data=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok"):
                            return data["result"]
        except:
            pass
        return None

    async def get_invoice_status(self, invoice_id: str) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/getInvoices"
                params = {"invoice_ids": invoice_id}
                async with session.get(url, headers=self.headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok") and data["result"]["items"]:
                            return data["result"]["items"][0]["status"]
        except:
            pass
        return None

    async def create_check(self, amount: float, asset: str = "USDT") -> Optional[Dict]:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/createCheck"
                params = {
                    "asset": asset,
                    "amount": str(amount)
                }
                async with session.post(url, headers=self.headers, data=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok"):
                            return data["result"]
        except:
            pass
        return None

# ==================== FSM ====================
class WithdrawStates(StatesGroup):
    waiting_for_amount = State()

class DepositStates(StatesGroup):
    waiting_for_amount = State()

class AdminStates(StatesGroup):
    waiting_for_user_id_balance = State()
    waiting_for_amount_balance = State()
    waiting_for_user_id_reset = State()
    waiting_for_message = State()

class BetChangeStates(StatesGroup):
    waiting_for_new_bet = State()

class PayStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

# ==================== INLINE КНОПКИ ====================
def get_start_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ИГРАТЬ", callback_data="menu_games"),
         InlineKeyboardButton(text="👤 ПРОФИЛЬ", callback_data="menu_profile")],
        [InlineKeyboardButton(text="💬 ЧАТЫ", callback_data="menu_chats")]
    ])

def get_games_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 КУБЫ", callback_data="game_dice"),
            InlineKeyboardButton(text="🎰 СЛОТЫ", callback_data="game_slots")
        ],
        [
            InlineKeyboardButton(text="🎯 ДАРТС", callback_data="game_darts"),
            InlineKeyboardButton(text="🎳 БОУЛИНГ", callback_data="game_bowling")
        ],
        [
            InlineKeyboardButton(text="💣 МИНЫ", callback_data="mines_menu"),
            InlineKeyboardButton(text="✏️ СТАВКА", callback_data="change_bet")
        ],
        [
            InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")
        ]
    ])

def get_mines_menu_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💣 НАЧАТЬ ИГРУ", callback_data="mines_start")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_games")]
    ])

def get_mines_field_buttons(game_id: int, opened: list, active: bool, mult: float = 1.0):
    """Создание поля 5x5 для игры в мины"""
    kb = []
    
    # Строки 0-4
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            if idx in opened:
                row.append(InlineKeyboardButton(text="✅", callback_data="ignore"))
            else:
                if active:
                    # ПРОСТЕЙШАЯ callback_data - только цифры
                    row.append(InlineKeyboardButton(text="⬛", callback_data=f"m{idx}"))
                else:
                    row.append(InlineKeyboardButton(text="⬛", callback_data="ignore"))
        kb.append(row)
    
    # Кнопка забора выигрыша
    if active and len(opened) > 0:
        kb.append([InlineKeyboardButton(text=f"💰 ЗАБРАТЬ x{mult:.2f}", callback_data=f"take")])
    
    # Кнопка выхода
    kb.append([InlineKeyboardButton(text="◀️ ВЫЙТИ", callback_data="mines_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_profile_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ПОПОЛНИТЬ", callback_data="deposit"),
         InlineKeyboardButton(text="💸 ВЫВЕСТИ", callback_data="withdraw")],
        [InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")]
    ])

def get_deposit_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 CRYPTO BOT", callback_data="deposit_crypto")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_profile")]
    ])

def get_withdraw_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 CRYPTO BOT", callback_data="withdraw_crypto")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_profile")]
    ])

def get_admin_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ ПОПОЛНИТЬ БАЛАНС", callback_data="admin_add")],
        [InlineKeyboardButton(text="2️⃣ ОБНУЛИТЬ БАЛАНС", callback_data="admin_reset")],
        [InlineKeyboardButton(text="3️⃣ РАССЫЛКА", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")]
    ])

def get_back_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_games")]
    ])

def get_main_menu_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")]
    ])

# ==================== ЛОГИКА ИГР ====================
class GameLogic:
    @staticmethod
    def check_dice_win(value: int, bet: float) -> Tuple[float, str]:
        if value >= 4:
            win = bet * 1.9
            return win, f"✅ ВЫИГРЫШ! +{win:.2f} {premium('dollar')}"
        return 0, f"❌ ПРОИГРЫШ (выпало {value})"

    @staticmethod
    def check_slots_win(value: int, bet: float) -> Tuple[float, str]:
        if value in [64, 65]:
            win = bet * 15
            return win, f"🎰 ДЖЕКПОТ! +{win:.2f} {premium('dollar')}"
        return 0, f"❌ ПРОИГРЫШ"

    @staticmethod
    def check_darts_win(value: int, bet: float) -> Tuple[float, str]:
        if value == 6:
            win = bet * 5
            return win, f"🎯 ТОЧНО В ЦЕНТР! +{win:.2f} {premium('dollar')}"
        elif value == 5:
            win = bet * 2
            return win, f"🎯 ХОРОШИЙ БРОСОК! +{win:.2f} {premium('dollar')}"
        return 0, f"🎯 ОЧКИ: {value}"

    @staticmethod
    def check_bowling_win(value: int, bet: float) -> Tuple[float, str]:
        if value == 6:
            win = bet * 5
            return win, f"🎳 СТРАЙК! +{win:.2f} {premium('dollar')}"
        elif value == 5:
            win = bet * 2
            return win, f"🎳 ХОРОШИЙ БРОСОК! +{win:.2f} {premium('dollar')}"
        return 0, f"🎳 СБИТО: {value}"

    @staticmethod
    def generate_mines_field(mines: int = 2) -> list:
        field = [0] * 25
        for p in random.sample(range(25), mines):
            field[p] = 1
        return field

    @staticmethod
    def get_multiplier(opened: int) -> float:
        mults = [1.02, 1.11, 1.22, 1.34, 1.48, 1.65, 1.84, 2.07, 2.35, 2.69,
                 3.1, 3.62, 4.27, 5.13, 6.27, 7.83, 10.07, 13.43, 18.8, 28.2,
                 47, 94, 282]
        if opened <= len(mults):
            return mults[opened - 1]
        return mults[-1]

# ==================== БОТ ====================
logging.basicConfig(level=logging.INFO)

if BOT_TOKEN == "8216893084:AAER8aRjEUUYWMepqn5l2_7IPxLjl56K9Ps":
    print("❌ ОШИБКА: Токен бота недействителен!")
    exit()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
db = Database()
crypto = CryptoPayClient(CRYPTOPAY_TOKEN)

bot_info = None

@dp.startup()
async def on_startup():
    global bot_info
    bot_info = await bot.get_me()
    print(f"🚀 БОТ @{bot_info.username} ЗАПУЩЕН!")

# ==================== МЕНЮ ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.create_user(user.id, user.username or "", user.first_name or "")
    await message.answer(
        f"{premium('rocket')} <b>ДОБРО ПОЖАЛОВАТЬ, {user.first_name}!</b>\n\n"
        f"🎮 <b>ИГРЫ С РЕАЛЬНЫМ ВЫИГРЫШЕМ</b>\n"
        f"💰 <b>МГНОВЕННЫЕ ВЫВОДЫ</b>\n\n"
        f"👇 <b>ВЫБЕРИ РАЗДЕЛ:</b>",
        reply_markup=get_start_buttons()
    )

@dp.message(Command("pay"))
async def cmd_pay(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) == 3:
        try:
            to_id = int(args[1])
            amount = float(args[2])
            if amount <= 0:
                await message.answer(f"{premium('dollar')} Сумма должна быть > 0")
                return
            balance = db.get_balance(message.from_user.id)
            if balance < amount:
                await message.answer(f"{premium('dollar')} Недостаточно средств")
                return
            if not db.get_user(to_id):
                await message.answer(f"{premium('dollar')} Пользователь не найден")
                return
            db.update_balance(message.from_user.id, -amount)
            db.update_balance(to_id, amount)
            await message.answer(f"{premium('balance')} Перевод выполнен! +{amount}$ пользователю {to_id}")
            try:
                await bot.send_message(to_id, f"{premium('balance')} Вы получили {amount}$ от {message.from_user.id}")
            except:
                pass
        except:
            await message.answer(f"{premium('dollar')} Неверный формат. Используй: /pay ID СУММА")
    else:
        await state.set_state(PayStates.waiting_for_user_id)
        await message.answer(f"{premium('transfer')} Введи ID получателя:")

@dp.message(PayStates.waiting_for_user_id)
async def pay_user_id(message: Message, state: FSMContext):
    try:
        to_id = int(message.text)
        if not db.get_user(to_id):
            await message.answer(f"{premium('dollar')} Пользователь не найден")
            await state.clear()
            return
        await state.update_data(to_id=to_id)
        await state.set_state(PayStates.waiting_for_amount)
        await message.answer(f"{premium('balance')} Введи сумму (баланс: {db.get_balance(message.from_user.id):.2f}$):")
    except:
        await message.answer(f"{premium('dollar')} Введи корректный ID")

@dp.message(PayStates.waiting_for_amount)
async def pay_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace("$", ""))
        if amount <= 0:
            await message.answer(f"{premium('dollar')} Сумма должна быть > 0")
            return
        balance = db.get_balance(message.from_user.id)
        if balance < amount:
            await message.answer(f"{premium('dollar')} Недостаточно средств")
            return
        data = await state.get_data()
        to_id = data["to_id"]
        db.update_balance(message.from_user.id, -amount)
        db.update_balance(to_id, amount)
        await message.answer(f"{premium('balance')} Перевод выполнен! +{amount}$ пользователю {to_id}")
        try:
            await bot.send_message(to_id, f"{premium('balance')} Вы получили {amount}$ от {message.from_user.id}")
        except:
            pass
        await state.clear()
    except:
        await message.answer(f"{premium('dollar')} Введи корректную сумму")

@dp.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('rocket')} <b>ГЛАВНОЕ МЕНЮ</b>\n\n👇 ВЫБЕРИ РАЗДЕЛ:",
        reply_markup=get_start_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_games")
async def menu_games(callback: CallbackQuery):
    uid = callback.from_user.id
    bal = db.get_balance(uid)
    bet = db.get_bet(uid)
    await callback.message.edit_text(
        f"{premium('casino')} <b>ВЫБЕРИ ИГРУ</b>\n\n"
        f"{premium('balance')} БАЛАНС: {bal:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {bet:.2f} {premium('dollar')}\n\n"
        f"👇 НАЖМИ НА ИГРУ:",
        reply_markup=get_games_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    user = callback.from_user
    u = db.get_user(user.id)
    bal = u["balance"] if u else 0
    await callback.message.edit_text(
        f"{premium('rocket')} <b>ПРОФИЛЬ</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"{premium('balance')} БАЛАНС: {bal:.2f} {premium('dollar')}\n\n"
        f"👇 ДЕЙСТВИЯ:",
        reply_markup=get_profile_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_chats")
async def menu_chats(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('lightning')} <b>ЧАТЫ</b>\n\nСкоро появятся!",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer(f"{premium('dollar')} НЕТ ПРАВ!")
        return
    await message.answer(
        f"{premium('lightning')} <b>АДМИН ПАНЕЛЬ</b>\n\n👇 ВЫБЕРИ ДЕЙСТВИЕ:",
        reply_markup=get_admin_buttons()
    )

# ==================== ИГРЫ ====================
@dp.callback_query(F.data.startswith("game_"))
async def game_play(callback: CallbackQuery):
    uid = callback.from_user.id
    game = callback.data.split("_")[1]
    bal = db.get_balance(uid)
    bet = db.get_bet(uid)

    if bal < bet:
        await callback.message.edit_text(
            f"{premium('dollar')} НЕДОСТАТОЧНО СРЕДСТВ!\n"
            f"{premium('balance')} БАЛАНС: {bal:.2f} {premium('dollar')}",
            reply_markup=get_back_buttons()
        )
        await callback.answer()
        return

    db.update_balance(uid, -bet)

    if game == "dice":
        msg = await bot.send_dice(callback.message.chat.id, emoji=DiceEmoji.DICE)
        win, text = GameLogic.check_dice_win(msg.dice.value, bet)
    elif game == "slots":
        msg = await bot.send_dice(callback.message.chat.id, emoji=DiceEmoji.SLOT_MACHINE)
        win, text = GameLogic.check_slots_win(msg.dice.value, bet)
    elif game == "darts":
        msg = await bot.send_dice(callback.message.chat.id, emoji=DiceEmoji.DART)
        win, text = GameLogic.check_darts_win(msg.dice.value, bet)
    elif game == "bowling":
        msg = await bot.send_dice(callback.message.chat.id, emoji=DiceEmoji.BOWLING)
        win, text = GameLogic.check_bowling_win(msg.dice.value, bet)
    else:
        await callback.answer()
        return

    if win > 0:
        db.update_balance(uid, win)

    new_bal = db.get_balance(uid)
    text += f"\n\n{premium('balance')} БАЛАНС: {new_bal:.2f} {premium('dollar')}"
    await msg.reply(text, reply_markup=get_back_buttons())
    await callback.answer()

# ==================== МИНЫ ====================
# Хранилище игр в памяти (для простоты)
active_games = {}

@dp.callback_query(F.data == "mines_menu")
async def mines_menu(callback: CallbackQuery):
    print("👉 mines_menu вызван")
    uid = callback.from_user.id
    bal = db.get_balance(uid)
    bet = db.get_bet(uid)
    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ</b>\n\n"
        f"{premium('balance')} БАЛАНС: {bal:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {bet:.2f} {premium('dollar')}\n\n"
        f"💣 2 МИНЫ НА ПОЛЕ 5x5\n"
        f"📊 МНОЖИТЕЛИ ДО x282\n\n"
        f"👇 НАЧНИ ИГРУ:",
        reply_markup=get_mines_menu_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "mines_start")
async def mines_start(callback: CallbackQuery):
    print("👉 mines_start вызван")
    uid = callback.from_user.id
    bal = db.get_balance(uid)
    bet = db.get_bet(uid)

    if bal < bet:
        await callback.answer("❌ НЕДОСТАТОЧНО СРЕДСТВ!", show_alert=True)
        return

    # Списываем ставку
    db.update_balance(uid, -bet)
    
    # Создаем поле
    field = GameLogic.generate_mines_field(2)
    print(f"👉 Создано поле: {field}")
    
    # Сохраняем в памяти (для простоты)
    game_id = uid  # Используем ID пользователя как game_id для простоты
    active_games[game_id] = {
        "field": field,
        "opened": [],
        "active": True,
        "bet": bet
    }
    print(f"👉 Игра сохранена с ID: {game_id}")
    
    user = db.get_user(uid)
    name = user["username"] or user["first_name"] or f"ID{uid}"
    
    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ИГРА</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {bal - bet:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {bet:.2f} {premium('dollar')}\n\n"
        f"💣 МИН: 2\n"
        f"⬛ ОТКРЫВАЙ КЛЕТКИ:",
        reply_markup=get_mines_field_buttons(game_id, [], True, 1.0)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("m"))
async def mines_cell(callback: CallbackQuery):
    print(f"👉 mines_cell вызван с data: {callback.data}")
    
    try:
        # data = "m0", "m1", ... "m24"
        idx = int(callback.data[1:])
        print(f"👉 Индекс клетки: {idx}")
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        await callback.answer("❌ ОШИБКА!", show_alert=True)
        return

    uid = callback.from_user.id
    game = active_games.get(uid)
    
    if not game:
        print(f"❌ Игра не найдена для пользователя {uid}")
        await callback.answer("❌ ИГРА НЕ НАЙДЕНА!", show_alert=True)
        return
    
    print(f"👉 Игра найдена: {game}")

    if not game["active"]:
        await callback.answer("❌ ИГРА ЗАКОНЧЕНА!", show_alert=True)
        return

    if idx in game["opened"]:
        await callback.answer("✅ УЖЕ ОТКРЫТО!", show_alert=True)
        return

    print(f"👉 Поле: {game['field']}, клетка {idx} = {game['field'][idx]}")

    # ПРОВЕРКА НА МИНУ
    if game["field"][idx] == 1:
        print(f"💥 МИНА! Клетка {idx} - мина")
        # ПРОИГРЫШ
        game["active"] = False
        
        user = db.get_user(uid)
        name = user["username"] or user["first_name"] or f"ID{uid}"
        
        await callback.message.edit_text(
            f"{premium('lightning')} <b>МИНЫ | ПРОИГРЫШ</b>\n\n"
            f"👤 {name}\n"
            f"{premium('balance')} БАЛАНС: {db.get_balance(uid):.2f} {premium('dollar')}\n\n"
            f"💥 БАБАХ! ТЫ ПОДОРВАЛСЯ!",
            reply_markup=get_mines_field_buttons(uid, game["opened"] + [idx], False, 0)
        )
        await callback.answer("💥 МИНА!", show_alert=True)
        return

    # ОТКРЫВАЕМ КЛЕТКУ
    print(f"✅ Клетка {idx} безопасна, открываем")
    game["opened"].append(idx)

    mult = GameLogic.get_multiplier(len(game["opened"]))
    potential = game["bet"] * mult
    print(f"👉 Множитель: {mult}, потенциальный выигрыш: {potential}")

    user = db.get_user(uid)
    name = user["username"] or user["first_name"] or f"ID{uid}"

    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ИГРА</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(uid):.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {game['bet']:.2f} {premium('dollar')}\n\n"
        f"📊 МНОЖИТЕЛЬ: x{mult}\n"
        f"💰 ВЫИГРЫШ: {potential:.2f} {premium('dollar')}\n"
        f"⬛ ОТКРЫТО: {len(game['opened'])}",
        reply_markup=get_mines_field_buttons(uid, game["opened"], True, mult)
    )
    await callback.answer()

@dp.callback_query(F.data == "take")
async def mines_take(callback: CallbackQuery):
    print(f"👉 mines_take вызван")
    
    uid = callback.from_user.id
    game = active_games.get(uid)
    
    if not game:
        print(f"❌ Игра не найдена для пользователя {uid}")
        await callback.answer("❌ ИГРА НЕ НАЙДЕНА!", show_alert=True)
        return

    if not game["active"]:
        await callback.answer("❌ ИГРА ЗАКОНЧЕНА!", show_alert=True)
        return

    if not game["opened"]:
        await callback.answer("❌ ОТКРОЙ ХОТЯ БЫ 1 КЛЕТКУ!", show_alert=True)
        return

    mult = GameLogic.get_multiplier(len(game["opened"]))
    win = game["bet"] * mult
    print(f"👉 Выигрыш: {win} (x{mult})")

    db.update_balance(uid, win)
    game["active"] = False

    user = db.get_user(uid)
    name = user["username"] or user["first_name"] or f"ID{uid}"

    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ВЫИГРЫШ</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(uid):.2f} {premium('dollar')}\n\n"
        f"✅ ВЫИГРЫШ: {win:.2f} {premium('dollar')} (x{mult})",
        reply_markup=get_mines_field_buttons(uid, game["opened"], False, mult)
    )
    await callback.answer(f"💰 +{win:.2f} {premium('dollar')}", show_alert=True)

@dp.callback_query(F.data == "change_bet")
async def change_bet(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BetChangeStates.waiting_for_new_bet)
    await callback.message.edit_text(
        f"✏️ <b>ИЗМЕНЕНИЕ СТАВКИ</b>\n\n"
        f"💰 ТЕКУЩАЯ: {db.get_bet(callback.from_user.id):.2f} {premium('dollar')}\n\n"
        f"📝 ВВЕДИ НОВУЮ СУММУ (например: 2.5):",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(BetChangeStates.waiting_for_new_bet)
async def new_bet(message: Message, state: FSMContext):
    try:
        bet = float(message.text.replace("$", "").replace(",", "."))
        if bet <= 0:
            await message.answer(f"{premium('dollar')} СТАВКА ДОЛЖНА БЫТЬ > 0")
            return
        db.set_bet(message.from_user.id, bet)
        await state.clear()
        await message.answer(
            f"✅ СТАВКА ИЗМЕНЕНА: {bet:.2f} {premium('dollar')}",
            reply_markup=get_main_menu_button()
        )
    except:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

# ==================== ПРОФИЛЬ ====================
@dp.callback_query(F.data == "deposit")
async def deposit(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('deposit')} <b>ПОПОЛНЕНИЕ</b>\n\n👇 ВЫБЕРИ СПОСОБ:",
        reply_markup=get_deposit_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "deposit_crypto")
async def deposit_crypto(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('deposit')} <b>ПОПОЛНЕНИЕ</b>\n\n"
        f"💰 МИНИМУМ: 0.1$\n"
        f"📉 КОМИССИЯ: 3% (>0.15$)\n\n"
        f"📝 ВВЕДИ СУММУ:",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(DepositStates.waiting_for_amount)
async def deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace("$", ""))
        if amount < 0.1:
            await message.answer(f"{premium('dollar')} МИНИМУМ 0.1$")
            return
        
        invoice = await crypto.create_invoice(amount)
        if invoice:
            db.save_payment(invoice["invoice_id"], message.from_user.id, amount)
            fee = amount * 0.03 if amount > 0.15 else 0
            final = amount - fee
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=invoice["pay_url"])],
                [InlineKeyboardButton(text="✅ ПРОВЕРИТЬ", callback_data=f"check_{invoice['invoice_id']}")],
                [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="menu_main")]
            ])
            await message.answer(
                f"{premium('deposit')} <b>СЧЕТ СОЗДАН!</b>\n\n"
                f"💰 СУММА: {amount}$\n"
                f"📉 КОМИССИЯ: {fee:.2f}$\n"
                f"📈 К ЗАЧИСЛЕНИЮ: {final:.2f}$\n\n"
                f"✅ ПОСЛЕ ОПЛАТЫ НАЖМИ ПРОВЕРИТЬ",
                reply_markup=kb
            )
        else:
            await message.answer(f"{premium('dollar')} ОШИБКА СОЗДАНИЯ СЧЕТА", reply_markup=get_main_menu_button())
        await state.clear()
    except:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

@dp.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery):
    try:
        inv_id = callback.data.split("_")[1]
    except:
        await callback.answer("❌ ОШИБКА", show_alert=True)
        return
    
    status = await crypto.get_invoice_status(inv_id)
    if status == "paid":
        pay = db.confirm_payment(inv_id)
        if pay:
            uid, amount = pay
            fee = amount * 0.03 if amount > 0.15 else 0
            final = amount - fee
            db.update_balance(uid, final)
            await callback.message.edit_text(
                f"{premium('balance')} <b>ОПЛАТА ПОДТВЕРЖДЕНА!</b>\n\n"
                f"💰 ПОПОЛНЕНО: {final:.2f} {premium('dollar')}",
                reply_markup=get_main_menu_button()
            )
        else:
            await callback.answer("❌ ПЛАТЕЖ НЕ НАЙДЕН", show_alert=True)
    elif status == "active":
        await callback.answer("⏳ ОЖИДАНИЕ ОПЛАТЫ...", show_alert=True)
    else:
        await callback.answer("❌ НЕ ОПЛАЧЕНО", show_alert=True)

@dp.callback_query(F.data == "withdraw")
async def withdraw(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('withdraw')} <b>ВЫВОД</b>\n\n👇 ВЫБЕРИ СПОСОБ:",
        reply_markup=get_withdraw_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw_crypto")
async def withdraw_crypto(callback: CallbackQuery, state: FSMContext):
    bal = db.get_balance(callback.from_user.id)
    await state.set_state(WithdrawStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('withdraw')} <b>ВЫВОД</b>\n\n"
        f"{premium('balance')} БАЛАНС: {bal:.2f}$\n"
        f"💰 МИНИМУМ: 1$\n\n"
        f"📝 ВВЕДИ СУММУ:",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace("$", ""))
        uid = message.from_user.id
        bal = db.get_balance(uid)
        
        if amount < 1:
            await message.answer(f"{premium('dollar')} МИНИМУМ 1$")
            return
        if amount > bal:
            await message.answer(f"{premium('dollar')} НЕДОСТАТОЧНО СРЕДСТВ")
            return
        
        check = await crypto.create_check(amount)
        if check:
            db.update_balance(uid, -amount)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 ПОЛУЧИТЬ", url=check["check_url"])],
                [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="menu_main")]
            ])
            await message.answer(
                f"{premium('withdraw')} <b>ЧЕК СОЗДАН!</b>\n\n{check['check_url']}",
                reply_markup=kb
            )
        else:
            await message.answer(f"{premium('dollar')} ОШИБКА", reply_markup=get_main_menu_button())
        await state.clear()
    except:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

# ==================== АДМИНКА ====================
@dp.callback_query(F.data.startswith("admin_"))
async def admin_action(callback: CallbackQuery, state: FSMContext):
    user = db.get_user(callback.from_user.id)
    if not user or not user.get("is_admin"):
        await callback.answer("❌ НЕТ ПРАВ!", show_alert=True)
        return

    action = callback.data.split("_")[1]
    if action == "add":
        await state.set_state(AdminStates.waiting_for_user_id_balance)
        await callback.message.edit_text("👑 ВВЕДИ ID ПОЛЬЗОВАТЕЛЯ:", reply_markup=get_main_menu_button())
    elif action == "reset":
        await state.set_state(AdminStates.waiting_for_user_id_reset)
        await callback.message.edit_text("👑 ВВЕДИ ID ПОЛЬЗОВАТЕЛЯ:", reply_markup=get_main_menu_button())
    elif action == "broadcast":
        await state.set_state(AdminStates.waiting_for_message)
        await callback.message.edit_text("👑 ВВЕДИ ТЕКСТ РАССЫЛКИ:", reply_markup=get_main_menu_button())
    await callback.answer()

@dp.message(AdminStates.waiting_for_user_id_balance)
async def admin_add_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text)
        u = db.get_user(uid)
        if not u:
            await message.answer("❌ НЕ НАЙДЕН")
            await state.clear()
            return
        await state.update_data(target=uid)
        await state.set_state(AdminStates.waiting_for_amount_balance)
        await message.answer(f"👑 БАЛАНС: {u['balance']:.2f}$\nВВЕДИ СУММУ:")
    except:
        await message.answer("❌ ВВЕДИ ID")

@dp.message(AdminStates.waiting_for_amount_balance)
async def admin_add_amount(message: Message, state: FSMContext):
    try:
        amt = float(message.text)
        data = await state.get_data()
        new = db.update_balance(data["target"], amt)
        await message.answer(f"✅ НОВЫЙ БАЛАНС: {new:.2f}$", reply_markup=get_main_menu_button())
        await state.clear()
    except:
        await message.answer("❌ ВВЕДИ СУММУ")

@dp.message(AdminStates.waiting_for_user_id_reset)
async def admin_reset_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text)
        if not db.get_user(uid):
            await message.answer("❌ НЕ НАЙДЕН")
            await state.clear()
            return
        db.set_balance(uid, 0)
        await message.answer(f"✅ БАЛАНС {uid} ОБНУЛЕН", reply_markup=get_main_menu_button())
        await state.clear()
    except:
        await message.answer("❌ ВВЕДИ ID")

@dp.message(AdminStates.waiting_for_message)
async def admin_broadcast(message: Message, state: FSMContext):
    text = message.text
    users = db.get_all_users()
    sent = 0
    fail = 0
    status = await message.answer(f"📨 РАССЫЛКА... 0/{len(users)}")
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            fail += 1
        if (sent + fail) % 10 == 0:
            await status.edit_text(f"📨 {sent + fail}/{len(users)}\n✅ {sent} | ❌ {fail}")
    await status.edit_text(f"✅ ГОТОВО!\nУСПЕШНО: {sent}\nОШИБОК: {fail}", reply_markup=get_main_menu_button())
    await state.clear()

@dp.callback_query(F.data == "ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()

# ==================== ЗАПУСК ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
