from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hcode
from database import db
from handlers.new import cmd_new  # 👈 Импортируем cmd_new

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user
    user_id = user.id
    first_name = user.first_name or "друг"

    # Добавляем пользователя в БД
    await db.add_user(user_id, user.username)

    # Проверяем, есть ли у пользователя активы
    assets = await db.get_user_assets(user_id)

    # Если активов нет - показываем красивое приветствие для новичка
    if not assets:
        welcome_text = (
            f"🌟 {hbold(f'Привет, {first_name}!')} 🌟\n\n"
            f"✨ {hbold('Добро пожаловать в Savings Bot')} ✨\n"
            f"— твой личный помощник по учету сбережений!\n\n"
            f"{hbold('📊 Что я умею:')}\n"
            f"💰 Учитывать вклады и накопления\n"
            f"📈 Следить за ростом процентов\n"
            f"💱 Работать с разными валютами\n"
            f"📅 Отправлять ежемесячные отчеты\n\n"
            f"{hbold('🚀 Как начать:')}\n"
            f"1️⃣ Нажми кнопку {hcode('➕ Новый актив')}\n"
            f"2️⃣ Выбери тип (вклад или кэш)\n"
            f"3️⃣ Введи название и сумму\n"
            f"4️⃣ Наблюдай за ростом!\n\n"
            f"❓ Если нужна помощь — нажми кнопку {hcode('Помощь')}\n\n"
            f"🎉 {hbold('Удачных накоплений!')} 🎉"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать первый актив", callback_data="new_from_start")
            ],
            [
                InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
                InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
            ]
        ])
    else:
        total_balance = sum(asset['current_amount'] for asset in assets)

        welcome_text = (
            f"👋 {hbold(f'С возвращением, {first_name}!')}\n\n"
            f"📊 {hbold('Твоя статистика:')}\n"
            f"💰 Активов: {len(assets)}\n"
            f"💵 Баланс: {total_balance:,.2f} ₽\n\n"
            f"Выбери действие:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Активы", callback_data="list"),
                InlineKeyboardButton(text="➕ Новый", callback_data="new")
            ],
            [
                InlineKeyboardButton(text="📈 Баланс", callback_data="total"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="help")
            ]
        ])

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# 👇 НОВЫЙ ОБРАБОТЧИК для кнопки из start
@router.callback_query(F.data == "new_from_start")
async def new_from_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_new(callback.message, state)


@router.callback_query(F.data == "new")
async def new_asset(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_new(callback.message, state)


@router.callback_query(F.data == "about")
async def about_bot(callback: CallbackQuery):
    about_text = (
        f"{hbold('ℹ️ О боте Savings Bot')}\n\n"
        f"{hbold('📝 Описание:')}\n"
        f"Бот создан для учета личных сбережений, "
        f"вкладов и инвестиций. Помогает следить за "
        f"ростом капитала и достигать финансовых целей.\n\n"
        f"{hbold('⚙️ Версия:')} 1.0.0\n"
        f"{hbold('📅 Дата создания:')} Февраль 2026\n\n"
        f"{hbold('📋 Основные команды:')}\n"
        f"/new — создать актив\n"
        f"/list — список активов\n"
        f"/total — общий баланс\n"
        f"/add — пополнить\n"
        f"/take — снять\n"
        f"/help — помощь\n\n"
        f"💡 {hbold('Совет:')} Добавляй даже небольшие суммы — "
        f"каждая копейка работает на твое будущее!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])

    await callback.message.edit_text(
        about_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_command(callback: CallbackQuery):
    help_text = (
        f"{hbold('❓ Помощь по командам')}\n\n"
        f"{hbold('📋 Основные команды:')}\n"
        f"{hcode('/start')} — главное меню\n"
        f"{hcode('/new')} — создать новый актив\n"
        f"{hcode('/list')} — показать все активы\n"
        f"{hcode('/total')} — общий баланс\n"
        f"{hcode('/add <сумма> <название>')} — пополнить\n"
        f"{hcode('/take <сумма> <название>')} — снять\n"
        f"{hcode('/del <название>')} — удалить актив\n\n"
        f"{hbold('💰 Типы активов:')}\n"
        f"• {hcode('deposit')} — вклад с процентами\n"
        f"• {hcode('cash')} — кэш (без процентов)\n\n"
        f"{hbold('📝 Примеры:')}\n"
        f"/new СберВклад 100000 deposit 8.5\n"
        f"/add 25000 СберВклад\n"
        f"/take 10000 Заначка\n\n"
        f"{hbold('📊 Ежемесячный отчет:')}\n"
        f"Каждое 1-е число месяца я присылаю статистику "
        f"с начисленными процентами!\n\n"
        f"💬 По всем вопросам: @username"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])

    await callback.message.edit_text(
        help_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    user = callback.from_user
    first_name = user.first_name or "друг"

    assets = await db.get_user_assets(user.id)

    if not assets:
        welcome_text = (
            f"🌟 {hbold(f'Привет, {first_name}!')} 🌟\n\n"
            f"✨ {hbold('Добро пожаловать в Savings Bot')} ✨\n\n"
            f"Начни с создания первого актива 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать первый актив", callback_data="new_from_start")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ])
    else:
        total_balance = sum(asset['current_amount'] for asset in assets)
        welcome_text = (
            f"👋 {hbold('Главное меню')}\n\n"
            f"💰 Активов: {len(assets)}\n"
            f"💵 Баланс: {total_balance:,.2f} ₽"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Активы", callback_data="list"),
                InlineKeyboardButton(text="➕ Новый", callback_data="new")
            ],
            [
                InlineKeyboardButton(text="📈 Баланс", callback_data="total"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="help")
            ]
        ])

    await callback.message.edit_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()