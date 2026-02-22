import warnings
warnings.filterwarnings("ignore", category=UserWarning, message='Field "model_custom_emoji_id" has conflict with protected namespace "model_"')

import asyncio
import logging
import sys
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery, LinkPreviewOptions
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import hashlib
import json
import config

import re

# --- Состояния FSM ---
class DepositState(StatesGroup):
    entering_amount = State()

class WithdrawState(StatesGroup):
    entering_amount = State()
    choosing_method = State()

class PrivacyState(StatesGroup):
    entering_nickname = State()

class BetState(StatesGroup):
    entering_bet = State()

class MinesState(StatesGroup):
    choosing_mines = State()
    playing = State()

class TowerState(StatesGroup):
    choosing_mines = State()
    playing = State()

class PlayingState(StatesGroup):
    dice = State()
    custom = State()
    old = State()
    strategy = State()

# --- API Клиенты ---
class CryptoPay:
    def __init__(self, token):
        self.token = token
        self.api_url = "https://pay.crypt.bot/api/"

    async def create_invoice(self, amount, currency="USD"):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            payload = {
                "asset": "USDT",
                "amount": str(amount),
                "description": "Deposit",
                "paid_btn_name": "callback",
                "paid_btn_url": "https://t.me/spins"
            }
            async with session.post(f"{self.api_url}createInvoice", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]["pay_url"], data["result"]["invoice_id"]
                return None, None

    async def get_invoice(self, invoice_id):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            params = {"invoice_ids": str(invoice_id)}
            async with session.get(f"{self.api_url}getInvoices", params=params, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok") and data["result"]["items"]:
                    return data["result"]["items"][0]
                return None

    async def transfer(self, user_id, amount, asset="USDT"):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            spend_id = hashlib.md5(f"{user_id}_{amount}_{datetime.now()}".encode()).hexdigest()
            payload = {
                "user_id": int(user_id),
                "asset": asset,
                "amount": str(amount),
                "spend_id": spend_id
            }
            async with session.post(f"{self.api_url}transfer", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return True, data["result"]
                return False, data.get("error", {}).get("name", "Unknown error")

    async def create_check(self, amount, asset="USDT", pin_to_user_id=None):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            payload = {
                "asset": asset,
                "amount": str(amount)
            }
            if pin_to_user_id:
                payload["pin_to_user_id"] = pin_to_user_id
            
            async with session.post(f"{self.api_url}createCheck", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]["bot_check_url"]
                return None

    async def get_balance(self):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            async with session.get(f"{self.api_url}getBalance", headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]
                return None

    async def get_exchange_rates(self):
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": self.token}
            async with session.get(f"{self.api_url}getExchangeRates", headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]
                return None

class XRocket:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api_url = "https://pay.xrocket.io/api/"

    async def create_invoice(self, amount):
        async with aiohttp.ClientSession() as session:
            headers = {"Rocket-Pay-Key": self.api_key}
            payload = {
                "amount": float(amount),
                "currency": "USD",
                "description": "Deposit",
                "hiddenMessage": "Thank you!",
                "callbackUrl": "https://example.com/callback"
            }
            async with session.post(f"{self.api_url}v1/invoice/create", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"]["link"], data["data"]["id"]
                return None, None

    async def get_invoice(self, invoice_id):
        async with aiohttp.ClientSession() as session:
            headers = {"Rocket-Pay-Key": self.api_key}
            async with session.get(f"{self.api_url}v1/invoice/{invoice_id}", headers=headers) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"]
                return None

    async def transfer(self, user_id, amount, currency="USD"):
        async with aiohttp.ClientSession() as session:
            headers = {"Rocket-Pay-Key": self.api_key}
            payload = {
                "tgUserId": int(user_id),
                "currency": currency,
                "amount": float(amount)
            }
            async with session.post(f"{self.api_url}v1/transfer", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("success"):
                    return True, data["data"]
                return False, data.get("error", {}).get("message", "Unknown error")

    async def create_check(self, amount, currency="USD", pin_to_user_id=None):
        async with aiohttp.ClientSession() as session:
            headers = {"Rocket-Pay-Key": self.api_key}
            payload = {
                "currency": currency,
                "amount": float(amount),
                "chequesCount": 1
            }
            if pin_to_user_id:
                payload["forUserId"] = int(pin_to_user_id)
            
            async with session.post(f"{self.api_url}v1/cheque/create", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"]["cheques"][0]["link"]
                return None

    async def get_balance(self):
        async with aiohttp.ClientSession() as session:
            headers = {"Rocket-Pay-Key": self.api_key}
            async with session.get(f"{self.api_url}v1/balance", headers=headers) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"]
                return None

crypto_pay = CryptoPay(config.CRYPTO_PAY_TOKEN)
xrocket = XRocket(config.XROCKET_API_KEY)

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# --- База данных ---
class Database:
    def __init__(self, db_name="users.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                reg_date TEXT,
                player_num INTEGER,
                lang TEXT DEFAULT 'ru',
                balance REAL DEFAULT 0.0,

                privacy_type TEXT DEFAULT 'username',
                nickname TEXT,
                total_bets INTEGER DEFAULT 0,
                total_turnover REAL DEFAULT 0.0,
                total_deposits REAL DEFAULT 0.0,
                total_withdrawals REAL DEFAULT 0.0,
                current_bet REAL DEFAULT 0.2,
                referrer_id INTEGER,
                ref_balance REAL DEFAULT 0.0,
                total_ref_earned REAL DEFAULT 0.0,
                rank_id INTEGER DEFAULT 0
            )
        """)
        # Таблица для предотвращения повторного зачисления платежей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_invoices (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                date TEXT
            )
        """)
        # Проверяем колонки
        self.cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if "balance" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0.0")
        if "privacy_type" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN privacy_type TEXT DEFAULT 'username'")
        if "nickname" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT")
        if "total_bets" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN total_bets INTEGER DEFAULT 0")
        if "total_turnover" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN total_turnover REAL DEFAULT 0.0")
        if "total_deposits" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN total_deposits REAL DEFAULT 0.0")
        if "total_withdrawals" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN total_withdrawals REAL DEFAULT 0.0")
        if "current_bet" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN current_bet REAL DEFAULT 0.2")
        if "referrer_id" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        if "ref_balance" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN ref_balance REAL DEFAULT 0.0")
        if "total_ref_earned" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN total_ref_earned REAL DEFAULT 0.0")
        if "rank_id" not in columns:
            self.cursor.execute("ALTER TABLE users ADD COLUMN rank_id INTEGER DEFAULT 0")
        self.conn.commit()

    def is_invoice_processed(self, invoice_id):
        self.cursor.execute("SELECT 1 FROM processed_invoices WHERE invoice_id = ?", (invoice_id,))
        return self.cursor.fetchone() is not None

    def mark_invoice_processed(self, invoice_id, user_id, amount, method):
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO processed_invoices (invoice_id, user_id, amount, method, date) VALUES (?, ?, ?, ?, ?)",
            (invoice_id, user_id, amount, method, date)
        )
        self.conn.commit()

    def register_user(self, user_id, username, referrer_id=None):
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("SELECT COUNT(*) FROM users")
            count = self.cursor.fetchone()[0]
            player_num = count + 1
            reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO users (user_id, username, reg_date, player_num, balance, total_bets, total_turnover, total_deposits, total_withdrawals, current_bet, referrer_id, ref_balance, total_ref_earned, rank_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, reg_date, player_num, 0.0, 0, 0.0, 0.0, 0.0, 0.2, referrer_id, 0.0, 0.0, 0)
            )
            self.conn.commit()
            return True
        return False

    def get_user_data(self, user_id):
        self.cursor.execute("SELECT reg_date, player_num, lang, balance, privacy_type, nickname, username, total_bets, total_turnover, total_deposits, total_withdrawals, current_bet, referrer_id, ref_balance, total_ref_earned, rank_id FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def add_ref_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET ref_balance = ref_balance + ?, total_ref_earned = total_ref_earned + ? WHERE user_id = ?", (amount, amount, user_id))
        self.conn.commit()

    def claim_ref_balance(self, user_id):
        # Атомарная операция получения и сброса реферального баланса
        self.cursor.execute("SELECT ref_balance FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        if not row:
            return 0
        balance = row[0]
        if balance >= 1.0:
            # Сначала обнуляем, потом добавляем на основной баланс (или используем транзакцию)
            self.cursor.execute("UPDATE users SET ref_balance = 0 WHERE user_id = ? AND ref_balance = ?", (user_id, balance))
            if self.cursor.rowcount > 0:
                self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (balance, user_id))
                self.conn.commit()
                return balance
        return 0

    def get_ref_stats(self, user_id):
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        count = self.cursor.fetchone()[0]
        return count

    def set_bet(self, user_id, amount):
        if amount < 0: amount = 0 # Защита от отрицательных ставок
        self.cursor.execute("UPDATE users SET current_bet = ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def add_balance(self, user_id, amount, is_deposit=False, is_withdraw=False, is_bet=False):
        # Атомарное обновление баланса
        if is_bet or is_withdraw:
            # Списание (ставка или вывод): проверяем, что баланс >= абсолютной величине
            self.cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ? AND balance >= ?",
                (amount, user_id, abs(amount))
            )
        else:
            # Начисление (выигрыш или депозит)
            self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        
        if self.cursor.rowcount == 0:
            return False
        
        if is_deposit:
            self.cursor.execute("UPDATE users SET total_deposits = total_deposits + ? WHERE user_id = ?", (amount, user_id))
        if is_withdraw:
            self.cursor.execute("UPDATE users SET total_withdrawals = total_withdrawals + ? WHERE user_id = ?", (abs(amount), user_id))
        if is_bet:
            # Обновляем количество ставок и оборот
            self.cursor.execute("UPDATE users SET total_bets = total_bets + 1, total_turnover = total_turnover + ? WHERE user_id = ?", (abs(amount), user_id))
            
            # Логика повышения ранга: каждые 1000 оборота = +1 ранг
            self.cursor.execute("SELECT total_turnover FROM users WHERE user_id = ?", (user_id,))
            turnover_row = self.cursor.fetchone()
            if turnover_row:
                turnover = turnover_row[0]
                new_rank = int(turnover // 1000)
                self.cursor.execute("UPDATE users SET rank_id = ? WHERE user_id = ?", (new_rank, user_id))
            
        self.conn.commit()
        return True

    def set_lang(self, user_id, lang):
        self.cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        self.conn.commit()

    def set_privacy(self, user_id, privacy_type):
        self.cursor.execute("UPDATE users SET privacy_type = ? WHERE user_id = ?", (privacy_type, user_id))
        self.conn.commit()

    def set_nickname(self, user_id, nickname):
        self.cursor.execute("UPDATE users SET nickname = ? WHERE user_id = ?", (nickname, user_id))
        self.conn.commit()

db = Database()

# Инициализируем диспетчер
dp = Dispatcher()

# --- Глобальные настройки ---
RANKS = [
    "🌑 None", "🥉 Bronze", "🥈 Silver", "🥇 Gold", "💎 Platinum", 
    "🏆 Diamond", "👑 Master", "🔥 Grandmaster", "✨ Legend", "🌌 Immortal"
]

# Глобальный юзернейм бота (обновится при запуске)
BOT_USERNAME = "@spins"

async def update_bot_username(bot: Bot):
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = f"@{me.username}"

def get_lang(user_id: int) -> str:
    """Возвращает язык пользователя из БД"""
    data = db.get_user_data(user_id)
    return data[2] if data else "ru"

def get_text(user_id: int, key: str) -> str:
    """Возвращает текст по ключу для текущего языка пользователя с заменой юзернейма бота"""
    lang = get_lang(user_id)
    text = config.TEXTS[lang].get(key, "")
    if isinstance(text, str):
        text = text.replace("@spins", BOT_USERNAME).replace("spins", BOT_USERNAME.replace("@", ""))
    return text

def get_btn(user_id: int, key: str) -> str:
    """Возвращает текст кнопки по ключу с заменой юзернейма бота"""
    lang = get_lang(user_id)
    text = config.TEXTS[lang]["buttons"].get(key, "")
    if isinstance(text, str):
        text = text.replace("@spins", BOT_USERNAME).replace("spins", BOT_USERNAME.replace("@", ""))
    return text

def get_user_display_name(user_id: int, first_name: str = "Игрок") -> str:
    """Возвращает отображаемое имя пользователя (всегда @username согласно запросу)"""
    data = db.get_user_data(user_id)
    if not data:
        return first_name
    
    reg_date, player_num, lang, balance, privacy_type, nickname, username, *rest = data
    
    if username:
        return f"@{username}"
    
    return first_name

async def check_owner(callback: CallbackQuery, owner_id: int) -> bool:
    """Проверяет, является ли пользователь владельцем сообщения/кнопки"""
    if callback.from_user.id != owner_id:
        await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
        return False
    return True

def get_main_keyboard(user_id: int):
    """Возвращает клавиатуру главного меню"""
    builder = InlineKeyboardBuilder()
    
    # 1 ряд: Играть, Игровые чаты
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "play"), callback_data=f"play:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "chats"), callback_data=f"chats:{user_id}")
    )
    
    # 2 ряд: Профиль, Реф. программа
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "profile"), callback_data=f"profile:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "referral"), callback_data=f"referral:{user_id}")
    )
    
    # 4 ряд: Язык
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "language"), callback_data=f"language:{user_id}")
    )
    return builder.as_markup()

def get_back_button(user_id: int):
    """Возвращает кнопку Назад"""
    return InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"main_menu:{user_id}")

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Обработка реферальной ссылки
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("invite_"):
        try:
            potential_ref_id = args[1].replace("invite_", "")
            if potential_ref_id.isdigit():
                referrer_id = int(potential_ref_id)
                if referrer_id == user_id:
                    referrer_id = None # Нельзя пригласить самого себя
        except:
            pass

    # Регистрируем пользователя в БД
    is_new = db.register_user(user_id, username, referrer_id)
    
    if is_new and referrer_id:
        try:
            # Можно отправить уведомление пригласителю
            await message.bot.send_message(referrer_id, f"👤 У вас новый реферал: <b>{username}</b>!")
        except:
            pass
        
    await message.answer(
        get_text(user_id, "welcome"), 
        reply_markup=get_main_keyboard(user_id), 
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text.regexp(r"(?i)(дартс|футбол|боулинг|слоты|баскетбол|мины|башня)"))
async def game_text_handler(message: Message, state: FSMContext):
    """Обработчик текстовых команд для запуска игр"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    db.register_user(user_id, username) # Убеждаемся, что пользователь зарегистрирован

    text = message.text.lower()
    game_map = {
        "дартс": "darts",
        "футбол": "soccer",
        "боулинг": "bowling",
        "слоты": "slots",
        "баскетбол": "basket",
        "мины": "mines",
        "башня": "tower"
    }
    
    game_type = None
    for key in game_map:
        if key in text:
            game_type = game_map[key]
            break
            
    if game_type == "mines":
        await show_mines_menu(message, user_id, state, edit=False)
    elif game_type == "tower":
        await show_tower_menu(message, user_id, state, edit=False)
    elif game_type:
        await emoji_strategy_menu(message, state, game_type)

@dp.message(StateFilter(None), F.text.regexp(r"^(\d+[\.,]?\d*)[\$💰]?$"))
async def set_bet_by_text_handler(message: Message, state: FSMContext):
    """Установка ставки через текст (например, '0.1 💰')"""
    # Проверка, что сообщение отправлено в приватном чате или пользователь ответил на сообщение бота
    # Но так как бот должен реагировать на сообщения в чате, добавим проверку:
    
    user_id = message.from_user.id
    text = message.text.replace("$", "").replace("💰", "").replace(",", ".").strip()
    try:
        amount = float(text)
        if amount < 0.01:
            return await message.answer("❌ Минимальная ставка — <b>0.01 💰</b>")
        
        if amount > config.MAX_BET:
            return await message.answer(f"❌ Максимальная ставка — <b>{config.MAX_BET:.2f} 💰</b>")
        
        db.set_bet(user_id, amount)
        await message.answer(f"✅ Ваша ставка установлена на <b>{amount:.2f} 💰</b>")
    except ValueError:
        pass

@dp.message(StateFilter(None), F.text.lower().regexp(r"^(куб|кубы)"))
async def dice_text_handler(message: Message, state: FSMContext):
    """Обработчик текстовых ставок на кубики (куб чет, кубы 7 и т.д.)"""
    
    text_raw = message.text.lower()
    # Убираем "кубы" или "куб" из начала строки
    text = re.sub(r"^(кубы|куб)", "", text_raw).strip()
    
    # Новое: команда "кубы 7" открывает меню
    if text == "7":
        # Имитируем вызов меню через callback
        user_id = message.from_user.id
        user_data = db.get_user_data(user_id)
        balance = user_data[3]
        current_bet = user_data[11]
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🎲 Меньше 7 (x2.4)", callback_data=f"dice_bet:sum_less_7:{user_id}"))
        builder.row(InlineKeyboardButton(text="🎲 Точно 7 (x6)", callback_data=f"dice_bet:sum_equal_7:{user_id}"))
        builder.row(InlineKeyboardButton(text="🎲 Больше 7 (x2.4)", callback_data=f"dice_bet:sum_more_7:{user_id}"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
        
        return await message.answer(
            f"Сделайте выбор для игры\n\nСумма двух 🎲, от 2 до 12\n\n"
            f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
            f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
            f"<i>Пополняй и сыграй на реальные деньги</i>",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )

    if not text:
        return await message.answer("❓ <b>Как играть?</b>\n\n"
                                  "• <code>куб чет</code> — на четное\n"
                                  "• <code>куб нечет</code> — на нечетное\n"
                                  "• <code>куб меньше</code> — на 1-3\n"
                                  "• <code>куб больше</code> — на 4-6\n"
                                  "• <code>куб 1</code> — на число 1 (x6)\n"
                                  "• <code>куб 1,2</code> — на числа 1 и 2 (x3)")

    user_id = message.from_user.id
    bet_type = None
    custom_numbers = None

    if text in ["чет", "четное", "even"]:
        bet_type = "1_even"
    elif text in ["нечет", "нечетное", "odd"]:
        bet_type = "1_odd"
    elif text in ["меньше", "less", "low"]:
        bet_type = "1_low"
    elif text in ["больше", "more", "high"]:
        bet_type = "1_high"
    else:
        # Попытка распарсить числа
        try:
            # Убираем все лишнее, оставляем цифры и запятые/пробелы
            nums_str = re.sub(r'[^0-9, ]', '', text)
            nums = [int(n.strip()) for n in nums_str.replace(",", " ").split() if n.strip()]
            nums = list(set(nums)) # Убираем дубликаты
            
            if not nums:
                return await message.answer("❌ Не удалось распознать числа для ставки.")
            
            if any(n < 1 or n > 6 for n in nums):
                return await message.answer("❌ Числа должны быть от 1 до 6.")
            
            if len(nums) > 5:
                return await message.answer("❌ Можно выбрать не более 5 чисел.")
            
            if len(nums) == 1:
                bet_type = f"num_{nums[0]}"
            else:
                custom_numbers = nums
                bet_type = f"custom_{len(nums)}"
        except:
            return await message.answer("❌ Неверный формат команды.")

    if bet_type:
        await state.set_state(PlayingState.dice)
        await process_dice_game(message, user_id, bet_type, state, custom_numbers=custom_numbers)

@dp.message(StateFilter(None), F.text.lower() == "произведение")
async def multiply_text_handler(message: Message, state: FSMContext):
    """Обработчик текстовой команды 'произведение'"""
        
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Умн. 1-18 (x1.25)", callback_data=f"dice_bet:mult_1_18:{user_id}"))
    builder.row(InlineKeyboardButton(text="Умн. 19-36 (x4.4)", callback_data=f"dice_bet:mult_19_36:{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
    
    await message.answer(
        f"Сделайте выбор для игры произведение двух 🎲\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.lower().in_({"игры", "играть"}))
async def text_games_handler(message: Message, user_id: int = None):
    """Текстовая команда вызова меню игр"""
    if user_id is None:
        user_id = message.from_user.id
    
    user_data = db.get_user_data(user_id)
    if not user_data:
        db.register_user(user_id, message.from_user.username or message.from_user.first_name)
        user_data = db.get_user_data(user_id)
        
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    # 1 ряд: Эмодзи-игры
    builder.row(
        InlineKeyboardButton(text="🎲", callback_data=f"game:dice_emoji:{user_id}"),
        InlineKeyboardButton(text="⚽", callback_data=f"game:soccer:{user_id}"),
        InlineKeyboardButton(text="🏀", callback_data=f"game:basket:{user_id}"),
        InlineKeyboardButton(text="🎯", callback_data=f"game:darts:{user_id}"),
        InlineKeyboardButton(text="🎳", callback_data=f"game:bowling:{user_id}"),
        InlineKeyboardButton(text="🎰", callback_data=f"game:slots:{user_id}")
    )
    # 2 ряд: Telegram / Авторские
    builder.row(
        InlineKeyboardButton(text="☃️ Telegram", callback_data=f"game:dice:{user_id}"),
        InlineKeyboardButton(text="🐋 Авторские", callback_data=f"custom_games_menu:{user_id}")
    )
    
    # 3 ряд: Режимы
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "modes"), callback_data=f"modes_menu:{user_id}")
    )
    
    text = (
        "🎮 <b>Выбирайте игру!</b>\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f} 💰</b> ❞\n"
        f"Ставка — <b>{current_bet:.2f} 💰</b></blockquote>\n\n"
        "<i>Пополняй и сыграй на реальные деньги</i>"
    )

    await message.answer(
        text, 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.lower() == "куб 7")
async def cmd_cubes_7_handler(message: Message, state: FSMContext):
    """Текстовая команда для режима 'Кубы 7'"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        db.register_user(user_id, message.from_user.username or message.from_user.first_name)
        user_data = db.get_user_data(user_id)
    
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    text = "Сделайте выбор для игры\n\nСумма двух 🎲, от 2 до 12"
    builder.row(InlineKeyboardButton(text="🎲 Меньше 7 (x2.4)", callback_data=f"dice_bet:sum_less_7:{user_id}"))
    builder.row(InlineKeyboardButton(text="🎲 Точно 7 (x6)", callback_data=f"dice_bet:sum_equal_7:{user_id}"))
    builder.row(InlineKeyboardButton(text="🎲 Больше 7 (x2.4)", callback_data=f"dice_bet:sum_more_7:{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
    
    await message.answer(
        f"{text}\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.lower() == "произведение")
async def cmd_multiply_handler(message: Message, state: FSMContext):
    """Текстовая команда для режима 'Произведение'"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        db.register_user(user_id, message.from_user.username or message.from_user.first_name)
        user_data = db.get_user_data(user_id)
    
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    text = "Сделайте выбор для игры произведение двух 🎲"
    builder.row(InlineKeyboardButton(text="Умн. 1-18 (x1.25)", callback_data=f"dice_bet:mult_1_18:{user_id}"))
    builder.row(InlineKeyboardButton(text="Умн. 19-36 (x4.4)", callback_data=f"dice_bet:mult_19_36:{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
    
    await message.answer(
        f"{text}\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text == "/5")
async def cmd_not_6_handler(message: Message):
    """Быстрый вызов меню 'Всё кроме 6'"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    if not user_data:
         # На всякий случай
         db.register_user(user_id, message.from_user.username or message.from_user.first_name)
         user_data = db.get_user_data(user_id)
    
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    
    text = (
        "<b>Всё кроме 6 — большие иксы</b>\n\n"
        "🎲 1 это <b>× 3</b>\n"
        "🎲 2 это <b>× 4</b>\n"
        "🎲 3 это <b>× 5,2</b>\n"
        "🎲 4 это <b>× 6,4</b>\n"
        "🎲 5 это <b>× 7,6</b>\n"
        "🎲 6 это <b>минус × 19</b>"
    )
    builder.row(InlineKeyboardButton(text="🎲 Играть", callback_data=f"dice_bet:not_6:{user_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
    
    await message.answer(
        f"{text}\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.lower() == "вб")
async def vb_command_handler(message: Message):
    """Команда ва-банк"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
    
    balance = user_data[3]
    if balance <= 0:
        return await message.answer("❌ Ваш баланс пуст!")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_vb:{user_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_vb:{user_id}"))

    await message.answer(
        f"Вы действительно хотите поставить весь баланс (<b>{balance:.2f} 💰</b>)?",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("confirm_vb:"))
async def confirm_vb_callback(callback: CallbackQuery):
    """Подтверждение ва-банка"""
    try:
        owner_id = int(callback.data.split(":")[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
    
    balance = user_data[3]
    
    # Ограничение по макс ставке для ва-банка
    bet_amount = balance
    if bet_amount > config.MAX_BET:
        bet_amount = config.MAX_BET
        
    db.set_bet(user_id, bet_amount)
    
    await callback.message.edit_text(
            f"✅ Ваша ставка установлена на: <b>{bet_amount:.2f} 💰</b>" + 
            (f" (ограничено макс. ставкой)" if bet_amount < balance else ""),
            parse_mode=ParseMode.HTML
        )
    # Показываем меню игр после установки ставки
    await text_games_handler(callback.message, user_id=user_id)

@dp.callback_query(F.data.startswith("cancel_vb:"))
async def cancel_vb_callback(callback: CallbackQuery):
    """Отмена ва-банка"""
    try:
        owner_id = int(callback.data.split(":")[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
    
    await callback.message.edit_text("❌ Установка ставки отменена.")

@dp.message(F.text.lower().in_({"балик","б", "бал", "баланс", "бабанс", "деп", "вывод"}))
async def text_balance_handler(message: Message):
    """Текстовая команда баланса (также реагирует на 'деп' и 'вывод')"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    if not user_data:
        db.register_user(user_id, message.from_user.username or message.from_user.first_name)
        user_data = db.get_user_data(user_id)
    
    # Распаковка данных (согласно структуре в db.get_user_data)
    # reg_date, player_num, lang, balance, privacy_type, nickname, username, ...
    player_num = user_data[1]
    balance = user_data[3]
    nickname = user_data[5]
    username = user_data[6]
    
    display_name = nickname if nickname else (f"@{username}" if username else message.from_user.first_name)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "deposit"), callback_data=f"deposit:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "withdraw"), callback_data=f"withdraw:{user_id}")
    )
    
    text = (
        f"<b>#{player_num} {display_name}</b>\n\n"
        f"<blockquote><b>💳 Баланс — {balance:.2f} 💰</b></blockquote>"
    )
    
    await message.answer(
        text,
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.startswith("/givebalance"))
async def give_balance_handler(message: Message):
    """Админ-команда выдачи баланса"""
    if message.from_user.id not in config.ADMINS:
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            return await message.answer("❌ Формат: <code>/givebalance айди сумма</code>")
        
        target_id = int(parts[1])
        amount = float(parts[2])
        
        if db.add_balance(target_id, amount):
            await message.answer(f"✅ Баланс игрока <code>{target_id}</code> изменен на <b>{amount:.2f} 💰</b>")
            logging.info(f"Admin {message.from_user.id} changed balance for {target_id} by {amount}")
        else:
            await message.answer(f"❌ Игрок <code>{target_id}</code> не найден в базе.")
    except ValueError:
        await message.answer("❌ Ошибка: ID должен быть числом, а сумма — числом (через точку)")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(F.text.lower().regexp(r"^дать\s+(\d+[\.,]?\d*)"))
async def transfer_balance_handler(message: Message):
    """Команда передачи баланса другому игроку через ответ на сообщение"""
    if not message.reply_to_message:
        return
    
    if message.reply_to_message.from_user.is_bot:
        return await message.answer("❌ Нельзя передавать монеты ботам!")

    sender_id = message.from_user.id
    recipient_id = message.reply_to_message.from_user.id
    
    if sender_id == recipient_id:
        return await message.answer("❌ Нельзя передавать монеты самому себе!")

    # Извлекаем сумму
    match = re.search(r"(?i)дать\s+(\d+[\.,]?\d*)", message.text)
    if not match:
        return

    try:
        amount = float(match.group(1).replace(",", "."))
    except ValueError:
        return

    if amount < 0.1:
        return await message.answer("❌ Минимальная сумма перевода — <b>0.10 💰</b>", parse_mode=ParseMode.HTML)

    # Проверяем баланс отправителя
    sender_data = db.get_user_data(sender_id)
    if not sender_data:
        db.register_user(sender_id, message.from_user.username or message.from_user.first_name)
        sender_data = db.get_user_data(sender_id)
        
    if sender_data[3] < amount:
        return await message.answer("❌ У вас недостаточно средств на балансе!")

    # Убеждаемся, что получатель зарегистрирован
    recipient_data = db.get_user_data(recipient_id)
    if not recipient_data:
        db.register_user(recipient_id, message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name)

    # Выполняем перевод
    if db.add_balance(sender_id, -amount, is_withdraw=True):
        db.add_balance(recipient_id, amount)
        
        sender_name = message.from_user.mention_html()
        recipient_name = message.reply_to_message.from_user.mention_html()
        
        await message.answer(
            f"🎊 {sender_name} передаёт <b>{amount:,.2f} 💰</b> {recipient_name}",
            parse_mode=ParseMode.HTML
        )
        logging.info(f"User {sender_id} transferred {amount} to {recipient_id}")
    else:
        await message.answer("❌ Произошла ошибка при переводе.")

@dp.message(F.text.in_({"/reserve", "/reserv"}))
async def reserve_command_handler(message: Message):
    """Команда проверки резервов (Фейковые данные)"""
    wait_msg = await message.answer("🔄 Загрузка данных о резервах...")

    # --- Фейковые данные ---
    fake_total_usd = 101

    # Список фейковых активов (для красоты)
    fake_assets = [
        ("USDT", 101, 101.00),
        ("TON", 0, 0),  # (кол-во, примерная цена в USD)
        ("BTC", 0, 0),
        ("ETH", 0, 0)
    ]

    # Эмодзи для валют
    currency_emojis = {
        "USDT": "🟢",
        "TON": "💎",
        "BTC": "🟠",
        "ETH": "🔷",
        "SOL": "🟣",
        "TRX": "🔴",
        "LTC": "🥈",
        "BNB": "🟡",
        "USDC": "🔵",
        "XRP": "⚪"
    }

    # Формируем текст
    text = f"<b>🥣 Crypto Bot: ${fake_total_usd:,.2f}</b>\n"
    for asset, amount, usd_val in fake_assets:
        emoji = currency_emojis.get(asset, "🔹")
        text += f"{emoji} {asset}: {amount:,.2f} (${usd_val:,.2f})\n"

    # Добавим немного текста в конце для правдоподобности
    text += "\n<code>Баланс обновлен: только что</code>"

    await wait_msg.edit_text(text, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("profile:"))
async def profile_callback(callback: CallbackQuery):
    """Обработчик кнопки Профиль"""
    owner_id = int(callback.data.split(":")[-1])
    if not await check_owner(callback, owner_id):
        return
    user_id = callback.from_user.id
        
    user_data = db.get_user_data(user_id)
    
    if not user_data:
        # Если вдруг данных нет, регистрируем
        db.register_user(user_id, callback.from_user.username or callback.from_user.first_name)
        user_data = db.get_user_data(user_id)

    reg_date_str, player_num, lang, balance, privacy_type, nickname, username, total_bets, total_turnover, total_deposits, total_withdrawals, current_bet, referrer_id, ref_balance, total_ref_earned, rank_id = user_data
    
    # Расчет прогресса ранга
    # Ранг повышается каждые 1000 оборота
    # Процент прогресса до следующего ранга: (остаток от деления оборота на 1000) / 1000 * 100
    rank_progress = (total_turnover % 1000) / 1000 * 100
    current_rank_name = RANKS[min(rank_id, len(RANKS)-1)]
    next_rank_name = RANKS[min(rank_id + 1, len(RANKS)-1)]
    
    # Формирование прогресс-бара (10 символов)
    filled_chars = int(rank_progress // 10)
    progress_bar = "⬜" * filled_chars + "⬛" * (10 - filled_chars)
    
    # Расчет дней аккаунту
    reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d %H:%M:%S")
    days_delta = (datetime.now() - reg_date).days
    
    # Форматирование текста дней
    if lang == "ru":
        if days_delta == 0:
            days_text = "меньше дня"
        elif days_delta % 10 == 1 and days_delta % 100 != 11:
            days_text = f"{days_delta} день"
        elif days_delta % 10 in [2, 3, 4] and days_delta % 100 not in [12, 13, 14]:
            days_text = f"{days_delta} дня"
        else:
            days_text = f"{days_delta} дней"
    else:
        if days_delta == 0:
            days_text = "less than a day"
        elif days_delta == 1:
            days_text = "1 day"
        else:
            days_text = f"{days_delta} days"

    # Получаем шаблон текста из конфига и форматируем его
    display_name = get_user_display_name(user_id, callback.from_user.first_name)
    profile_template = get_text(user_id, "profile")
    profile_text = profile_template.format(
        player_id=player_num, 
        days=days_text, 
        balance=balance, 
        name=display_name,
        turnover=total_turnover,
        bets=total_bets,
        rank_progress=rank_progress,
        current_rank=current_rank_name,
        next_rank=next_rank_name,
        progress_bar=progress_bar
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "deposit"), callback_data=f"deposit:{user_id}"), 
        InlineKeyboardButton(text=get_btn(user_id, "withdraw"), callback_data=f"withdraw:{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "stats"), callback_data=f"stats:{user_id}"), 
        InlineKeyboardButton(text=get_btn(user_id, "privacy"), callback_data=f"privacy:{user_id}")
    )
    builder.row(get_back_button(user_id))
    
    await callback.message.edit_text(
        profile_text, 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("stats:"))
async def stats_callback(callback: CallbackQuery):
    """Обработчик кнопки Статистика"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    
    reg_date_str, player_num, lang, balance, privacy_type, nickname, username, total_bets, total_turnover, total_deposits, total_withdrawals, current_bet, referrer_id, ref_balance, total_ref_earned, rank_id = user_data
    
    # Расчет дней аккаунту
    reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d %H:%M:%S")
    days_delta = (datetime.now() - reg_date).days
    
    # Форматирование дней (для метки "дней" или "days")
    days_label = ""
    if lang == "ru":
        if days_delta == 0:
            days_label = "" # Уже учтено в логике ниже, но для шаблона нужно число
            days_str = "0"
            days_word = "дней"
        elif days_delta % 10 == 1 and days_delta % 100 != 11:
            days_word = "день"
        elif days_delta % 10 in [2, 3, 4] and days_delta % 100 not in [12, 13, 14]:
            days_word = "дня"
        else:
            days_word = "дней"
    else:
        days_word = "days" if days_delta != 1 else "day"
    
    display_name = get_user_display_name(user_id, callback.from_user.first_name)
    stats_text = get_text(user_id, "stats_text").format(
        name=display_name,
        bets=total_bets,
        turnover=total_turnover,
        days=days_delta,
        days_label=days_word,
        deposits=total_deposits,
        withdrawals=total_withdrawals
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"profile:{user_id}"))
    
    await callback.message.edit_text(stats_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("deposit:"))
async def deposit_callback(callback: CallbackQuery):
    """Обработчик кнопки Пополнить"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    builder = InlineKeyboardBuilder()
    
    # Добавляем только Crypto Bot и xRocket
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "crypto_bot"), callback_data=f"deposit_cryptobot:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "xrocket"), callback_data=f"deposit_xrocket:{user_id}")
    )
    
    # Кнопка назад
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"profile:{user_id}"))
    
    await callback.message.edit_text(
        get_text(user_id, "deposit_method"),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("deposit_"))
async def deposit_method_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор метода пополнения"""
    parts = callback.data.split(":")
    method = parts[0].split("_")[-1]
    
    # Проверка владельца если есть :user_id
    if len(parts) > 1:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    
    await state.update_data(method=method)
    user_id = callback.from_user.id
    await state.set_state(DepositState.entering_amount)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_action:{user_id}"))
    
    await callback.message.edit_text(
        get_text(user_id, "enter_deposit_amount").format(min_amount=config.MIN_DEPOSIT),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(DepositState.entering_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    """Ввод суммы пополнения"""
    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        return await message.answer(get_text(user_id, "enter_deposit_amount").format(min_amount=config.MIN_DEPOSIT))

    if amount < config.MIN_DEPOSIT:
        return await message.answer(get_text(user_id, "error_min_deposit").format(min_amount=config.MIN_DEPOSIT))

    if amount > 1000000:
        return await message.answer("❌ Сумма слишком велика.")

    data = await state.get_data()
    method = data.get("method")
    
    pay_url = None
    invoice_id = None
    if method == "cryptobot":
        pay_url, invoice_id = await crypto_pay.create_invoice(amount)
    elif method == "xrocket":
        pay_url, invoice_id = await xrocket.create_invoice(amount)

    if not pay_url:
        # Если API ключи не настроены, создаем "фейковую" ссылку для теста
        pay_url = f"https://t.me/CryptoBot?start=IVVQxQuLnQA" if method == "cryptobot" else "https://t.me/RocketBot?start=invoice"
        invoice_id = "test_id"
        # return await message.answer("❌ Ошибка при создании счета. Обратитесь в поддержку.")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "pay").format(amount=amount), url=pay_url))
    # Добавляем кнопку проверки оплаты с ID счета и суммой
    builder.row(InlineKeyboardButton(text=get_text(user_id, "check_payment"), callback_data=f"check:{method}:{invoice_id}:{amount}:{user_id}"))
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "change_amount"), callback_data=f"deposit_{method}:{user_id}"))
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"deposit:{user_id}"))
    
    await message.answer(
        get_text(user_id, "deposit_created"),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(None)

@dp.callback_query(F.data.startswith("check:"))
async def check_payment_callback(callback: CallbackQuery):
    """Проверка статуса оплаты"""
    # Формат: check:method:invoiceid:amount:user_id
    parts = callback.data.split(":")
    method = parts[1]
    invoice_id = parts[2]
    amount = float(parts[3])
    
    # Проверка владельца если есть user_id
    if len(parts) > 4:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id

    is_paid = False
    
    if invoice_id == "test_id":
        # Для тестов (если ключи не валидны) - имитируем оплату
        # is_paid = True 
        pass

    if method == "cryptobot":
        invoice = await crypto_pay.get_invoice(invoice_id)
        if invoice and invoice.get("status") == "paid":
            is_paid = True
    elif method == "xrocket":
        invoice = await xrocket.get_invoice(invoice_id)
        if invoice and invoice.get("status") == "paid":
            is_paid = True

    if is_paid:
        # ПРОВЕРКА: Не был ли этот счет уже зачислен?
        if db.is_invoice_processed(invoice_id):
            return await callback.answer("❌ Этот счет уже был зачислен!", show_alert=True)
            
        # Помечаем как обработанный СРАЗУ (до начисления, чтобы избежать гонки)
        db.mark_invoice_processed(invoice_id, user_id, amount, method)
        
        # Добавляем баланс и обновляем статистику пополнений
        db.add_balance(user_id, amount, is_deposit=True)
        await callback.message.edit_text(
            get_text(user_id, "payment_success").format(amount=amount),
            parse_mode=ParseMode.HTML
        )
        # Отправляем уведомление о крупном пополнении
        await send_alert(callback.bot, user_id, amount, "deposit")
    else:
        # Уведомляем что не оплачено
        await callback.answer(get_text(user_id, "payment_not_found"), show_alert=True)

@dp.callback_query(F.data.startswith("withdraw:"))
async def withdraw_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки Вывести"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3] if user_data else 0.0
    
    if balance < config.MIN_WITHDRAW:
        return await callback.answer(get_text(user_id, "error_min_withdraw").format(min_amount=config.MIN_WITHDRAW), show_alert=True)

    await state.set_state(WithdrawState.entering_amount)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_action:{user_id}"))
    
    await callback.message.edit_text(
        get_text(user_id, "enter_withdraw_amount").format(min_amount=config.MIN_WITHDRAW),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("cancel_action:"))
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия и возврат в профиль"""
    try:
        owner_id = int(callback.data.split(":")[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
        
    await state.set_state(None)
    await profile_callback(callback)

@dp.message(WithdrawState.entering_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    """Ввод суммы вывода"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3] if user_data else 0.0

    # Пробуем распарсить сумму, очищая от лишних знаков
    text = message.text.replace("$", "").replace(",", ".").strip()
    try:
        amount = float(text)
    except ValueError:
        # Если это не число, возможно пользователь просто пишет в чат, 
        # но так как он в состоянии ввода суммы, мы должны реагировать.
        # Если это не похоже на сумму, игнорируем (чтобы не спамить в чате)
        if not any(char.isdigit() for char in text):
            return
        return await message.answer(get_text(user_id, "enter_withdraw_amount").format(min_amount=config.MIN_WITHDRAW))

    if amount < config.MIN_WITHDRAW:
        return await message.answer(get_text(user_id, "error_min_withdraw").format(min_amount=config.MIN_WITHDRAW))

    if amount > 1000000: # Разумный предел для предотвращения ошибок с гигантскими числами
        return await message.answer("❌ Сумма слишком велика.")

    if amount > balance:
        return await message.answer(f"❌ Недостаточно средств. Ваш баланс: {balance:.2f} 💰")

    await state.update_data(amount=amount)
    await state.set_state(WithdrawState.choosing_method)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 Crypto Bot", callback_data=f"withdraw_method:cryptobot:{user_id}"),
        InlineKeyboardButton(text="🤖 xRocket", callback_data=f"withdraw_method:xrocket:{user_id}")
    )
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"withdraw_back:{user_id}"))
    
    await message.answer("� Выберите метод вывода:", reply_markup=builder.as_markup())

@dp.callback_query(WithdrawState.choosing_method, F.data.startswith("withdraw_method:"))
async def withdraw_method_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор API для вывода (сразу создание чека или прямой перевод)"""
    parts = callback.data.split(":")
    method = parts[1]
    try:
        owner_id = int(parts[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
        
    await state.update_data(method=method)
    user_id = callback.from_user.id
    data = await state.get_data()
    
    # Защита от спама кликами (вывод)
    if data.get("processing_withdraw"):
        return await callback.answer()
    await state.update_data(processing_withdraw=True)
    
    amount = data.get("amount")

    try:
        # Списываем баланс заранее и обновляем статистику выводов
        if not db.add_balance(user_id, -amount, is_withdraw=True):
            await state.update_data(processing_withdraw=False)
            await state.set_state(None)
            return await callback.answer("❌ Ошибка при списании баланса. Возможно, недостаточно средств.", show_alert=True)
        
        try:
            # Попытка прямого перевода
            transfer_success = False
            transfer_error = ""
            
            if method == "cryptobot":
                transfer_success, transfer_error = await crypto_pay.transfer(user_id, amount)
            else:
                transfer_success, transfer_error = await xrocket.transfer(user_id, amount)
                
            if transfer_success:
                await callback.message.edit_text(
                    f"✅ Вывод <b>{amount:.2f} 💰</b> успешно выполнен (прямой перевод)!",
                    parse_mode=ParseMode.HTML
                )
                await send_alert(callback.bot, user_id, amount, "withdraw")
                await state.update_data(processing_withdraw=False)
                await state.set_state(None)
                return

            # Если прямой перевод не удался, пробуем создать чек
            logging.warning(f"Direct transfer failed ({method}): {transfer_error}. Trying to create check...")
            
            check_url = None
            if method == "cryptobot":
                check_url = await crypto_pay.create_check(amount, pin_to_user_id=user_id)
            else:
                check_url = await xrocket.create_check(amount, pin_to_user_id=user_id)
            
            if check_url:
                await callback.message.edit_text(
                    f"✅ Чек на сумму <b>{amount:.2f} 💰</b> успешно создан!\n\n"
                    f"🔗 Ссылка: {check_url}",
                    reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🎁 Забрать", url=check_url)).as_markup(),
                    parse_mode=ParseMode.HTML
                )
                await send_alert(callback.bot, user_id, amount, "withdraw")
                await state.update_data(processing_withdraw=False)
                await state.set_state(None)
                return
            
            # Если и чек не создался — возвращаем баланс и уведомляем админа
            logging.error(f"Failed to create check for user {user_id} (amount: {amount})")
            
            # Возвращаем баланс пользователю
            db.add_balance(user_id, amount) 
            db.cursor.execute("UPDATE users SET total_withdrawals = total_withdrawals - ? WHERE user_id = ?", (amount, user_id))
            db.conn.commit()
            
            # Уведомление пользователю
            await callback.message.edit_text(
                "Заявка на вывод отправлена!\n"
                "🛡 Мы отправили запрос администраторам, они выплатят вам вручную в ближайшее время!",
                parse_mode=ParseMode.HTML
            )
            
            # Уведомление админам
            user_name = get_user_display_name(user_id)
            admin_text = (
                f"⚠️ <b>ОШИБКА ВЫПЛАТЫ</b>\n\n"
                f"👤 Игрок: {user_name} (ID: <code>{user_id}</code>)\n"
                f"<blockquote>💵 Сумма: <b>{amount:.2f} 💰</b>\n"
                f"🏦 Метод: <b>{method}</b></blockquote>\n\n"
                f"❌ Прямой перевод и чек не сработали. Выплатите вручную!"
            )
            
            for admin_id in config.ADMINS:
                try:
                    await callback.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logging.error(f"Failed to send admin alert to {admin_id}: {e}")
            
            await state.update_data(processing_withdraw=False)
            await state.set_state(None)
        except Exception as e:
            logging.error(f"Error during withdrawal process: {e}")
            # В случае непредвиденной ошибки также пробуем вернуть баланс
            db.add_balance(user_id, amount)
            db.cursor.execute("UPDATE users SET total_withdrawals = total_withdrawals - ? WHERE user_id = ?", (amount, user_id))
            db.conn.commit()
            await callback.answer("❌ Произошла ошибка. Баланс возвращен.", show_alert=True)
            await state.update_data(processing_withdraw=False)
            await state.set_state(None)
    finally:
        # Если стейт еще не очищен, снимаем флаг
        if await state.get_state() == WithdrawState.choosing_method:
            await state.update_data(processing_withdraw=False)

@dp.callback_query(F.data.startswith("withdraw_back:"))
async def withdraw_back_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу суммы вывода"""
    try:
        owner_id = int(callback.data.split(":")[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
    await state.set_state(WithdrawState.entering_amount)
    await withdraw_callback(callback, state)
@dp.callback_query(F.data.startswith("chats:"))
async def chats_callback(callback: CallbackQuery):
    """Обработчик кнопки Игровые чаты"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "main_chat"), url=config.CHAT_URL))
    builder.row(get_back_button(user_id))
    
    await callback.message.edit_text(
        get_text(user_id, "chats"), 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("language:"))
async def language_menu_callback(callback: CallbackQuery):
    """Обработчик кнопки Язык (открывает меню выбора)"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    current_lang = get_lang(user_id)
    
    builder = InlineKeyboardBuilder()
    
    # Формируем текст кнопок с галочкой
    ru_text = get_btn(user_id, "lang_ru") + (" ✅" if current_lang == "ru" else "")
    en_text = get_btn(user_id, "lang_en") + (" ✅" if current_lang == "en" else "")
    
    builder.row(
        InlineKeyboardButton(text=ru_text, callback_data=f"set_lang_ru:{user_id}"),
        InlineKeyboardButton(text=en_text, callback_data=f"set_lang_en:{user_id}")
    )
    builder.row(get_back_button(user_id))
    
    await callback.message.edit_text(
        get_text(user_id, "language_select"), 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language_callback(callback: CallbackQuery):
    """Установка языка"""
    parts = callback.data.split(":")
    new_lang = parts[0].split("_")[-1] # ru или en
    
    # Проверка владельца если есть :user_id
    if len(parts) > 1:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    # Сохраняем новый язык в БД
    db.set_lang(user_id, new_lang)
    
    current_lang = new_lang
    
    builder = InlineKeyboardBuilder()
    
    # Получаем тексты кнопок уже на НОВОМ языке
    ru_text = config.TEXTS[new_lang]["buttons"]["lang_ru"] + (" ✅" if current_lang == "ru" else "")
    en_text = config.TEXTS[new_lang]["buttons"]["lang_en"] + (" ✅" if current_lang == "en" else "")
    
    builder.row(
        InlineKeyboardButton(text=ru_text, callback_data=f"set_lang_ru:{user_id}"),
        InlineKeyboardButton(text=en_text, callback_data=f"set_lang_en:{user_id}")
    )
    builder.row(get_back_button(user_id)) # Кнопка Назад тоже будет на новом языке
    
    await callback.message.edit_text(
        get_text(user_id, "language_select"), 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("privacy:"))
async def privacy_callback(callback: CallbackQuery):
    """Обработчик кнопки Приватность (меню из скриншота)"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
    
    reg_date, player_num, lang, balance, privacy_type, nickname, username, *rest = user_data
    
    # Определяем, что сейчас отображается
    display_modes = {
        "username": f"@{username}" if username else "Username",
        "name": callback.from_user.first_name,
        "id": f"Игрок #{player_num}",
        "nickname": nickname if nickname else "Псевдоним"
    }
    current_display = display_modes.get(privacy_type, "Username")
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки как на скриншоте
    # 1 ряд: Username, First Name
    btn_user = ("✅ " if privacy_type == "username" else "") + (f"@{username}" if username else "Username")
    btn_name = ("✅ " if privacy_type == "name" else "") + callback.from_user.first_name
    builder.row(
        InlineKeyboardButton(text=btn_user, callback_data=f"set_priv:username:{user_id}"),
        InlineKeyboardButton(text=btn_name, callback_data=f"set_priv:name:{user_id}")
    )
    
    # 2 ряд: Player ID, Pseudonym
    btn_id = ("✅ " if privacy_type == "id" else "") + f"Игрок #{player_num}"
    btn_nick = ("✅ " if privacy_type == "nickname" else "") + (nickname if nickname else "Псевдоним")
    builder.row(
        InlineKeyboardButton(text=btn_id, callback_data=f"set_priv:id:{user_id}"),
        InlineKeyboardButton(text=btn_nick, callback_data=f"set_priv:nickname:{user_id}")
    )
    
    # 3 ряд: Настройки
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "settings"), callback_data=f"privacy_settings:{user_id}"))
    # 4 ряд: Назад
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"profile:{user_id}"))
    
    await callback.message.edit_text(
        get_text(user_id, "privacy").format(display_mode=current_display),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("set_priv:"))
async def set_privacy_type_callback(callback: CallbackQuery):
    """Установка типа приватности"""
    parts = callback.data.split(":")
    privacy_type = parts[1]
    
    # Проверка владельца если есть :user_id
    if len(parts) > 2:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    db.set_privacy(user_id, privacy_type)
    await callback.answer(get_text(user_id, "privacy_updated"))
    await privacy_callback(callback)

@dp.callback_query(F.data.startswith("privacy_settings"))
async def privacy_settings_callback(callback: CallbackQuery, state: FSMContext):
    """Начало установки псевдонима"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    await state.set_state(PrivacyState.entering_nickname)
    await callback.message.edit_text(
        get_text(user_id, "privacy_set_nickname"),
        parse_mode=ParseMode.HTML
    )

@dp.message(PrivacyState.entering_nickname)
async def process_nickname(message: Message, state: FSMContext):
    """Процесс ввода псевдонима"""
    user_id = message.from_user.id
    nickname = message.text[:15] # Ограничение 15 символов
    
    db.set_nickname(user_id, nickname)
    db.set_privacy(user_id, "nickname") # Сразу переключаем на псевдоним
    
    await state.set_state(None)
    await message.answer(get_text(user_id, "nickname_updated"))
    
    # Возвращаемся в профиль (или меню приватности)
    # Для простоты отправим новое сообщение с профилем
    await command_start_handler(message)

async def send_alert(bot: Bot, user_id: int, amount: float, type: str):
    """Отправка уведомления в канал крупных событий (>50 💰)"""
    if amount < 50:
        return
        
    try:
        user_name = get_user_display_name(user_id)
        if type == "deposit":
            text = f"💰 <b>Крупное пополнение!</b>\n\n👤 Игрок: {user_name}\n💵 Сумма: <b>{amount:.2f} 💰</b>"
        elif type == "withdraw":
            text = f"📥 <b>Крупный вывод!</b>\n\n👤 Игрок: {user_name}\n💵 Сумма: <b>{amount:.2f} 💰</b>"
        elif type == "win":
            text = f"🎉 <b>Огромная победа!</b>\n\n👤 Игрок: {user_name}\n💵 Выигрыш: <b>{amount:.2f} 💰</b>"
        else:
            return

        await bot.send_message(chat_id=config.ALERTS_CHANNEL, text=text)
    except Exception as e:
        logging.error(f"Error sending alert: {e}")

@dp.callback_query(F.data.startswith("referral:"))
async def referral_callback(callback: CallbackQuery):
    """Обработчик кнопки Реф. программа"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
        
    ref_count = db.get_ref_stats(user_id)
    ref_balance = user_data[13] # ref_balance
    total_earned = user_data[14] # total_ref_earned
    
    bot_info = await callback.bot.get_me()
    ref_link = f"t.me/{bot_info.username}?start=invite_{user_id}"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"Забрать на баланс · {ref_balance:.2f} 💰", callback_data=f"claim_ref:{user_id}"))
    builder.row(InlineKeyboardButton(text="Пригласить друга", switch_inline_query=f"Играй со мной! {ref_link}"))
    builder.row(InlineKeyboardButton(text="Подробнее", url=config.CHANNEL_URL))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"main_menu:{user_id}"))

    text = (
        f"<b>| 💰 Реф. система  ❞</b>\n\n"
        f"1 📈 5% | {ref_count} 👤 | {ref_balance:.2f} 💰 | {total_earned:.2f} 💰\n\n"
        f"Ваша ссылка\n"
        f"<code>{ref_link}</code>\n\n"
        f"Общий доход\n"
        f"{total_earned:.2f} 💰"
    )

    await callback.message.edit_text(
        text, 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("claim_ref:"))
async def claim_ref_callback(callback: CallbackQuery):
    """Сбор реферальных бонусов"""
    owner_id = int(callback.data.split(":")[-1])
    if not await check_owner(callback, owner_id):
        return
    user_id = callback.from_user.id
    claimed = db.claim_ref_balance(user_id)
    
    if claimed > 0:
        await callback.answer(f"✅ Выведено {claimed:.2f} 💰 на основной баланс!", show_alert=True)
        # Обновляем сообщение, чтобы цифры обновились
        await referral_callback(callback)
    else:
        await callback.answer("❌ На балансе меньше 1 💰 или он пуст.", show_alert=True)

@dp.callback_query(F.data.startswith("play:"))
async def play_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки Играть"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
        
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    # Игры (эмодзи)
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "game_dice"), callback_data=f"game:dice_emoji:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_soccer"), callback_data=f"game:soccer:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_basket"), callback_data=f"game:basket:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_darts"), callback_data=f"game:darts:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_bowling"), callback_data=f"game:bowling:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_slots"), callback_data=f"game:slots:{user_id}")
    )
    # Telegram / Авторские
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "provider_tg"), callback_data=f"game:dice:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "provider_custom"), callback_data=f"custom_games_menu:{user_id}")
    )
    
    # Режимы (Мины, Башня)
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "modes"), callback_data=f"modes_menu:{user_id}")
    )
    
    builder.row(get_back_button(user_id))

    await callback.message.edit_text(
        get_text(user_id, "play").format(balance=balance, bet=current_bet), 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("modes_menu:"))
async def modes_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Меню выбора режимов (Мины, Башня)"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
        
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_btn(user_id, "game_mines"), callback_data=f"game_mines:{user_id}"),
        InlineKeyboardButton(text=get_btn(user_id, "game_tower"), callback_data=f"game_tower:{user_id}")
    )
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"play:{user_id}"))

    await callback.message.edit_text(
        get_text(user_id, "modes_menu").format(balance=balance, bet=current_bet), 
        reply_markup=builder.as_markup(), 
        parse_mode=ParseMode.HTML
    )

def get_mines_coef(step, total_mines, commission=0.94):
    """Расчет коэффициента для игры Мины 5x5"""
    if step == 0:
        return 1.0
    if step > (25 - total_mines):
        return 0.0
    
    c = 1.0
    for i in range(step):
        c *= (25 - i) / (25 - total_mines - i)
    return c * commission

def get_mines_coefs_line(mines_count, current_step=0, limit=7):
    """Генерирует строку коэффициентов для отображения"""
    coefs = []
    start_step = max(1, current_step - 2)
    for i in range(start_step, start_step + limit):
        if i > (25 - mines_count):
            break
        val = get_mines_coef(i, mines_count)
        if i == current_step:
            coefs.append(f"<b>x{val:.2f}</b>")
        else:
            coefs.append(f"x{val:.2f}")
    
    line = " → ".join(coefs)
    if start_step + limit <= (25 - mines_count):
        line += " ... 🎀"
    else:
        line += " 🎀"
    return line

async def show_mines_menu(message: Message, user_id: int, state: FSMContext, edit: bool = True):
    """Главное меню игры Мины (Screenshot 1)"""
    
    data = await state.get_data()
    mines_count = data.get("mines_count", 3) # По умолчанию 3 мины
    
    user_data = db.get_user_data(user_id)
    player_id = user_data[1]
    balance = user_data[3]
    bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"🕹️ Играть · {bet:,.2f} 💰", callback_data=f"start_mines:{mines_count}:{user_id}"))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"modes_menu:{user_id}"),
        InlineKeyboardButton(text=f"Изменить · {mines_count} 💣", callback_data=f"select_mines_count:{user_id}")
    )
    
    text = get_text(user_id, "mines_main").format(
        player_id=player_id,
        balance=balance,
        bet=bet,
        mines=mines_count
    )
    
    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("game_mines:"))
async def game_mines_handler(callback: CallbackQuery, state: FSMContext):
    """Главное меню игры Мины (Screenshot 1)"""
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    await show_mines_menu(callback.message, user_id, state, edit=True)

@dp.callback_query(F.data.startswith("select_mines_count:"))
async def select_mines_count_handler(callback: CallbackQuery, state: FSMContext):
    """Меню выбора количества мин (Screenshot 2)"""
    owner_id = int(callback.data.split(":")[-1])
    if not await check_owner(callback, owner_id):
        return
    user_id = callback.from_user.id
    
    data = await state.get_data()
    current_mines = data.get("mines_count", 3)
    
    builder = InlineKeyboardBuilder()
    # Кнопки 2-24
    for i in range(2, 25):
        text = f"{i}"
        if i == current_mines:
            text = f"{i}💣"
        builder.add(InlineKeyboardButton(text=text, callback_data=f"set_mines:{i}:{user_id}"))
    
    builder.adjust(6)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_mines:{user_id}"))
    
    coefs_line = get_mines_coefs_line(current_mines, limit=8)
    text = get_text(user_id, "mines_select").format(
        mines=current_mines,
        coefs=coefs_line
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("set_mines:"))
async def set_mines_handler(callback: CallbackQuery, state: FSMContext):
    """Установка количества мин"""
    parts = callback.data.split(":")
    count = int(parts[1])
    owner_id = int(parts[-1])
    
    if not await check_owner(callback, owner_id):
        return
        
    await state.update_data(mines_count=count)
    await select_mines_count_handler(callback, state)

@dp.callback_query(F.data.startswith("start_mines:"))
async def start_mines_handler(callback: CallbackQuery, state: FSMContext):
    """Инициализация поля и начало игры"""
    
    data = callback.data.split(":")
    mines_count = int(data[1])
    owner_id = int(data[2])
    
    if not await check_owner(callback, owner_id):
        return
    
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    bet = user_data[11]
    
    if balance < bet:
        return await callback.answer("❌ Недостаточно средств!", show_alert=True)
        
    # Списываем ставку
    if not db.add_balance(user_id, -bet, is_bet=True):
        return await callback.answer("❌ Ошибка при списании ставки. Недостаточно средств!", show_alert=True)
        
    msg_id = str(callback.message.message_id)
    # Генерируем поле 5x5 (25 ячеек)
    field = [0] * 25
    mines_indices = random.sample(range(25), mines_count)
    for idx in mines_indices:
        field[idx] = 1
        
    game_data = {
        "type": "mines",
        "mines_count": mines_count,
        "field": field,
        "bet": bet,
        "revealed": [],
        "current_step": 0,
        "processing_click": False
    }
    await state.update_data({f"game_{msg_id}": game_data})
    
    await show_mines_field(callback.message, user_id, state)

async def show_mines_field(message: Message, user_id: int, state: FSMContext):
    """Отображение игрового поля Мины (Screenshot 3)"""
    msg_id = str(message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data:
        return
        
    revealed = game_data.get("revealed", [])
    mines_count = game_data.get("mines_count")
    bet = game_data.get("bet")
    
    current_coef = get_mines_coef(len(revealed), mines_count)
    win_amount = bet * current_coef
    
    builder = InlineKeyboardBuilder()
    for i in range(25):
        if i in revealed:
            builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
        else:
            builder.add(InlineKeyboardButton(text="🌑", callback_data=f"mine_click:{i}:{user_id}")) # Темный круг
    
    builder.adjust(5)
    
    # Кнопка Забрать
    builder.row(InlineKeyboardButton(
        text=f"⚡ Забрать · {win_amount:,.2f} 💰", 
        callback_data=f"mine_cashout:{user_id}"
    ))
    
    # Нижний ряд кнопок
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_mines:{user_id}")
    )

    coefs_line = get_mines_coefs_line(mines_count, len(revealed) + 1)
    text = get_text(user_id, "mines_playing").format(
        mines=mines_count,
        bet=bet,
        coef=current_coef,
        win=win_amount,
        coefs=coefs_line
    )
    
    await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("mine_click:"))
async def mine_click_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка клика по ячейке"""
    data = callback.data.split(":")
    idx = int(data[1])
    owner_id = int(data[2])
    
    if not await check_owner(callback, owner_id):
        return
        
    msg_id = str(callback.message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data or game_data.get("type") != "mines":
        return await callback.answer("❌ Игра уже завершена!", show_alert=True)
        
    # Защита от спама кликами
    if game_data.get("processing_click"):
        return await callback.answer()
        
    game_data["processing_click"] = True
    await state.update_data({f"game_{msg_id}": game_data})

    try:
        field = game_data["field"]
        revealed = game_data["revealed"]
        
        if idx in revealed:
            return await callback.answer("❌ Эта ячейка уже открыта!", show_alert=True)
        
        if field[idx] == 1: # Попал на мину
            # Конец игры, проигрыш
            builder = InlineKeyboardBuilder()
            for i in range(25):
                if i == idx:
                    builder.add(InlineKeyboardButton(text="💥", callback_data="none"))
                elif field[i] == 1:
                    builder.add(InlineKeyboardButton(text="💣", callback_data="none"))
                elif i in revealed:
                    builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
                else:
                    builder.add(InlineKeyboardButton(text="🌑", callback_data="none")) # Темный круг
            builder.adjust(5)
            builder.row(InlineKeyboardButton(text="🔄 Играть еще", callback_data=f"game_mines:{owner_id}"))
            builder.row(InlineKeyboardButton(text=get_btn(owner_id, "back"), callback_data=f"game_mines:{owner_id}"))
            
            # Удаляем данные игры для этого сообщения
            all_data = await state.get_data()
            if f"game_{msg_id}" in all_data:
                del all_data[f"game_{msg_id}"]
                await state.set_data(all_data)
                
            user_name = get_user_display_name(owner_id, callback.from_user.first_name)
            new_balance = db.get_user_data(owner_id)[3]
            text = (
                f"👤 <b>{user_name}</b>\n"
                f"<b>Проигрывает в игре 💣 на {game_data['bet']:.2f} 💰</b>\n"
                f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.HTML
            )
        else:
            # Успешный ход
            revealed.append(idx)
            game_data["revealed"] = revealed
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            
            # Если все ячейки без мин открыты - автовыплата
            if len(revealed) == (25 - game_data["mines_count"]):
                await mine_cashout_handler(callback, state)
            else:
                await show_mines_field(callback.message, owner_id, state)
    finally:
        # Снимаем флаг если игра все еще активна
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            current_game = all_data[f"game_{msg_id}"]
            if current_game.get("processing_click"):
                current_game["processing_click"] = False
                await state.update_data({f"game_{msg_id}": current_game})

@dp.callback_query(F.data.startswith("mine_cashout:"))
async def mine_cashout_handler(callback: CallbackQuery, state: FSMContext):
    """Забрать выигрыш в Минах"""
    owner_id = int(callback.data.split(":")[-1]) if ":" in callback.data else callback.from_user.id
    
    if not await check_owner(callback, owner_id):
        return
        
    msg_id = str(callback.message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data or game_data.get("type") != "mines":
        return await callback.answer("❌ Игра уже завершена!", show_alert=True)
        
    # Защита от спама кликами (выплата)
    if game_data.get("processing_click"):
        return await callback.answer()
        
    game_data["processing_click"] = True
    await state.update_data({f"game_{msg_id}": game_data})

    try:
        revealed = game_data["revealed"]
        mines_count = game_data["mines_count"]
        bet = game_data["bet"]
        
        # Нельзя забрать без открытых ячеек
        if not revealed:
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            return await callback.answer("❌ Откройте хотя бы одну ячейку!", show_alert=True)

        coef = get_mines_coef(len(revealed), mines_count)
        win_amount = bet * coef
        
        if not db.add_balance(owner_id, win_amount):
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            return await callback.answer("❌ Ошибка при начислении выигрыша!", show_alert=True)

        new_balance = db.get_user_data(owner_id)[3]
        
        # Показываем финальное поле перед выходом
        field = game_data["field"]
        builder = InlineKeyboardBuilder()
        for i in range(25):
            if i in revealed:
                builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
            elif field[i] == 1:
                builder.add(InlineKeyboardButton(text="💣", callback_data="none"))
            else:
                builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
        builder.adjust(5)
        builder.row(InlineKeyboardButton(text="🔄 Играть еще", callback_data=f"game_mines:{owner_id}"))
        builder.row(InlineKeyboardButton(text=get_btn(owner_id, "back"), callback_data=f"game_mines:{owner_id}"))

        # Удаляем данные игры для этого сообщения
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            del all_data[f"game_{msg_id}"]
            await state.set_data(all_data)
            
        user_name = get_user_display_name(owner_id, callback.from_user.first_name)
        
        text = (
            f"<b>👤 {user_name}</b>\n"
            f"<b>Побеждает в игре 💣 на {bet:.2f} 💰</b>\n"
            f"<blockquote><b>× {coef:.2f} 🎄 Выигрыш {win_amount:.2f} 💰 ❞</b></blockquote>\n\n"
            f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
        )
    
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
        if win_amount >= 50:
            await send_alert(callback.bot, owner_id, win_amount, "win")
    finally:
        # Снимаем флаг если игра все еще активна
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            current_game = all_data[f"game_{msg_id}"]
            if current_game.get("processing_click"):
                current_game["processing_click"] = False
                await state.update_data({f"game_{msg_id}": current_game})

TOWER_COEFS = {
    1: [1.17, 1.47, 1.84, 2.29, 2.87],
    2: [1.46, 2.19, 3.29, 4.93, 7.40],
    3: [1.95, 3.90, 7.80, 15.60, 31.20],
    4: [2.92, 8.76, 26.28, 78.84, 236.52]
}

def get_tower_coefs_line(bombs_count):
    """Генерирует строку коэффициентов для меню выбора"""
    coefs = TOWER_COEFS.get(bombs_count, TOWER_COEFS[1])
    line = " → ".join([f"x{c:.2f}" for c in coefs])
    return line + " ❞"

async def show_tower_menu(event: CallbackQuery | Message, user_id: int, state: FSMContext, edit=True):
    """Главное меню игры Башня"""
    data = await state.get_data()
    bombs_count = data.get("tower_bombs", 1) # По умолчанию 1 бомба
    
    user_data = db.get_user_data(user_id)
    if not user_data: return
    username = user_data[6] or "Игрок"
    balance = user_data[3]
    bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"🕹 Играть · {bet:,.2f} 💰", callback_data=f"tower_start_game:{bombs_count}:{user_id}"))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"modes_menu:{user_id}"),
        InlineKeyboardButton(text=f"Изменить · {bombs_count} 💣", callback_data=f"tower_select_bombs:{user_id}")
    )
    
    coefs_line = get_tower_coefs_line(bombs_count)
    text = (
        f"🏙 <b>Башня</b>\n\n"
        f"👤 <b>{username}</b>\n"
        f"<blockquote>👛 <b>Баланс — {balance:,.2f} 💰</b>\n"
        f"<b>Ставка — {bet:,.2f} 💰</b></blockquote>\n\n"
        f"Выбрано — {bombs_count} 💣\n"
        f"<blockquote>{coefs_line}</blockquote>"
    )
    
    if edit and isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        message = event if isinstance(event, Message) else event.message
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("game_tower:"))
async def game_tower_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик колбэка для входа в Башню"""
    owner_id = int(callback.data.split(":")[-1]) if ":" in callback.data else callback.from_user.id
    if not await check_owner(callback, owner_id):
        return
    
    await show_tower_menu(callback, owner_id, state)

@dp.callback_query(F.data.startswith("tower_select_bombs:"))
async def tower_select_bombs_handler(callback: CallbackQuery, state: FSMContext):
    """Меню выбора количества бомб"""
    owner_id = int(callback.data.split(":")[-1])
    if not await check_owner(callback, owner_id):
        return
    
    data = await state.get_data()
    current_bombs = data.get("tower_bombs", 1)
    
    builder = InlineKeyboardBuilder()
    # Кнопки 1-4
    for i in range(1, 5):
        text = f"{i}"
        if i == current_bombs:
            text = f"{i} 💣"
        builder.add(InlineKeyboardButton(text=text, callback_data=f"tower_set_bombs:{i}:{owner_id}"))
    
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_tower:{owner_id}"))
    
    coefs_line = get_tower_coefs_line(current_bombs)
    text = (
        f"💣 <b>Выберите количество</b>\n\n"
        f"Выбрано — {current_bombs} 💣\n\n"
        f"<blockquote>{coefs_line}</blockquote>"
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("tower_set_bombs:"))
async def tower_set_bombs_handler(callback: CallbackQuery, state: FSMContext):
    """Установка количества бомб"""
    parts = callback.data.split(":")
    count = int(parts[1])
    owner_id = int(parts[-1])
    
    if not await check_owner(callback, owner_id):
        return
        
    await state.update_data(tower_bombs=count)
    await tower_select_bombs_handler(callback, state)

@dp.callback_query(F.data.startswith("tower_start_game:"))
async def tower_start_game_handler(callback: CallbackQuery, state: FSMContext):
    """Начало игры в Башню"""
    parts = callback.data.split(":")
    bombs_count = int(parts[1])
    owner_id = int(parts[2])
    
    if not await check_owner(callback, owner_id):
        return
    
    user_data = db.get_user_data(owner_id)
    balance = user_data[3]
    bet = user_data[11]
    
    if balance < bet:
        return await callback.answer("❌ Недостаточно средств!", show_alert=True)
        
    # Списываем ставку
    if not db.add_balance(owner_id, -bet, is_bet=True):
        return await callback.answer("❌ Ошибка при списании ставки!", show_alert=True)
        
    msg_id = str(callback.message.message_id)
    # Генерация поля: 5 уровней, в каждом 5 ячеек, в bombs_count из них бомбы
    field = []
    for _ in range(5):
        level = [0] * 5
        # Ограничиваем количество бомб до 4, чтобы всегда был свободный проход
        actual_bombs = min(bombs_count, 4)
        bombs_indices = random.sample(range(5), actual_bombs)
        for idx in bombs_indices:
            level[idx] = 1
        field.append(level)
        
    game_data = {
        "type": "tower",
        "tower_bombs": bombs_count,
        "tower_field": field,
        "tower_bet": bet,
        "tower_level": 0, # Текущий уровень (0-4)
        "tower_revealed": [], # Список выбранных индексов на каждом уровне
        "processing_click": False
    }
    await state.update_data({f"game_{msg_id}": game_data})
    
    await show_tower_field(callback.message, owner_id, state)

async def show_tower_field(message: Message, user_id: int, state: FSMContext):
    """Отображение игрового поля Башни"""
    msg_id = str(message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data:
        return
        
    level = game_data.get("tower_level", 0)
    bombs_count = game_data.get("tower_bombs", 1)
    bet = game_data.get("tower_bet")
    revealed = game_data.get("tower_revealed", [])
    
    coefs = TOWER_COEFS[bombs_count]
    current_coef = coefs[level-1] if level > 0 else 1.0
    win_amount = bet * current_coef
    
    builder = InlineKeyboardBuilder()
    
    # Рисуем уровни сверху вниз (от 4 до 0)
    for l in range(4, -1, -1):
        # Коэффициент слева
        builder.add(InlineKeyboardButton(text=f"x{coefs[l]:.2f}", callback_data="none"))
        
        # 5 ячеек уровня
        for i in range(5):
            if l < level:
                # Пройденные уровни
                chosen_idx = revealed[l]
                if i == chosen_idx:
                    builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
                else:
                    builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
            elif l == level:
                # Текущий уровень
                builder.add(InlineKeyboardButton(text="🌍", callback_data=f"tower_click:{l}:{i}:{user_id}"))
            else:
                # Будущие уровни
                builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
    
    builder.adjust(6) # 1 (коэф) + 5 (ячейки)
    
    # Кнопка Забрать (если уже есть выигрыш)
    if level > 0:
        builder.row(InlineKeyboardButton(
            text=f"⚡ Забрать · {win_amount:,.2f} 💰", 
            callback_data=f"tower_cashout:{user_id}"
        ))
    
    # Нижний ряд кнопок
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_tower:{user_id}")
    )

    text = (
        f"🏙 <b>Башня · {bombs_count} 💣</b>\n\n"
        f"<b>{bet:,.2f} 💰 × {current_coef:.2f} ➔ {win_amount:,.2f} 💰</b>"
    )
    
    await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("tower_click:"))
async def tower_click_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка клика по ячейке в Башне"""
    parts = callback.data.split(":")
    level = int(parts[1])
    idx = int(parts[2])
    owner_id = int(parts[3])
    
    if not await check_owner(callback, owner_id):
        return
        
    msg_id = str(callback.message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data or game_data.get("type") != "tower":
        return await callback.answer("❌ Игра уже завершена!", show_alert=True)
        
    if game_data.get("processing_click"):
        return await callback.answer()
        
    game_data["processing_click"] = True
    await state.update_data({f"game_{msg_id}": game_data})

    try:
        current_level = game_data["tower_level"]
        if level != current_level:
            return await callback.answer()

        field = game_data["tower_field"]
        revealed = game_data["tower_revealed"]
        bombs_count = game_data["tower_bombs"]
        bet = game_data["tower_bet"]
        
        if field[level][idx] == 1: # Попал на бомбу
            # Проигрыш
            # Удаляем данные игры для этого сообщения
            all_data = await state.get_data()
            if f"game_{msg_id}" in all_data:
                del all_data[f"game_{msg_id}"]
                await state.set_data(all_data)
                
            user_name = get_user_display_name(owner_id, callback.from_user.first_name)
            new_balance = db.get_user_data(owner_id)[3]
            
            # Показываем поле с бомбой
            builder = InlineKeyboardBuilder()
            for l in range(4, -1, -1):
                builder.add(InlineKeyboardButton(text=f"x{TOWER_COEFS[bombs_count][l]:.2f}", callback_data="none"))
                for i in range(5):
                    if l < level:
                        if i == revealed[l]: builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
                        else: builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
                    elif l == level:
                        if i == idx: builder.add(InlineKeyboardButton(text="💥", callback_data="none"))
                        elif field[l][i] == 1: builder.add(InlineKeyboardButton(text="💣", callback_data="none"))
                        else: builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
                    else:
                        if field[l][i] == 1: builder.add(InlineKeyboardButton(text="💣", callback_data="none"))
                        else: builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
            builder.adjust(6)
            builder.row(InlineKeyboardButton(text="🔄 Играть еще", callback_data=f"game_tower:{owner_id}"))
            builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_tower:{owner_id}"))

            text = (
                f"👤 <b>{user_name}</b>\n"
                f"<b>Проигрывает в игре 🏙 на {bet:,.2f} 💰</b>\n"
                f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:,.2f} 💰</b>"
            )
            await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
        else:
            # Успешный ход
            revealed.append(idx)
            new_level = level + 1
            game_data["tower_level"] = new_level
            game_data["tower_revealed"] = revealed
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            
            if new_level == 5:
                # Победа (прошел все уровни)
                await tower_cashout_handler(callback, state)
            else:
                await show_tower_field(callback.message, owner_id, state)
    finally:
        # Снимаем флаг если игра все еще активна
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            current_game = all_data[f"game_{msg_id}"]
            if current_game.get("processing_click"):
                current_game["processing_click"] = False
                await state.update_data({f"game_{msg_id}": current_game})

@dp.callback_query(F.data.startswith("tower_cashout:"))
async def tower_cashout_handler(callback: CallbackQuery, state: FSMContext):
    """Забрать выигрыш в Башне"""
    owner_id = int(callback.data.split(":")[-1])
    if not await check_owner(callback, owner_id):
        return
        
    msg_id = str(callback.message.message_id)
    all_data = await state.get_data()
    game_data = all_data.get(f"game_{msg_id}")
    
    if not game_data or game_data.get("type") != "tower":
        return await callback.answer("❌ Игра уже завершена!", show_alert=True)
        
    if game_data.get("processing_click"):
        return await callback.answer()
        
    game_data["processing_click"] = True
    await state.update_data({f"game_{msg_id}": game_data})

    try:
        level = game_data["tower_level"]
        bombs_count = game_data["tower_bombs"]
        bet = game_data["tower_bet"]
        revealed = game_data["tower_revealed"]
        
        if level == 0:
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            return await callback.answer("❌ Сделайте хотя бы один ход!", show_alert=True)
            
        coef = TOWER_COEFS[bombs_count][level-1]
        win_amount = bet * coef
        
        if not db.add_balance(owner_id, win_amount):
            game_data["processing_click"] = False
            await state.update_data({f"game_{msg_id}": game_data})
            return await callback.answer("❌ Ошибка при начислении выигрыша!", show_alert=True)

        new_balance = db.get_user_data(owner_id)[3]
        user_name = get_user_display_name(owner_id, callback.from_user.first_name)
        
        # Показываем финальное поле
        builder = InlineKeyboardBuilder()
        for l in range(4, -1, -1):
            builder.add(InlineKeyboardButton(text=f"x{TOWER_COEFS[bombs_count][l]:.2f}", callback_data="none"))
            for i in range(5):
                if l < level:
                    if i == revealed[l]: builder.add(InlineKeyboardButton(text="💎", callback_data="none"))
                    else: builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
                else:
                    if game_data["tower_field"][l][i] == 1: builder.add(InlineKeyboardButton(text="💣", callback_data="none"))
                    else: builder.add(InlineKeyboardButton(text="🌑", callback_data="none"))
        builder.adjust(6)
        builder.row(InlineKeyboardButton(text="🔄 Играть еще", callback_data=f"game_tower:{owner_id}"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game_tower:{owner_id}"))

        # Удаляем данные игры для этого сообщения
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            del all_data[f"game_{msg_id}"]
            await state.set_data(all_data)
            
        text = (
            f"<b>👤 {user_name}</b>\n"
            f"<b>Побеждает в игре 🏙 на {bet:,.2f} 💰</b>\n"
            f"<blockquote><b>× {coef:.2f} 🎄 Выигрыш {win_amount:,.2f} 💰 ❞</b></blockquote>\n\n"
            f"<b>📋 Баланс {new_balance:,.2f} 💰</b>"
        )
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
        
        if win_amount >= 50:
            await send_alert(callback.bot, owner_id, win_amount, "win")
    finally:
        # Снимаем флаг если игра все еще активна
        all_data = await state.get_data()
        if f"game_{msg_id}" in all_data:
            current_game = all_data[f"game_{msg_id}"]
            if current_game.get("processing_click"):
                current_game["processing_click"] = False
                await state.update_data({f"game_{msg_id}": current_game})

@dp.callback_query(F.data.startswith("custom_games_menu:"))
async def custom_games_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Меню авторских игр"""
        
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
        
    user_data = db.get_user_data(user_id)
    if not user_data:
        return
        
    balance = user_data[3]
    bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    # Ряд 1: x2, x3, x4, x5
    builder.row(
        InlineKeyboardButton(text="🏴‍☠️ x2", callback_data=f"custom_game:2:{user_id}"),
        InlineKeyboardButton(text="🧭 x3", callback_data=f"custom_game:3:{user_id}"),
        InlineKeyboardButton(text="🐟 x4", callback_data=f"custom_game:4:{user_id}"),
        InlineKeyboardButton(text="🎈 x5", callback_data=f"custom_game:5:{user_id}")
    )
    # Ряд 2: x10, x15, x20, x30
    builder.row(
        InlineKeyboardButton(text="💣 x10", callback_data=f"custom_game:10:{user_id}"),
        InlineKeyboardButton(text="🍄 x15", callback_data=f"custom_game:15:{user_id}"),
        InlineKeyboardButton(text="🍒 x20", callback_data=f"custom_game:20:{user_id}"),
        InlineKeyboardButton(text="🦋 x30", callback_data=f"custom_game:30:{user_id}")
    )
    # Ряд 3: x40, x50, x100
    builder.row(
        InlineKeyboardButton(text="💎 x40", callback_data=f"custom_game:40:{user_id}"),
        InlineKeyboardButton(text="🚀 x50", callback_data=f"custom_game:50:{user_id}"),
        InlineKeyboardButton(text="🐳 x100", callback_data=f"custom_game:100:{user_id}")
    )
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"play:{user_id}"))
    
    text = (
        "<b>🐋 Авторские игры</b>\n\n"
        f"<blockquote>Баланс — {balance:.2f} 💰\n"
        f"Ставка — {bet:.2f} 💰</blockquote>\n\n"
        "<i>Выбирайте коэффициент и испытайте удачу!</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("custom_game:"))
async def custom_game_play_handler(callback: CallbackQuery, state: FSMContext):
    """Обработка игры с коэффициентом"""
    
    data = callback.data.split(":")
    coef = int(data[1])
    owner_id = int(data[2])
    
    if not await check_owner(callback, owner_id):
        return
        
    game_data = await state.get_data()
    if game_data.get("processing_click"):
        return await callback.answer()
    await state.update_data(processing_click=True)
    
    await state.set_state(PlayingState.custom)
    
    try:
        user_id = callback.from_user.id
        user_data = db.get_user_data(user_id)
        if not user_data:
            return
            
        balance = user_data[3]
        bet = user_data[11]
        
        if balance < bet:
            return await callback.answer("❌ Недостаточно средств!", show_alert=True)
            
        # Списываем ставку
        if not db.add_balance(user_id, -bet, is_bet=True):
            return await callback.answer("❌ Ошибка при списании ставки. Недостаточно средств!", show_alert=True)
        
        # Отправляем сообщение о ставке
        user_name = get_user_display_name(user_id, callback.from_user.first_name)
        bet_msg_text = (
            f"<b>{user_name} ставит {bet:.2f} 💰</b>\n"
            f"<blockquote><b>🐋 Авторская игра: x{coef}</b></blockquote>"
        )
        await callback.message.answer(bet_msg_text, parse_mode=ParseMode.HTML)
        
        # Отправляем эмодзи игры
        emoji_map = {
            2: "🏴‍☠️", 3: "🧭", 4: "🐟", 5: "🎈",
            10: "💣", 15: "🍄", 20: "🍒", 30: "🦋",
            40: "💎", 50: "🚀", 100: "🐳"
        }
        emoji = emoji_map.get(coef, "🎲")
        await callback.message.answer(emoji)
        
        # Рандом 1 к N
        # Шанс 1/coef
        win_number = random.randint(1, coef)
        is_win = (win_number == coef) 
        
        win_amount = bet * coef if is_win else 0
        
        if is_win:
            if not db.add_balance(user_id, win_amount):
                 # Если вдруг баланс не начислился (хотя тут прибавка, но для консистентности)
                 return await callback.answer("❌ Ошибка при начислении выигрыша!", show_alert=True)
            
        # Получаем обновленный баланс
        new_balance = db.get_user_data(user_id)[3]
        user_name = get_user_display_name(user_id, callback.from_user.first_name)
        
        if is_win:
            win_chance = 100 / coef
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Побеждает в игре {emoji} на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× {coef} 🎄 Выигрыш {win_amount:.2f} 💰 ❞</b></blockquote>\n\n"
                f"<blockquote>{emoji} Шанс выигрыша {win_chance:.1f}%, коэффициент: x{coef}\n"
                f"🎟 Ваше число {win_number}, нужно: {coef}</blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
        else:
            # Начисляем рефские 5%
            referrer_id = user_data[12]
            if referrer_id:
                db.add_ref_balance(referrer_id, bet * 0.05)
                
            win_chance = 100 / coef
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Проигрывает в игре {emoji} на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                f"<blockquote>{emoji} Шанс выигрыша {win_chance:.1f}%, коэффициент: x{coef}\n"
                f"🎟 Ваше число {win_number}, нужно: {coef}</blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            
        # Отправляем сообщение
        all_data = await state.get_data()
        if "processing_click" in all_data:
            del all_data["processing_click"]
            await state.set_data(all_data)
        
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
        
        if is_win and win_amount >= 50:
            await send_alert(callback.bot, user_id, win_amount, "win")
    finally:
        # Если игра не закончилась (не был вызван state.clear()), снимаем флаг
        if await state.get_state() == PlayingState.custom:
            await state.update_data(processing_click=False)

@dp.callback_query(F.data.startswith("change_bet:"))
async def change_bet_callback(callback: CallbackQuery, state: FSMContext):
    """Начало изменения ставки"""
    try:
        owner_id = int(callback.data.split(":")[-1])
        if callback.from_user.id != owner_id:
            return await callback.answer("❌ Это не ваша кнопка!", show_alert=True)
    except:
        pass
    user_id = callback.from_user.id
    await state.set_state(BetState.entering_bet)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_action:{user_id}"))
    
    await callback.message.edit_text(
        get_text(user_id, "enter_bet_amount"),
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.message(BetState.entering_bet)
async def process_bet_amount(message: Message, state: FSMContext):
    """Процесс изменения ставки"""
    user_id = message.from_user.id
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0.01:
             return await message.answer("❌ Минимальная ставка — <b>0.01 💰</b>")
        if amount > config.MAX_BET:
             return await message.answer(f"❌ Максимальная ставка — <b>{config.MAX_BET:.2f} 💰</b>")
    except ValueError:
        return await message.answer("❌ Введите корректную сумму (число больше 0)")

    db.set_bet(user_id, amount)
    await state.set_state(None)
    await message.answer(f"✅ Ставка успешно изменена на <b>{amount:.2f} 💰</b>")
    # Возвращаемся в меню игры
    # Имитируем нажатие кнопки "Играть"
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
    await play_callback(FakeCallback(message))

@dp.callback_query(F.data.startswith("game:"))
async def game_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора игры"""
        
    parts = callback.data.split(":")
    game_type = parts[1]
    
    # Проверка владельца если есть :user_id
    if len(parts) > 2:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    
    if game_type == "dice":
        await dice_menu_handler(callback, state)
    elif game_type in ["soccer", "basket", "darts", "bowling", "slots"]:
         await emoji_strategy_menu(callback, state, game_type)
    elif game_type in ["dice_emoji"]:
         # Для эмодзи оставляем старую логику броска
         await old_game_handler(callback, state)
    else:
         await callback.answer("🚧 Режим в разработке", show_alert=True)

EMOJI_GAME_OPTIONS = {
    "soccer": ["Мимо ворот", "В штангу", "Гол в центр", "Гол от штанги", "Гол в угол"],
    "basket": ["Мимо", "Об дужку", "Об щит", "В корзину", "Чистый мяч"],
    "darts": ["Мимо", "Белое кольцо", "Чёрное кольцо", "Красное кольцо", "Центр"],
    "bowling": ["Мимо", "1 кегля", "2-3 кегли", "4-5 кегль", "Страйк"],
    "slots": ["🎰 3 семёрки", "🍇 3 винограда", "🍋 3 лимона", "💿 3 бара"]
}

async def emoji_strategy_menu(event: CallbackQuery | Message, state: FSMContext, game_type: str, selected_indices: list = None):
    """Меню выбора стратегии для эмодзи-игр"""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    message = event.message if is_callback else event
    
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    current_bet = user_data[11]
    
    if selected_indices is None:
        selected_indices = []
        
    options = EMOJI_GAME_OPTIONS.get(game_type, [])
    
    # Расчет коэффициента
    count = len(selected_indices)
    coef = 0
    if game_type == "slots":
        if count == 1: coef = 60.0
        elif count == 2: coef = 30.0
        elif count == 3: coef = 20.0
        elif count == 4: coef = 15.0
    else:
        # 1 вариант - x5, 2 - x2.5, 3 - x1.66, 4 - x1.25
        if count == 1: coef = 5.0
        elif count == 2: coef = 2.5
        elif count == 3: coef = 1.66
        elif count == 4: coef = 1.25
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки выбора исходов (в 2 колонки)
    for i, opt_text in enumerate(options):
        prefix = "✅ " if i in selected_indices else ""
        builder.add(InlineKeyboardButton(
            text=f"{prefix}{opt_text}", 
            callback_data=f"emoji_strat_toggle:{game_type}:{i}:{user_id}"
        ))
    builder.adjust(2)
    
    # Эмодзи для заголовка
    header_emoji = {
        "soccer": "⚽",
        "basket": "🏀",
        "darts": "🎯",
        "bowling": "🎳",
        "slots": "🎰"
    }.get(game_type, "🎲")
    
    # Кнопка "Играть"
    if count > 0:
        builder.row(InlineKeyboardButton(
            text=f"🫐 Играть (x{coef}) 🫐", 
            callback_data=f"emoji_strat_play:{game_type}:{user_id}"
        ))
    
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"play:{user_id}"))
    
    text = (
        f"{header_emoji} <b>Выберите стратегию игры!</b>\n\n"
        f"<i>Вы можете выбрать несколько исходов, чем больше исходов — тем меньше коэффициент</i>\n\n"
        f"<blockquote>Баланс — <b>{balance:,.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:,.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>"
    )
    
    # Сохраняем выбранные индексы в стейт
    await state.update_data(selected_indices=selected_indices)
    await state.set_state(PlayingState.strategy)
    
    if is_callback:
        try:
            await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
        except Exception as e:
            logging.error(f"Error editing strategy menu: {e}")
            pass
    else:
        try:
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
        except Exception as e:
            logging.error(f"Error sending strategy menu: {e}")
            # Попробуем отправить без HTML если произошла ошибка
            await message.answer(text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<blockquote>", "").replace("</blockquote>", ""), 
                               reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("emoji_strat_toggle:"))
async def emoji_strat_toggle_handler(callback: CallbackQuery, state: FSMContext):
    """Переключение выбора исхода"""
    parts = callback.data.split(":")
    game_type = parts[1]
    index = int(parts[2])
    owner_id = int(parts[-1])
    
    if not await check_owner(callback, owner_id):
        return
        
    data = await state.get_data()
    selected_indices = data.get("selected_indices", [])
    
    if index in selected_indices:
        selected_indices.remove(index)
    else:
        if len(selected_indices) >= 4:
            return await callback.answer("❌ Можно выбрать максимум 4 варианта!", show_alert=True)
        selected_indices.append(index)
        
    await emoji_strategy_menu(callback, state, game_type, selected_indices)

@dp.callback_query(F.data.startswith("emoji_strat_play:"))
async def emoji_strat_play_handler(callback: CallbackQuery, state: FSMContext):
    """Запуск игры с выбранной стратегией"""
    parts = callback.data.split(":")
    game_type = parts[1]
    owner_id = int(parts[-1])
    
    if not await check_owner(callback, owner_id):
        return
        
    game_data = await state.get_data()
    if game_data.get("processing_click"):
        return await callback.answer()
    await state.update_data(processing_click=True)
    
    try:
        selected_indices = game_data.get("selected_indices", [])
        
        if not selected_indices:
            return await callback.answer("❌ Выберите хотя бы один исход!", show_alert=True)
            
        # Запускаем игру
        await start_emoji_strat_game(callback, state, game_type, selected_indices)
    finally:
        # Если игра не закончилась (не был вызван state.clear()), снимаем флаг
        if await state.get_state() == PlayingState.strategy:
            await state.update_data(processing_click=False)

async def start_emoji_strat_game(callback: CallbackQuery, state: FSMContext, game_type: str, selected_indices: list):
    """Логика игры с выбранной стратегией"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    bet = user_data[11]
    
    if balance < bet:
        await state.update_data(processing_click=False)
        return await callback.answer("❌ Недостаточно средств для ставки!", show_alert=True)
        
    # Списываем ставку
    if not db.add_balance(user_id, -bet, is_bet=True):
        await state.update_data(processing_click=False)
        return await callback.answer("❌ Ошибка при списании ставки. Недостаточно средств!", show_alert=True)
    
    # Расчет коэффициента
    count = len(selected_indices)
    coef = 0
    if game_type == "slots":
        if count == 1: coef = 60.0
        elif count == 2: coef = 30.0
        elif count == 3: coef = 20.0
        elif count == 4: coef = 15.0
    else:
        if count == 1: coef = 5.0
        elif count == 2: coef = 2.5
        elif count == 3: coef = 1.66
        elif count == 4: coef = 1.25
    
    # Эмодзи
    emoji = {
        "soccer": "⚽",
        "basket": "🏀",
        "darts": "🎯",
        "bowling": "🎳",
        "slots": "🎰"
    }.get(game_type, "🎲")
    
    # Отправляем сообщение о ставке
    user_name = get_user_display_name(user_id, callback.from_user.first_name)
    options = EMOJI_GAME_OPTIONS[game_type]
    selected_texts = [options[i] for i in selected_indices]
    
    bet_msg_text = (
        f"<b>{user_name} ставит {bet:.2f} 💰</b>\n"
        f"<blockquote><b>🎮 Игра: {emoji} (x{coef})</b>\n"
        f"🎯 Выбрано: {', '.join(selected_texts)}</blockquote>"
    )
    await callback.message.answer(bet_msg_text, parse_mode=ParseMode.HTML)
    
    msg = await callback.message.answer_dice(emoji=emoji)
    value = msg.dice.value
    
    is_win = False
    if game_type == "slots":
        # 1 - 777, 22 - Grapes, 43 - Lemons, 64 - Bar
        slot_values = {0: 1, 1: 22, 2: 43, 3: 64}
        for idx in selected_indices:
            if value == slot_values.get(idx):
                is_win = True
                break
    else:
        for idx in selected_indices:
            target_val = idx + 1
            if idx == 4: # Последний вариант (индекс 4) выигрывает при 5 или 6
                if value >= 5:
                    is_win = True
                    break
            else:
                if value == target_val:
                    is_win = True
                    break
                
    await asyncio.sleep(4)
    
    win_amount = bet * coef if is_win else 0
    user_name = get_user_display_name(user_id, callback.from_user.first_name)

    if is_win:
        if not db.add_balance(user_id, win_amount):
             return await callback.answer("❌ Ошибка при начислении выигрыша!", show_alert=True)
            
        # Получаем обновленный баланс
        new_balance = db.get_user_data(user_id)[3]
        
        text = (
            f"<b>👤 {user_name}</b>\n"
            f"<b>Побеждает в игре {emoji} на {bet:.2f} 💰</b>\n"
            f"<blockquote><b>× {coef} 🎄 Выигрыш {win_amount:.2f} 💰 ❞</b></blockquote>\n\n"
            f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
        )
    else:
        # Начисляем рефские 5%
        referrer_id = user_data[12]
        if referrer_id:
            db.add_ref_balance(referrer_id, bet * 0.05)
            
        new_balance = db.get_user_data(user_id)[3]
        text = (
            f"<b>👤 {user_name}</b>\n"
            f"<b>Проигрывает в игре {emoji} на {bet:.2f} 💰</b>\n"
            f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
            f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
        )
        
    await state.update_data(processing_click=False)
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    if is_win and win_amount >= 50:
        await send_alert(callback.bot, user_id, win_amount, "win")


async def dice_menu_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    
    # Скрин 1: Выбор режима кубиков
    builder.row(
        InlineKeyboardButton(text="🎲 1 куб", callback_data=f"dice_mode:1:{user_id}"),
        InlineKeyboardButton(text="🎲 2 куба", callback_data=f"dice_mode:2:{user_id}"),
        InlineKeyboardButton(text="🎲 3 куба", callback_data=f"dice_mode:3:{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🎲 На число", callback_data=f"dice_mode:number:{user_id}"),
        InlineKeyboardButton(text="🎲 Нет 6", callback_data=f"dice_mode:not_6:{user_id}")
    )
    # Новые режимы
    builder.row(
        InlineKeyboardButton(text="🎲 Кубы 7", callback_data=f"dice_mode:cubes_7:{user_id}"),
        InlineKeyboardButton(text="🎲 Произведение", callback_data=f"dice_mode:multiply:{user_id}")
    )
    
    builder.row(InlineKeyboardButton(text=get_btn(user_id, "back"), callback_data=f"play:{user_id}"))
    
    await callback.message.edit_text(
        f"<b>🎲 Выберите режим игры!</b>\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("dice_mode:"))
async def dice_mode_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора режима кубиков"""
    parts = callback.data.split(":")
    mode = parts[1]
    
    # Проверка владельца если есть :user_id
    if len(parts) > 2:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    balance = user_data[3]
    current_bet = user_data[11]
    
    builder = InlineKeyboardBuilder()
    text = ""
    
    if mode == "1":
        # Скрин 2: 1 куб
        text = "Сделайте выбор для игры 🎲"
        builder.row(
            InlineKeyboardButton(text="🎲 1, 2, 3 (x2)", callback_data=f"dice_bet:1_low:{user_id}"),
            InlineKeyboardButton(text="🎲 4, 5, 6 (x2)", callback_data=f"dice_bet:1_high:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🎲 Чётное (x2)", callback_data=f"dice_bet:1_even:{user_id}"),
            InlineKeyboardButton(text="🎲 Нечётное (x2)", callback_data=f"dice_bet:1_odd:{user_id}")
        )
        
    elif mode == "2":
        # Скрин 3: 2 куба
        text = "Сделайте выбор для игры 🎲🎲"
        builder.row(
            InlineKeyboardButton(text="Сумма чёт. (x2)", callback_data=f"dice_bet:2_even:{user_id}"),
            InlineKeyboardButton(text="Сумма нечёт. (x2)", callback_data=f"dice_bet:2_odd:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🎲 > 🎲 (x2.4)", callback_data=f"dice_bet:2_left_more:{user_id}"),
            InlineKeyboardButton(text="🎲 < 🎲 (x2.4)", callback_data=f"dice_bet:2_right_more:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="Оба чёт. (x4)", callback_data=f"dice_bet:2_both_even:{user_id}"),
            InlineKeyboardButton(text="Оба нечёт. (x4)", callback_data=f"dice_bet:2_both_odd:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="Шаг (x3.6)", callback_data=f"dice_bet:2_step:{user_id}"),
            InlineKeyboardButton(text="🎲 Дубль", callback_data=f"dice_bet:2_double:{user_id}")
        )

    elif mode == "3":
        # Скрин 4: 3 куба
        text = "Выберите игру с тремя бросками 🎲"
        builder.row(
            InlineKeyboardButton(text="🎲 Трипл", callback_data=f"dice_bet:3_triple:{user_id}"),
            InlineKeyboardButton(text="🎲 67", callback_data=f"dice_bet:3_67:{user_id}")
        )

    elif mode == "number":
        # Скрин 5: На число
        text = "Сделайте выбор для игры\n\nЧто выпадет на 🎲?"
        builder.row(
            InlineKeyboardButton(text="🎲 1 (x6)", callback_data=f"dice_bet:num_1:{user_id}"),
            InlineKeyboardButton(text="🎲 2 (x6)", callback_data=f"dice_bet:num_2:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🎲 3 (x6)", callback_data=f"dice_bet:num_3:{user_id}"),
            InlineKeyboardButton(text="🎲 4 (x6)", callback_data=f"dice_bet:num_4:{user_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🎲 5 (x6)", callback_data=f"dice_bet:num_5:{user_id}"),
            InlineKeyboardButton(text="🎲 6 (x6)", callback_data=f"dice_bet:num_6:{user_id}")
        )

    elif mode == "not_6":
        # Специальный режим: Всё кроме 6
        text = (
            "<b>Всё кроме 6 — большие иксы</b>\n\n"
            "🎲 1 это <b>× 3</b>\n"
            "🎲 2 это <b>× 4</b>\n"
            "🎲 3 это <b>× 5,2</b>\n"
            "🎲 4 это <b>× 6,4</b>\n"
            "🎲 5 это <b>× 7,6</b>\n"
            "🎲 6 это <b>минус × 19</b>"
        )
        builder.row(InlineKeyboardButton(text="🎲 Играть", callback_data=f"dice_bet:not_6:{user_id}"))

    elif mode == "cubes_7":
        text = "Сделайте выбор для игры\n\nСумма двух 🎲, от 2 до 12"
        builder.row(InlineKeyboardButton(text="🎲 Меньше 7 (x2.4)", callback_data=f"dice_bet:sum_less_7:{user_id}"))
        builder.row(InlineKeyboardButton(text="🎲 Точно 7 (x6)", callback_data=f"dice_bet:sum_equal_7:{user_id}"))
        builder.row(InlineKeyboardButton(text="🎲 Больше 7 (x2.4)", callback_data=f"dice_bet:sum_more_7:{user_id}"))

    elif mode == "multiply":
        text = "Сделайте выбор для игры произведение двух 🎲"
        builder.row(InlineKeyboardButton(text="Умн. 1-18 (x1.25)", callback_data=f"dice_bet:mult_1_18:{user_id}"))
        builder.row(InlineKeyboardButton(text="Умн. 19-36 (x4.4)", callback_data=f"dice_bet:mult_19_36:{user_id}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"game:dice:{user_id}"))
    
    await callback.message.edit_text(
        f"{text}\n\n"
        f"<blockquote>Баланс — <b>{balance:.2f}</b> 💰\n"
        f"Ставка — <b>{current_bet:.2f}</b> 💰</blockquote>\n\n"
        f"<i>Пополняй и сыграй на реальные деньги</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

async def process_dice_game(message: Message, user_id: int, bet_type: str, state: FSMContext, custom_numbers: list = None, callback: CallbackQuery = None):
    """Универсальная логика игры в кости"""
    game_data = await state.get_data()
    if game_data.get("processing_click"):
        if callback: await callback.answer()
        return
    await state.update_data(processing_click=True)
    
    try:
        user_data = db.get_user_data(user_id)
        if not user_data:
            return
    
        balance = user_data[3]
        bet = user_data[11]
        
        if bet <= 0:
            db.set_bet(user_id, 0.2)
            bet = 0.2

        if bet_type == "not_6":
            if bet < 0.1:
                if callback: return await callback.answer("❌ Минимальная ставка в этом режиме — 0.1 💰", show_alert=True)
                else: return await message.answer("❌ Минимальная ставка в этом режиме — 0.1 💰")
            if balance < 2.0:
                if callback: return await callback.answer("❌ Для игры в этом режиме баланс должен быть не менее 2 💰", show_alert=True)
                else: return await message.answer("❌ Для игры в этом режиме баланс должен быть не менее 2 💰")

        if balance < bet:
            await state.update_data(processing_click=False)
            if callback: return await callback.answer("❌ Недостаточно средств для ставки!", show_alert=True)
            else: return await message.answer("❌ Недостаточно средств для ставки!")
            
        # Списываем ставку
        # Для режима "Всё кроме 6" ставка списывается только при проигрыше (выпадении 6)
        if bet_type == "not_6":
            potential_loss = bet * 19
            if balance < potential_loss:
                 await state.update_data(processing_click=False)
                 text = f"❌ Недостаточно средств! При выпадении 6 вы потеряете {potential_loss:.2f} 💰.\nНужно иметь эту сумму на балансе."
                 if callback: return await callback.answer(text, show_alert=True)
                 else: return await message.answer(text)
        else:
            if not db.add_balance(user_id, -bet, is_bet=True):
                await state.update_data(processing_click=False)
                text = "❌ Ошибка при списании ставки. Недостаточно средств!"
                if callback: return await callback.answer(text, show_alert=True)
                else: return await message.answer(text)
        
        # Определяем количество кубиков и логику выигрыша
        dice_count = 1
        if bet_type.startswith("2_") or bet_type.startswith("sum_") or bet_type.startswith("mult_"):
            dice_count = 2
        elif bet_type.startswith("3_"):
            dice_count = 3
            
        targets_map = {
            "1_low": "1-3", "1_high": "4-6", "1_even": "Чет", "1_odd": "Нечет",
            "2_even": "Сумма чет", "2_odd": "Сумма нечет", 
            "2_left_more": "Левый > Правый", "2_right_more": "Левый < Правый",
            "2_both_even": "Оба чет", "2_both_odd": "Оба нечет",
            "2_double": "Дубль", "2_step": "Шаг",
            "3_triple": "Трипл", "3_67": "Сумма 6 или 7",
            "not_6": "Всё кроме 6",
            "sum_less_7": "Меньше 7", "sum_equal_7": "Точно 7", "sum_more_7": "Больше 7",
            "mult_1_18": "Умн. 1-18", "mult_19_36": "Умн. 19-36"
        }
        
        if custom_numbers:
            target = f"на числа {', '.join(map(str, sorted(custom_numbers)))}"
        elif bet_type.startswith("num_"):
            target = f"на число {bet_type.split('_')[1]}"
        else:
            target = targets_map.get(bet_type, bet_type)

        user_name = get_user_display_name(user_id, message.from_user.first_name)
        bet_msg_text = (
            f"<b>{user_name} ставит {bet:.2f} 💰</b>\n"
            f"<blockquote><b>🎲 {target}</b></blockquote>"
        )
        await message.answer(bet_msg_text, parse_mode=ParseMode.HTML)

        win_coef = 0
        dices = []
        for _ in range(dice_count):
            msg = await message.answer_dice(emoji="🎲")
            dices.append(msg.dice.value)
        
        await asyncio.sleep(4) 
        
        # Логика выигрыша
        if custom_numbers:
            if dices[0] in custom_numbers:
                # 1 - x6, 2 - x3, 3 - x2, 4 - x1.5, 5 - x1.2
                coefs = {1: 6, 2: 3, 3: 2, 4: 1.5, 5: 1.2}
                win_coef = coefs.get(len(custom_numbers), 0)
        elif bet_type == "1_low": # 1-3
            if dices[0] in [1, 2, 3]: win_coef = 2
        elif bet_type == "1_high": # 4-6
            if dices[0] in [4, 5, 6]: win_coef = 2
        elif bet_type == "1_even": # Чет
            if dices[0] % 2 == 0: win_coef = 2
        elif bet_type == "1_odd": # Нечет
            if dices[0] % 2 != 0: win_coef = 2
        elif bet_type.startswith("num_"):
            target_num = int(bet_type.split("_")[1])
            if dices[0] == target_num: win_coef = 6
        elif bet_type == "2_even": # Сумма чет
            if sum(dices) % 2 == 0: win_coef = 2
        elif bet_type == "2_odd": # Сумма нечет
            if sum(dices) % 2 != 0: win_coef = 2
        elif bet_type == "2_left_more": # Левый > Правый
            if dices[0] > dices[1]: win_coef = 2.4
        elif bet_type == "2_right_more": # Левый < Правый
            if dices[0] < dices[1]: win_coef = 2.4
        elif bet_type == "2_both_even": # Оба чет
            if dices[0] % 2 == 0 and dices[1] % 2 == 0: win_coef = 4
        elif bet_type == "2_both_odd": # Оба нечет
            if dices[0] % 2 != 0 and dices[1] % 2 != 0: win_coef = 4
        elif bet_type == "2_double": # Дубль
            if dices[0] == dices[1]: win_coef = 6
        elif bet_type == "2_step": # Шаг
            if abs(dices[0] - dices[1]) == 1: win_coef = 3.6
        elif bet_type == "3_triple": # Все равны
            if dices[0] == dices[1] == dices[2]: win_coef = 30
        elif bet_type == "3_67": # Сумма 6 или 7
            if sum(dices) in [6, 7]: win_coef = 5
        elif bet_type == "sum_less_7":
            if sum(dices) < 7: win_coef = 2.4
        elif bet_type == "sum_equal_7":
            if sum(dices) == 7: win_coef = 6
        elif bet_type == "sum_more_7":
            if sum(dices) > 7: win_coef = 2.4
        elif bet_type == "mult_1_18":
            if dices[0] * dices[1] <= 18: win_coef = 1.25
        elif bet_type == "mult_19_36":
            if dices[0] * dices[1] >= 19: win_coef = 4.4
        elif bet_type == "not_6":
            if dices[0] == 6:
                # ПРОИГРЫШ: Списываем убыток (bet * 19)
                if not db.add_balance(user_id, -(bet * 19), is_bet=True):
                     # Если вдруг баланса не хватило на убыток (хотя мы проверяли перед игрой), 
                     # списываем сколько есть
                     current_bal = db.get_user_data(user_id)[3]
                     db.add_balance(user_id, -current_bal)
                win_coef = 0
                # Реферальные 5% (от общей суммы потери)
                referrer_id = user_data[12]
                if referrer_id:
                    db.add_ref_balance(referrer_id, (bet * 19) * 0.05)
                
                user_name = get_user_display_name(user_id, message.from_user.first_name)
                new_balance = db.get_user_data(user_id)[3]
                text = (
                    f"<b>👤 {user_name}</b>\n"
                    f"<b>Проигрывает в игре 🎲 на {bet:.2f} 💰</b>\n"
                    f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                    f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
                )
                await state.update_data(processing_click=False)
                return await message.answer(text, parse_mode=ParseMode.HTML)
            else:
                if dices[0] == 1: win_coef = 3
                elif dices[0] == 2: win_coef = 4
                elif dices[0] == 3: win_coef = 5.2
                elif dices[0] == 4: win_coef = 6.4
                elif dices[0] == 5: win_coef = 7.6

        # Обработка выигрыша/проигрыша
        win_amount = 0
        if win_coef > 0:
            win_amount = bet * win_coef
            if bet_type == "not_6":
                db.add_balance(user_id, bet * (win_coef - 1))
            else:
                db.add_balance(user_id, win_amount)
                
            user_name = get_user_display_name(user_id, message.from_user.first_name)
            new_balance = db.get_user_data(user_id)[3]
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Побеждает в игре 🎲 на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× {win_coef} 🎄 Выигрыш {win_amount:.2f} 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            await state.update_data(processing_click=False)
            await message.answer(text, parse_mode=ParseMode.HTML)
            if win_amount >= 50:
                await send_alert(message.bot, user_id, win_amount, "win")
        else:
            # Начисляем рефские 5%
            referrer_id = user_data[12]
            if referrer_id:
                db.add_ref_balance(referrer_id, bet * 0.05)
            
            user_name = get_user_display_name(user_id, message.from_user.first_name)
            new_balance = db.get_user_data(user_id)[3]
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Проигрывает в игре 🎲 на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            await state.update_data(processing_click=False)
            await message.answer(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Error in process_dice_game: {e}")
        await message.answer("❌ Произошла ошибка во время игры. Пожалуйста, обратитесь в поддержку.")
    finally:
        # Снимаем флаг если игра не закончилась (state.clear() не был вызван)
        if await state.get_state() == PlayingState.dice:
            await state.update_data(processing_click=False)


@dp.callback_query(F.data.startswith("dice_bet:"))
async def dice_bet_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик ставок на кубики"""
    
    parts = callback.data.split(":")
    bet_type = parts[1]
    
    # Проверка владельца если есть :user_id
    if len(parts) > 2:
        owner_id = int(parts[-1])
        if not await check_owner(callback, owner_id):
            return
    
    await state.set_state(PlayingState.dice)
    await process_dice_game(callback.message, callback.from_user.id, bet_type, state, callback=callback)


async def old_game_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик игр (эмодзи) - старая логика"""
        
    # Защита от спама кликами
    game_data = await state.get_data()
    if game_data.get("processing_click"):
        return await callback.answer()
    await state.update_data(processing_click=True)
    
    try:
        await state.set_state(PlayingState.old)
        user_id = callback.from_user.id
        game_type = callback.data.split(":")[1]
        
        user_data = db.get_user_data(user_id)
        balance = user_data[3]
        bet = user_data[11]
        
        # Защита от багов ставки (отрицательная ставка и т.д.)
        if bet <= 0:
            db.set_bet(user_id, 0.2)
            bet = 0.2

        if balance < bet:
            await state.update_data(processing_click=False)
            return await callback.answer("❌ Недостаточно средств для ставки!", show_alert=True)
            
        # Списываем ставку
        if not db.add_balance(user_id, -bet, is_bet=True):
            await state.update_data(processing_click=False)
            return await callback.answer("❌ Ошибка при списании ставки. Недостаточно средств!", show_alert=True)
        
        # Инициализируем win_coef
        win_coef = 0
        
        # Отправляем кубик
        emoji = {
            "dice_emoji": "🎲",
            "dice": "🎲",
            "soccer": "⚽",
            "basket": "🏀",
            "darts": "🎯",
            "bowling": "🎳",
            "slots": "🎰"
        }.get(game_type, "🎲")

        # Отправляем сообщение о ставке
        user_name = get_user_display_name(user_id, callback.from_user.first_name)
        bet_msg_text = (
            f"<b>{user_name} ставит {bet:.2f} 💰</b>\n"
            f"<blockquote><b>🎮 Игра: {emoji}</b></blockquote>"
        )
        await callback.message.answer(bet_msg_text, parse_mode=ParseMode.HTML)
        
        msg = await callback.message.answer_dice(emoji=emoji)
        value = msg.dice.value
        
        # Логика выигрыша
        win_amount = 0
        is_win = False
        coef = 1.9
        target = ""
        
        if game_type == "dice":
            target = "4, 5, 6"
            coef = 1.9
            if value >= 4: # 4, 5, 6 - победа (x1.9)
                is_win = True
                win_amount = bet * coef
        elif game_type == "soccer":
            target = "Гол"
            coef = 1.9
            if value >= 3:
                is_win = True
                win_amount = bet * coef
        elif game_type == "basket":
            target = "Попадание"
            coef = 1.9
            if value >= 3:
                is_win = True
                win_amount = bet * coef
        elif game_type == "darts":
            target = "Центр"
            coef = 2.0
            if value >= 4:
                is_win = True
                win_amount = bet * coef
        elif game_type == "bowling":
            target = "5-6 кегль"
            coef = 2.0
            if value >= 5:
                is_win = True
                win_amount = bet * coef
        elif game_type == "slots":
            target = "777/Джекпот"
            coef = 10.0
            if value in [1, 22, 43, 64]:
                is_win = True
                win_amount = bet * coef
                
        await asyncio.sleep(4) # Ждем анимацию
        
        # Получаем актуальные данные пользователя
        user_data = db.get_user_data(user_id)
        user_name = get_user_display_name(user_id, callback.from_user.first_name)
        
        if is_win:
            db.add_balance(user_id, win_amount)
            new_balance = db.get_user_data(user_id)[3]
            
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Побеждает в игре {emoji} на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× {coef} 🎄 Выигрыш {win_amount:.2f} 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            await msg.reply(text, parse_mode=ParseMode.HTML)
            
            if win_amount >= 50:
                await send_alert(callback.bot, user_id, win_amount, "win")
            
            await state.update_data(processing_click=False)
        else:
            referrer_id = user_data[12]
            if referrer_id:
                ref_reward = bet * 0.05
                db.add_ref_balance(referrer_id, ref_reward)
                
            new_balance = db.get_user_data(user_id)[3]
            
            text = (
                f"<b>👤 {user_name}</b>\n"
                f"<b>Проигрывает в игре {emoji} на {bet:.2f} 💰</b>\n"
                f"<blockquote><b>× 0 🎄 Выигрыш 0.00 💰 ❞</b></blockquote>\n\n"
                f"<b>📋 Баланс {new_balance:.2f} 💰</b>"
            )
            await state.update_data(processing_click=False)
            await msg.reply(text, parse_mode=ParseMode.HTML)
    finally:
        # Если игра не закончилась (не был вызван state.clear()), снимаем флаг
        if await state.get_state() == PlayingState.old:
            await state.update_data(processing_click=False)

@dp.callback_query(F.data.startswith("coming_soon"))
async def coming_soon_callback(callback: CallbackQuery):
    # Проверка владельца если есть :user_id
    if ":" in callback.data:
        owner_id = int(callback.data.split(":")[-1])
        if not await check_owner(callback, owner_id):
            return
    await callback.answer("🚧 Этот раздел находится в разработке!", show_alert=True)

@dp.callback_query(F.data == "bonuses")
async def bonuses_callback(callback: CallbackQuery):
    await callback.answer("🍬 Бонусы будут доступны скоро!", show_alert=True)

@dp.callback_query(F.data == "transactions")
async def transactions_callback(callback: CallbackQuery):
    await callback.answer("📠 История транзакций пуста.", show_alert=True)

@dp.callback_query(F.data == "game_history")
async def game_history_callback(callback: CallbackQuery):
    await callback.answer("🔬 История игр пуста.", show_alert=True)


async def main() -> None:
    # Проверяем наличие токена
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_bot_token_here":
        print("ОШИБКА: Токен бота не найден. Укажите его в файле .env или config.py")
        return

    # Инициализируем бота
    bot = Bot(
        token=config.BOT_TOKEN, 
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML, 
            link_preview=LinkPreviewOptions(is_disabled=True)
        )
    )
    
    # Обновляем юзернейм бота для замены в текстах
    await update_bot_username(bot)
    
    # Запускаем поллинг
    print(f"Бот {BOT_USERNAME} запущен и готов к работе!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Критическая ошибка при работе бота: {e}")
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
