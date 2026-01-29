from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu():
                      
    keyboard = [
        [KeyboardButton(text="📝 Начать анкету")],
        [KeyboardButton(text="ℹ️ О боте"), KeyboardButton(text="📊 Моя анкета")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirmation_keyboard():
                                                    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Понятно, продолжаем", callback_data="confirm_understand")
    keyboard.button(text="❌ Не понятно", callback_data="not_understand")
    return keyboard.as_markup()

def get_admin_menu():
                      
    keyboard = [
        [KeyboardButton(text="📊 Посмотреть все анкеты")],
        [KeyboardButton(text="❓ Управление вопросами")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="⬅️ Назад в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_questions_management_keyboard():
                                             
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📝 Редактировать вопрос", callback_data="edit_question")
    keyboard.button(text="➕ Добавить вопрос", callback_data="add_question")
    keyboard.button(text="👁️ Показать все вопросы", callback_data="show_questions")
    keyboard.button(text="❌ Деактивировать вопрос", callback_data="deactivate_question")
    keyboard.button(text="⬅️ Назад", callback_data="admin_back")
    keyboard.adjust(1)
    return keyboard.as_markup()