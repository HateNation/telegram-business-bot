from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    phone_number = Column(String(20))                            
    formatted_phone = Column(String(30))                                         
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, phone={self.phone_number})>"

class Questionnaire(Base):
    __tablename__ = 'questionnaires'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    answers = Column(Text)                          
    status = Column(String(20), default='completed')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_answers(self):
                                            
        try:
            return json.loads(self.answers) if self.answers else {}
        except json.JSONDecodeError:
            return {}
    
    def set_answers(self, answers_dict):
                                          
        self.answers = json.dumps(answers_dict, ensure_ascii=False)
        
    def get_formatted_answers(self):
                                                               
        answers = self.get_answers()
        formatted = []
        
        for q_id, answer_data in answers.items():
            formatted.append({
                'question_id': q_id,
                'question_text': answer_data.get('question_text', 'Неизвестный вопрос'),
                'answer': answer_data.get('answer', 'Нет ответа'),
                'question_number': answer_data.get('question_number', 0)
            })
        
                                     
        formatted.sort(key=lambda x: x.get('question_number', 0))
        return formatted

class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    question_text = Column(Text, nullable=False)
    question_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Question(id={self.id}, text='{self.question_text[:50]}...', order={self.question_order})>"