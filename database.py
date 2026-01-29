from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from models.models import Base, User, Questionnaire, Question
from config import config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
                               
        self.engine = create_engine(
            config.DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.create_tables()                                    
        self.update_tables()                                                   
        self.create_default_questions()                                
    
    def create_tables(self):
                                           
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Таблицы SQLite успешно созданы/проверены")
        except Exception as e:
            logger.error(f"❌ Ошибка при создании таблиц: {e}")
    
    def update_tables(self):
                                                                  
        session = self.get_session()
        try:
                                                                  
            inspector = inspect(self.engine)
            columns = inspector.get_columns('users')
            column_names = [col['name'] for col in columns]
            
            logger.info(f"📊 Существующие поля в таблице users: {column_names}")
            
                                          
            if 'phone_number' not in column_names:
                session.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))
                logger.info("✅ Добавлено поле phone_number в таблицу users")
            
            if 'formatted_phone' not in column_names:
                session.execute(text("ALTER TABLE users ADD COLUMN formatted_phone VARCHAR(30)"))
                logger.info("✅ Добавлено поле formatted_phone в таблицу users")
            
            if 'updated_at' not in column_names:
                session.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                logger.info("✅ Добавлено поле updated_at в таблицу users")
            
            session.commit()
            logger.info("✅ Структура таблиц успешно обновлена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении таблиц: {e}")
            session.rollback()
        finally:
            session.close()
    
    def create_default_questions(self):
                                            
        session = self.get_session()
        try:
                                        
            if session.query(Question).count() == 0:
                default_questions = [
                    Question(question_text="Як вас звати?", question_order=1),
                    Question(question_text="Скільки вам років?", question_order=2),
                    Question(question_text="Яка у вас професія?", question_order=3),
                    Question(question_text="Розкажіть про ваші захоплення", question_order=4),
                    Question(question_text="Яке ваше місто проживання?", question_order=5),
                    Question(question_text="Що для вас важливо в житті?", question_order=6)
                ]
                session.add_all(default_questions)
                session.commit()
                logger.info("✅ Створені питання за замовчуванням")
        except Exception as e:
            logger.error(f"❌ Помилка при створенні питань: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_session(self):
                                         
        return self.SessionLocal()
    
                                        
    def get_or_create_user(self, user_id, username, full_name):
                                               
        session = self.get_session()
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                user = User(user_id=user_id, username=username, full_name=full_name)
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"✅ Створено нового користувача: {user_id}")
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Помилка при створенні користувача: {e}")
            raise e
        finally:
            session.close()
    
    def update_user_phone(self, user_id, phone_number, formatted_phone=None):
                                                  
        session = self.get_session()
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            
            if user:
                user.phone_number = phone_number
                if formatted_phone:
                    user.formatted_phone = formatted_phone
                else:
                    user.formatted_phone = phone_number
                
                user.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"✅ Номер телефону оновлено для користувача {user_id}")
                return True
            else:
                logger.warning(f"⚠️ Користувача {user_id} не знайдено")
                return False
                
        except Exception as e:
            logger.error(f"❌ Помилка при оновленні номера телефону: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_user_by_id(self, user_id):
                                         
        session = self.get_session()
        try:
            return session.query(User).filter(User.user_id == user_id).first()
        finally:
            session.close()
    
                                   
    def get_active_questions(self):
                                       
        session = self.get_session()
        try:
            questions = session.query(Question).filter(
                Question.is_active == True
            ).order_by(Question.question_order).all()
            
            logger.info(f"📊 Отримано активних питань: {len(questions)}")
            
            if not questions:
                logger.warning("⚠️ Немає активних питань в базі!")
                
                                                   
                all_questions = session.query(Question).count()
                logger.info(f"📊 Всього питань в базі: {all_questions}")
                
                                                                        
                if all_questions > 0:
                    logger.info("🔄 Активую всі питання...")
                    session.query(Question).update({Question.is_active: True})
                    session.commit()
                    questions = session.query(Question).order_by(Question.question_order).all()
                    logger.info(f"✅ Активовано {len(questions)} питань")
            
            return questions
        except Exception as e:
            logger.error(f"❌ Помилка при отриманні питань: {e}")
            return []
        finally:
            session.close()
    
    def get_all_questions(self):
                                  
        session = self.get_session()
        try:
            return session.query(Question).order_by(Question.question_order).all()
        finally:
            session.close()
    
    def get_question_by_id(self, question_id):
                                   
        session = self.get_session()
        try:
            return session.query(Question).filter(Question.id == question_id).first()
        finally:
            session.close()
    
    def update_question(self, question_id, new_text):
                                    
        session = self.get_session()
        try:
            question = session.query(Question).filter(Question.id == question_id).first()
            if question:
                question.question_text = new_text
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Помилка при оновленні питання: {e}")
            return False
        finally:
            session.close()
    
    def add_question(self, question_text, order):
                                   
        session = self.get_session()
        try:
            question = Question(question_text=question_text, question_order=order)
            session.add(question)
            session.commit()
            session.refresh(question)
            return question
        except Exception as e:
            session.rollback()
            logger.error(f"Помилка при додаванні питання: {e}")
            return None
        finally:
            session.close()
    
                                  
    def save_questionnaire(self, user_id, answers):
                                            
        session = self.get_session()
        try:
            import json
            
                                         
            logger.info(f"💾 Збереження анкети для користувача {user_id}")
            logger.info(f"📊 Кількість відповідей: {len(answers)}")
            
                                                             
            answers_to_save = {}
            for question_id, answer_data in answers.items():
                answers_to_save[str(question_id)] = {
                    'question_id': answer_data.get('question_id'),
                    'question_text': answer_data.get('question_text', ''),
                    'answer': answer_data.get('answer', ''),
                    'question_number': answer_data.get('question_number', 0)
                }
            
            questionnaire = Questionnaire(user_id=user_id)
            questionnaire.set_answers(answers_to_save)
            session.add(questionnaire)
            session.commit()
            session.refresh(questionnaire)
            
            logger.info(f"✅ Анкету #{questionnaire.id} збережено для користувача {user_id}")
            return questionnaire
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Помилка при збереженні анкети: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            session.close()
    
    def get_all_questionnaires(self):
                                 
        session = self.get_session()
        try:
            return session.query(Questionnaire).order_by(Questionnaire.created_at.desc()).all()
        finally:
            session.close()
    
    def get_user_questionnaire(self, user_id):
                                          
        session = self.get_session()
        try:
            return session.query(Questionnaire).filter(
                Questionnaire.user_id == user_id
            ).order_by(Questionnaire.created_at.desc()).first()
        finally:
            session.close()
    
    def get_statistics(self):
                                 
        session = self.get_session()
        try:
            total_users = session.query(User).count()
            total_questionnaires = session.query(Questionnaire).count()
            total_questions = session.query(Question).count()
            active_questions = session.query(Question).filter(Question.is_active == True).count()
            
            return {
                'total_users': total_users,
                'total_questionnaires': total_questionnaires,
                'total_questions': total_questions,
                'active_questions': active_questions
            }
        finally:
            session.close()

                                          
db = Database()