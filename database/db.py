import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path
from services.calculator import calculate_deposit


class AsyncDatabaseManager:
    """Асинхронный менеджер базы данных для Telegram бота"""

    def __init__(self, db_path='savings.db'):
        self.db_path = str(Path(db_path).absolute())
        print(f"📁 БД: {self.db_path}")

    async def init_database(self):
        """Инициализация таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица активов (базовая структура)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    type TEXT,
                    currency TEXT DEFAULT 'RUB',
                    start_amount REAL,
                    start_date DATE,
                    interest_rate REAL,
                    current_amount REAL,
                    last_updated DATE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # Таблица транзакций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER,
                    type TEXT CHECK(type IN ('add', 'take', 'interest', 'correction')),
                    amount REAL,
                    description TEXT,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (asset_id) REFERENCES assets(id)
                )
            ''')

            await db.commit()
            print("✅ Базовая структура создана")

            # Добавляем колонку end_date если её нет
            await self._add_end_date_column()

            # Обновляем проценты при запуске
            await self.update_all_deposits()

            print("✅ База данных полностью готова")

    async def _add_end_date_column(self):
        """Добавление колонки end_date в таблицу assets если её нет"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, какие колонки есть в таблице
            cursor = await db.execute("PRAGMA table_info(assets)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            print("📊 Существующие колонки:", column_names)

            # Если колонки end_date нет - добавляем
            if 'end_date' not in column_names:
                try:
                    await db.execute("ALTER TABLE assets ADD COLUMN end_date DATE")
                    await db.commit()
                    print("✅ Колонка end_date добавлена в таблицу assets")
                except Exception as e:
                    print(f"⚠️ Ошибка при добавлении колонки: {e}")
            else:
                print("✅ Колонка end_date уже существует")

    async def add_user(self, user_id, username=None):
        """Добавление пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            await db.commit()

    async def add_asset(self, user_id, name, asset_type, start_amount,
                        interest_rate=None, currency='RUB', end_date=None):
        """Добавление актива"""
        start_date = datetime.now().strftime('%Y-%m-%d')

        # Сразу рассчитываем текущую сумму с процентами
        if asset_type == 'deposit' and interest_rate:
            current_amount = calculate_deposit(
                start_amount,
                interest_rate,
                start_date
            )
        else:
            current_amount = start_amount

        async with aiosqlite.connect(self.db_path) as db:
            # Сначала проверяем, есть ли колонка end_date
            cursor = await db.execute("PRAGMA table_info(assets)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if 'end_date' in column_names:
                # Если есть колонка end_date - используем полный INSERT
                cursor = await db.execute('''
                    INSERT INTO assets 
                    (user_id, name, type, currency, start_amount, start_date, end_date, 
                     interest_rate, current_amount, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, name, asset_type, currency, start_amount,
                    start_date, end_date, interest_rate, current_amount, start_date
                ))
            else:
                # Если нет колонки end_date - INSERT без неё
                cursor = await db.execute('''
                    INSERT INTO assets 
                    (user_id, name, type, currency, start_amount, start_date, 
                     interest_rate, current_amount, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, name, asset_type, currency, start_amount,
                    start_date, interest_rate, current_amount, start_date
                ))

            await db.commit()
            return cursor.lastrowid

    async def get_user_assets(self, user_id):
        """Получение активов пользователя с пересчетом процентов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Получаем все колонки, которые есть в таблице
            cursor = await db.execute("PRAGMA table_info(assets)")
            columns_info = await cursor.fetchall()
            all_columns = [col[1] for col in columns_info]

            # Формируем SELECT запрос со всеми существующими колонками
            columns_str = ", ".join(all_columns)

            cursor = await db.execute(f'''
                SELECT {columns_str} FROM assets WHERE user_id = ?
            ''', (user_id,))
            rows = await cursor.fetchall()

            # Преобразуем Row в dict
            assets = []
            for row in rows:
                asset = dict(row)
                # Преобразуем числовые поля
                if asset.get('start_amount'):
                    asset['start_amount'] = float(asset['start_amount'])
                if asset.get('current_amount'):
                    asset['current_amount'] = float(asset['current_amount'])
                if asset.get('interest_rate'):
                    asset['interest_rate'] = float(asset['interest_rate'])
                assets.append(asset)

            # Пересчитываем проценты для каждого вклада
            today = datetime.now().strftime('%Y-%m-%d')
            for asset in assets:
                if asset.get('type') == 'deposit' and asset.get('interest_rate'):
                    # Пересчитываем с учетом последней операции
                    new_amount = calculate_deposit(
                        asset['start_amount'],
                        asset['interest_rate'],
                        asset['start_date']
                    )

                    # Если сумма изменилась, обновляем в БД
                    if abs(new_amount - asset['current_amount']) > 0.01:
                        asset['current_amount'] = new_amount
                        await db.execute('''
                            UPDATE assets 
                            SET current_amount = ?, last_updated = ?
                            WHERE id = ?
                        ''', (new_amount, today, asset['id']))
                        await db.commit()

            return assets

    async def add_transaction(self, asset_id: int, transaction_type: str, amount: float):
        """Добавление транзакции и обновление баланса"""
        if transaction_type not in ['add', 'take']:
            raise ValueError("transaction_type должен быть 'add' или 'take'")

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Получаем все колонки, которые есть в таблице
            cursor = await db.execute("PRAGMA table_info(assets)")
            columns_info = await cursor.fetchall()
            all_columns = [col[1] for col in columns_info]

            # Формируем SELECT запрос
            columns_str = ", ".join(all_columns)

            cursor = await db.execute(f'''
                SELECT {columns_str} FROM assets WHERE id = ?
            ''', (asset_id,))
            row = await cursor.fetchone()

            if not row:
                raise ValueError("Актив не найден")

            # Преобразуем Row в dict
            asset = dict(row)

            # Преобразуем числовые поля
            if asset.get('start_amount'):
                asset['start_amount'] = float(asset['start_amount'])
            if asset.get('current_amount'):
                asset['current_amount'] = float(asset['current_amount'])
            if asset.get('interest_rate'):
                asset['interest_rate'] = float(asset['interest_rate'])

            # Добавляем транзакцию
            await db.execute('''
                INSERT INTO transactions (asset_id, type, amount)
                VALUES (?, ?, ?)
            ''', (asset_id, transaction_type, amount))

            # Обновляем начальную сумму
            sign = 1 if transaction_type == 'add' else -1
            new_start_amount = asset['start_amount'] + (sign * amount)

            # Пересчитываем текущую сумму
            today = datetime.now().strftime('%Y-%m-%d')

            if asset['type'] == 'deposit' and asset.get('interest_rate'):
                new_current = calculate_deposit(
                    new_start_amount,
                    asset['interest_rate'],
                    today
                )
            else:
                new_current = asset['current_amount'] + (sign * amount)

            # Обновляем актив
            await db.execute('''
                UPDATE assets 
                SET start_amount = ?,
                    current_amount = ?,
                    last_updated = ?,
                    start_date = ?
                WHERE id = ?
            ''', (new_start_amount, new_current, today, today, asset_id))

            await db.commit()

    async def delete_asset(self, asset_id: int):
        """Удаление актива по ID"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Удаляем связанные транзакции
            await conn.execute("DELETE FROM transactions WHERE asset_id = ?", (asset_id,))
            # Удаляем сам актив
            await conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            await conn.commit()
        return True

    async def delete_asset_by_name(self, user_id: int, asset_name: str):
        """Удаление актива по названию"""
        try:
            assets = await self.get_user_assets(user_id)
            asset = next((a for a in assets if a['name'].lower() == asset_name.lower()), None)

            if not asset:
                return False, "Актив не найден"

            await self.delete_asset(asset['id'])
            return True, f"Актив '{asset_name}' удален"

        except Exception as e:
            return False, str(e)

    async def update_all_deposits(self):
        """Обновить проценты по всем вкладам"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Получаем все колонки, которые есть в таблице
            cursor = await db.execute("PRAGMA table_info(assets)")
            columns_info = await cursor.fetchall()
            all_columns = [col[1] for col in columns_info]

            # Формируем SELECT запрос
            columns_str = ", ".join(all_columns)

            cursor = await db.execute(f'''
                SELECT {columns_str} FROM assets WHERE type = 'deposit' AND interest_rate IS NOT NULL
            ''')
            rows = await cursor.fetchall()

            today = datetime.now().strftime('%Y-%m-%d')
            updated = 0

            for row in rows:
                asset = dict(row)

                # Преобразуем в числа
                start_amount = float(asset['start_amount']) if asset['start_amount'] else 0
                current_amount = float(asset['current_amount']) if asset['current_amount'] else 0
                interest_rate = float(asset['interest_rate']) if asset['interest_rate'] else None
                start_date = asset['start_date']
                asset_id = asset['id']

                if interest_rate:
                    new_amount = calculate_deposit(
                        start_amount,
                        interest_rate,
                        start_date
                    )

                    if abs(new_amount - current_amount) > 0.01:
                        await db.execute('''
                            UPDATE assets 
                            SET current_amount = ?, last_updated = ?
                            WHERE id = ?
                        ''', (new_amount, today, asset_id))
                        updated += 1

            if updated > 0:
                await db.commit()
                print(f"📈 Обновлено {updated} вкладов")