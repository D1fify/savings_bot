from datetime import datetime, date
import math


def calculate_deposit(amount: float, rate: float, start_date, current_date=None):
    """
    Расчет суммы вклада с капитализацией процентов

    Формула: amount * (1 + rate/100/365)^количество_дней

    Args:
        amount: начальная сумма
        rate: годовая процентная ставка (%)
        start_date: дата начала вклада (datetime или str)
        current_date: дата расчета (если None - сегодня)

    Returns:
        float: текущая сумма с процентами
    """
    if rate == 0 or rate is None:
        return amount

    # Преобразуем даты
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if current_date is None:
        current_date = datetime.now().date()
    elif isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d').date()

    # Количество дней
    days = (current_date - start_date).days

    if days <= 0:
        return amount

    # Формула сложных процентов
    daily_rate = rate / 100 / 365  # дневная ставка в долях
    result = amount * ((1 + daily_rate) ** days)

    return round(result, 2)


def calculate_profit(amount: float, rate: float, start_date, current_date=None):
    """
    Расчет только дохода (без начальной суммы)
    """
    current = calculate_deposit(amount, rate, start_date, current_date)
    return round(current - amount, 2)


def days_between(start_date, end_date=None):
    """Количество дней между датами"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if end_date is None:
        end_date = datetime.now().date()
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    return (end_date - start_date).days