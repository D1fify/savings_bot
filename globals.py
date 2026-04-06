# globals.py
from services.scheduler import MonthlyReportScheduler

# Глобальные переменные
bot = None
scheduler = None

def init_scheduler(bot_instance):
    """Инициализация планировщика"""
    global bot, scheduler
    bot = bot_instance
    scheduler = MonthlyReportScheduler(bot)
    return scheduler

def get_scheduler():
    """Получить планировщик"""
    global scheduler
    return scheduler

def get_bot():
    """Получить бота"""
    global bot
    return bot