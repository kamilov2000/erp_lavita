from flask import g, current_app
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.base import session, engine, Base
from app import CrudOperations
from app.finance.models import Transaction, TransactionHistory, CashRegister, CashRegisterHistory, Counterparty, \
    CounterpartyHistory

Session = sessionmaker(bind=engine)


def create_history_data(model: Base, action, target, extra_fields):
    res = {
        "model": model,
        "data": {
            'user_id': g.user.id if hasattr(g, "user") else None,
            'operation_status': action,
            'data': target.format(),
            'user_full_name': g.user.full_name if hasattr(g, "user") else None,
        }
    }
    # merge two default history data with extra
    res['data'] = {**res['data'], **extra_fields}
    return res


def register_events():
    @event.listens_for(Transaction, 'after_insert')
    @event.listens_for(Transaction, 'after_update')
    def prepare_data_for_transaction(mapper, connection, target):
        action = CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        if not hasattr(g, 'history_to_commit'):
            g.history_to_commit = []
        g.history_to_commit.append(create_history_data(
            model=TransactionHistory,
            action=action,
            target=target,
            extra_fields={
                "status": target.status,
                "transaction_id": target.id
            }
        ))

    @event.listens_for(CashRegister, 'after_insert')
    @event.listens_for(CashRegister, 'after_update')
    def prepare_data_for_cash_register(mapper, connection, target):
        action = CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        if not hasattr(g, 'history_to_commit'):
            g.history_to_commit = []
        g.history_to_commit.append(create_history_data(
            model=CashRegisterHistory,
            action=action,
            target=target,
            extra_fields={
                "cash_register_id": target.id
            }
        ))

    @event.listens_for(Counterparty, 'after_insert')
    @event.listens_for(Counterparty, 'after_update')
    def prepare_data_for_counterparty(mapper, connection, target):
        action = CrudOperations.CREATED if not target.histories else CrudOperations.UPDATED
        if not hasattr(g, 'history_to_commit'):
            g.history_to_commit = []
        g.history_to_commit.append(create_history_data(
            model=CounterpartyHistory,
            action=action,
            target=target,
            extra_fields={
                "status": target.status,
                "counterparty_id": target.id
            }
        ))

    @event.listens_for(session, 'after_commit')
    def insert_additional_data(session):
        # Проверяем наличие данных в g.history_to_commit
        if hasattr(g, 'history_to_commit') and g.history_to_commit:
            try:
                # Используем сессию вне слушателя для добавления данных после коммита
                with Session() as new_session:
                    for item in g.history_to_commit:
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
