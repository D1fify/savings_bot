from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from database import db
from datetime import datetime, timedelta
import asyncio

router = Router()


class NewAsset(StatesGroup):
    type = State()
    name = State()
    amount = State()
    rate = State()
    start_date = State()
    end_date = State()


# Вспомогательная функция для удаления старых сообщений
async def delete_previous_messages(message: Message, state: FSMContext):
    """Удаляет предыдущие сообщения из диалога"""
    data = await state.get_data()

    if 'last_bot_message_id' in data:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=data['last_bot_message_id']
            )
        except:
            pass

    if 'last_user_message_id' in data:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=data['last_user_message_id']
            )
        except:
            pass


async def safe_delete(message: Message, message_id: int = None):
    """Безопасное удаление сообщения"""
    try:
        if message_id:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message_id
            )
        else:
            await message.delete()
    except:
        pass


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    # Очищаем предыдущее состояние
    await state.clear()

    # Удаляем команду /new
    await safe_delete(message)

    # 👇 ИСПРАВЛЕНО: сохраняем правильный user_id
    await state.update_data(user_id=message.chat.id)  # вместо message.from_user.id

    # ... остальной код

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Вклад", callback_data="type_deposit"),
            InlineKeyboardButton(text="💵 Кэш", callback_data="type_cash")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

    sent_msg = await message.answer(
        "Выбери тип актива:",
        reply_markup=keyboard
    )

    await state.update_data(
        first_message_id=sent_msg.message_id,
        last_bot_message_id=sent_msg.message_id
    )
    await state.set_state(NewAsset.type)


@router.callback_query(NewAsset.type, F.data.startswith("type_"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    asset_type = callback.data.replace("type_", "")
    await state.update_data(type=asset_type)

    await safe_delete(callback.message)

    sent_msg = await callback.message.answer("📝 Введи название актива:")

    await state.update_data(last_bot_message_id=sent_msg.message_id)
    await state.set_state(NewAsset.name)
    await callback.answer()


@router.message(NewAsset.name, F.text)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Название должно быть от 2 до 50 символов.")
        return

    await delete_previous_messages(message, state)
    await state.update_data(name=name)

    sent_msg = await message.answer("💰 Введи начальную сумму:")

    await state.update_data(
        last_bot_message_id=sent_msg.message_id,
        last_user_message_id=message.message_id
    )
    await state.set_state(NewAsset.amount)


@router.message(NewAsset.amount, F.text)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введи число (например: 100000)")
        return

    await delete_previous_messages(message, state)
    await state.update_data(amount=amount)
    data = await state.get_data()

    if data['type'] == 'deposit':
        sent_msg = await message.answer("📈 Введи процентную ставку: \nНапример, 13.5")
        await state.set_state(NewAsset.rate)
    else:
        # Для кэша - только дата начала
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="start_date_today")]
        ])
        sent_msg = await message.answer(
            "📅 Введи дату начала (ДД.ММ.ГГГГ):",
            reply_markup=keyboard
        )
        await state.update_data(rate=None)
        await state.set_state(NewAsset.start_date)

    await state.update_data(
        last_bot_message_id=sent_msg.message_id,
        last_user_message_id=message.message_id
    )


@router.message(NewAsset.rate, F.text)
async def process_rate(message: Message, state: FSMContext):
    try:
        rate = float(message.text.strip().replace(',', '.'))
        if rate < 0 or rate > 100:
            await message.answer("❌ Ставка должна быть от 0 до 100%")
            return
    except ValueError:
        await message.answer("❌ Введи число (например: 8.5)")
        return

    await delete_previous_messages(message, state)
    await state.update_data(rate=rate)

    # Для вклада - сначала дата начала
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="start_date_today")]
    ])
    sent_msg = await message.answer(
        "📅 Введи дату начала (ДД.ММ.ГГГГ):",
        reply_markup=keyboard
    )

    await state.update_data(
        last_bot_message_id=sent_msg.message_id,
        last_user_message_id=message.message_id
    )
    await state.set_state(NewAsset.start_date)


# Обработка даты начала (кнопка Сегодня)
@router.callback_query(NewAsset.start_date, F.data == "start_date_today")
async def process_start_date_today(callback: CallbackQuery, state: FSMContext):
    today = datetime.now().strftime('%Y-%m-%d')
    await state.update_data(start_date=today)

    await safe_delete(callback.message)

    # После даты начала - запрашиваем дату окончания (только для вклада)
    data = await state.get_data()
    if data['type'] == 'deposit':
        await ask_end_date(callback.message, state)
    else:
        # Для кэша сразу сохраняем
        await save_asset(callback.message, state)

    await callback.answer()


# Обработка даты начала (текст)
@router.message(NewAsset.start_date, F.text)
async def process_start_date_text(message: Message, state: FSMContext):
    try:
        date_text = message.text.strip()
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                parsed = datetime.strptime(date_text, fmt)
                date_str = parsed.strftime('%Y-%m-%d')
                break
            except:
                continue
        else:
            await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
            return
    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
        return

    await delete_previous_messages(message, state)
    await state.update_data(start_date=date_str, last_user_message_id=message.message_id)

    # После даты начала - запрашиваем дату окончания (только для вклада)
    data = await state.get_data()
    if data['type'] == 'deposit':
        await ask_end_date(message, state)
    else:
        # Для кэша сразу сохраняем
        await save_asset(message, state)


async def ask_end_date(message: Message, state: FSMContext):
    """Запрос даты окончания вклада"""
    # Рассчитываем дату через год по умолчанию
    default_end = (datetime.now() + timedelta(days=365)).strftime('%d.%m.%Y')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Через год", callback_data="end_date_year")],
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="end_date_skip")]
    ])

    sent_msg = await message.answer(
        f"📅 Введи дату окончания вклада (ДД.ММ.ГГГГ)\n\n"
        f"Рекомендуемая: {default_end}\n"
        f"Если не знаешь - нажми 'Пропустить'",
        reply_markup=keyboard
    )

    await state.update_data(last_bot_message_id=sent_msg.message_id)
    await state.set_state(NewAsset.end_date)


# Обработка даты окончания (кнопка "Через год")
@router.callback_query(NewAsset.end_date, F.data == "end_date_year")
async def process_end_date_year(callback: CallbackQuery, state: FSMContext):
    end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    await state.update_data(end_date=end_date)

    await safe_delete(callback.message)

    # 👈 ВАЖНО: передаем правильный user_id
    data = await state.get_data()
    user_id = data.get('user_id') or callback.from_user.id
    await save_asset(callback.message, state)
    await callback.answer()


# Обработка даты окончания (кнопка "Пропустить")
@router.callback_query(NewAsset.end_date, F.data == "end_date_skip")
async def process_end_date_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(end_date=None)

    await safe_delete(callback.message)

    # 👈 ВАЖНО: передаем правильный user_id
    data = await state.get_data()
    user_id = data.get('user_id') or callback.from_user.id
    await save_asset(callback.message, state)
    await callback.answer()


# Обработка даты окончания (текст)
@router.message(NewAsset.end_date, F.text)
async def process_end_date_text(message: Message, state: FSMContext):
    try:
        date_text = message.text.strip()
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                parsed = datetime.strptime(date_text, fmt)
                date_str = parsed.strftime('%Y-%m-%d')
                break
            except:
                continue
        else:
            await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
            return

        # Проверяем, что дата окончания позже даты начала
        data = await state.get_data()
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        if parsed <= start_date:
            await message.answer("❌ Дата окончания должна быть позже даты начала")
            return

    except:
        await message.answer("❌ Неверный формат. Используй ДД.ММ.ГГГГ")
        return

    await delete_previous_messages(message, state)
    await state.update_data(end_date=date_str, last_user_message_id=message.message_id)
    await save_asset(message, state)


async def save_asset(message: Message, state: FSMContext):
    data = await state.get_data()

    # 👇 ИСПРАВЛЕНО: берем user_id из chat_id, а не из message.from_user.id
    user_id = message.chat.id  # ВСЕГДА правильный ID пользователя

    print(f"\n{'=' * 50}")
    print(f"💾 СОХРАНЕНИЕ АКТИВА")
    print(f"  user_id из chat.id: {user_id}")  # Должен быть 854697538
    print(f"  data: {data}")

    try:
        # Добавляем актив
        asset_id = await db.add_asset(
            user_id=user_id,  # 👈 используем правильный ID
            name=data['name'],
            asset_type=data['type'],
            start_amount=data['amount'],
            interest_rate=data.get('rate'),
            currency='RUB',
            end_date=data.get('end_date')
        )

        if not asset_id:
            await message.answer("❌ Ошибка при сохранении в БД")
            await state.clear()
            return

        # Удаляем все сообщения диалога
        if 'first_message_id' in data:
            await safe_delete(message, data['first_message_id'])
        if 'last_bot_message_id' in data:
            await safe_delete(message, data['last_bot_message_id'])
        if 'last_user_message_id' in data:
            await safe_delete(message, data['last_user_message_id'])

        # Формируем сообщение об успехе
        result_text = (
            f"{hbold('✅ Актив создан!')}\n\n"
            f"💰 {data['name']}\n"
            f"💵 {data['amount']:,.2f} ₽"
        )

        if data.get('rate'):
            result_text += f"\n📈 {data['rate']}%"

        # Добавляем дату окончания если есть
        if data.get('end_date'):
            end_date_formatted = datetime.strptime(data['end_date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            result_text += f"\n📅 До: {end_date_formatted}"

        await message.answer(result_text, parse_mode="HTML")

    except Exception as e:
        print(f"❌ Ошибка в save_asset: {e}")
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if 'first_message_id' in data:
        await safe_delete(callback.message, data['first_message_id'])
    if 'last_bot_message_id' in data:
        await safe_delete(callback.message, data['last_bot_message_id'])

    await safe_delete(callback.message)
    await state.clear()

    await callback.message.answer("❌ Создание актива отменено")
    await callback.answer()