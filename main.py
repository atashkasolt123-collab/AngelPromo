import asyncio
import logging
import sqlite3
import random
from datetime import datetime
from typing import Dict, Optional, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import aiohttp

# ==================== ТОКЕНЫ ====================
BOT_TOKEN = "8216893084:AAGSY3AMqduQxL57HivPLqinBfESkGRho50"
ADMIN_ID = 7313407194
CRYPTOPAY_TOKEN = "531599:AAI1evU9c44MxbWqwMV6DNZ2PyWqDPzFnZV"

# ==================== ПРЕМИУМ ЭМОДЗИ (только для валюты/статуса) ====================
PREMIUM_EMOJIS = {
    "rocket": {"id": "5377336433692412420", "char": "🚀"},
    "dollar": {"id": "5377852667286559564", "char": "💲"},
    "transfer": {"id": "5377720025811555309", "char": "🔄"},
    "lightning": {"id": "5375469677696815127", "char": "⚡"},
    "casino": {"id": "5969709082049779216", "char": "🎰"},
    "balance": {"id": "5262509177363787445", "char": "💰"},
    "withdraw": {"id": "5226731292334235524", "char": "💸"},
    "deposit": {"id": "5226731292334235524", "char": "💳"},
}

def premium(name: str) -> str:
    """Возвращает премиум эмодзи в HTML формате"""
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
            cursor.execute("UPDATE OR IGNORE users SET is_admin = 1 WHERE user_id = ?", (ADMIN_ID,))
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

# ==================== CRYPTO BOT API ====================
class CryptoPayClient:
    def __init__(self, token: str, testnet: bool = True):
        self.token = token
        self.base_url = "https://testnet-pay.crypt.bot" if testnet else "https://pay.crypt.bot"
        self.headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(self, amount: float, asset: str = "USDT") -> Optional[Dict]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/createInvoice"
            params = {
                "asset": asset,
                "amount": str(amount),
                "description": "Пополнение игрового баланса"
            }
            async with session.post(url, headers=self.headers, data=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return data["result"]
        return None

    async def create_check(self, amount: float, asset: str = "USDT") -> Optional[Dict]:
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

# ==================== КЛАВИАТУРЫ (без премиум) ====================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Играть"), KeyboardButton(text="💬 Игровые чаты")],
            [KeyboardButton(text="👤 Профиль")]
        ],
        resize_keyboard=True
    )

def get_games_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 Кубы", callback_data="game_dice"),
         InlineKeyboardButton(text="🎰 Слоты", callback_data="game_slots"),
         InlineKeyboardButton(text="🎯 Дартс", callback_data="game_darts")],
        [InlineKeyboardButton(text="🎳 Боулинг", callback_data="game_bowling"),
         InlineKeyboardButton(text="💣 Режимы", callback_data="game_modes")],
        [InlineKeyboardButton(text="✏️ Изменить ставку", callback_data="change_bet")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_modes_keyboard():
    buttons = [[InlineKeyboardButton(text="💣 Мины (2 мины)", callback_data="mode_mines")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_mines_field_keyboard(game_id: int, opened_cells: list, game_active: bool):
    keyboard = []
    for i in range(5):
        row = []
        for j in range(5):
            cell_index = i * 5 + j
            if cell_index in opened_cells:
                row.append(InlineKeyboardButton(text="✅", callback_data=f"mines_opened_{game_id}_{cell_index}"))
            elif not game_active:
                row.append(InlineKeyboardButton(text="⬜", callback_data=f"mines_inactive_{game_id}"))
            else:
                row.append(InlineKeyboardButton(text="⬛", callback_data=f"mines_open_{game_id}_{cell_index}"))
        keyboard.append(row)
    if game_active:
        keyboard.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data=f"mines_cashout_{game_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_deposit_keyboard():
    buttons = [[InlineKeyboardButton(text="Crypto Bot", callback_data="deposit_crypto")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_withdraw_keyboard():
    buttons = [[InlineKeyboardButton(text="Crypto Bot (USDT)", callback_data="withdraw_crypto")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1️⃣ Пополнить баланс", callback_data="admin_add")],
        [InlineKeyboardButton(text="2️⃣ Аннулировать баланс", callback_data="admin_reset")],
        [InlineKeyboardButton(text="3️⃣ Рассылка", callback_data="admin_broadcast")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== ЛОГИКА ИГР ====================
class GameLogic:
    @staticmethod
    def play_dice(bet: float) -> Tuple[float, int]:
        dice_value = random.randint(1, 6)
        if dice_value >= 4:
            return bet * 1.9, dice_value
        return 0, dice_value

    @staticmethod
    def play_slots(bet: float) -> Tuple[float, list]:
        symbols = ["🍋", "🍒", "🍊", "7️⃣", "BAR"]
        result = [random.choice(symbols) for _ in range(3)]
        if all(s == "7️⃣" for s in result) or all(s == "BAR" for s in result) or all(s == "🍋" for s in result):
            return bet * 15, result
        return 0, result

    @staticmethod
    def play_darts(bet: float) -> Tuple[float, int]:
        score = random.randint(1, 20)
        if score == 20:
            return bet * 5, score
        elif score >= 15:
            return bet * 2, score
        return 0, score

    @staticmethod
    def play_bowling(bet: float) -> Tuple[float, int]:
        pins = random.randint(0, 10)
        if pins == 10:
            return bet * 5, pins
        return 0, pins

    @staticmethod
    def generate_mines_field(mines_count: int = 2) -> list:
        field = [0] * 25
        for pos in random.sample(range(25), mines_count):
            field[pos] = 1
        return field

    @staticmethod
    def get_mines_multiplier(opened_count: int) -> float:
        multipliers = [
            1.02, 1.11, 1.22, 1.34, 1.48, 1.65, 1.84, 2.07, 2.35, 2.69,
            3.1, 3.62, 4.27, 5.13, 6.27, 7.83, 10.07, 13.43, 18.8, 28.2,
            47, 94, 282
        ]
        return multipliers[opened_count - 1] if opened_count <= len(multipliers) else multipliers[-1]

# ==================== БОТ ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
db = Database()
crypto = CryptoPayClient(CRYPTOPAY_TOKEN)

# ==================== ХЕНДЛЕРЫ ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.create_user(user.id, user.username or "", user.first_name or "")
    await message.answer(
        f"{premium('rocket')} Привет, {user.first_name}! Добро пожаловать в Plays\n\n"
        f"Подписывайся на наш канал чтобы следить за новостями и конкурсами.",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("stars"))
@dp.message(F.text == "🎮 Играть")
async def cmd_stars(message: Message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    bet = db.get_bet(user_id)
    await message.answer(
        f"{premium('rocket')} Выбирайте игру или режим!\n\n"
        f"{premium('balance')} Баланс — {balance:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} Ставка — {bet:.2f} {premium('dollar')}",
        reply_markup=get_games_keyboard()
    )

@dp.message(F.text == "💬 Игровые чаты")
async def cmd_chats(message: Message):
    await message.answer("Скоро здесь появится список игровых чатов!")

@dp.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message):
    user = message.from_user
    user_data = db.get_user(user.id)
    balance = user_data["balance"] if user_data else 0
    await message.answer(
        f"{premium('rocket')} Игрок\n"
        f"ID игрока: <code>{user.id}</code>\n\n"
        f"{premium('balance')} Баланс — {balance:.2f} {premium('dollar')}",
        reply_markup=get_profile_keyboard()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user = db.get_user(message.from_user.id)
    if not user or not user["is_admin"]:
        await message.answer("У вас нет прав администратора.")
        return
    await message.answer("👑 Админ панель", reply_markup=get_admin_keyboard())

# ==================== ИГРЫ ====================
@dp.callback_query(F.data.startswith("game_"))
async def process_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    game_type = callback.data.split("_")[1]
    balance = db.get_balance(user_id)
    bet = db.get_bet(user_id)

    if balance < bet:
        await callback.message.edit_text(
            f"{premium('dollar')} Недостаточно средств!\n"
            f"{premium('balance')} Баланс: {balance:.2f} {premium('dollar')}"
        )
        await callback.answer()
        return

    db.update_balance(user_id, -bet)

    if game_type == "dice":
        win, value = GameLogic.play_dice(bet)
        result = f"🎲 Выпало: {value}"
    elif game_type == "slots":
        win, symbols = GameLogic.play_slots(bet)
        result = f"{' '.join(symbols)}"
    elif game_type == "darts":
        win, score = GameLogic.play_darts(bet)
        result = f"🎯 Очки: {score}"
    elif game_type == "bowling":
        win, pins = GameLogic.play_bowling(bet)
        result = f"🎳 Сбито: {pins}"
    else:
        await callback.answer("Игра в разработке")
        return

    if win > 0:
        db.update_balance(user_id, win)
        result += f"\n✅ Победа! +{win:.2f} {premium('dollar')}"
    else:
        result += "\n❌ Проигрыш"

    new_balance = db.get_balance(user_id)
    result += f"\n\n{premium('balance')} Баланс: {new_balance:.2f} {premium('dollar')}"
    await callback.message.edit_text(result)
    await callback.answer()

@dp.callback_query(F.data == "game_modes")
async def process_modes(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    bet = db.get_bet(user_id)
    await callback.message.edit_text(
        f"{premium('rocket')} Выбирайте мини-игру!\n\n"
        f"{premium('balance')} Баланс — {balance:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} Ставка — {bet:.2f} {premium('dollar')}",
        reply_markup=get_modes_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "mode_mines")
async def process_mines_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    bet = db.get_bet(user_id)

    if balance < bet:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    db.update_balance(user_id, -bet)
    field = GameLogic.generate_mines_field(2)
    game_id = db.create_mines_game(user_id, bet, ",".join(map(str, field)))
    user_data = db.get_user(user_id)
    username = user_data["username"] or user_data["first_name"] or f"ID {user_id}"

    await callback.message.edit_text(
        f"{premium('bomb', '💣')} Мины\n\n"
        f"{username}\n"
        f"{premium('balance')} Баланс — {balance - bet:.2f} {premium('dollar')}\n"
        f"{premium('transfer')} Ставка — {bet:.2f} {premium('dollar')}\n\n"
        f"Выбрано — 2 💣",
        reply_markup=get_mines_field_keyboard(game_id, [], True)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("mines_open_"))
async def process_mines_open(callback: CallbackQuery):
    parts = callback.data.split("_")
    game_id = int(parts[2])
    cell_index = int(parts[3])

    game = db.get_mines_game(game_id)
    if not game or not game["game_active"]:
        await callback.answer("Игра уже закончена!")
        return

    opened = list(map(int, game["opened_cells"].split(","))) if game["opened_cells"] else []
    if cell_index in opened:
        await callback.answer("Клетка уже открыта!")
        return

    field = list(map(int, game["field"].split(",")))

    if field[cell_index] == 1:
        db.update_mines_game(game_id, game["opened_cells"], 0)
        user_data = db.get_user(game["user_id"])
        username = user_data["username"] or user_data["first_name"] or f"ID {game['user_id']}"
        await callback.message.edit_text(
            f"{premium('bomb', '💣')} Мины\n\n"
            f"{username}\n"
            f"{premium('balance')} Баланс — {db.get_balance(game['user_id']):.2f} {premium('dollar')}\n"
            f"{premium('transfer')} Ставка — {game['bet']:.2f} {premium('dollar')}\n\n"
            f"💥 БАБАХ! Ты подорвался!",
            reply_markup=get_mines_field_keyboard(game_id, opened + [cell_index], False)
        )
        await callback.answer("💥 Мина!", show_alert=True)
        return

    opened.append(cell_index)
    db.update_mines_game(game_id, ",".join(map(str, opened)), 1)

    multiplier = GameLogic.get_mines_multiplier(len(opened))
    potential_win = game["bet"] * multiplier
    user_data = db.get_user(game["user_id"])
    username = user_data["username"] or user_data["first_name"] or f"ID {game['user_id']}"

    await callback.message.edit_text(
        f"{premium('bomb', '💣')} Мины\n\n"
        f"{username}\n"
        f"{premium('balance')} Баланс — {db.get_balance(game['user_id']):.2f} {premium('dollar')}\n"
        f"{premium('transfer')} Ставка — {game['bet']:.2f} {premium('dollar')}\n\n"
        f"💰 Потенциальный выигрыш: {potential_win:.2f} {premium('dollar')} (x{multiplier})",
        reply_markup=get_mines_field_keyboard(game_id, opened, True)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("mines_cashout_"))
async def process_mines_cashout(callback: CallbackQuery):
    game_id = int(callback.data.split("_")[2])
    game = db.get_mines_game(game_id)

    if not game or not game["game_active"]:
        await callback.answer("Игра уже закончена!")
        return

    opened = list(map(int, game["opened_cells"].split(","))) if game["opened_cells"] else []
    if not opened:
        await callback.answer("Открой хотя бы одну клетку!")
        return

    multiplier = GameLogic.get_mines_multiplier(len(opened))
    win = game["bet"] * multiplier
    db.update_balance(game["user_id"], win)
    db.update_mines_game(game_id, game["opened_cells"], 0)

    user_data = db.get_user(game["user_id"])
    username = user_data["username"] or user_data["first_name"] or f"ID {game['user_id']}"

    await callback.message.edit_text(
        f"{premium('bomb', '💣')} Мины\n\n"
        f"{username}\n"
        f"{premium('balance')} Баланс — {db.get_balance(game['user_id']):.2f} {premium('dollar')}\n"
        f"{premium('transfer')} Ставка — {game['bet']:.2f} {premium('dollar')}\n\n"
        f"✅ Выигрыш: {win:.2f} {premium('dollar')} (x{multiplier})",
        reply_markup=get_mines_field_keyboard(game_id, opened, False)
    )
    await callback.answer(f"💰 Выигрыш {win:.2f} {premium('dollar')} зачислен!", show_alert=True)

@dp.callback_query(F.data == "change_bet")
async def process_change_bet(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BetChangeStates.waiting_for_new_bet)
    await callback.message.edit_text(
        f"✏️ Чтобы изменить ставку, напишите в чат новую сумму\n"
        f"Пример: 2{premium('dollar')}"
    )
    await callback.answer()

@dp.message(BetChangeStates.waiting_for_new_bet)
async def process_new_bet(message: Message, state: FSMContext):
    try:
        new_bet = float(message.text.replace("$", "").replace(",", ".").strip())
        if new_bet <= 0:
            await message.answer("❌ Ставка должна быть больше 0")
            return
        db.set_bet(message.from_user.id, new_bet)
        await state.clear()
        await message.answer(
            f"✅ Ставка изменена на {new_bet:.2f} {premium('dollar')}",
            reply_markup=get_main_keyboard()
        )
    except ValueError:
        await message.answer("❌ Введите число. Например: 2.5")

# ==================== ПРОФИЛЬ ====================
@dp.callback_query(F.data == "deposit")
async def process_deposit(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('deposit')} Выберите способ пополнения",
        reply_markup=get_deposit_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "deposit_crypto")
async def process_deposit_crypto(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('deposit')} Введите сумму пополнения в {premium('dollar')} от 0.1$"
    )
    await callback.answer()

@dp.message(DepositStates.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace("$", "").strip())
        if amount < 0.1:
            await message.answer("❌ Минимальная сумма 0.1$")
            return
        fee = amount * 0.03 if amount > 0.15 else 0
        invoice = await crypto.create_invoice(amount)
        if invoice:
            await message.answer(
                f"{premium('deposit')} Нажмите ниже, чтобы пополнить баланс\n\n"
                f"Сумма: {amount}$\nКомиссия: {fee:.2f}$\nК зачислению: {amount - fee:.2f}$",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Пополнить", url=invoice["pay_url"])]
                ])
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка создания счета")
    except ValueError:
        await message.answer("❌ Введите корректную сумму")

@dp.callback_query(F.data == "withdraw")
async def process_withdraw(callback: CallbackQuery):
    await callback.message.edit_text(
        f"{premium('withdraw')} Выберите способ вывода",
        reply_markup=get_withdraw_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw_crypto")
async def process_withdraw_crypto(callback: CallbackQuery, state: FSMContext):
    balance = db.get_balance(callback.from_user.id)
    await state.set_state(WithdrawStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{premium('withdraw')} Введите сумму вывода от 1$\n"
        f"Ваш баланс: {balance:.2f} {premium('dollar')}"
    )
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace("$", "").strip())
        user_id = message.from_user.id
        balance = db.get_balance(user_id)

        if amount < 1:
            await message.answer("❌ Минимальная сумма 1$")
            return
        if amount > balance:
            await message.answer(f"❌ Недостаточно средств")
            return

        check = await crypto.create_check(amount)
        if check:
            db.update_balance(user_id, -amount)
            await message.answer(
                f"{premium('withdraw')} Ваш чек:\n\n{check['check_url']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💰 Получить", url=check["check_url"])]
                ])
            )
            await state.clear()
        else:
            await message.answer("❌ Ошибка создания чека")
    except ValueError:
        await message.answer("❌ Введите корректную сумму")

# ==================== АДМИНКА ====================
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin(callback: CallbackQuery, state: FSMContext):
    user = db.get_user(callback.from_user.id)
    if not user or not user["is_admin"]:
        await callback.answer("Нет прав!")
        return

    action = callback.data.split("_")[1]
    if action == "add":
        await state.set_state(AdminStates.waiting_for_user_id_balance)
        await callback.message.edit_text("Введите ID пользователя для пополнения:")
    elif action == "reset":
        await state.set_state(AdminStates.waiting_for_user_id_reset)
        await callback.message.edit_text("Введите ID пользователя для обнуления баланса:")
    elif action == "broadcast":
        await state.set_state(AdminStates.waiting_for_message)
        await callback.message.edit_text("Введите текст для рассылки:")
    await callback.answer()

@dp.message(AdminStates.waiting_for_user_id_balance)
async def admin_add_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        user = db.get_user(user_id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminStates.waiting_for_amount_balance)
        await message.answer(f"Введите сумму (текущий баланс: {user['balance']:.2f}$):")
    except ValueError:
        await message.answer("❌ Введите корректный ID")

@dp.message(AdminStates.waiting_for_amount_balance)
async def admin_add_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        new_balance = db.update_balance(data["target_user_id"], amount)
        await message.answer(f"✅ Баланс пополнен. Новый баланс: {new_balance:.2f}$")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректную сумму")

@dp.message(AdminStates.waiting_for_user_id_reset)
async def admin_reset_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if not db.get_user(user_id):
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        db.set_balance(user_id, 0)
        await message.answer(f"✅ Баланс пользователя {user_id} обнулен")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректный ID")

@dp.message(AdminStates.waiting_for_message)
async def admin_broadcast(message: Message, state: FSMContext):
    text = message.text
    users = db.get_all_users()
    sent = 0
    failed = 0
    status = await message.answer(f"📨 Рассылка... 0/{len(users)}")
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except:
            failed += 1
        if (sent + failed) % 10 == 0:
            await status.edit_text(f"📨 Прогресс: {sent + failed}/{len(users)}\n✅ {sent} | ❌ {failed}")
    await status.edit_text(f"✅ Рассылка завершена!\nУспешно: {sent}\nОшибок: {failed}")
    await state.clear()

# ==================== ЗАПУСК ====================
async def main():
    print("🚀 Бот запущен с премиум эмодзи!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
