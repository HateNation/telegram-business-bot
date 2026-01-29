from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu():
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📝 Начать анкету")
    builder.button(text="📊 Моя анкета")
    builder.button(text="📱 Оновити номер")
    builder.button(text="ℹ️ О боте")
    builder.button(text="🛠️ Админка")  # Кнопка админки
    
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Оберіть дію...")

def get_phone_request_keyboard():
    """Клавиатура для запроса номера телефона"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📱 Відправити номер", request_contact=True)
    builder.button(text="✏️ Ввести вручну")
    builder.button(text="🚫 Пропустити")
    
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_admin_menu():
    """Меню админки (старое)"""
    keyboard = [
        [KeyboardButton(text="📊 Посмотреть все анкеты")],
        [KeyboardButton(text="❓ Управление вопросами")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📱 Пользователи с телефонами")],
        [KeyboardButton(text="⬅️ Назад в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_questions_management_keyboard():
    """Клавиатура для управления вопросами"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Редактировать вопрос", callback_data="edit_question")
    builder.button(text="➕ Добавить вопрос", callback_data="add_question")
    builder.button(text="👁️ Показать все вопросы", callback_data="show_questions")
    builder.button(text="❌ Деактивировать вопрос", callback_data="deactivate_question")
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    
    builder.adjust(1)
    return builder.as_markup()