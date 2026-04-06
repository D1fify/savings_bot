from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hcode
from database import db
from datetime import datetime  # 👈 ЭТОТ ИМПОРТ

router = Router()


# Вспомогательная функция для поиска актива по названию
async def find_asset(user_id: int, name: str):
    assets = await db.get_user_assets(user_id)
    for asset in assets:
        if asset['name'].lower() == name.lower():
            return asset
    return None


# /add - пополнение
@router.message(Command("add"))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            f"{hbold('❌ Неправильный формат')}\n\n"
            f"Используй: {hcode('/add <сумма> <название>')}\n"
            f"Пример: {hcode('/add 25000 СберВклад')}",
            parse_mode="HTML"
        )
        return

    try:
        amount_str = parts[1].replace(' ', '').replace(',', '.')
        amount = float(amount_str)

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        if amount > 10_000_000:
            await message.answer("❌ Слишком большая сумма (макс. 10 000 000)")
            return
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Пример: 25000 или 1500.50")
        return

    asset_name = parts[2].strip()
    asset = await find_asset(user_id, asset_name)

    if not asset:
        await message.answer(
            f"❌ Актив '{asset_name}' не найден.\n\n"
            f"Используй {hcode('/list')} чтобы увидеть все активы",
            parse_mode="HTML"
        )
        return

    try:
        await db.add_transaction(asset['id'], 'add', amount)

        # Получаем обновленный актив
        updated_assets = await db.get_user_assets(user_id)
        updated_asset = next((a for a in updated_assets if a['id'] == asset['id']), None)

        if updated_asset:
            new_amount = updated_asset['current_amount']

            await message.answer(
                f"{hbold('✅ Актив пополнен!')}\n\n"
                f"{hbold(asset['name'])}\n"
                f"➕ Пополнение: +{amount:,.2f} ₽\n"
                f"💰 Новый баланс: {new_amount:,.2f} ₽",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# /take - снятие
@router.message(Command("take"))
async def cmd_take(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            f"{hbold('❌ Неправильный формат')}\n\n"
            f"Используй: {hcode('/take <сумма> <название>')}\n"
            f"Пример: {hcode('/take 10000 Заначка')}",
            parse_mode="HTML"
        )
        return

    try:
        amount_str = parts[1].replace(' ', '').replace(',', '.')
        amount = float(amount_str)

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Пример: 10000 или 1500.50")
        return

    asset_name = parts[2].strip()
    asset = await find_asset(user_id, asset_name)

    if not asset:
        await message.answer(
            f"❌ Актив '{asset_name}' не найден.\n\n"
            f"Используй {hcode('/list')} чтобы увидеть все активы",
            parse_mode="HTML"
        )
        return

    # Проверяем достаточно ли средств
    if asset['current_amount'] < amount:
        await message.answer(
            f"❌ Недостаточно средств\n\n"
            f"Доступно: {asset['current_amount']:,.2f} ₽\n"
            f"Запрошено: {amount:,.2f} ₽",
            parse_mode="HTML"
        )
        return

    try:
        await db.add_transaction(asset['id'], 'take', amount)

        # Получаем обновленный актив
        updated_assets = await db.get_user_assets(user_id)
        updated_asset = next((a for a in updated_assets if a['id'] == asset['id']), None)

        if updated_asset:
            new_amount = updated_asset['current_amount']

            await message.answer(
                f"{hbold('✅ Средства сняты!')}\n\n"
                f"{hbold(asset['name'])}\n"
                f"➖ Снятие: -{amount:,.2f} ₽\n"
                f"💰 Новый баланс: {new_amount:,.2f} ₽",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# /del - удаление актива
@router.message(Command("del"))
async def cmd_del(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            f"{hbold('❌ Неправильный формат')}\n\n"
            f"Используй: {hcode('/del <название>')}\n"
            f"Пример: {hcode('/del СберВклад')}",
            parse_mode="HTML"
        )
        return

    asset_name = parts[1].strip()

    # Ищем актив
    asset = await find_asset(user_id, asset_name)

    if not asset:
        await message.answer(
            f"❌ Актив '{asset_name}' не найден.\n\n"
            f"Используй {hcode('/list')} чтобы увидеть все активы",
            parse_mode="HTML"
        )
        return

    # Кнопки подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{asset['id']}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_del")
        ]
    ])

    await message.answer(
        f"{hbold('⚠️ Подтверждение удаления')}\n\n"
        f"Ты действительно хочешь удалить актив?\n\n"
        f"{hbold(asset['name'])}\n"
        f"Тип: {'💰 Вклад' if asset['type'] == 'deposit' else '💵 Кэш'}\n"
        f"Баланс: {asset['current_amount']:,.2f} ₽\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# Подтверждение удаления
@router.callback_query(F.data.startswith("confirm_del_"))
async def confirm_delete(callback: CallbackQuery):
    await callback.answer()

    asset_id = int(callback.data.replace("confirm_del_", ""))
    user_id = callback.from_user.id

    try:
        # Получаем информацию об активе до удаления
        assets = await db.get_user_assets(user_id)
        asset = next((a for a in assets if a['id'] == asset_id), None)

        if not asset:
            await callback.message.edit_text("❌ Актив не найден")
            return

        # Сохраняем данные для сообщения
        asset_name = asset['name']
        asset_amount = asset['current_amount']

        # 👇 ИСПОЛЬЗУЕМ НОВЫЙ МЕТОД ИЗ db.py
        await db.delete_asset(asset_id)

        await callback.message.edit_text(
            f"{hbold('✅ Актив удален')}\n\n"
            f"{asset_name} - {asset_amount:,.2f} ₽",
            parse_mode="HTML"
        )

    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при удалении: {e}")


# Отмена удаления
@router.callback_query(F.data == "cancel_del")
async def cancel_delete(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("✅ Удаление отменено")