from .db import AsyncDatabaseManager
import os

# Абсолютный путь к БД
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'savings.db')
print(f"📁 Создаем db с путем: {DB_PATH}")

db = AsyncDatabaseManager(DB_PATH)