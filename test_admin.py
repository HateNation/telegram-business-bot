import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config

print("🧪 Тестирование конфигурации админки...")
print(f"BOT_TOKEN: {'✅ Установлен' if config.BOT_TOKEN else '❌ Отсутствует'}")
print(f"ADMIN_ID: {config.ADMIN_ID}")
print(f"Ваш ID в списке админов: {8553510941 in [int(id) for id in config.ADMIN_ID if id]}")
print(f"Все админы: {config.ADMIN_ID}")