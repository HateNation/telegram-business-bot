import asyncio
import logging
import sys
import os

                                       
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import user_handlers, admin_handlers

                       
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
                                       
    
                              
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в .env файле!")
        return
    
                                     
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
                          
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    
    
   
    
    logger.info("🤖 Бот запускается...")
    logger.info(f"📊 База данных: {config.DATABASE_URL}")
    logger.info(f"👑 Админы: {config.ADMIN_ID}")
    
                                        
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")