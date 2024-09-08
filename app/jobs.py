from datetime import datetime

from sqlalchemy import func, types
from app.finance.models import Counterparty
from app.base import session
from app.utils.func import sql_exception_handler


@sql_exception_handler
def scheduled_auto_charge_task():
    current_date = datetime.now().date()

    counterparties = Counterparty.query \
        .filter(
        Counterparty.auto_charge == True,
        # Проверяем, что текущая дата меньше или равна дате создания + месяцы начисления
        func.date(Counterparty.created_at + func.cast(func.concat(Counterparty.charge_period_months, ' months'),
                                                      types.Interval)) >= current_date
    ) \
        .all()

    for counterparty in counterparties:
        transaction = counterparty.create_auto_charge_transaction()
        session.add(transaction)
    session.commit()
