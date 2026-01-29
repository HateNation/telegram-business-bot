from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_admin_main_menu():
    """Главное меню админки"""
    builder = ReplyKeyboardBuilder()
    
    # Основные разделы
    builder.button(text="📋 Управление вопросами")
    builder.button(text="👥 Управление пользователями")
    builder.button(text="📊 Просмотр анкет")
    builder.button(text="📈 Статистика")
    
    # Дополнительные функции
    builder.button(text="⚙️ Настройки")
    builder.button(text="📤 Экспорт данных")
    
    # Выход
    builder.button(text="⬅️ Выйти из админки")
    
    # Располагаем кнопки
    builder.adjust(2, 2, 2, 1)
    
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите раздел...")

def get_questions_management_menu():
    """Меню управления вопросами"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Список всех вопросов", callback_data="admin_questions_list")
    builder.button(text="➕ Добавить вопрос", callback_data="admin_add_question")
    builder.button(text="✏️ Редактировать вопрос", callback_data="admin_edit_question")
    builder.button(text="✅ Активировать/❌ Деактивировать", callback_data="admin_toggle_question")
    builder.button(text="📋 Изменить порядок", callback_data="admin_reorder_questions")
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    
    builder.adjust(1)
    return builder.as_markup()

def get_users_management_menu():
    """Меню управления пользователями"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👥 Список пользователей", callback_data="admin_users_list")
    builder.button(text="📱 Пользователи с телефонами", callback_data="admin_users_with_phones")
    builder.button(text="📊 Пользователи по активности", callback_data="admin_users_activity")
    builder.button(text="🔍 Поиск пользователя", callback_data="admin_search_user")
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    
    builder.adjust(1)
    return builder.as_markup()

def get_questionnaires_management_menu():
    """Меню просмотра анкет"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 Все анкеты", callback_data="admin_all_questionnaires")
    builder.button(text="📅 Анкеты за период", callback_data="admin_questionnaires_period")
    builder.button(text="🔍 Поиск анкеты по ID", callback_data="admin_search_questionnaire")
    builder.button(text="👤 Анкеты пользователя", callback_data="admin_user_questionnaires")
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    
    builder.adjust(1)
    return builder.as_markup()

def get_question_actions_keyboard(question_id):
    """Действия с конкретным вопросом"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏️ Редактировать", callback_data=f"admin_question_edit_{question_id}")
    builder.button(text="✅/❌ Активация", callback_data=f"admin_question_toggle_{question_id}")
    builder.button(text="⬆️ Вверх", callback_data=f"admin_question_up_{question_id}")
    builder.button(text="⬇️ Вниз", callback_data=f"admin_question_down_{question_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"admin_question_delete_{question_id}")
    builder.button(text="⬅️ Назад к списку", callback_data="admin_questions_list")
    
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_pagination_keyboard(current_page, total_pages, prefix):
    """Клавиатура пагинации"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    if current_page > 1:
        builder.button(text="◀️ Назад", callback_data=f"{prefix}_page_{current_page-1}")
    
    builder.button(text=f"📄 {current_page}/{total_pages}", callback_data="current_page")
    
    if current_page < total_pages:
        builder.button(text="Вперед ▶️", callback_data=f"{prefix}_page_{current_page+1}")
    
    # Дополнительные кнопки
    builder.button(text="⬅️ На главную", callback_data="admin_back")
    
    builder.adjust(3, 1)
    return builder.as_markup()

def get_confirmation_keyboard(action, item_id):
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_{action}_{item_id}")
    builder.button(text="❌ Отменить", callback_data="cancel_action")
    
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_admin_keyboard():
    """Кнопка возврата в админку"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в админку", callback_data="admin_back")
    return builder.as_markup()

def get_simple_back_keyboard():
    """Простая кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    return builder.as_markup()