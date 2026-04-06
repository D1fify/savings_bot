import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DEBUG
from database import db
from handlers.start import router as start_router
from handlers.new import router as new_router
from handlers.total_list import router as total_list_router
from handlers.operations import router as operations_router
from handlers.help import router as help_router
from services.scheduler import MonthlyReportScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
bot = None
scheduler = None


async def main():
    global bot, scheduler

    logger.info("🚀 Запуск бота...")

    # Инициализируем БД
    await db.init_database()

    # Создаем бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаем и запускаем планировщик
    scheduler = MonthlyReportScheduler(bot)
    scheduler.start()

    # Настраиваем диспетчер
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем роутеры
    dp.include_router(start_router)
    dp.include_router(new_router)
    dp.include_router(total_list_router)
    dp.include_router(operations_router)
    dp.include_router(help_router)


    # Удаляем вебхук (на случай если был установлен)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ Бот успешно запущен и готов к работе")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())