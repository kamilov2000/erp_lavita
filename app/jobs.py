import datetime
import logging

from sqlalchemy import func, types

from app.base import session
from app.choices import DaysOfWeekShort, WorkScheduleStatus
from app.finance.models import Counterparty
from app.user.models import User, WorkingDay, WorkSchedule
from app.utils.func import sql_exception_handler

logger = logging.getLogger(__name__)


@sql_exception_handler
def scheduled_auto_charge_task():
    current_date = datetime.datetime.now().date()
    logger.info("Starts scheduled_auto_charge_task!")
    counterparties = Counterparty.query.filter(
        Counterparty.auto_charge == True,
        # Проверяем, что текущая дата меньше или равна дате создания + месяцы начисления
        func.date(
            Counterparty.created_at
            + func.cast(
                func.concat(Counterparty.charge_period_months, " months"),
                types.Interval,
            )
        )
        >= current_date,
    ).all()

    for counterparty in counterparties:
        transaction = counterparty.create_auto_charge_transaction(
            month=counterparty.created_at.month,
            year=counterparty.created_at.year,
            n=counterparty.charge_period_months,
        )
        session.add(transaction)
    session.commit()


@sql_exception_handler
def create_working_days_for_all_staff_task():
    all_staff = session.query(User).all()

    # Получаем текущее строковое представление дня недели в формате 'MONDAY', 'TUESDAY' и т.д.
    today_string = datetime.datetime.today().strftime("%a").upper()

    today_date = datetime.date.today()

    # Преобразуем строку в элемент перечисления DaysOfWeekShort
    today_enum = DaysOfWeekShort[today_string]

    for user in all_staff:
        # Получаем график работы из DaysOfWeekShort для каждого сотрудника
        working_day = (
            session.query(WorkingDay)
            .filter(WorkingDay.user == user, WorkingDay.day_of_week == today_enum)
            .first()
        )

        existing_schedule = (
            session.query(WorkSchedule)
            .filter(
                WorkSchedule.user == user,
                WorkSchedule.date == today_date,
            )
            .first()
        )
        data = {}
        if not existing_schedule:
            if working_day:
                # Создаем рабочий день на основе графика
                data["working_day_id"] = working_day.id
                data["status"] = (
                    WorkScheduleStatus.DAY_OFF
                    if not working_day.is_working_day
                    else None
                )

            working_schedule = WorkSchedule(
                user=user,
                date=today_date,
                working_day_id=data.get("working_day_id"),
                status=data.get("status"),
            )

            session.add(working_schedule)

    session.commit()
