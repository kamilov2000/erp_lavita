import datetime

from sqlalchemy import func, types

from app.base import session
from app.choices import DaysOfWeek
from app.finance.models import Counterparty
from app.user.models import User, WorkingDay, WorkSchedule
from app.utils.func import sql_exception_handler


@sql_exception_handler
def scheduled_auto_charge_task():
    current_date = datetime.datetime.now().date()

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
        transaction = counterparty.create_auto_charge_transaction()
        session.add(transaction)
    session.commit()


@sql_exception_handler
def create_working_days_for_all_staff_task():
    all_staff = session.query(User).all()

    # Получаем текущее строковое представление дня недели в формате 'MONDAY', 'TUESDAY' и т.д.
    today_string = datetime.datetime.today().strftime("%A").upper()

    today_date = datetime.date.today()

    # Преобразуем строку в элемент перечисления DaysOfWeek
    today_enum = DaysOfWeek[today_string]

    for user in all_staff:
        # Получаем график работы из DaysOfWeek для каждого сотрудника
        working_day = (
            session.query(WorkingDay)
            .filter(WorkingDay.user == user, WorkingDay.day_of_week == today_enum)
            .first()
        )

        # Проверяем, что запись для этого дня еще не создана
        existing_schedule = (
            session.query(WorkSchedule)
            .filter(
                WorkSchedule.user == user,
                WorkSchedule.date == today_date,
                WorkSchedule.working_day_id == working_day.id,
            )
            .first()
        )

        if not existing_schedule:
            # Создаем рабочий день на основе графика
            working_schedule = WorkSchedule(
                user=user, date=today_date, working_day_id=working_day.id
            )

            # Добавляем партнеров из графика
            working_day.partners.extend(working_day.partners)

            session.add(working_schedule)

        session.commit()
