import asyncio
import logging
import sqlite3
import random
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

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
BOT_TOKEN = "8216893084:AAEu4U9ftWicx3UFO9Qlvm42WO0z4Q_nmT4"
ADMIN_ID = 7313407194
CRYPTOPAY_TOKEN = "531599:AAxGq5ZSfCUBnSn0gyfUCyB5tB4VKr0rmRd"
WITHDRAW_ADMIN = "@qwhatss"
CHATS_LINK = "https://t.me/PllaysBet"

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
        self.reserve_cache = {
            "amount": random.uniform(700, 790),
            "updated": datetime.now()
        }
        self.fast_contests = {}

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
                    turnover REAL DEFAULT 0.0,
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
                CREATE TABLE IF NOT EXISTS checks (
                    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    uses INTEGER DEFAULT 1,
                    uses_left INTEGER DEFAULT 1,
                    check_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    invoice_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    type TEXT,
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
                    "turnover": row[4],
                    "bet": row[5],
                    "created_at": row[6],
                    "is_admin": row[7]
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

    def update_turnover(self, user_id: int, amount: float):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET turnover = turnover + ? WHERE user_id = ?",
                (amount, user_id)
            )
            conn.commit()

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

    def get_turnover(self, user_id: int) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT turnover FROM users WHERE user_id = ?", (user_id,))
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

    def get_top_balance(self, limit: int = 10) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, first_name, balance FROM users ORDER BY balance DESC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()

    def get_top_turnover(self, limit: int = 10) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, first_name, turnover FROM users ORDER BY turnover DESC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()

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

    def save_check(self, user_id: int, amount: float, uses: int, check_data: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO checks (user_id, amount, uses, uses_left, check_data) VALUES (?, ?, ?, ?, ?) RETURNING check_id",
                (user_id, amount, uses, uses, check_data)
            )
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else 0

    def get_checks(self, user_id: Optional[int] = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    "SELECT check_id, amount, uses, uses_left, check_data, created_at FROM checks WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                )
            else:
                cursor.execute("SELECT check_id, user_id, amount, uses, uses_left, check_data, created_at FROM checks ORDER BY created_at DESC")
            rows = cursor.fetchall()
            if user_id:
                return [{"id": r[0], "amount": r[1], "uses": r[2], "uses_left": r[3], "data": r[4], "created_at": r[5]} for r in rows]
            else:
                return [{"id": r[0], "user_id": r[1], "amount": r[2], "uses": r[3], "uses_left": r[4], "data": r[5], "created_at": r[6]} for r in rows]

    def use_check(self, check_data: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT check_id, user_id, amount, uses_left FROM checks WHERE check_data = ? AND uses_left > 0",
                (check_data,)
            )
            row = cursor.fetchone()
            if row:
                check_id, owner_id, amount, uses_left = row
                if uses_left > 1:
                    cursor.execute(
                        "UPDATE checks SET uses_left = uses_left - 1 WHERE check_id = ?",
                        (check_id,)
                    )
                else:
                    cursor.execute("DELETE FROM checks WHERE check_id = ?", (check_id,))
                conn.commit()
                return {"owner_id": owner_id, "amount": amount}
            return None

    def save_payment_request(self, user_id: int, amount: float, type: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO payments (user_id, amount, type) VALUES (?, ?, ?) RETURNING invoice_id",
                (user_id, amount, type)
            )
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else 0

    def get_payment_requests(self, status: str = "pending") -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rowid, user_id, amount, type, created_at FROM payments WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
            rows = cursor.fetchall()
            return [{"id": r[0], "user_id": r[1], "amount": r[2], "type": r[3], "created_at": r[4]} for r in rows]

    def confirm_payment(self, payment_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE payments SET status = 'completed' WHERE rowid = ?",
                (payment_id,)
            )
            conn.commit()

    def get_reserve(self) -> float:
        now = datetime.now()
        if now - self.reserve_cache["updated"] > timedelta(minutes=5):
            self.reserve_cache["amount"] = random.uniform(700, 790)
            self.reserve_cache["updated"] = now
        return self.reserve_cache["amount"]

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
        except Exception as e:
            print(f"Ошибка CryptoPay: {e}")
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
        except Exception as e:
            print(f"Ошибка проверки: {e}")
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
        except Exception as e:
            print(f"Ошибка CryptoPay: {e}")
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
    waiting_for_payment_id = State()
    waiting_for_payment_amount = State()
    waiting_for_fast_amount = State()

class BetChangeStates(StatesGroup):
    waiting_for_new_bet = State()

class PayStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class CheckStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_uses = State()

# ==================== INLINE КНОПКИ ====================
def get_start_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ИГРАТЬ", callback_data="menu_games"),
         InlineKeyboardButton(text="👤 ПРОФИЛЬ", callback_data="menu_profile")],
        [InlineKeyboardButton(text="🏆 ТОПЫ", callback_data="menu_top"),
         InlineKeyboardButton(text="💬 ЧАТЫ", callback_data="menu_chats")],
        [InlineKeyboardButton(text="💰 ЧЕКИ", callback_data="menu_checks")]
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

def get_top_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 ТОП БАЛАНС", callback_data="top_balance"),
            InlineKeyboardButton(text="🔄 ТОП ОБОРОТ", callback_data="top_turnover")
        ],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_main")]
    ])

def get_checks_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СОЗДАТЬ ЧЕК", callback_data="check_create")],
        [InlineKeyboardButton(text="📋 МОИ ЧЕКИ", callback_data="check_list")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_main")]
    ])

def get_mines_menu_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💣 НАЧАТЬ ИГРУ", callback_data="mines_start")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_games")]
    ])

def get_mines_field_buttons(game_id: int, opened: list, active: bool, mult: float = 1.0):
    kb = []
    for i in range(5):
        row = []
        for j in range(5):
            idx = i * 5 + j
            if idx in opened:
                if game_id in active_games and active_games[game_id]["field"][idx] == 1:
                    row.append(InlineKeyboardButton(text="💥", callback_data="ignore"))
                else:
                    row.append(InlineKeyboardButton(text="✅", callback_data="ignore"))
            else:
                if active:
                    row.append(InlineKeyboardButton(text="⬛", callback_data=f"cell_{idx}"))
                else:
                    row.append(InlineKeyboardButton(text="⬛", callback_data="ignore"))
        kb.append(row)
    if active and len(opened) > 0:
        kb.append([InlineKeyboardButton(text=f"💰 ЗАБРАТЬ x{mult:.2f}", callback_data="take")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_profile_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ПОПОЛНИТЬ", callback_data="deposit"),
         InlineKeyboardButton(text="💸 ВЫВЕСТИ", callback_data="withdraw")],
        [InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")]
    ])

def get_deposit_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 АДМИН", callback_data="deposit_admin")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_profile")]
    ])

def get_withdraw_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 АДМИН", callback_data="withdraw_admin")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="menu_profile")]
    ])

def get_admin_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ ПОПОЛНИТЬ БАЛАНС", callback_data="admin_add")],
        [InlineKeyboardButton(text="2️⃣ ОБНУЛИТЬ БАЛАНС", callback_data="admin_reset")],
        [InlineKeyboardButton(text="3️⃣ РАССЫЛКА", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="4️⃣ ЗАПРОСЫ ВЫВОДА", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="5️⃣ ЧЕКИ", callback_data="admin_checks")],
        [InlineKeyboardButton(text="6️⃣ БЫСТРЫЙ КОНКУРС", callback_data="admin_fast")],
        [InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="menu_main")]
    ])

def get_fast_participate_button(contest_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 УЧАСТВОВАТЬ", callback_data=f"fast_join_{contest_id}")]
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

print("🔧 Запуск бота...")
print(f"🤖 Токен: {BOT_TOKEN[:15]}...")

try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    db = Database()
    crypto = CryptoPayClient(CRYPTOPAY_TOKEN)
    print("✅ Бот создан успешно")
except Exception as e:
    print(f"❌ Ошибка создания бота: {e}")
    exit(1)

@dp.startup()
async def on_startup():
    try:
        bot_info = await bot.get_me()
        print(f"🚀 БОТ @{bot_info.username} ЗАПУЩЕН!")
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        raise e

# ==================== АВТОМАТИЧЕСКОЕ ИЗМЕНЕНИЕ СТАВКИ ====================
@dp.message(F.text)
async def auto_change_bet(message: Message):
    """Автоматическое изменение ставки при вводе числа с $ в конце"""
    try:
        if not message.text:
            return
        
        text = message.text.strip()
        
        # Проверяем, что сообщение заканчивается на $
        if not text.endswith('$'):
            return  # Игнорируем, если нет $ в конце
        
        # Убираем $ и пробелы
        cleaned = text.replace('$', '').replace(' ', '').replace(',', '.')
        
        # Пробуем преобразовать в число
        try:
            new_bet = float(cleaned)
        except ValueError:
            return  # Если не число - игнорируем
        
        # Проверяем корректность ставки
        if new_bet <= 0:
            await message.answer(f"{premium('dollar')} Ставка должна быть больше 0")
            return
        
        if new_bet < 0.1:
            await message.answer(f"{premium('dollar')} Минимальная ставка 0.1$")
            return
        
        # Сохраняем новую ставку
        db.set_bet(message.from_user.id, new_bet)
        
        await message.answer(
            f"{premium('transfer')} <b>СТАВКА ИЗМЕНЕНА</b>\n\n"
            f"{premium('dollar')} Новая ставка: {new_bet:.2f}$",
            reply_markup=get_main_menu_button()
        )
        
    except Exception:
        # Игнорируем все ошибки
        pass


# ==================== КОМАНДЫ ====================
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

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        f"{premium('rocket')} <b>ПОМОЩЬ ПО ИГРАМ И КОМАНДАМ</b>\n\n"
        f"<b>🎮 ИГРЫ:</b>\n"
        f"• 🎲 КУБЫ - выигрыш x1.9 при 4+\n"
        f"• 🎰 СЛОТЫ - джекпот x15\n"
        f"• 🎯 ДАРТС - x5 в центр, x2 рядом\n"
        f"• 🎳 БОУЛИНГ - x5 страйк, x2 рядом\n"
        f"• 💣 МИНЫ - множители до x282\n\n"
        f"<b>📋 КОМАНДЫ:</b>\n"
        f"• /start - главное меню\n"
        f"• /pay ID СУММА - перевести средства\n"
        f"• /top - топ игроков\n"
        f"• /reserve - резерв бота\n"
        f"• /activate КОД - активировать чек\n"
        f"• /help - эта справка\n\n"
        f"<b>💳 ВЫВОДЫ:</b>\n"
        f"Выводы через администратора {WITHDRAW_ADMIN}\n"
        f"После запроса напишите администратору\n\n"
        f"<b>💬 НАШ ЧАТ:</b> {CHATS_LINK}"
    )
    await message.answer(help_text)

@dp.message(Command("reserve"))
async def cmd_reserve(message: Message):
    reserve = db.get_reserve()
    await message.answer(
        f"{premium('balance')} <b>РЕЗЕРВ PLAYS</b>\n\n"
        f"{premium('lightning')} <b>CryptoBot:</b> {reserve:.2f} {premium('dollar')}\n"
        f"<i>Обновление каждые 5 минут</i>"
    )

@dp.message(Command("top"))
async def cmd_top(message: Message):
    await message.answer(
        f"{premium('lightning')} <b>ВЫБЕРИ КАТЕГОРИЮ ТОПА</b>\n\n"
        f"💰 Топ по балансу\n"
        f"🔄 Топ по обороту",
        reply_markup=get_top_buttons()
    )

@dp.message(Command("game"))
async def cmd_game(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer(f"{premium('dollar')} НЕТ ПРАВ!")
        return
    
    args = message.text.split()
    if len(args) != 3 or args[1] != "mines":
        await message.answer(f"{premium('dollar')} Используй: /game mines НОМЕР_ИГРЫ")
        return
    
    try:
        game_id = int(args[2])
        game = db.get_mines_game(game_id)
        if not game:
            await message.answer(f"{premium('dollar')} ИГРА НЕ НАЙДЕНА")
            return
        
        field = list(map(int, game["field"].split(",")))
        opened = list(map(int, game["opened_cells"].split(","))) if game["opened_cells"] else []
        
        field_map = ""
        for i in range(5):
            row = ""
            for j in range(5):
                idx = i * 5 + j
                if field[idx] == 1:
                    row += "💥 "
                else:
                    row += "⬜ "
            field_map += row + "\n"
        
        await message.answer(
            f"{premium('lightning')} <b>МИНЫ | ИГРА #{game_id}</b>\n\n"
            f"👤 ИГРОК: {game['user_id']}\n"
            f"💰 СТАВКА: {game['bet']} {premium('dollar')}\n"
            f"🔄 ОТКРЫТО: {len(opened)}\n"
            f"⚡ АКТИВНА: {'ДА' if game['game_active'] else 'НЕТ'}\n\n"
            f"<b>ПОЛЕ:</b>\n{field_map}"
        )
    except Exception as e:
        await message.answer(f"{premium('dollar')} ОШИБКА: {e}")

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
        if not message.text:
            await message.answer(f"{premium('dollar')} Введи корректный ID")
            return
            
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
        if not message.text:
            await message.answer(f"{premium('dollar')} Введи корректную сумму")
            return
            
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

# ==================== БЫСТРЫЙ КОНКУРС ====================
@dp.message(Command("fast"))
async def cmd_fast(message: Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    if not user or not user.get("is_admin"):
        await message.answer(f"{premium('dollar')} НЕТ ПРАВ!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            f"{premium('dollar')} <b>ИСПОЛЬЗУЙ:</b> /fast СУММА\n\n"
            f"Пример: /fast 10"
        )
        return
    
    try:
        amount = float(args[1].replace("$", ""))
        if amount < 0.1:
            await message.answer(f"{premium('dollar')} Минимальная сумма 0.1$")
            return
        
        contest_id = f"fast_{datetime.now().timestamp()}"
        db.fast_contests[contest_id] = {
            "amount": amount,
            "participants": [],
            "active": True,
            "created_by": message.from_user.id,
            "message_id": None,
            "chat_id": message.chat.id
        }
        
        contest_text = (
            f"{premium('dollar')} <b>БЫСТРЫЙ КОНКУРС</b> {premium('dollar')}\n\n"
            f"💰 <b>ПРИЗОВОЙ ФОНД:</b> {amount} {premium('dollar')}\n"
            f"🎲 <b>УЧАСТНИКОВ:</b> 0/6\n\n"
            f"<b>УЧАСТНИКИ:</b>\n"
        )
        
        sent_msg = await message.answer(
            contest_text,
            reply_markup=get_fast_participate_button(contest_id)
        )
        db.fast_contests[contest_id]["message_id"] = sent_msg.message_id
        
    except ValueError:
        await message.answer(f"{premium('dollar')} Введи корректную сумму")

# ==================== АКТИВАЦИЯ ЧЕКА ====================
@dp.message(Command("activate"))
async def cmd_activate(message: Message):
    args = message.text.split()
    
    if len(args) != 2:
        await message.answer(
            f"{premium('dollar')} <b>ИСПОЛЬЗУЙ:</b> /activate КОД_ЧЕКА\n\n"
            f"Пример: /activate CHECK73134071943644"
        )
        return
    
    check_code = args[1].strip()
    uid = message.from_user.id
    
    check = db.use_check(check_code)
    
    if not check:
        await message.answer(f"{premium('dollar')} <b>ЧЕК НЕ НАЙДЕН ИЛИ УЖЕ ИСПОЛЬЗОВАН</b>")
        return
    
    db.update_balance(uid, check["amount"])
    
    await message.answer(
        f"{premium('balance')} <b>ЧЕК АКТИВИРОВАН!</b>\n\n"
        f"💰 СУММА: +{check['amount']} {premium('dollar')}\n"
        f"{premium('balance')} НОВЫЙ БАЛАНС: {db.get_balance(uid):.2f} {premium('dollar')}"
    )
    
    try:
        await bot.send_message(
            check["owner_id"],
            f"{premium('balance')} <b>ЧЕК АКТИВИРОВАН</b>\n\n"
            f"💰 Ваш чек на {check['amount']} {premium('dollar')} был активирован"
        )
    except:
        pass

# ==================== МЕНЮ ====================
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
    turnover = u["turnover"] if u else 0
    await callback.message.edit_text(
        f"{premium('rocket')} <b>ПРОФИЛЬ</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"{premium('balance')} БАЛАНС: {bal:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} ОБОРОТ: {turnover:.2f} {premium('dollar')}\n\n"
        f"👇 ДЕЙСТВИЯ:",
        reply_markup=get_profile_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_top")
async def menu_top(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('lightning')} <b>ВЫБЕРИ КАТЕГОРИЮ ТОПА</b>\n\n"
        f"💰 Топ по балансу\n"
        f"🔄 Топ по обороту",
        reply_markup=get_top_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_checks")
async def menu_checks(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('balance')} <b>ЧЕКИ</b>\n\n"
        f"💰 СОЗДАВАЙ И УПРАВЛЯЙ ЧЕКАМИ\n\n"
        f"👇 ВЫБЕРИ ДЕЙСТВИЕ:",
        reply_markup=get_checks_buttons()
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_chats")
async def menu_chats(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('lightning')} <b>НАШ ЧАТ</b>\n\n"
        f"💬 Присоединяйся к общению:\n{CHATS_LINK}",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

# ==================== ТОПЫ ====================
@dp.callback_query(F.data == "top_balance")
async def top_balance(callback: CallbackQuery):
    top_users = db.get_top_balance(10)
    text = f"{premium('lightning')} <b>ТОП 10 ПО БАЛАНСУ</b>\n\n"
    
    if not top_users:
        text += "Пока нет участников"
    else:
        for i, (uid, username, first_name, balance) in enumerate(top_users, 1):
            name = username or first_name or f"ID{uid}"
            text += f"{i}. {name} — {balance:.2f} {premium('dollar')}\n"
    
    text += f"\n{premium('balance')} <i>Всего игроков: {len(db.get_all_users())}</i>"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_button())
    await callback.answer()

@dp.callback_query(F.data == "top_turnover")
async def top_turnover(callback: CallbackQuery):
    top_users = db.get_top_turnover(10)
    text = f"{premium('lightning')} <b>ТОП 10 ПО ОБОРОТУ</b>\n\n"
    
    if not top_users:
        text += "Пока нет участников"
    else:
        for i, (uid, username, first_name, turnover) in enumerate(top_users, 1):
            name = username or first_name or f"ID{uid}"
            text += f"{i}. {name} — {turnover:.2f} {premium('dollar')}\n"
    
    text += f"\n{premium('balance')} <i>Всего игроков: {len(db.get_all_users())}</i>"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_button())
    await callback.answer()

# ==================== ЧЕКИ ====================
@dp.callback_query(F.data == "check_create")
async def check_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('balance')} <b>СОЗДАНИЕ ЧЕКА</b>\n\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(callback.from_user.id):.2f} {premium('dollar')}\n"
        f"💰 МИНИМУМ: 0.1$\n\n"
        f"📝 ВВЕДИ СУММУ ЧЕКА:",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(CheckStates.waiting_for_amount)
async def check_amount(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")
            return
            
        amount = float(message.text.replace("$", ""))
        uid = message.from_user.id
        bal = db.get_balance(uid)
        
        if amount < 0.1:
            await message.answer(f"{premium('dollar')} МИНИМУМ 0.1$")
            return
        if amount > bal:
            await message.answer(f"{premium('dollar')} НЕДОСТАТОЧНО СРЕДСТВ")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(CheckStates.waiting_for_uses)
        await message.answer(
            f"{premium('balance')} <b>КОЛИЧЕСТВО АКТИВАЦИЙ</b>\n\n"
            f"💰 СУММА ЧЕКА: {amount} {premium('dollar')}\n"
            f"📝 ВВЕДИ КОЛИЧЕСТВО АКТИВАЦИЙ (например: 1, 5, 100):",
            reply_markup=get_main_menu_button()
        )
    except ValueError:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

@dp.message(CheckStates.waiting_for_uses)
async def check_uses(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")
            return
            
        uses = int(message.text)
        if uses < 1:
            await message.answer(f"{premium('dollar')} Минимум 1 активация")
            return
        
        data = await state.get_data()
        amount = data["amount"]
        uid = message.from_user.id
        
        total_cost = amount * uses
        db.update_balance(uid, -total_cost)
        
        check_codes = []
        for i in range(uses):
            check_data = f"CHECK{uid}{random.randint(1000, 9999)}{i}"
            check_id = db.save_check(uid, amount, 1, check_data)
            check_codes.append(check_data)
        
        if uses == 1:
            await message.answer(
                f"{premium('balance')} <b>ЧЕК СОЗДАН!</b>\n\n"
                f"💰 СУММА: {amount} {premium('dollar')}\n"
                f"📋 КОЛИЧЕСТВО: 1\n"
                f"🔑 КОД: <code>{check_codes[0]}</code>\n\n"
                f"📤 Отправьте код получателю",
                reply_markup=get_main_menu_button()
            )
        else:
            text = f"{premium('balance')} <b>ЧЕКИ СОЗДАНЫ!</b>\n\n"
            text += f"💰 СУММА КАЖДОГО: {amount} {premium('dollar')}\n"
            text += f"📋 КОЛИЧЕСТВО: {uses}\n"
            text += f"💵 ОБЩАЯ СУММА: {total_cost} {premium('dollar')}\n\n"
            text += f"<b>КОДЫ ЧЕКОВ:</b>\n"
            for i, code in enumerate(check_codes, 1):
                text += f"{i}. <code>{code}</code>\n"
            
            await message.answer(text, reply_markup=get_main_menu_button())
        
        await state.clear()
        
    except ValueError:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

@dp.callback_query(F.data == "check_list")
async def check_list(callback: CallbackQuery):
    checks = db.get_checks(callback.from_user.id)
    
    if not checks:
        await callback.message.edit_text(
            f"{premium('balance')} <b>У ВАС НЕТ ЧЕКОВ</b>",
            reply_markup=get_main_menu_button()
        )
        await callback.answer()
        return
    
    text = f"{premium('balance')} <b>ВАШИ ЧЕКИ</b>\n\n"
    for c in checks:
        text += f"#{c['id']} | {c['amount']} {premium('dollar')} | {c['uses_left']}/{c['uses']} | {c['created_at'][:10]}\n"
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_button())
    await callback.answer()

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
        db.update_turnover(uid, bet)

    new_bal = db.get_balance(uid)
    text += f"\n\n{premium('balance')} БАЛАНС: {new_bal:.2f} {premium('dollar')}"
    await msg.reply(text, reply_markup=get_back_buttons())
    await callback.answer()

# ==================== МИНЫ ====================
active_games = {}

@dp.callback_query(F.data == "mines_menu")
async def mines_menu(callback: CallbackQuery):
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
    uid = callback.from_user.id
    bal = db.get_balance(uid)
    bet = db.get_bet(uid)

    if bal < bet:
        await callback.answer("❌ НЕДОСТАТОЧНО СРЕДСТВ!", show_alert=True)
        return

    db.update_balance(uid, -bet)
    
    field = GameLogic.generate_mines_field(2)
    field_str = ",".join(map(str, field))
    game_id = db.create_mines_game(uid, bet, field_str)
    
    active_games[game_id] = {
        "field": field,
        "opened": [],
        "active": True,
        "bet": bet,
        "user_id": uid
    }
    
    user = db.get_user(uid)
    name = user["username"] or user["first_name"] or f"ID{uid}"
    
    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ИГРА #{game_id}</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {bal - bet:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {bet:.2f} {premium('dollar')}\n\n"
        f"💣 МИН: 2\n"
        f"⬛ ОТКРЫВАЙ КЛЕТКИ:",
        reply_markup=get_mines_field_buttons(game_id, [], True, 1.0)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("cell_"))
async def mines_cell(callback: CallbackQuery):
    try:
        idx = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("❌ ОШИБКА!", show_alert=True)
        return

    game_id = None
    game = None
    for gid, g in active_games.items():
        if g["user_id"] == callback.from_user.id and g["active"]:
            game_id = gid
            game = g
            break
    
    if not game:
        await callback.answer("❌ ИГРА НЕ НАЙДЕНА!", show_alert=True)
        return

    if idx in game["opened"]:
        await callback.answer("✅ УЖЕ ОТКРЫТО!", show_alert=True)
        return

    if game["field"][idx] == 1:
        game["active"] = False
        db.update_mines_game(game_id, ",".join(map(str, game["opened"])), 0)
        
        user = db.get_user(callback.from_user.id)
        name = user["username"] or user["first_name"] or f"ID{callback.from_user.id}"
        
        await callback.message.edit_text(
            f"{premium('lightning')} <b>МИНЫ | ПРОИГРЫШ</b>\n\n"
            f"👤 {name}\n"
            f"{premium('balance')} БАЛАНС: {db.get_balance(callback.from_user.id):.2f} {premium('dollar')}\n\n"
            f"💥 БАБАХ! ТЫ ПОДОРВАЛСЯ!",
            reply_markup=get_mines_field_buttons(game_id, game["opened"] + [idx], False, 0)
        )
        await callback.answer("💥 МИНА!", show_alert=True)
        return

    game["opened"].append(idx)
    db.update_mines_game(game_id, ",".join(map(str, game["opened"])), 1)

    mult = GameLogic.get_multiplier(len(game["opened"]))
    potential = game["bet"] * mult

    user = db.get_user(callback.from_user.id)
    name = user["username"] or user["first_name"] or f"ID{callback.from_user.id}"

    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ИГРА #{game_id}</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(callback.from_user.id):.2f} {premium('dollar')}\n"
        f"{premium('transfer')} СТАВКА: {game['bet']:.2f} {premium('dollar')}\n\n"
        f"📊 МНОЖИТЕЛЬ: x{mult}\n"
        f"💰 ВЫИГРЫШ: {potential:.2f} {premium('dollar')}\n"
        f"⬛ ОТКРЫТО: {len(game['opened'])}",
        reply_markup=get_mines_field_buttons(game_id, game["opened"], True, mult)
    )
    await callback.answer()

@dp.callback_query(F.data == "take")
async def mines_take(callback: CallbackQuery):
    game_id = None
    game = None
    for gid, g in active_games.items():
        if g["user_id"] == callback.from_user.id and g["active"]:
            game_id = gid
            game = g
            break
    
    if not game:
        await callback.answer("❌ ИГРА НЕ НАЙДЕНА!", show_alert=True)
        return

    if not game["opened"]:
        await callback.answer("❌ ОТКРОЙ ХОТЯ БЫ 1 КЛЕТКУ!", show_alert=True)
        return

    mult = GameLogic.get_multiplier(len(game["opened"]))
    win = game["bet"] * mult

    db.update_balance(callback.from_user.id, win)
    db.update_turnover(callback.from_user.id, game["bet"])
    game["active"] = False
    db.update_mines_game(game_id, ",".join(map(str, game["opened"])), 0)

    user = db.get_user(callback.from_user.id)
    name = user["username"] or user["first_name"] or f"ID{callback.from_user.id}"

    await callback.message.edit_text(
        f"{premium('lightning')} <b>МИНЫ | ВЫИГРЫШ</b>\n\n"
        f"👤 {name}\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(callback.from_user.id):.2f} {premium('dollar')}\n\n"
        f"✅ ВЫИГРЫШ: {win:.2f} {premium('dollar')} (x{mult})",
        reply_markup=get_mines_field_buttons(game_id, game["opened"], False, mult)
    )
    await callback.answer(f"💰 +{win:.2f} {premium('dollar')}", show_alert=True)

# ==================== БЫСТРЫЙ КОНКУРС (CALLBACK) ====================
@dp.callback_query(F.data.startswith("fast_join_"))
async def fast_join(callback: CallbackQuery):
    contest_id = callback.data.replace("fast_join_", "")
    
    if contest_id not in db.fast_contests:
        await callback.answer("❌ КОНКУРС НЕ НАЙДЕН!", show_alert=True)
        return
    
    contest = db.fast_contests[contest_id]
    
    if not contest["active"]:
        await callback.answer("❌ КОНКУРС УЖЕ ЗАВЕРШЕН!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    if any(p["id"] == user_id for p in contest["participants"]):
        await callback.answer("✅ ВЫ УЖЕ УЧАСТВУЕТЕ!", show_alert=True)
        return
    
    if len(contest["participants"]) >= 6:
        await callback.answer("❌ ВСЕ МЕСТА ЗАНЯТЫ!", show_alert=True)
        return
    
    user = callback.from_user
    contest["participants"].append({
        "id": user_id,
        "name": user.username or user.first_name or f"ID{user_id}"
    })
    
    contest_text = (
        f"{premium('dollar')} <b>БЫСТРЫЙ КОНКУРС</b> {premium('dollar')}\n\n"
        f"💰 <b>ПРИЗОВОЙ ФОНД:</b> {contest['amount']} {premium('dollar')}\n"
        f"🎲 <b>УЧАСТНИКОВ:</b> {len(contest['participants'])}/6\n\n"
        f"<b>УЧАСТНИКИ:</b>\n"
    )
    
    for i, p in enumerate(contest["participants"], 1):
        contest_text += f"{i}. {p['name']}\n"
    
    if len(contest["participants"]) == 6:
        contest["active"] = False
        
        msg = await bot.send_dice(callback.message.chat.id, emoji=DiceEmoji.DICE)
        dice_value = msg.dice.value
        
        winner_index = dice_value
        if winner_index > 6:
            winner_index = 6
        winner = contest["participants"][winner_index - 1]
        
        db.update_balance(winner["id"], contest["amount"])
        
        contest_text += f"\n{premium('dice')} <b>ВЫПАЛО: {dice_value}</b>\n"
        contest_text += f"{premium('balance')} <b>ПОБЕДИТЕЛЬ: {winner['name']}</b>\n"
        contest_text += f"{premium('dollar')} <b>ВЫИГРЫШ: +{contest['amount']}$</b>"
        
        await callback.message.edit_text(contest_text)
        
        try:
            await bot.send_message(
                winner["id"],
                f"{premium('balance')} <b>ВЫ ПОБЕДИЛИ В КОНКУРСЕ!</b>\n\n"
                f"💰 ВЫИГРЫШ: +{contest['amount']} {premium('dollar')}"
            )
        except:
            pass
        
        del db.fast_contests[contest_id]
    else:
        await callback.message.edit_text(
            contest_text,
            reply_markup=get_fast_participate_button(contest_id)
        )
    
    await callback.answer()

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
        if not message.text:
            await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")
            return
            
        bet = float(message.text.replace("$", "").replace(",", "."))
        if bet <= 0:
            await message.answer(f"{premium('dollar')} СТАВКА ДОЛЖНА БЫТЬ > 0")
            return
        if bet < 0.1:
            await message.answer(f"{premium('dollar')} МИНИМАЛЬНАЯ СТАВКА 0.1$")
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
        f"{premium('deposit')} <b>ПОПОЛНЕНИЕ ЧЕРЕЗ АДМИНА</b>\n\n"
        f"💰 Для пополнения напишите администратору:\n"
        f"{WITHDRAW_ADMIN}\n\n"
        f"📝 Укажите ваш ID: <code>{callback.from_user.id}</code> и сумму",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WithdrawStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('withdraw')} <b>ВЫВОД СРЕДСТВ</b>\n\n"
        f"{premium('balance')} БАЛАНС: {db.get_balance(callback.from_user.id):.2f} {premium('dollar')}\n"
        f"💰 МИНИМУМ: 1.1$\n\n"
        f"📝 ВВЕДИ СУММУ ДЛЯ ВЫВОДА:",
        reply_markup=get_main_menu_button()
    )
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")
            return
            
        amount = float(message.text.replace("$", ""))
        uid = message.from_user.id
        bal = db.get_balance(uid)
        
        if amount < 1.1:
            await message.answer(f"{premium('dollar')} МИНИМУМ 1.1$")
            return
        if amount > bal:
            await message.answer(f"{premium('dollar')} НЕДОСТАТОЧНО СРЕДСТВ")
            return
        
        payment_id = db.save_payment_request(uid, amount, "withdraw")
        
        user = db.get_user(uid)
        name = user["username"] or user["first_name"] or f"ID{uid}"
        
        admin_text = (
            f"{premium('lightning')} <b>НОВЫЙ ЗАПРОС НА ВЫВОД</b>\n\n"
            f"👤 {name}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"💰 СУММА: {amount} {premium('dollar')}\n"
            f"📅 ЗАЯВКА №{payment_id}\n\n"
            f"Для подтверждения нажми /confirm_{payment_id}"
        )
        
        await bot.send_message(ADMIN_ID, admin_text)
        
        await message.answer(
            f"{premium('withdraw')} <b>ЗАЯВКА НА ВЫВОД СОЗДАНА!</b>\n\n"
            f"💰 СУММА: {amount} {premium('dollar')}\n"
            f"📅 НОМЕР: #{payment_id}\n\n"
            f"⏳ Ожидайте подтверждения от администратора {WITHDRAW_ADMIN}",
            reply_markup=get_main_menu_button()
        )
        await state.clear()
        
    except ValueError:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

# ==================== АДМИНКА ====================
@dp.message(lambda message: message.text and message.text.startswith('/confirm_'))
async def confirm_withdraw(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ НЕТ ПРАВ!")
        return
    
    try:
        payment_id = int(message.text.replace('/confirm_', ''))
        payments = db.get_payment_requests()
        
        payment = next((p for p in payments if p["id"] == payment_id), None)
        if not payment:
            await message.answer("❌ ЗАЯВКА НЕ НАЙДЕНА")
            return
        
        db.confirm_payment(payment_id)
        db.update_balance(payment["user_id"], -payment["amount"])
        
        await message.answer(f"✅ ВЫВОД #{payment_id} ПОДТВЕРЖДЕН")
        
        try:
            await bot.send_message(
                payment["user_id"],
                f"{premium('balance')} <b>ВЫВОД ПОДТВЕРЖДЕН!</b>\n\n"
                f"💰 СУММА: {payment['amount']} {premium('dollar')}\n"
                f"📅 НОМЕР: #{payment_id}\n\n"
                f"Свяжитесь с {WITHDRAW_ADMIN} для получения средств"
            )
        except:
            pass
            
    except Exception as e:
        await message.answer(f"❌ ОШИБКА: {e}")

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
    elif action == "withdraws":
        payments = db.get_payment_requests()
        if not payments:
            await callback.message.edit_text("📭 НЕТ АКТИВНЫХ ЗАЯВОК", reply_markup=get_main_menu_button())
        else:
            text = f"{premium('lightning')} <b>ЗАЯВКИ НА ВЫВОД</b>\n\n"
            for p in payments:
                user = db.get_user(p["user_id"])
                name = user["username"] or user["first_name"] or f"ID{p['user_id']}"
                text += f"#{p['id']} | {name} | {p['amount']}$\n"
            await callback.message.edit_text(text, reply_markup=get_main_menu_button())
    elif action == "checks":
        checks = db.get_checks()
        if not checks:
            await callback.message.edit_text("📭 НЕТ ЧЕКОВ", reply_markup=get_main_menu_button())
        else:
            text = f"{premium('lightning')} <b>ВСЕ ЧЕКИ</b>\n\n"
            for c in checks:
                user = db.get_user(c["user_id"])
                name = user["username"] or user["first_name"] or f"ID{c['user_id']}"
                text += f"#{c['id']} | {name} | {c['amount']}$ | {c['uses_left']}/{c['uses']} | {c['created_at'][:10]}\n"
            await callback.message.edit_text(text, reply_markup=get_main_menu_button())
    elif action == "fast":
        await state.set_state(AdminStates.waiting_for_fast_amount)
        await callback.message.edit_text(
            f"{premium('dollar')} <b>БЫСТРЫЙ КОНКУРС</b>\n\n"
            f"💰 ВВЕДИ СУММУ ПРИЗА:",
            reply_markup=get_main_menu_button()
        )
    await callback.answer()

@dp.message(AdminStates.waiting_for_fast_amount)
async def admin_fast_amount(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")
            return
            
        amount = float(message.text.replace("$", ""))
        if amount < 0.1:
            await message.answer(f"{premium('dollar')} Минимальная сумма 0.1$")
            return
        
        contest_id = f"fast_{datetime.now().timestamp()}"
        db.fast_contests[contest_id] = {
            "amount": amount,
            "participants": [],
            "active": True,
            "created_by": message.from_user.id
        }
        
        contest_text = (
            f"{premium('dollar')} <b>БЫСТРЫЙ КОНКУРС</b> {premium('dollar')}\n\n"
            f"💰 <b>ПРИЗОВОЙ ФОНД:</b> {amount} {premium('dollar')}\n"
            f"🎲 <b>УЧАСТНИКОВ:</b> 0/6\n\n"
            f"<b>УЧАСТНИКИ:</b>\n"
        )
        
        await message.answer(
            contest_text,
            reply_markup=get_fast_participate_button(contest_id)
        )
        await state.clear()
        
    except ValueError:
        await message.answer(f"{premium('dollar')} ВВЕДИ ЧИСЛО")

@dp.message(AdminStates.waiting_for_user_id_balance)
async def admin_add_id(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("❌ ВВЕДИ ID")
            return
            
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
        if not message.text:
            await message.answer("❌ ВВЕДИ СУММУ")
            return
            
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
        if not message.text:
            await message.answer("❌ ВВЕДИ ID")
            return
            
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
    if not message.text:
        await message.answer("❌ ВВЕДИ ТЕКСТ")
        return
        
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
