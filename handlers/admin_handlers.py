from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import sys
import os
from datetime import datetime

# Добавляем корневую папку в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from database import db
from models.models import User, Question, Questionnaire
from keybords.main_menu import get_main_menu

router = Router()
logger = logging.getLogger(__name__)

admin_sessions = {}

def user_in_admin(user_id):
    """Проверяет, находится ли пользователь в админке"""
    return admin_sessions.get(user_id, False)

def set_admin_session(user_id, status=True):
    """Устанавливает статус админ-сессии"""
    admin_sessions[user_id] = status
    
# Состояния для админки
class AdminStates(StatesGroup):
    waiting_for_new_question = State()
    waiting_for_edit_question_id = State()
    waiting_for_edit_question_text = State()

    

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return str(user_id) in config.ADMIN_ID

def get_admin_menu():
    """Меню админки"""
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    keyboard = [
        [KeyboardButton(text="📋 Список вопросов")],
        [KeyboardButton(text="➕ Добавить вопрос")],
        [KeyboardButton(text="✏️ Редактировать вопрос")],
        [KeyboardButton(text="📊 Просмотр анкет")],
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="⬅️ Выйти из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ========== КОМАНДА /admin ==========

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Вход в админ-панель через команду /admin"""
    logger.info(f"🛠️ Команда /admin от пользователя {message.from_user.id}")
    
    # Очищаем состояние
    await state.clear()
    
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    
    welcome_text = (
        "🛠️ Панель администратора\n\n"
        "Доступные функции:\n"
        "• 📋 Управление вопросами анкеты\n"
        "• 📊 Просмотр всех анкет\n"
        "• 👥 Управление пользователями\n"
        "• 📈 Просмотр статистики\n\n"
        "Используйте кнопки меню ниже:"
    )
    
    await message.answer(welcome_text, reply_markup=get_admin_menu())
    logger.info(f"✅ Админка открыта для пользователя {message.from_user.id}")

# ========== ВЫХОД ИЗ АДМИНКИ ==========

@router.message(F.text == "⬅️ Выйти из админки")
async def exit_admin(message: Message, state: FSMContext):
    """Выход из админки через ReplyKeyboard"""
    await state.clear()
    
    # Снимаем флаг админки
    set_admin_session(message.from_user.id, False)
    
    await message.answer(
        "✅ Вы вышли из панели администратора.",
        reply_markup=get_main_menu()
    )
    logger.info(f"👤 Пользователь {message.from_user.id} вышел из админки")


@router.callback_query(F.data == "admin_exit")
async def handle_admin_exit(callback: CallbackQuery, state: FSMContext):
    """Выход из админки через InlineKeyboard"""
    await state.clear()
    
    # Снимаем флаг админки
    set_admin_session(callback.from_user.id, False)
    
    # Удаляем клавиатуру из сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Отправляем сообщение с главным меню
    await callback.message.answer(
        "✅ Вы вышли из панели администратора.",
        reply_markup=get_main_menu()
    )
    
    # Подтверждаем callback
    await callback.answer()
    logger.info(f"👤 Пользователь {callback.from_user.id} вышел из админки (inline)")

# ========== УПРАВЛЕНИЕ ВОПРОСАМИ ==========

@router.message(F.text == "📋 Список вопросов")
async def show_questions_list(message: Message):
    """Показать список всех вопросов"""
    if not is_admin(message.from_user.id):
        return
    
    questions = db.get_all_questions()
    
    if not questions:
        await message.answer("📭 Вопросов пока нет.")
        return
    
    result_text = "📋 Список всех вопросов:\n\n"
    
    for i, question in enumerate(questions, 1):
        status = "✅ Активен" if question.is_active else "❌ Неактивен"
        result_text += f"{i}. ID: {question.id} ({status})\n"
        result_text += f"   Порядок: {question.question_order}\n"
        result_text += f"   Вопрос: {question.question_text}\n\n"
    
    await message.answer(result_text)

@router.message(F.text == "➕ Добавить вопрос")
async def add_question_start(message: Message, state: FSMContext):
    """Начало добавления нового вопроса"""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "➕ Добавление нового вопроса\n\n"
        "Введите текст нового вопроса:",
        reply_markup=get_admin_menu()
    )
    await state.set_state(AdminStates.waiting_for_new_question)

@router.message(AdminStates.waiting_for_new_question)
async def add_question_process(message: Message, state: FSMContext):
    """Обработка нового вопроса"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    if not message.text:
        await message.answer("⚠️ Введите текст вопроса.")
        return

    question_text = message.text.strip()
    
    if not question_text:
        await message.answer("❌ Текст вопроса не может быть пустым. Попробуйте снова:")
        return
    
    # Определяем порядок (последний порядок + 1)
    questions = db.get_all_questions()
    next_order = max([q.question_order for q in questions], default=0) + 1 if questions else 1
    
    question = db.add_question(question_text, next_order)
    
    if question:
        await message.answer(
            f"✅ Вопрос успешно добавлен!\n\n"
            f"📝 ID: {question.id}\n"
            f"🔢 Порядок: {question.question_order}\n"
            f"📋 Текст: {question_text}",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            "❌ Ошибка при добавлении вопроса.",
            reply_markup=get_admin_menu()
        )
    
    await state.clear()

@router.message(F.text == "✏️ Редактировать вопрос")
async def edit_question_start(message: Message, state: FSMContext):
    """Начало редактирования вопроса"""
    if not is_admin(message.from_user.id):
        return
    
    questions = db.get_all_questions()
    
    if not questions:
        await message.answer("📭 Нет вопросов для редактирования.")
        return
    
    questions_text = "✏️ Редактирование вопроса\n\n"
    questions_text += "Введите ID вопроса для редактирования:\n\n"
    
    for q in questions[:10]:  # Показываем первые 10
        status = "✅" if q.is_active else "❌"
        questions_text += f"ID: {q.id} {status} - {q.question_text[:50]}...\n"
    
    if len(questions) > 10:
        questions_text += f"\n... и еще {len(questions) - 10} вопросов"
    
    await message.answer(questions_text)
    await state.set_state(AdminStates.waiting_for_edit_question_id)

@router.message(AdminStates.waiting_for_edit_question_id)
async def edit_question_id_process(message: Message, state: FSMContext):
    """Обработка ID вопроса для редактирования"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    if not message.text:
        await message.answer("⚠️ Введите числовой ID вопроса:")
        return

    try:
        question_id = int(message.text)
        question = db.get_question_by_id(question_id)
        
        if not question:
            await message.answer("❌ Вопрос с таким ID не найден. Попробуйте снова:")
            return
        
        await state.update_data(edit_question_id=question_id)
        await message.answer(
            f"✏️ Редактирование вопроса ID: {question_id}\n\n"
            f"Текущий текст:\n{question.question_text}\n\n"
            "Введите новый текст вопроса:",
            reply_markup=get_admin_menu()
        )
        await state.set_state(AdminStates.waiting_for_edit_question_text)
        
    except (ValueError, TypeError):
        await message.answer("❌ Пожалуйста, введите числовой ID вопроса:")

@router.message(AdminStates.waiting_for_edit_question_text)
async def edit_question_text_process(message: Message, state: FSMContext):
    """Обработка нового текста вопроса"""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    data = await state.get_data()
    question_id = data.get('edit_question_id')
    if not message.text:
        await message.answer("⚠️ Введите новый текст вопроса.")
        return
    new_text = message.text.strip()
    
    if db.update_question(question_id, new_text):
        await message.answer(
            f"✅ Вопрос ID: {question_id} успешно обновлен!\n\n"
            f"Новый текст: {new_text}",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении вопроса.",
            reply_markup=get_admin_menu()
        )
    
    await state.clear()

# ========== ПРОСМОТР АНКЕТ ==========

@router.message(F.text == "📊 Просмотр анкет")
async def view_questionnaires(message: Message):
    """Просмотр всех анкет"""
    if not is_admin(message.from_user.id):
        return
    
    questionnaires = db.get_all_questionnaires()
    
    if not questionnaires:
        await message.answer("📭 Анкет пока нет.")
        return
    
    # Показываем последние 3 анкеты
    for i, questionnaire in enumerate(questionnaires[:3], 1):
        user = db.get_user_by_id(questionnaire.user_id)
        answers = questionnaire.get_answers()
        
        result_text = f"📋 Анкета #{i}\n"
        result_text += f"🆔 ID анкеты: {questionnaire.id}\n"
        result_text += f"👤 Пользователь: {user.full_name if user else 'Неизвестно'}\n"
        result_text += f"📱 Телефон: {user.phone_number if user and user.phone_number else 'Не указан'}\n"
        result_text += f"📊 Ответов: {len(answers)}\n"
        result_text += f"📅 Дата: {questionnaire.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Показываем первые 3 ответа
        if answers:
            result_text += "📝 Ответы:\n"
            for j, (q_id, answer_data) in enumerate(list(answers.items())[:3], 1):
                result_text += f"{j}. {answer_data.get('question_text', 'Вопрос')}\n"
                result_text += f"   ➡️ {answer_data.get('answer', 'Нет ответа')}\n"
        
        await message.answer(result_text)
    
    if len(questionnaires) > 3:
        await message.answer(f"📄 Показано 3 из {len(questionnaires)} анкет. Всего анкет: {len(questionnaires)}")

# ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========

@router.message(F.text == "👥 Пользователи")
async def view_users(message: Message):
    """Просмотр пользователей"""
    if not is_admin(message.from_user.id):
        return
    
    session = db.get_session()
    try:
        users = session.query(User).order_by(User.created_at.desc()).limit(10).all()
        
        if not users:
            await message.answer("📭 Пользователей пока нет.")
            return
        
        result_text = "👥 Последние 10 пользователей:\n\n"
        
        for i, user in enumerate(users, 1):
            phone_status = "✅" if user.phone_number and user.phone_number != "Не вказано" else "❌"
            result_text += f"{i}. 👤 {user.full_name or 'Без имени'}\n"
            result_text += f"   📱 {phone_status} Телефон: {user.formatted_phone or user.phone_number or 'Нет'}\n"
            result_text += f"   🆔 @{user.username or user.user_id}\n"
            result_text += f"   📅 Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Статистика по телефонам
        total_users = session.query(User).count()
        users_with_phones = session.query(User).filter(
            User.phone_number != None,
            User.phone_number != "Не вказано"
        ).count()
        
        result_text += f"📊 Статистика:\n"
        result_text += f"• Всего пользователей: {total_users}\n"
        result_text += f"• С телефонами: {users_with_phones}\n"
        result_text += f"• Без телефонов: {total_users - users_with_phones}"
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {e}")
        await message.answer("❌ Ошибка при получении данных.")
    finally:
        session.close()

# ========== СТАТИСТИКА ==========

@router.message(F.text == "📈 Статистика")
async def show_statistics(message: Message):
    """Показать статистику"""
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_statistics()
    
    # Дополнительная статистика
    session = db.get_session()
    try:
        # Статистика по пользователям с телефонами
        users_with_phones = session.query(User).filter(
            User.phone_number != None,
            User.phone_number != "Не вказано"
        ).count()
        
        # Статистика по анкетам за сегодня
        today = datetime.utcnow().date()
        today_questionnaires = session.query(Questionnaire).filter(
            Questionnaire.created_at >= datetime(today.year, today.month, today.day)
        ).count()
        
        stats_text = (
            "📊 Статистика бота\n\n"
            "👥 Пользователи:\n"
            f"• Всего: {stats['total_users']}\n"
            f"• С телефонами: {users_with_phones}\n"
            f"• Без телефонов: {stats['total_users'] - users_with_phones}\n\n"
            "📝 Анкеты:\n"
            f"• Всего: {stats['total_questionnaires']}\n"
            f"• За сегодня: {today_questionnaires}\n\n"
            "❓ Вопросы:\n"
            f"• Всего: {stats['total_questions']}\n"
            f"• Активных: {stats['active_questions']}\n"
            f"• Неактивных: {stats['total_questions'] - stats['active_questions']}"
        )
        
        await message.answer(stats_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        # Если есть ошибка, показываем базовую статистику
        basic_stats = (
            "📊 Базовая статистика\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"📝 Анкет: {stats['total_questionnaires']}\n"
            f"❓ Вопросов: {stats['total_questions']}\n"
            f"🏃 Активных вопросов: {stats['active_questions']}"
        )
        await message.answer(basic_stats)
    finally:
        session.close()

# ========== ОБРАБОТКА ОСТАЛЬНЫХ СООБЩЕНИЙ В АДМИНКЕ ==========

@router.message()
async def handle_admin_other_messages(message: Message, state: FSMContext):
    """Обработка прочих сообщений в админке"""
    # Проверяем, находится ли пользователь в админке
    current_state = await state.get_state()
    
    # Если мы в состоянии админки (ожидание ввода вопроса и т.д.)
    if current_state in [
        AdminStates.waiting_for_new_question,
        AdminStates.waiting_for_edit_question_id,
        AdminStates.waiting_for_edit_question_text
    ]:
        # Эти состояния обрабатываются специальными хендлерами выше
        return
    
    # Если пользователь админ, но отправил неизвестное сообщение в админке
    if is_admin(message.from_user.id):
        await message.answer(
            "❓ Неизвестная команда в админке.\n\n"
            "Используйте меню админки или команду:\n"
            "/admin - открыть админку\n"
            "⬅️ Выйти из админки - вернуться в главное меню",
            reply_markup=get_admin_menu()
        )
