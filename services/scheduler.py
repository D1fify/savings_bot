from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from database import db
from aiogram import Bot
import logging

logger = logging.getLogger(__name__)


class MonthlyReportScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def calculate_deposit_interest(self, asset):
        """Рассчитывает начисленные проценты за месяц"""
        if not asset['interest_rate'] or asset['type'] != 'deposit':
            return 0

        # Простой расчет: сумма * (ставка/100) / 12 месяцев
        monthly_rate = asset['interest_rate'] / 100 / 12
        interest = asset['current_amount'] * monthly_rate
        return round(interest, 2)

    async def send_monthly_report(self):
        """Отправляет ежемесячный отчет всем пользователям"""
        logger.info("📊 Запуск ежемесячного отчета")

        # Получаем всех пользователей
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT user_id FROM users")
            users = await cursor.fetchall()

        for user in users:
            user_id = user['user_id']
            await self.send_report_to_user(user_id)

    async def send_report_to_user(self, user_id: int):
        """Отправляет отчет конкретному пользователю"""
        try:
            # Получаем активы пользователя
            assets = await db.get_user_assets(user_id)

            if not assets:
                return

            # Собираем статистику
            total_balance = 0
            total_interest = 0
            deposits_data = []

            for asset in assets:
                total_balance += asset['current_amount']

                # Считаем проценты для вкладов
                if asset['type'] == 'deposit' and asset['interest_rate']:
                    interest = await self.calculate_deposit_interest(asset)
                    total_interest += interest

                    # Добавляем в список для детального показа
                    deposits_data.append({
                        'name': asset['name'],
                        'amount': asset['current_amount'],
                        'rate': asset['interest_rate'],
                        'interest': interest
                    })

                    # Записываем начисление процентов как транзакцию
                    try:
                        await db.add_transaction(
                            asset_id=asset['id'],
                            transaction_type='interest',
                            amount=interest,
                            description='Ежемесячное начисление %'
                        )
                    except:
                        pass

            # Формируем сообщение
            current_month = datetime.now().strftime('%B %Y')
            text = (
                f"📊 <b>Ежемесячный отчет за {current_month}</b>\n\n"
                f"💰 <b>Общий баланс:</b> {total_balance:,.2f} ₽\n"
            )

            if total_interest > 0:
                text += f"📈 <b>Начислено процентов:</b> +{total_interest:,.2f} ₽\n\n"

                # Детали по вкладам
                text += "<b>Детали по вкладам:</b>\n"
                for dep in deposits_data:
                    text += f"• {dep['name']}: {dep['amount']:,.2f} ₽ ({dep['rate']}%)\n"
                    text += f"  ➕ Начислено: +{dep['interest']:,.2f} ₽\n"
            else:
                text += "\n💡 У тебя пока нет вкладов с процентами"

            # Добавляем мотивацию
            if total_balance > 0:
                if total_balance < 100000:
                    text += "\n\n🚀 До 100 000 осталось: {:.2f} ₽".format(100000 - total_balance)
                elif total_balance < 500000:
                    text += "\n\n🎯 До 500 000 осталось: {:.2f} ₽".format(500000 - total_balance)
                elif total_balance < 1000000:
                    text += "\n\n💪 До миллиона осталось: {:.2f} ₽".format(1000000 - total_balance)
                else:
                    text += "\n\n🏆 Ты миллионер! Отличный результат!"

            # Отправляем
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML"
            )

            logger.info(f"✅ Отчет отправлен пользователю {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки отчета пользователю {user_id}: {e}")

    async def check_expiring_deposits(self):
        """Проверка приближающихся и просроченных вкладов"""
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute('''
                SELECT * FROM assets 
                WHERE type = 'deposit' AND end_date IS NOT NULL
            ''')
            deposits = await cursor.fetchall()

        for deposit in deposits:
            user_id = deposit['user_id']
            end_date = datetime.strptime(deposit['end_date'], '%Y-%m-%d')
            today = datetime.now()
            days_left = (end_date - today).days

            # Если вклад просрочен
            if days_left < 0:
                await self.bot.send_message(
                    user_id,
                    f"⚠️ {hbold('ВНИМАНИЕ!')}\n\n"
                    f"Вклад '{deposit['name']}' просрочен на {abs(days_left)} дней!\n"
                    f"Требуется переоформление.",
                    parse_mode="HTML"
                )
            # Если осталось меньше 7 дней
            elif 0 <= days_left <= 7:
                await self.bot.send_message(
                    user_id,
                    f"📅 {hbold('Напоминание')}\n\n"
                    f"Вклад '{deposit['name']}' заканчивается через {days_left} дней.\n"
                    f"Не забудь переоформить!",
                    parse_mode="HTML"
                )
    def start(self):
        """Запускает планировщик"""
        # Отправка каждый месяц 1-го числа в 09:00
        self.scheduler.add_job(
            self.send_monthly_report,
            CronTrigger(day=1, hour=9, minute=0),
            id='monthly_report'
        )
        self.scheduler.start()
        logger.info("✅ Планировщик ежемесячных отчетов запущен")