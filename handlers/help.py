from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold, hcode

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку по командам"""

    help_text = (
        f"{hbold('❓ Помощь по боту')}\n\n"

        f"{hbold('📋 Основные команды:')}\n"
        f"{hcode('/start')} - Начать контролировать свои финансы\n"
        f"{hcode('/help')} - Показать эту справку\n\n"

        f"{hbold('💰 Управление сбережениями:')}\n"
        f"{hcode('/new')} - Создать новое сбережение (пошаговый диалог)\n"
        f"{hcode('/list')} - Список всех сбережений\n"
        f"{hcode('/total')} - Общая сумма всех сбережений\n"
        f"{hcode('/del Название')} - Удалить актив\n\n"

        f"{hbold('📊 Операции:')}\n"
        f"{hcode('/add Сумма Название')} - Записать пополнение\n"
        f"  Пример: {hcode('/add 33333 Альфа-вклад')}\n"
        f"{hcode('/take Сумма Название')} - Записать снятие\n"
        f"  Пример: {hcode('/take 333 Альфа-вклад')}\n\n"

        f"{hbold('💡 Типы активов:')}\n"
        f"• {hcode('deposit')} - вклад с процентами\n"
        f"• {hcode('cash')} - кэш (без процентов)\n\n"

        f"{hbold('📝 Пример создания актива:')}\n"
        f"1. Введи {hcode('/new')}\n"
        f"2. Выбери тип (Вклад/Кэш)\n"
        f"3. Введи название\n"
        f"4. Введи сумму\n"
        f"5. Для вклада введи процентную ставку\n"
        f"6. Подтверди создание\n\n"

        f"{hbold('ℹ️ Дополнительно:')}\n"
        f"• Проценты начисляются автоматически каждый день\n"
        f"• После пополнения проценты считаются от новой суммы\n"
        f"• Все данные хранятся в базе данных и не теряются\n\n"

        f"{hbold('📞 Поддержка:')}\n"
        f"По вопросам: @Diifififi"
    )

    await message.answer(help_text, parse_mode="HTML")