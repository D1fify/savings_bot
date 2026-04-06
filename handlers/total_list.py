from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hcode
from database import db
import aiosqlite
import logging
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)


# ==================== КОМАНДА /total ====================
@router.message(Command("total"))
async def cmd_total(message: Message):
    """Обработчик команды /total"""
    user_id = message.from_user.id
    await show_total_balance(message, user_id)


# ==================== КОМАНДА /list ====================
@router.message(Command("list"))
async def cmd_list(message: Message):
    """Обработчик команды /list"""
    user_id = message.from_user.id
    await show_assets_list(message, user_id)


# ==================== ОБРАБОТЧИКИ CALLBACK ====================

@router.callback_query(F.data == "total")
async def callback_total(callback: CallbackQuery):
    """Обработчик callback для кнопки Баланс"""
    await callback.answer("💰 Считаю общий баланс...")
    user_id = callback.from_user.id
    await show_total_balance(callback.message, user_id)


@router.callback_query(F.data == "list")
async def callback_list(callback: CallbackQuery):
    """Обработчик callback для кнопки Список"""
    await callback.answer("📋 Загружаю список...")
    # Передаем правильный user_id из callback
    user_id = callback.from_user.id
    await show_assets_list(callback.message, user_id)


@router.callback_query(F.data == "refresh_list")
async def callback_refresh(callback: CallbackQuery):
    """Обработчик callback для кнопки Обновить"""
    await callback.answer("🔄 Обновляю список...")
    user_id = callback.from_user.id
    await show_assets_list(callback.message, user_id)


@router.callback_query(F.data == "new")
async def callback_new(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для кнопки Новый актив"""
    await callback.answer("➕ Создаю новый актив...")
    from handlers.new import cmd_new
    await cmd_new(callback.message, state)


@router.callback_query(F.data.startswith("del_"))
async def callback_delete(callback: CallbackQuery):
    """Обработчик callback для удаления конкретного актива"""
    if callback.data == "del_all":
        await callback_delete_all(callback)
        return

    asset_id = int(callback.data.replace("del_", ""))
    user_id = callback.from_user.id

    assets = await db.get_user_assets(user_id)
    asset = next((a for a in assets if a['id'] == asset_id), None)

    if not asset:
        await callback.answer("❌ Актив не найден")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{asset_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_del")
        ]
    ])

    await callback.message.edit_text(
        f"{hbold('⚠️ Подтверждение удаления')}\n\n"
        f"Ты действительно хочешь удалить актив?\n\n"
        f"{'💰' if asset['type'] == 'deposit' else '💵'} {hbold(asset['name'])}\n"
        f"Баланс: {asset['current_amount']:,.2f} ₽\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "del_all")
async def callback_delete_all(callback: CallbackQuery):
    """Обработчик callback для кнопки Удалить все"""
    user_id = callback.from_user.id
    assets = await db.get_user_assets(user_id)

    if not assets:
        await callback.answer("📭 Нет активов для удаления")
        return

    total = sum(a['current_amount'] for a in assets)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить все", callback_data="confirm_del_all"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_del")
        ]
    ])

    await callback.message.edit_text(
        f"{hbold('⚠️ ПОДТВЕРЖДЕНИЕ')}\n\n"
        f"Ты действительно хочешь удалить {hbold('ВСЕ')} активы?\n\n"
        f"Всего активов: {len(assets)}\n"
        f"Общий баланс: {total:,.2f} ₽\n\n"
        f"🚨 Это действие необратимо!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_del_all")
async def callback_confirm_delete_all(callback: CallbackQuery):
    """Подтверждение удаления всех активов"""
    user_id = callback.from_user.id

    try:
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute(
                "SELECT id FROM assets WHERE user_id = ?",
                (user_id,)
            )
            assets = await cursor.fetchall()

            for asset in assets:
                asset_id = asset[0]
                await conn.execute(
                    "DELETE FROM transactions WHERE asset_id = ?",
                    (asset_id,)
                )

            await conn.execute(
                "DELETE FROM assets WHERE user_id = ?",
                (user_id,)
            )
            await conn.commit()

        await callback.message.edit_text(
            f"{hbold('✅ Все активы удалены')}\n\n"
            f"Твой список активов пуст.\n"
            f"Создай новый актив командой /new",
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def callback_confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления конкретного актива"""
    asset_id = int(callback.data.replace("confirm_del_", ""))
    user_id = callback.from_user.id

    try:
        assets = await db.get_user_assets(user_id)
        asset = next((a for a in assets if a['id'] == asset_id), None)
        asset_name = asset['name'] if asset else "Актив"
        asset_amount = asset['current_amount'] if asset else 0

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "DELETE FROM transactions WHERE asset_id = ?",
                (asset_id,)
            )
            await conn.execute(
                "DELETE FROM assets WHERE id = ?",
                (asset_id,)
            )
            await conn.commit()

        await callback.message.edit_text(
            f"{hbold('✅ Актив удален')}\n\n"
            f"{asset_name} - {asset_amount:,.2f} ₽",
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {e}")

    await callback.answer()


@router.callback_query(F.data == "cancel_del")
async def callback_cancel_delete(callback: CallbackQuery):
    """Отмена удаления"""
    await callback.answer("✅ Удаление отменено")
    await cmd_list(callback.message)


# ==================== ОБЩАЯ ФУНКЦИЯ ДЛЯ ПОКАЗА БАЛАНСА ====================

async def show_total_balance(message: Message, user_id: int):
    """Общая функция для показа баланса (используется и в команде, и в callback)"""
    assets = await db.get_user_assets(user_id)

    if not assets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать первый актив", callback_data="new")]
        ])
        await message.answer(
            f"{hbold('💎 Всего сбережений: 0 ₽')}\n\n"
            f"У тебя пока нет активов",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Общая сумма
    total = sum(asset['current_amount'] for asset in assets)
    total_str = f"{total:,.2f}".replace(",", " ")

    # Считаем по типам
    deposits_total = sum(a['current_amount'] for a in assets if a['type'] == 'deposit')
    cash_total = sum(a['current_amount'] for a in assets if a['type'] == 'cash')

    # Считаем просроченные вклады
    expired_deposits = 0
    today = datetime.now()
    for asset in assets:
        if asset.get('end_date') and asset['type'] == 'deposit':
            try:
                end_date = datetime.strptime(asset['end_date'], '%Y-%m-%d')
                if end_date < today:
                    expired_deposits += 1
            except:
                pass

    text = f"{hbold('💎 Всего сбережений:')} {hbold(total_str)} ₽\n\n"

    if deposits_total > 0:
        text += f"💰 Вклады: {deposits_total:,.2f} ₽\n".replace(",", " ")
    if cash_total > 0:
        text += f"💵 Кэш: {cash_total:,.2f} ₽\n".replace(",", " ")

    text += f"\n📊 Всего активов: {len(assets)}"

    if expired_deposits > 0:
        text += f"\n⚠️ Просроченных вкладов: {expired_deposits}"

    # Кнопки для навигации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список", callback_data="list"),
            InlineKeyboardButton(text="➕ Новый", callback_data="new")
        ]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
async def show_assets_list(message: Message, user_id: int):
    """Общая функция для показа списка активов"""
    logger.debug(f"показать список: пользователь {user_id}")

    assets = await db.get_user_assets(user_id)

    if not assets:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать первый актив", callback_data="new")]
        ])
        await message.answer(
            f"{hbold('📭 У тебя пока нет активов')}\n\n"
            f"Создай первый актив командой {hcode('/new')}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Формируем список активов с нумерацией
    text = f"{hbold('📋 Твои активы:')}\n\n"

    for idx, asset in enumerate(assets, 1):
        # Эмодзи в зависимости от типа
        if asset['type'] == 'deposit':
            emoji = "💰"
        elif asset['type'] == 'cash':
            emoji = "💵"
        elif asset['type'] == 'currency':
            emoji = "💱"
        elif asset['type'] == 'metal':
            emoji = "🥇"
        else:
            emoji = "📊"

        # Форматируем сумму
        amount = asset['current_amount']
        amount_str = f"{amount:,.2f}".replace(",", " ")

        # Основная строка с номером
        text += f"{idx}. {emoji} {hbold(asset['name'])}: {amount_str} ₽"

        # Добавляем процентную ставку если есть
        if asset.get('interest_rate'):
            text += f" ({hbold(f'{asset["interest_rate"]}%')})"

        # Добавляем доход если есть
        if amount > asset['start_amount']:
            profit = amount - asset['start_amount']
            profit_str = f"+{profit:,.2f}".replace(",", " ")
            text += f" 📈 {profit_str} ₽"

        # Добавляем дату окончания если есть
        if asset.get('end_date'):
            try:
                end_date = datetime.strptime(asset['end_date'], '%Y-%m-%d')
                today = datetime.now()

                if end_date < today:
                    text += f" ⚠️ ПРОСРОЧЕН!"
                else:
                    days_left = (end_date - today).days
                    text += f" 📅 {days_left} дн."
            except:
                text += f" 📅 до {asset['end_date']}"

        text += "\n"

    # Создаем клавиатуру с кнопками для каждого актива
    keyboard_buttons = []

    # Добавляем кнопки для каждого актива (максимум 2 в ряд)
    for idx, asset in enumerate(assets, 1):
        short_name = asset['name'][:10] + "..." if len(asset['name']) > 10 else asset['name']
        keyboard_buttons.append(
            InlineKeyboardButton(
                text=f"❌ {idx}. {short_name}",
                callback_data=f"del_{asset['id']}"
            )
        )

    # Разбиваем на ряды по 2 кнопки
    keyboard_rows = []
    for i in range(0, len(keyboard_buttons), 2):
        row = keyboard_buttons[i:i + 2]
        keyboard_rows.append(row)

    # Добавляем кнопку "Удалить все" и навигацию
    keyboard_rows.append([
        InlineKeyboardButton(text="🗑 Удалить все", callback_data="del_all"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_list")
    ])

    keyboard_rows.append([
        InlineKeyboardButton(text="💰 Баланс", callback_data="total"),
        InlineKeyboardButton(text="➕ Новый", callback_data="new")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")