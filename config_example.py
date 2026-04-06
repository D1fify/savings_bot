import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота — замени на свой!
BOT_TOKEN = "ваш_токен_сюда"

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "savings.db")

# Режим отладки (True/False)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Проверка наличия токена
if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN в переменных окружения!")