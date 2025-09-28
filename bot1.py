import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler, # Импорт ConversationHandler
)
import random
import datetime
import os # Для переменных окружения

# ... (ваш токен, ID админа, ID чата, promo_codes) ...
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "8301185082:AAGUKofUSYK6tA4fJfjOlxdLJH3OApGYAxU") # Получаем токен из переменных окружения
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', 7313407194))
CHAT_ID = -1002920370736 # Пример ID чата

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

promo_codes = {}

# --- Состояния для ConversationHandler ---
GET_PROMO_NAME, GET_PROMO_ACTIVATIONS, GET_PROMO_COST, GET_PROMO_CONDITION = range(4)

# --- Функции для админ-панели (оставляем как есть) ---
def build_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton("Управлять промокодами", callback_data="manage_promos")],
        [InlineKeyboardButton("Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_manage_promos_keyboard():
    keyboard = []
    if promo_codes:
        for code, data in promo_codes.items():
            keyboard.append([
                InlineKeyboardButton(f"Промо: {code} ({data['activations_left']} осталось)", callback_data=f"promo_details_{code}")
            ])
    else:
        keyboard.append([InlineKeyboardButton("Нет созданных промокодов", callback_data="no_promos")])
    keyboard.append([InlineKeyboardButton("Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def build_promo_details_keyboard(code):
    keyboard = [
        [InlineKeyboardButton("➕ Прибавить активацию", callback_data=f"add_activation_{code}"),
         InlineKeyboardButton("➖ Убавить активацию", callback_data=f"remove_activation_{code}")],
        [InlineKeyboardButton("❌ Удалить промокод", callback_data=f"delete_promo_{code}")],
        [InlineKeyboardButton("Назад", callback_data="manage_promos")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Обработчики команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id == ADMIN_USER_ID:
        await update.message.reply_text(
            "👋 Добро пожаловать в админ-панель казино AngelWin!",
            reply_markup=build_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Доступ к боту имеют только администраторы. Попробуйте удачу в казино AngelWin!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Играть в казино", url="https://t.me/your_casino_bot_or_link")]]) # Замените на ссылку на ваше казино
        )

async def handle_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    message_text = update.message.text.upper()
    if message_text.startswith("/PROMO "):
        promo_code = message_text.split("/PROMO ")[1].strip()
        if promo_code in promo_codes:
            promo_data = promo_codes[promo_code]
            if promo_data["activations_left"] > 0:
                await update.message.reply_text(
                    f"🌟 **Промокод \"{promo_code}\"** 🌟\n\n"
                    f"✨ Условие активации: {promo_data['condition']} ✨\n\n"
                    f"💰 Стоимость: {promo_data['cost']}$ 💰\n"
                    f"⏳ Осталось активаций: {promo_data['activations_left']} ⏳\n\n"
                    f"🚀 После выполнения условия, обратитесь к [@pensiya_get](tg://user?id=7313407194) для активации.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ К сожалению, промокод \"{promo_code}\" уже был полностью активирован.",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                "❌ Неверный промокод. Попробуйте еще раз.",
                parse_mode='Markdown'
            )

# --- Функции для ConversationHandler ---

async def create_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает создание промокода."""
    await update.message.reply_text("Введите название промокода (например, New):")
    return GET_PROMO_NAME

async def get_promo_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает название промокода."""
    promo_name = update.message.text.strip().upper()
    if not promo_name:
        await update.message.reply_text("Название промокода не может быть пустым. Попробуйте снова.")
        return GET_PROMO_NAME # Остаемся в том же состоянии

    context.user_data['new_promo_name'] = promo_name
    await update.message.reply_text("Введите количество активаций (число):")
    return GET_PROMO_ACTIVATIONS

async def get_promo_activations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает количество активаций."""
    try:
        activations = int(update.message.text.strip())
        if activations <= 0:
            await update.message.reply_text("Количество активаций должно быть положительным числом. Попробуйте снова.")
            return GET_PROMO_ACTIVATIONS
        context.user_data['new_promo_activations'] = activations
        await update.message.reply_text("Введите стоимость активации в $ (например, 0.1):")
        return GET_PROMO_COST
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для количества активаций.")
        return GET_PROMO_ACTIVATIONS

async def get_promo_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает стоимость активации."""
    try:
        cost = float(update.message.text.strip())
        if cost < 0:
            await update.message.reply_text("Стоимость не может быть отрицательной. Попробуйте снова.")
            return GET_PROMO_COST
        context.user_data['new_promo_cost'] = cost
        await update.message.reply_text("Введите условие активации (например, Набрать 0.2$ выигрыша в казино!):")
        return GET_PROMO_CONDITION
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для стоимости.")
        return GET_PROMO_COST

async def get_promo_condition(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает условие активации и завершает создание промокода."""
    promo_name = context.user_data.get('new_promo_name')
    activations = context.user_data.get('new_promo_activations')
    cost = context.user_data.get('new_promo_cost')
    condition = update.message.text.strip()

    if not all([promo_name, activations is not None, cost is not None, condition]):
        await update.message.reply_text("Произошла ошибка при создании промокода. Пожалуйста, попробуйте снова.")
        # Очищаем временные данные
        context.user_data.pop('new_promo_name', None)
        context.user_data.pop('new_promo_activations', None)
        context.user_data.pop('new_promo_cost', None)
        return ConversationHandler.END # Выходим из разговора

    promo_codes[promo_name] = {
        "activations_left": activations,
        "cost": cost,
        "condition": condition,
        "created_by": ADMIN_USER_ID,
        "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    await update.message.reply_text(
        f"✅ **Промокод \"{promo_name}\" создан!** ✅\n\n"
        f"🌟 Условие: {condition}\n"
        f"💰 Стоимость: {cost}$\n"
        f"⏳ Доступно активаций: {activations}\n\n"
        f"🎉 Пользователи могут активировать его командой `/promo {promo_name}`.",
        reply_markup=build_admin_keyboard(), # Возвращаемся в главное меню админки
        parse_mode='Markdown'
    )

    # Очистка временных данных
    context.user_data.pop('new_promo_name', None)
    context.user_data.pop('new_promo_activations', None)
    context.user_data.pop('new_promo_cost', None)

    return ConversationHandler.END # Завершаем диалог

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    await update.message.reply_text("Создание промокода отменено.", reply_markup=build_admin_keyboard())
    # Очищаем временные данные, если они есть
    context.user_data.pop('new_promo_name', None)
    context.user_data.pop('new_promo_activations', None)
    context.user_data.pop('new_promo_cost', None)
    return ConversationHandler.END

# --- Обработчики Inline кнопок ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        await query.edit_message_text(text="❌ Доступ запрещен. Это только для администраторов.")
        return

    if data == "admin_panel":
        await query.edit_message_text(
            text="👋 Добро пожаловать в админ-панель казино AngelWin!",
            reply_markup=build_admin_keyboard()
        )
    elif data == "create_promo":
        # Начинаем ConversationHandler
        return await create_promo_start(update, context) # Возвращаем результат, чтобы ConversationHandler начал работу
    elif data == "manage_promos":
        await query.edit_message_text(
            text="Список ваших промокодов:",
            reply_markup=build_manage_promos_keyboard()
        )
    elif data == "back_to_menu":
        await query.edit_message_text(text="👋 Добро пожаловать в админ-панель казино AngelWin!", reply_markup=build_admin_keyboard())
    elif data == "no_promos": # Если нет промокодов
        await query.answer("Пока нет созданных промокодов.")

    elif data.startswith("promo_details_"):
        code = data.split("_")[2]
        if code in promo_codes:
            promo_data = promo_codes[code]
            await query.edit_message_text(
                text=f"⚙️ **Детали промокода: {code}** ⚙️\n\n"
                     f"🌟 Условие: {promo_data['condition']}\n"
                     f"💰 Стоимость: {promo_data['cost']}$\n"
                     f"⏳ Осталось активаций: {promo_data['activations_left']}\n"
                     f"📅 Создан: {promo_data.get('creation_date', 'Неизвестно')}",
                reply_markup=build_promo_details_keyboard(code),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(text="❌ Промокод не найден.")

    elif data.startswith("add_activation_"):
        code = data.split("_")[2]
        if code in promo_codes:
            promo_codes[code]["activations_left"] += 1
            await query.edit_message_text(
                text=f"👍 Активация для промокода \"{code}\" добавлена. Теперь доступно: {promo_codes[code]['activations_left']}",
                reply_markup=build_promo_details_keyboard(code)
            )
        else:
            await query.edit_message_text(text="❌ Промокод не найден.")

    elif data.startswith("remove_activation_"):
        code = data.split("_")[2]
        if code in promo_codes:
            if promo_codes[code]["activations_left"] > 0:
                promo_codes[code]["activations_left"] -= 1
                await query.edit_message_text(
                    text=f"👎 Активация для промокода \"{code}\" убавлена. Осталось: {promo_codes[code]['activations_left']}",
                    reply_markup=build_promo_details_keyboard(code)
                )
            else:
                await query.edit_message_text(text="❌ Активаций уже 0, нельзя убавить.")
        else:
            await query.edit_message_text(text="❌ Промокод не найден.")

    elif data.startswith("delete_promo_"):
        code = data.split("_")[2]
        if code in promo_codes:
            del promo_codes[code]
            await query.edit_message_text(text=f"✅ Промокод \"{code}\" удален.", reply_markup=build_manage_promos_keyboard())
        else:
            await query.edit_message_text(text="❌ Промокод не найден.")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # --- ConversationHandler для создания промокода ---
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^create_promo$")], # Вход через нажатие кнопки
        states={
            GET_PROMO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_name)],
            GET_PROMO_ACTIVATIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_activations)],
            GET_PROMO_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_cost)],
            GET_PROMO_CONDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_condition)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation), # Команда /cancel для выхода
            CallbackQueryHandler(cancel_conversation, pattern="^cancel_promo$"), # Кнопка отмены
            MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: c.bot.send_message(chat_id=u.effective_chat.id, text="Неверный ввод. Попробуйте еще раз или введите /cancel.")), # Обработка некорректного ввода
        ],
        per_user=True, # Отдельный разговор для каждого пользователя
        per_message=False # Диалог продолжается, пока не завершится или не отменится
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promo)) # Обработка промокодов (должна быть перед ConversationHandler, если /promo не будет прерывать диалог)

    application.add_handler(conv_handler) # Добавляем ConversationHandler
    application.add_handler(CallbackQueryHandler(button_callback)) # Добавляем обработчик callback'ов для других кнопок

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()