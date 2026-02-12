import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from decimal import Decimal, ROUND_HALF_UP

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = "8488987410:AAFQDM7jUEVOwcAtwYwjSWBEKm3CDOxrbHM"

ADMIN_IDS = [7313407194, 5877542500]

CRYPTOBOT_LINK = "http://t.me/send?start=IVjPbr6PN7s6"

USD_RUB_RATE = 74

# ==================== 5 РАБОЧИХ ПРЕМИУМ ЭМОДЗИ ====================
PREMIUM = {
    "rocket": '<tg-emoji emoji-id="5377336433692412420">🚀</tg-emoji>',
    "dice": '<tg-emoji emoji-id="5377346496800786271">🎯</tg-emoji>',
    "lightning": '<tg-emoji emoji-id="5375469677696815127">⚡</tg-emoji>',
    "win": '<tg-emoji emoji-id="5436386989857320953">🏆</tg-emoji>',
    "check": '<tg-emoji emoji-id="5377720025811555309">✅</tg-emoji>',
}

def emj(name):
    """Возвращает премиум эмодзи"""
    return PREMIUM.get(name, '•')

# ==================== УСЛУГИ ====================
SERVICES = {
    "15": {
        "name": "Премиум Буст канала 15 Д",
        "desc": (
            f"{emj('win')} Буст 15 дней\n"
            f"{emj('lightning')} Моментальные\n"
            f"{emj('dice')} Время: от 10 мин. до 5 ч.\n"
            f"{emj('win')} Качество: Премиум\n"
            f"{emj('rocket')} Гео: Весь мир\n"
            f"{emj('check')} С гарантией"
        ),
        "price": 20699.0,
        "min": 10,
        "max": 100000,
        "step": 10,
    },
    "1": {
        "name": "Буст канала 1 день",
        "desc": (
            f"{emj('lightning')} Быстро\n"
            f"{emj('dice')} Время: от 10 мин. до 5 ч.\n"
            f"{emj('win')} Качество: Премиум"
        ),
        "price": 3285.48,
        "min": 10,
        "max": 100000,
        "step": 10,
    },
    "30": {
        "name": "Буст канала 30 дней",
        "desc": (
            f"{emj('win')} Премиум Подписчики\n"
            f"{emj('lightning')} Моментальные\n"
            f"{emj('dice')} Время: от 10 мин. до 5 ч.\n"
            f"{emj('check')} Гарантия 30 дн."
        ),
        "price": 36896.0,
        "min": 10,
        "max": 100000,
        "step": 10,
    },
    "complaints": {
        "name": "Насилие жалобы",
        "desc": (
            f"{emj('rocket')} Жалобы на канал/группу\n"
            f"{emj('dice')} Причина: Насилие\n"
            f"{emj('lightning')} Быстрый старт\n"
            f"{emj('dice')} Время: от 10 мин. до 5 ч.\n"
            f"{emj('win')} Скорость до 10к/сутки"
        ),
        "price": 11361.6,
        "min": 200,
        "max": 40000,
        "step": 10,
    }
}

# ==================== ХРАНИЛИЩЕ ====================
user_service = {}
orders = {}
order_counter = 0

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==================== КНОПКИ - БЕЗ ЭМОДЗИ! ====================
def menu_kb():
    kb = [
        [KeyboardButton(text="Буст 15 дней")],
        [KeyboardButton(text="Буст 1 день"), KeyboardButton(text="Буст 30 дней")],
        [KeyboardButton(text="Жалобы")],
        [KeyboardButton(text="Поддержка")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀ Назад")]], resize_keyboard=True)

# ==================== ФУНКЦИИ ====================
def rub_to_usd(rub):
    return (Decimal(str(rub)) / Decimal(str(USD_RUB_RATE))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def fmt_price(p):
    return f"{int(p)}" if p == int(p) else f"{p:.2f}".rstrip('0').rstrip('.')

def calc_price(service, qty):
    total = (service["price"] / 1000) * qty
    return fmt_price(total), f"{rub_to_usd(total)}"

# ==================== ОБРАБОТЧИКИ ====================
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    """СТАРТ - ПРЕМИУМ ЭМОДЗИ ТОЛЬКО В ТЕКСТЕ!"""
    text = (
        f"{emj('win')} <b>Premium Boost Bot</b> {emj('win')}\n\n"
        f"{emj('rocket')} Бусты и жалобы\n"
        f"{emj('lightning')} Моментально • {emj('check')} С гарантией\n\n"
        f"{emj('dice')} Выбери услугу:"
    )
    await msg.answer(text, reply_markup=menu_kb())

@dp.message(lambda m: m.text == "Поддержка")
async def support(msg: Message):
    text = (
        f"{emj('rocket')} <b>Поддержка</b>\n\n"
        f"@TsideEnjoyer\n"
        f"{emj('dice')} 5-30 мин"
    )
    await msg.answer(text, reply_markup=menu_kb())

@dp.message(lambda m: m.text == "◀ Назад")
async def back(msg: Message):
    if msg.from_user.id in user_service:
        del user_service[msg.from_user.id]
    await cmd_start(msg)

@dp.message(lambda m: m.text in ["Буст 15 дней", "Буст 1 день", "Буст 30 дней", "Жалобы"])
async def service_select(msg: Message):
    key = {
        "Буст 15 дней": "15",
        "Буст 1 день": "1",
        "Буст 30 дней": "30", 
        "Жалобы": "complaints"
    }[msg.text]
    
    service = SERVICES[key]
    user_service[msg.from_user.id] = key
    
    min_rub, min_usd = calc_price(service, service["min"])
    
    text = (
        f"<b>{emj('rocket')} {service['name']}</b>\n"
        f"{service['desc']}\n\n"
        f"{emj('dice')} <i>Данные могут быть неточны</i>\n\n"
        f"{emj('win')} <b>1000:</b> {fmt_price(service['price'])} ₽\n"
        f"{emj('dice')} <b>Мин:</b> {service['min']} | <b>Макс:</b> {service['max']}\n"
        f"{emj('rocket')} <b>{service['min']}:</b> {min_rub} ₽ | {min_usd} $\n\n"
        f"{emj('lightning')} <b>Введите количество (кратно {service['step']}):</b>"
    )
    await msg.answer(text, reply_markup=back_kb())

@dp.message()
async def process_qty(msg: Message):
    global order_counter
    
    if msg.text in ["Буст 15 дней", "Буст 1 день", "Буст 30 дней", "Жалобы", "Поддержка", "◀ Назад"]:
        return
    
    if msg.from_user.id not in user_service:
        await msg.answer(
            f"{emj('dice')} Сначала выбери услугу!",
            reply_markup=menu_kb()
        )
        return
    
    try:
        qty = int(''.join(filter(str.isdigit, msg.text)))
        key = user_service[msg.from_user.id]
        service = SERVICES[key]
        
        if qty < service["min"]:
            await msg.answer(f"{emj('dice')} Минимум: {service['min']}!")
            return
        if qty > service["max"]:
            await msg.answer(f"{emj('dice')} Максимум: {service['max']}!")
            return
        if qty % service["step"] != 0:
            await msg.answer(f"{emj('dice')} Кратно {service['step']}!")
            return
        
        rub, usd = calc_price(service, qty)
        order_counter += 1
        oid = f"#{order_counter}"
        
        orders[oid] = {
            "user_id": msg.from_user.id,
            "username": msg.from_user.username or msg.from_user.full_name,
            "service": service['name'],
            "qty": qty,
            "rub": rub,
            "usd": usd
        }
        
        order_text = (
            f"{emj('win')} <b>ЗАКАЗ {oid}</b> {emj('win')}\n"
            f"{'─' * 30}\n\n"
            f"<b>{emj('rocket')} {service['name']}</b>\n"
            f"{emj('lightning')} Моментальные\n"
            f"{emj('dice')} Время: от 10 мин. до 5 ч.\n"
            f"{emj('rocket')} <b>Кол-во:</b> {qty}\n"
            f"{emj('win')} <b>Сумма:</b> {rub} ₽ | {usd} $\n\n"
            f"{emj('lightning')} <b>Ссылка:</b>\n"
            f"<code>вставь ссылку на канал</code>\n\n"
            f"{emj('rocket')} <b>Оплата:</b>"
        )
        
        # Inline кнопки - БЕЗ ПРЕМИУМ ЭМОДЗИ В ТЕКСТЕ КНОПОК!
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {usd}$ CryptoBot", url=CRYPTOBOT_LINK)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"pay_{oid}")]
        ])
        
        await msg.answer(order_text, reply_markup=keyboard)
        
        for admin in ADMIN_IDS:
            try:
                admin_text = (
                    f"{emj('dice')} <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
                    f"{emj('rocket')} <b>{oid}</b>\n"
                    f"{emj('win')} {service['name']}\n"
                    f"{emj('dice')} {qty} шт.\n"
                    f"{emj('win')} {rub} ₽ | {usd} $\n"
                    f"{emj('rocket')} @{msg.from_user.username if msg.from_user.username else 'no_username'}\n"
                    f"ID: <code>{msg.from_user.id}</code>"
                )
                await bot.send_message(admin, admin_text)
            except:
                pass
        
    except ValueError:
        await msg.answer(f"{emj('dice')} Введи число!")

@dp.callback_query(lambda c: c.data and c.data.startswith('pay_'))
async def payment(c: CallbackQuery):
    oid = c.data.replace('pay_', '')
    if oid not in orders:
        await c.answer("❌ Заказ не найден!", show_alert=True)
        return
    
    confirm_text = (
        f"{emj('check')} <b>Заказ {oid} отправлен!</b>\n\n"
        f"{emj('dice')} Проверка: 5-10 мин\n"
        f"{emj('rocket')} @TsideEnjoyer\n\n"
        f"{emj('win')} Спасибо за заказ!"
    )
    
    await c.message.edit_text(confirm_text)
    await c.answer("✅ Отправлено!")

async def main():
    print("=" * 50)
    print("🚀 БОТ ЗАПУЩЕН!")
    print("=" * 50)
    print("✅ КНОПКИ - БЕЗ ЭМОДЗИ!")
    print("✅ ПРЕМИУМ ЭМОДЗИ - ТОЛЬКО В ТЕКСТЕ!")
    print("✅ 5 РАБОЧИХ ПРЕМИУМ ЭМОДЗИ:")
    print("   🚀 rocket - Бусты, ссылки, оплата")
    print("   🎯 dice - Жалобы, числа, предупреждения") 
    print("   ⚡ lightning - Скорость, время")
    print("   🏆 win - Услуги, цены, успех")
    print("   ✅ check - Гарантия, подтверждение")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
