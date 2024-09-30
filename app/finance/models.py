import calendar
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, session
from app.choices import (
    AccountCategories,
    AccountTypes,
    Statuses,
    TaxRateCategories,
    TransactionStatuses,
)
from app.utils.mixins import BalanceMixin, HistoryMixin, TempDataMixin


class PaymentType(Base):
    """
    Тип оплаты - способ оплаты, например Наличные, которые используется
    при приеме оплаты через мобильное приложение Курьера.
    """

    __tablename__ = "payment_type"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    has_commissioner: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commission_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fiscal: Mapped["Statuses"] = mapped_column(Enum(Statuses), default=Statuses.OFF)

    def create_counterparty(self):
        counter_party = Counterparty.query.filter(
            Counterparty.name == self.name
        ).first()
        if self.has_commissioner == True and not counter_party:
            counter_party = Counterparty(name=self.name, code="4030")
            session.add(counter_party)

    def update_counterparty(self, name):
        if (name != None) and (name != self.name):
            counter_party = Counterparty.query.filter(
                Counterparty.name == self.name
            ).first()
            counter_party.name = name


# Ассоциативная таблица для отношения многие-ко-многим между кассами и типами оплат
cash_register_payment_type = Table(
    "cash_register_payment_type",
    Base.metadata,
    Column(
        "cash_register_id", Integer, ForeignKey("cash_register.id"), primary_key=True
    ),
    Column("payment_type_id", Integer, ForeignKey("payment_type.id"), primary_key=True),
)


class CashRegister(TempDataMixin, Base, BalanceMixin):
    """
    Касса - место, которое хранит Баланс, а так же имеет принимаемые типы
    оплаты, также выбирается в мобильном приложении Курьера, при оплате
    заказа, всегда имеет статичный Код.
    """

    __tablename__ = "cash_register"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    payment_types: Mapped[List[PaymentType]] = relationship(
        "PaymentType", secondary=cash_register_payment_type, lazy="subquery"
    )
    code: Mapped[str] = mapped_column(String(4), default="5100")
    histories: Mapped[List["CashRegisterHistory"]] = relationship(
        back_populates="cash_register"
    )

    def __repr__(self) -> str:
        return f"<CashRegister(name={self.name}, code={self.code})>"

    def format(self):
        return {
            "name": self.name,
            "payment_types": [
                {"name": payment_type.name} for payment_type in self.payment_types
            ],
            "balance": float(self.balance),
        }


class CashRegisterHistory(Base, HistoryMixin):
    __tablename__ = "cash_register_history"
    cash_register_id: Mapped[int] = mapped_column(
        ForeignKey("cash_register.id", ondelete="SET NULL"), nullable=True
    )
    cash_register: Mapped["CashRegister"] = relationship(back_populates="histories")


class BalanceAccount(Base, BalanceMixin):
    """
    Счет баланса - полный аналог Кассы, только не содержит Типы оплаты
    и не участвует в мобильном приложении, может иметь любой Код.
    """

    __tablename__ = "balance_account"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(4), nullable=False)
    category: Mapped[AccountCategories] = mapped_column(
        Enum(AccountCategories), nullable=False, default=AccountCategories.SYSTEM
    )
    account_type: Mapped[AccountTypes] = mapped_column(
        Enum(AccountTypes), default=AccountTypes.ACTIVE
    )

    @property
    def can_edit_delete(self):
        return self.category == AccountCategories.USER

    def __repr__(self) -> str:
        return (
            f"<BalanceAccount(name={self.name},"
            f" code={self.code}, category={self.category}, "
            f"account_type={self.account_type})>"
        )


class TransactionHistory(Base, HistoryMixin):
    __tablename__ = "transaction_history"
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id", ondelete="SET NULL"), nullable=True
    )
    transaction: Mapped["Transaction"] = relationship(back_populates="histories")
    status: Mapped[TransactionStatuses] = mapped_column(
        Enum(TransactionStatuses), nullable=False
    )


class TransactionComment(Base):
    __tablename__ = "transaction_comment"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    user = relationship("User")
    user_full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    comment: Mapped[int] = mapped_column(String(250))
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id", ondelete="SET NULL"), nullable=True
    )
    transaction: Mapped["Transaction"] = relationship(back_populates="comments")


class Transaction(TempDataMixin, Base):
    """
    Транзакция - документ, который содержит Кредит (откуда) и Дебет (куда), а также фиксирует Сумму транзакции. В качестве Дебета или
    Кредита может выступать Касса, Счет баланса и Контрагент. Может Создаваться как Черновик,
    Публиковаться и Отменяться. Не может публиковаться задним числом.
    """

    __tablename__ = "transaction"

    number_transaction: Mapped[str] = mapped_column(String, nullable=False)
    published_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )  # если опубликована
    status: Mapped[TransactionStatuses] = mapped_column(
        Enum(TransactionStatuses), default=TransactionStatuses.PUBLISHED, nullable=False
    )

    debit_content_type = Column(String(50), nullable=False)
    debit_object_id = Column(Integer, nullable=False)
    credit_content_type = Column(String(50), nullable=False)
    credit_object_id = Column(Integer, nullable=False)
    amount: Mapped[str] = mapped_column(Float, nullable=False)
    category: Mapped[AccountCategories] = mapped_column(
        Enum(AccountCategories), default=AccountCategories.SYSTEM, nullable=False
    )
    credit_name = Column(String(50), nullable=False)
    debit_name = Column(String(50), nullable=False)
    histories: Mapped[List["TransactionHistory"]] = relationship(
        back_populates="transaction"
    )
    comments: Mapped[List["TransactionComment"]] = relationship(
        back_populates="transaction"
    )

    @property
    def debit_object(self):
        debit_class = globals()[self.debit_content_type]
        return session.get(debit_class, self.debit_object_id)

    @property
    def credit_object(self):
        credit_class = globals()[self.credit_content_type]
        return session.get(credit_class, self.credit_object_id)

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, status={self.status}, amount={self.amount})>"
        )

    @property
    def can_edit(self) -> bool:
        """Проверка, можно ли редактировать транзакцию"""
        return self.status == TransactionStatuses.DRAFT

    @property
    def can_cancel(self) -> bool:
        """Проверка, можно ли отменить транзакцию"""
        return self.status == TransactionStatuses.PUBLISHED

    def publish(self):
        """Опубликовать транзакцию, если возможно"""
        if self.status == TransactionStatuses.PUBLISHED:
            self.published_date = datetime.now()

            amount = self.amount
            self.credit_object.balance -= amount
            if hasattr(self.credit_object, "_temp_data"):
                self.credit_object.add_temp_data(
                    "history_data", {"balance": self.credit_object.balance}
                )
            self.debit_object.balance += amount
            if hasattr(self.debit_object, "_temp_data"):
                self.debit_object.add_temp_data(
                    "history_data", {"balance": self.debit_object.balance}
                )

    def cancel(self):
        """Отменить транзакцию, если возможно"""
        self.status = TransactionStatuses.CANCELLED
        self.credit_object.balance += self.amount
        if hasattr(self.credit_object, "_temp_data"):
            self.credit_object.add_temp_data(
                "history_data", {"balance": self.credit_object.balance}
            )
        self.debit_object.balance -= self.amount
        if hasattr(self.debit_object, "_temp_data"):
            self.debit_object.add_temp_data(
                "history_data", {"balance": self.debit_object.balance}
            )

    def format(self):
        return {
            "credit_category": self.credit_content_type,
            "debit_category": self.debit_content_type,
            "credit_name": self.credit_object.name,
            "debit_name": self.debit_object.name,
            "amount": float(self.amount),
        }


class CounterpartyHistory(Base, HistoryMixin):
    __tablename__ = "counterparty_history"
    counterparty_id: Mapped[int] = mapped_column(
        ForeignKey("counterparty.id", ondelete="SET NULL"), nullable=True
    )
    counterparty: Mapped["Counterparty"] = relationship(back_populates="histories")
    status: Mapped[Statuses] = mapped_column(Enum(Statuses), nullable=False)


class Counterparty(TempDataMixin, Base, BalanceMixin):
    """
    Контрагенты - аналог Кассы, только не содержит Типы оплаты и не участвует в мобильном приложении, может иметь любой Код.
    Также может создаваться автоматически, например при создании Налоговой ставки или активации механики Комиссионер,
    в таком случае имеет тип Системный. Могут иметь Автоматическое начисление (создание Авто транзакций).
    """

    __tablename__ = "counterparty"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(4), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200))
    legal_name: Mapped[Optional[str]] = mapped_column(String(200))
    inn_or_pinfl: Mapped[Optional[str]] = mapped_column(String(20))
    mfo: Mapped[Optional[str]] = mapped_column(String(20))
    legal_address: Mapped[Optional[str]] = mapped_column(String(200))
    contact: Mapped[Optional[str]] = mapped_column(String(100))
    category: Mapped[AccountCategories] = mapped_column(
        Enum(AccountCategories), default=AccountCategories.SYSTEM, nullable=False
    )
    status: Mapped[Statuses] = mapped_column(
        Enum(Statuses), default=Statuses.ON, nullable=False
    )
    files: Mapped[List["AttachedFile"]] = relationship(
        "AttachedFile", backref="counterparty"
    )
    auto_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    charge_period_months: Mapped[Optional[int]] = mapped_column(
        Integer, default=0
    )  # Период начисления в месяцах
    charge_amount: Mapped[Optional[float]] = mapped_column(
        Float, default=0
    )  # Сумма начисления в сум
    histories: Mapped[List["CounterpartyHistory"]] = relationship(
        back_populates="counterparty"
    )

    def format(self):
        return {
            "name": self.name,
            "code": self.code,
            "address": self.address,
            "legal_name": self.legal_name,
            "inn_or_pinfl": self.inn_or_pinfl,
            "mfo": self.mfo,
            "legal_address": self.legal_address,
            "contact": self.contact,
            "category": self.category.value.capitalize(),
            "status": self.status.value.capitalize(),
            "auto_charge": self.auto_charge,
            "charge_period_months": self.charge_period_months,
            "charge_amount": self.charge_amount,
            "balance": float(self.balance),
        }

    @property
    def can_delete_and_edit(self) -> bool:
        return self.category == AccountCategories.USER

    def create_auto_charge_transaction(self):
        current_year = datetime.now().year
        current_month = datetime.now().month
        # получить количество дней в текущем месяце
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        # Получаем объект балансового счета
        debit_object = BalanceAccount.query.filter_by(name="Постоянные расходы").first()
        transaction = Transaction(
            credit_content_type="Counterparty",
            credit_object_id=self.id,
            debit_content_type="BalanceAccount",
            debit_object_id=debit_object.id,
            status=TransactionStatuses.PUBLISHED,
            amount=self.charge_amount / days_in_month,
            credit_name=self.name,
            debit_name=debit_object.name,
        )
        transaction.publish()
        return transaction

    def __repr__(self):
        return (
            f"<Counterparty(name={self.name}, code={self.code}, status={self.status})>"
        )


class AttachedFile(Base):
    """
    Прикрепленнык файлы к контраагенту
    """

    __tablename__ = "attached_file"

    filename: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(100))
    filepath: Mapped[str] = mapped_column(String(100))
    counterparty_id: Mapped[int] = mapped_column(Integer, ForeignKey("counterparty.id"))

    def __repr__(self):
        return f"<AttachedFile(filename={self.filename})>"


# Ассоциативная таблица для отношения многие-ко-многим между налоговыми ставками и типами оплат
tax_rate_payment_type = Table(
    "tax_rate_payment_type",
    Base.metadata,
    Column("tax_rate_id", Integer, ForeignKey("tax_rate.id"), primary_key=True),
    Column("payment_type_id", Integer, ForeignKey("payment_type.id"), primary_key=True),
)


class TaxRate(Base):
    """
    Налоговая ставка - содержит список Типов оплаты, для которых применяется и процентное значение (например 5%),
    создает Авто транзакции при завершении заказа с использованием Типа оплаты, к которому есть Налоговая ставка.
    Создает системного Контрагента с названием данной Налоговой ставки.
    """

    __tablename__ = "tax_rate"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False)  # Ставка в процентах
    category: Mapped[TaxRateCategories] = mapped_column(
        Enum(TaxRateCategories), nullable=False
    )
    code: Mapped[str] = mapped_column(
        String(4), nullable=False
    )  # Код зависит от категории
    status: Mapped[Statuses] = mapped_column(
        Enum(Statuses), default=Statuses.ON, nullable=False
    )  # Статус по умолчанию On
    payment_types: Mapped[List[PaymentType]] = relationship(
        "PaymentType", secondary=tax_rate_payment_type, lazy="subquery"
    )

    def __init__(
        self,
        name: str,
        rate: float,
        category: TaxRateCategories,
        payment_types: List[PaymentType],
    ):
        self.name = name
        self.rate = rate
        self.category = category
        self.code = 9825 if category == TaxRateCategories.VAT else 9820
        self.payment_types = payment_types

    def __repr__(self) -> str:
        return f"<TaxRate(name={self.name}, rate={self.rate}%, category={self.category}, code={self.code})>"

    def create_counterparty(self):
        counter_party = Counterparty.query.filter(
            Counterparty.name == self.name
        ).first()
        if not counter_party:
            counter_party = Counterparty(name=self.name, code=self.code)
            session.add(counter_party)

    def update_counterparty(self, name):
        if (name != None) and (name != self.name):
            counter_party = Counterparty.query.filter(
                Counterparty.name == self.name
            ).first()
            counter_party.name = name
