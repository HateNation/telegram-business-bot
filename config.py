import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_ID = os.getenv("ADMIN_ID", "").split(",")
    GMAIL_TO = os.getenv("GMAIL_TO", "jasiaua90@gmail.com")
    GMAIL_SENDER = os.getenv("GMAIL_SENDER", "jasiaua90@gmail.com")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    
    @property
    def DATABASE_URL(self):
                           
        return "sqlite:///bot_database.db"

config = Config()
