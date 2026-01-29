from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
import sys
import os
import re
from datetime import datetime
from texts.welcome_text import WELCOME_TEXT
from handlers.admin_handlers import user_in_admin, set_admin_session

# Добавляем корневую папку в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from keyboards.main_menu import get_main_menu
from services.smtp_sender import send_gmail_smtp



router = Router()
logger = logging.getLogger(__name__)

class QuestionnaireStates(StatesGroup):
    """Состояния для анкеты"""
    waiting_for_phone = State()      # Ожидание номера телефона
    asking_questions = State()       # Задаем вопросы анкеты
    answers = State()                # Сохраненные ответы

def parse_question_options(question_text):
    """Извлечь варианты ответов из текста вопроса (строки с '• ')."""
    if not question_text:
        return []
    options = []
    for line in question_text.splitlines()[1:]:
        line = line.strip()
        if line.startswith("• "):
            options.append(line[2:].strip())
    return options

def strip_question_options(question_text):
    """Убрать варианты ответов из текста вопроса (оставить только заголовок)."""
    if not question_text:
        return ""
    lines = question_text.splitlines()
    return lines[0].strip() if lines else question_text

def build_options_inline_keyboard(options):
    """Inline-клавиатура с вариантами ответов."""
    if not options:
        return None
    builder = InlineKeyboardBuilder()
    for idx, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"qopt:{idx}")
    builder.adjust(2)
    return builder.as_markup()

def get_phone_request_keyboard():
    """Клавиатура для запроса номера телефона"""
    keyboard = [
        [KeyboardButton(text="📱 Відправити номер", request_contact=True)],
        [KeyboardButton(text="✏️ Ввести вручну")],
        [KeyboardButton(text="🚫 Пропустити")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

def validate_ukrainian_phone(phone):
    """Валидация украинского номера телефона"""
    if not phone:
        return False
    
    # Убираем все нецифровые символы
    cleaned = re.sub(r'\D', '', phone)
    
    # Украинские номера начинаются с 380, затем 9 цифр (всего 12 цифр)
    if cleaned.startswith('380'):
        if len(cleaned) == 12:
            return f"+{cleaned}"
    
    # Если номер начинается с 0 (например, 0671234567)
    elif cleaned.startswith('0') and len(cleaned) == 10:
        return f"+38{cleaned}"
    
    # Если номер начинается с +380
    elif phone.startswith('+380'):
        cleaned_plus = re.sub(r'\D', '', phone[1:])  # Убираем + и все нецифры
        if len(cleaned_plus) == 12:
            return phone
    
    # Если ввели без кода страны (например, 0671234567)
    elif len(cleaned) == 10 and cleaned.startswith(('050', '066', '095', '099', '063', '073', '093', '067', '068', '096', '097', '098')):
        return f"+38{cleaned}"
    
    return None

def format_ukrainian_phone(phone):
    """Форматирование украинского номера телефона"""
    cleaned = re.sub(r'\D', '', phone)
    
    if len(cleaned) == 12 and cleaned.startswith('380'):
        # Формат: +380 (XX) XXX-XX-XX
        return f"+{cleaned[:3]} ({cleaned[3:5]}) {cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
    elif len(cleaned) == 12 and cleaned.startswith('38'):
        # Формат: +38 (0XX) XXX-XX-XX
        return f"+{cleaned[:2]} ({cleaned[2:5]}) {cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
    elif len(cleaned) == 10:
        # Формат: +38 (0XX) XXX-XX-XX
        return f"+38 ({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:8]}-{cleaned[8:10]}"
    else:
        return phone

async def save_phone_to_db(user_id, phone_number, formatted_phone):
    """Сохранить номер телефона в базу данных"""
    try:
        success = db.update_user_phone(user_id, phone_number, formatted_phone)
        if success:
            logger.info(f"✅ Номер телефону збережено для користувача {user_id}: {formatted_phone}")
        else:
            logger.warning(f"⚠️ Не вдалося зберегти номер телефону для користувача {user_id}")
        return success
    except Exception as e:
        logger.error(f"❌ Помилка при збереженні номера телефону: {e}")
        return False

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    # Очищаем состояние
    await state.clear()
    
    # Создаем или получаем пользователя
    user = db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    await message.answer(WELCOME_TEXT, 
                        reply_markup=get_phone_request_keyboard(),
                        parse_mode="HTML")
    await state.set_state(QuestionnaireStates.waiting_for_phone)

@router.message(QuestionnaireStates.waiting_for_phone)
async def process_phone_number(message: Message, state: FSMContext):
    """Обработка номера телефона"""
    phone_number = None
    
    # Проверяем, отправил ли пользователь контакт
    if message.contact:
        phone_number = message.contact.phone_number
        logger.info(f"Отримано контакт: {phone_number}")
    elif not message.text:
        await message.answer(
            "⚠️ Будь ласка, надішліть номер телефону текстом "
            "або натисніть '📱 Відправити номер'.",
            reply_markup=get_phone_request_keyboard()
        )
        return
    
    # Или ввел номер вручную
    elif message.text:
        user_input = message.text.strip()
        
        if user_input.lower() in ['пропустити', 'пропустить', 'skip', '🚫 пропустити']:
            phone_number = "Не вказано"
            await message.answer("✅ Номер телефону пропущено.", reply_markup=get_main_menu())
            await state.clear()
            return
        
        elif user_input == "✏️ Ввести вручну":
            await message.answer(
                "📝 Введіть свій номер телефону у форматі:\n\n"
                "• +380XXXXXXXXX\n"
                "• 0XXXXXXXXX\n"
                "• 380XXXXXXXXX\n\n"
                "Наприклад: +380671234567 або 0671234567",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        else:
            # Валидируем номер
            if user_input == "📱 Відправити номер":
                await message.answer(
                    "⚠️ Контакт не надіслано. Дозвольте відправку контакту у Telegram "
                    "або введіть номер вручну.",
                    reply_markup=get_phone_request_keyboard()
                )
                return

            validated_phone = validate_ukrainian_phone(user_input)
            if validated_phone:
                phone_number = validated_phone
            else:
                await message.answer(
                    "❌ Неправильний формат номера телефону.\n\n"
                    "Будь ласка, введіть номер у форматі:\n"
                    "• +380XXXXXXXXX (12 цифр після +)\n"
                    "• 0XXXXXXXXX (10 цифр, починається з 0)\n"
                    "• 380XXXXXXXXX (12 цифр)\n\n"
                    "Або натисніть '📱 Відправити номер'",
                    reply_markup=get_phone_request_keyboard()
                )
                return
    
    if phone_number:
        # Форматируем номер для красивого отображения
        formatted_phone = format_ukrainian_phone(phone_number)
        
        # Сохраняем номер телефона в состоянии
        await state.update_data({
            'phone_number': phone_number,
            'formatted_phone': formatted_phone,
            'user_id': message.from_user.id
        })
        
        # Гарантируем, что пользователь существует (мог открыть /phone без /start)
        db.get_or_create_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )

        # Сохраняем номер в базу данных
        await save_phone_to_db(message.from_user.id, phone_number, formatted_phone)
        
        # Показываем меню
        menu_text = (
            f"✅ Номер телефону збережено: {formatted_phone}\n\n"
            "Тепер ви можете розпочати заповнення анкети."
        )
        await message.answer(menu_text, reply_markup=get_main_menu())
        await state.clear()

@router.message(F.text == "📝 Начать анкету")
async def start_questionnaire(message: Message, state: FSMContext):
    """Начало заполнения анкеты"""
    # Получаем активные вопросы
    questions = db.get_active_questions()
    
    if not questions:
        await message.answer("❌ Питання для анкети тимчасово відсутні.")
        return
    
    # Проверяем, есть ли сохраненный номер телефона
    user = db.get_user_by_id(message.from_user.id)
    
    if not user or not user.phone_number or user.phone_number == "Не вказано":
        # Если номера нет, запрашиваем его
        await message.answer(
            "📱 Для початку анкети потрібен ваш номер телефону.\n\n"
            "Будь ласка, відправте номер:",
            reply_markup=get_phone_request_keyboard()
        )
        await state.set_state(QuestionnaireStates.waiting_for_phone)
        return
    
    # Инициализируем данные анкеты
    await state.update_data({
        'questions': questions,
        'current_question_index': 0,
        'answers': {},
        'total_questions': len(questions),
        'phone_number': user.phone_number,
        'formatted_phone': user.formatted_phone if user.formatted_phone else user.phone_number
    })
    
    # Показываем первый вопрос
    await ask_next_question(message, state)

async def ask_next_question(message: Message, state: FSMContext):
    """Задать следующий вопрос"""
    data = await state.get_data()
    questions = data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    
    if current_index >= len(questions):
        # Все вопросы отвечены
        await finish_questionnaire(message, state)
        return
    
    question = questions[current_index]
    
    options = parse_question_options(question.question_text)
    prompt = "✍️ Напишіть вашу відповідь:" if not options else "👇 Оберіть варіант відповіді:"
    # Формируем текст вопроса
    question_text = (
        f"📝 Питання {current_index + 1}/{len(questions)}\n\n"
        f"❓ {question.question_text}\n\n"
        f"{prompt}"
    )
    
    # Отправляем вопрос
    reply_markup = build_options_inline_keyboard(options) if options else ReplyKeyboardRemove()
    await message.answer(question_text, reply_markup=reply_markup)
    
    # Устанавливаем состояние ожидания ответа
    await state.set_state(QuestionnaireStates.asking_questions)

@router.message(QuestionnaireStates.asking_questions)
async def process_answer(message: Message, state: FSMContext):
    """Обработка ответа пользователя"""
    if not message.text:
        await message.answer("⚠️ Будь ласка, надішліть відповідь текстом.")
        return
    await handle_answer(message, state, message.text.strip())

@router.callback_query(F.data.startswith("qopt:"))
async def process_option_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора варианта ответа через inline-кнопки."""
    current_state = await state.get_state()
    if current_state != QuestionnaireStates.asking_questions:
        await callback.answer()
        return
    
    data = await state.get_data()
    questions = data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    
    if current_index >= len(questions):
        await callback.answer()
        return
    
    question = questions[current_index]
    options = parse_question_options(question.question_text)
    
    try:
        idx = int(callback.data.split(":", 1)[1])
        user_answer = options[idx] if 0 <= idx < len(options) else None
    except Exception:
        user_answer = None
    
    if not user_answer:
        await callback.answer("Невірний вибір")
        return
    
    await callback.answer()
    await handle_answer(callback.message, state, user_answer)

async def handle_answer(message: Message, state: FSMContext, user_answer: str):
    """Сохранить ответ и перейти к следующему вопросу."""
    data = await state.get_data()
    questions = data.get('questions', [])
    current_index = data.get('current_question_index', 0)
    answers = data.get('answers', {})
    
    if current_index < len(questions):
        question = questions[current_index]
        options = parse_question_options(question.question_text)
        
        # Проверяем, не пустой ли ответ
        if not user_answer:
            await message.answer("⚠️ Будь ласка, напишіть відповідь на питання.")
            return
        
        # Обработка команды "пропустить"
        if user_answer.lower() in ['пропустити', 'пропустить', 'skip', 'pass']:
            user_answer = "❌ Питання пропущено"
            await message.answer(
                f"✅ Питання {current_index + 1} пропущено.",
                reply_markup=ReplyKeyboardRemove()
            )
        elif options and user_answer not in options:
            await message.answer(
                "⚠️ Будь ласка, оберіть один із варіантів відповіді.",
                reply_markup=build_options_inline_keyboard(options)
            )
            return
        else:
            await message.answer(
                f"✅ Відповідь на питання {current_index + 1} прийнято!",
                reply_markup=ReplyKeyboardRemove()
            )
        
        # Сохраняем ответ
        answers[question.id] = {
            'question_id': question.id,
            'question_text': question.question_text,
            'answer': user_answer,
            'question_number': current_index + 1
        }
        
        # Увеличиваем индекс вопроса
        next_index = current_index + 1
        
        # Обновляем данные состояния
        await state.update_data({
            'answers': answers,
            'current_question_index': next_index
        })
        
        # Небольшая пауза перед следующим вопросом
        import asyncio
        await asyncio.sleep(0.5)
        
        # Показываем следующий вопрос
        await ask_next_question(message, state)

async def finish_questionnaire(message: Message, state: FSMContext):
    """Завершение анкеты и сохранение в базу"""
    data = await state.get_data()
    answers = data.get('answers', {})
    total_questions = data.get('total_questions', 0)
    phone_number = data.get('formatted_phone', 'Не вказано')
    
    if not answers:
        await message.answer("❌ Ви не відповіли жодного питання.")
        await state.clear()
        return
    
    try:
        # Сохраняем анкету в базу данных
        saved_questionnaire = db.save_questionnaire(
            user_id=message.from_user.id,
            answers=answers
        )
        
        if saved_questionnaire:
            # Формируем итоговое сообщение
            result_text = "🎉 Анкету успішно збережено!\n\n"
            result_text += f"📱 Ваш номер: {phone_number}\n\n"
            result_text += "📋 Ваші відповіді:\n\n"
            
            for i, (question_id, answer_data) in enumerate(answers.items(), 1):
                answer = answer_data['answer']
                if answer == "❌ Питання пропущено":
                    result_text += f"{i}. ❌ {answer_data['question_text']} - Пропущено\n"
                else:
                    result_text += f"{i}. {answer_data['question_text']}\n"
                    result_text += f"   ➡️ {answer}\n"
                result_text += "\n"
            
            result_text += f"📊 Статистика:\n"
            result_text += f"• Всього питань: {total_questions}\n"
            answered_count = len([a for a in answers.values() if a['answer'] != "❌ Питання пропущено"])
            result_text += f"• Відповіли: {answered_count}\n"
            result_text += f"• Пропущено: {total_questions - answered_count}\n"
            result_text += "💾 Дані збережено в базу даних"
            
            await message.answer(result_text, reply_markup=get_main_menu())

            # Отправляем анкету на почту
            try:
                user = db.get_user_by_id(message.from_user.id)
                subject = f"Анкета #{saved_questionnaire.id} — {user.full_name if user else message.from_user.id}"

                header = (
                    "АНКЕТА КЛІЄНТА\n"
                    "=================\n"
                    f"ID: {saved_questionnaire.id}\n"
                    f"Дата: {saved_questionnaire.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"ПІБ: {user.full_name if user else 'Невідомо'}\n"
                    f"Username: @{user.username if user and user.username else message.from_user.id}\n"
                    f"Телефон: {phone_number}\n\n"
                )

                def step_title(qn: int) -> str:
                    if 1 <= qn <= 10:
                        return "Крок 1 — Основна інформація"
                    if 11 <= qn <= 14:
                        return "Крок 2 — Анамнез пологів"
                    if 15 <= qn <= 21:
                        return "Крок 3 — Здоров'я"
                    return "Крок 4 — Соціальні аспекти"

                # Сортируем ответы по номеру вопроса
                ordered_answers = []
                for _, a in answers.items():
                    ordered_answers.append(
                        (a.get("question_number", 0), a.get("question_text", ""), a.get("answer", ""))
                    )
                ordered_answers.sort(key=lambda x: x[0])

                # Строим таблицу с шагами
                email_body = header
                current_step = None
                col_width = 44
                sep = "+" + "-" * (col_width + 2) + "+" + "-" * (col_width + 2) + "+\n"
                for qn, qtext, ans in ordered_answers:
                    step = step_title(qn)
                    if step != current_step:
                        email_body += f"{step}\n"
                        email_body += sep
                        email_body += f"| {'Питання'.ljust(col_width)} | {'Відповідь'.ljust(col_width)} |\n"
                        email_body += sep
                        current_step = step
                    qt = strip_question_options(qtext).replace("\n", " ")
                    at = ans.replace("\n", " ")
                    email_body += f"| {qt[:col_width].ljust(col_width)} | {at[:col_width].ljust(col_width)} |\n"
                email_body += sep

                import asyncio
                await asyncio.to_thread(send_gmail_smtp, subject, email_body)
            except Exception as e:
                logger.error(f"Помилка надсилання анкети на Gmail: {e}")
        else:
            await message.answer("❌ Помилка при збереженні анкети в базу даних.")
    
    except Exception as e:
        logger.error(f"Помилка при збереженні анкети: {e}")
        await message.answer("❌ Сталася помилка при збереженні анкети.")
    
    # Очищаем состояние
    await state.clear()

@router.message(F.text == "📊 Моя анкета")
async def show_my_questionnaire(message: Message):
    """Показать анкету пользователя"""
    questionnaire = db.get_user_questionnaire(message.from_user.id)
    
    if questionnaire:
        answers = questionnaire.get_answers()
        
        if not answers:
            await message.answer("❌ У вашій анкеті немає відповідей.")
            return
        
        # Получаем данные пользователя для номера телефона
        user = db.get_user_by_id(message.from_user.id)
        phone_number = user.formatted_phone if user and user.formatted_phone else (user.phone_number if user and user.phone_number else 'Не вказано')
        
        result_text = f"📋 Ваша остання анкета\n"
        result_text += f"📱 Номер: {phone_number}\n\n"
        
        # Преобразуем ответы в список и сортируем по номеру вопроса
        answers_list = []
        for question_id, answer_data in answers.items():
            answers_list.append({
                'number': answer_data.get('question_number', 0),
                'text': answer_data.get('question_text', ''),
                'answer': answer_data.get('answer', '')
            })
        
        # Сортируем по номеру вопроса
        answers_list.sort(key=lambda x: x['number'])
        
        for i, answer_data in enumerate(answers_list, 1):
            answer = answer_data['answer']
            if answer == "❌ Питання пропущено":
                result_text += f"{i}. ❌ {answer_data['text']} - Пропущено\n"
            else:
                result_text += f"{i}. {answer_data['text']}\n"
                result_text += f"   ➡️ {answer}\n"
            result_text += "\n"
        
        result_text += f"📅 Дата заповнення: {questionnaire.created_at.strftime('%d.%m.%Y %H:%M')}"
    else:
        result_text = "❌ У вас поки немає заповненої анкети.\nНатисніть '📝 Начать анкету' для заповнення."
    
    await message.answer(result_text)

@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    """Информация о боте"""
    about_text = (
        "🤖 Інформація про бота\n\n"
        "Цей бот призначений для заповнення анкет.\n\n"
        "📌 Як це працює:\n"
        "1. Надайте номер телефону\n"
        "2. Натисніть '📝 Начать анкету'\n"
        "3. Відповідайте на питання текстом\n"
        "4. Для пропуску питання напишіть 'пропустити'\n"
        "5. В кінці анкета зберігається автоматично\n\n"
    )
    await message.answer(about_text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    help_text = (
        "📋 Доступні команди:\n\n"
        "/start - Почати роботу з ботом\n"
        "/help - Показати цю довідку\n"
        "/cancel - Скасувати поточну анкету\n\n"
        "💡 Поради:\n"
        "• Для пропуску питання напишіть 'пропустити'\n"
        "• Меню доступне завжди, окрім процесу заповнення анкети\n\n"
        "Використовуйте кнопки меню для навігації."
    )
    await message.answer(help_text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущей анкеты"""
    current_state = await state.get_state()
    
    if current_state == QuestionnaireStates.asking_questions:
        data = await state.get_data()
        current_index = data.get('current_question_index', 0)
        total_questions = data.get('total_questions', 0)
        
        progress = f" (пройдено {current_index} з {total_questions} питань)" if current_index > 0 else ""
        
        await state.clear()
        await message.answer(
            f"🚫 Анкету скасовано{progress}.\n\n"
            "Ви можете розпочати нову анкету, натиснувши '📝 Начать анкету'.",
            reply_markup=get_main_menu()
        )
    elif current_state == QuestionnaireStates.waiting_for_phone:
        await state.clear()
        await message.answer(
            "🚫 Запит номера телефону скасовано.\n\n"
            "Ви можете спробувати знову, натиснувши '📝 Начать анкету'.",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer("Немає активної анкети для скасування.")

@router.message(Command("phone"))
async def cmd_phone(message: Message, state: FSMContext):
    """Команда для обновления номера телефона"""
    await state.clear()
    
    # Запрашиваем новый номер телефона
    await message.answer(
        "📱 Введіть новий номер телефону або натисніть '📱 Відправити номер':",
        reply_markup=get_phone_request_keyboard()
    )
    await state.set_state(QuestionnaireStates.waiting_for_phone)

# ========== ЕДИНСТВЕННЫЙ ОБЩИЙ ОБРАБОТЧИК ==========

@router.message()
async def handle_all_messages(message: Message, state: FSMContext):
    """Обработчик ВСЕХ сообщений - должен быть ПОСЛЕДНИМ в файле"""
    
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        if message.text == '/admin' or message.text.startswith('/admin '):
            return  
        
        return
    current_state = await state.get_state()
    
    if current_state == QuestionnaireStates.asking_questions:
        data = await state.get_data()
        current_index = data.get('current_question_index', 0)
        questions = data.get('questions', [])
        
        if current_index < len(questions):
            question = questions[current_index]
            await message.answer(
                f"⚠️ Будь ласка, дайте відповідь на поточне питання:\n\n"
                f"❓ {question.question_text}\n\n"
                "Або використовуйте /cancel для скасування анкети."
            )
        return
    
    elif current_state == QuestionnaireStates.waiting_for_phone:
        await message.answer(
            "⚠️ Будь ласка, надайте свій номер телефону.\n\n"
            "Натисніть '📱 Відправити номер' або введіть номер вручну.\n"
            "Або напишіть 'пропустити' щоб пропустити.",
            reply_markup=get_phone_request_keyboard()
        )
        return
    else:
        await message.answer(
            "⚠️ Я не розумію ваше повідомлення.\n\n"
            "Будь ласка, використовуйте меню для навігації або натисніть /help для довідки.",
            reply_markup=get_main_menu()
    )
    
