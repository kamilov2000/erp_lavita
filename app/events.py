from flask import current_app, g
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.base import Base, engine, session
from app.choices import CrudOperations
from app.finance.models import (
    CashRegister,
    CashRegisterHistory,
    Counterparty,
    CounterpartyHistory,
    Transaction,
    TransactionHistory,
)
from app.user.models import Department, DepartmentHistory, User, UserHistory

Session = sessionmaker(bind=engine)


def create_history_data(model: Base, action, target, extra_fields):
    res = {
        "model": model,
        "data": {
            "user_id": g.user.id if hasattr(g, "user") else None,
            "operation_status": action,
            "data": target.get_temp_data("history_data"),
            "user_full_name": g.user.full_name if hasattr(g, "user") else None,
        },
    }
    target.clear_temp_data()
    # merge two default history data with extra
    res["data"] = {**res["data"], **extra_fields}
    return res


def register_events():  # noqa: C901
    @event.listens_for(Transaction, "after_insert")
    @event.listens_for(Transaction, "after_update")
    def prepare_data_for_transaction(mapper, connection, target):
        action = (
            CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        )
        if not hasattr(g, "history_to_commit"):
            g.history_to_commit = []
        g.history_to_commit.append(
            create_history_data(
                model=TransactionHistory,
                action=action,
                target=target,
                extra_fields={"status": target.status, "transaction_id": target.id},
            )
        )

    @event.listens_for(CashRegister, "after_insert")
    @event.listens_for(CashRegister, "after_update")
    def prepare_data_for_cash_register(mapper, connection, target):
        action = (
            CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        )
        if not hasattr(g, "history_to_commit"):
            g.history_to_commit = []
        g.history_to_commit.append(
            create_history_data(
                model=CashRegisterHistory,
                action=action,
                target=target,
                extra_fields={"cash_register_id": target.id},
            )
        )

    @event.listens_for(Counterparty, "after_insert")
    @event.listens_for(Counterparty, "after_update")
    def prepare_data_for_counterparty(mapper, connection, target):
        action = (
            CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        )
        if not hasattr(g, "history_to_commit"):
            g.history_to_commit = []

        g.history_to_commit.append(
            create_history_data(
                model=CounterpartyHistory,
                action=action,
                target=target,
                extra_fields={"status": target.status, "counterparty_id": target.id},
            )
        )

    @event.listens_for(User, "after_insert")
    @event.listens_for(User, "after_update")
    def prepare_data_for_user(mapper, connection, target):
        action = (
            CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        )
        if not hasattr(g, "history_to_commit"):
            g.history_to_commit = []

        g.history_to_commit.append(
            create_history_data(
                model=UserHistory,
                action=action,
                target=target,
                extra_fields={"user_id": target.id},
            )
        )

    @event.listens_for(Department, "after_insert")
    @event.listens_for(Department, "after_update")
    def prepare_data_for_department(mapper, connection, target):
        action = (
            CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        )
        if not hasattr(g, "history_to_commit"):
            g.history_to_commit = []

        g.history_to_commit.append(
            create_history_data(
                model=DepartmentHistory,
                action=action,
                target=target,
                extra_fields={"department_id": target.id},
            )
        )

    @event.listens_for(session, "after_commit")
    def insert_additional_data(session):
        # Проверяем наличие данных в g.history_to_commit
        if hasattr(g, "history_to_commit") and g.history_to_commit:
            try:
                # Используем сессию вне слушателя для добавления данных после коммита
                with Session() as new_session:
                    for item in g.history_to_commit:
                        if item["data"]["data"] is None:
                            break
                        model = item["model"]
                        data = item["data"]
                        instance = model(**data)
                        new_session.add(instance)
                    new_session.commit()  # Закоммитим данные после основного коммита
            except (AttributeError, SQLAlchemyError) as e:
                current_app.logger.error(str(e.args))
                new_session.rollback()  # Откатываем транзакцию, если произошла ошибка
            finally:
                new_session.close()

    reg_invoice_events()


def reg_invoice_events():
    from app.invoice.models import Invoice
    from app.product.models import ContainerLot, PartLot, ProductLot

    # Обработчик событий на изменение инвойсов
    @event.listens_for(Invoice, "after_insert")
    @event.listens_for(Invoice, "after_update")
    def update_invoice_fields_self(mapper, connection, target):
        if target:
            target.update_fields()

    # Обработчик событий на изменение лотов
    @event.listens_for(ProductLot, "after_insert")
    @event.listens_for(ProductLot, "after_update")
    @event.listens_for(ProductLot, "after_delete")
    @event.listens_for(ContainerLot, "after_insert")
    @event.listens_for(ContainerLot, "after_update")
    @event.listens_for(ContainerLot, "after_delete")
    @event.listens_for(PartLot, "after_insert")
    @event.listens_for(PartLot, "after_update")
    @event.listens_for(PartLot, "after_delete")
    def update_invoice_fields(mapper, connection, target):
        # target — это объект лота (ProductLot, ContainerLot, или PartLot)
        # Получаем связанный invoice и обновляем количество
        invoice = target.invoice
        if invoice:
            invoice.update_fields()
