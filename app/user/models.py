import datetime

from sqlalchemy import Column, ForeignKey, String, Table, Integer, Date, Boolean, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash

from typing import List, Optional, TYPE_CHECKING
from app.base import Base, session
from app.choices import Statuses

if TYPE_CHECKING:
    from app.warehouse.models import Warehouse
    from app.invoice.models import Invoice

warehouse_user = Table(
    "warehouse_user",
    Base.metadata,
    Column("warehouse_id", ForeignKey("warehouse.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)


class Partner(Base):
    __tablename__ = "partner"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    partner_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))  # Напарник, тоже пользователь

    user: Mapped["User"] = relationship('User', foreign_keys=[user_id], back_populates='partners')
    partner: Mapped["User"] = relationship('User', foreign_keys=[partner_id])

    @staticmethod
    def add_partners(user: "User", partner: "User"):
        """Добавить напарников друг к другу"""
        # Проверяем, что они не напарники друг другу
        if not session.query(Partner).filter_by(user_id=user.id, partner_id=partner.id).first():
            # Добавляем напарника
            new_partner = Partner(user_id=user.id, partner_id=partner.id)
            session.add(new_partner)

        # Проверяем, что обратная связь тоже установлена
        if not session.query(Partner).filter_by(user_id=partner.id, partner_id=user.id).first():
            reverse_partner = Partner(user_id=partner.id, partner_id=user.id)
            session.add(reverse_partner)

        session.commit()


class User(Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    role: Mapped[str] = mapped_column(String(50), default="staff")
    password: Mapped[str] = mapped_column(String(200))

    status: Mapped[Statuses] = mapped_column(
        Enum(Statuses),
        nullable=True
    )
    warehouses: Mapped[List["Warehouse"]] = relationship(
        back_populates="users", secondary=warehouse_user
    )
    photo: Mapped[str] = mapped_column(String(100), nullable=True)
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")
    phone_number: Mapped[str] = mapped_column(String(50), nullable=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('department.id', ondelete="SET NULL"), nullable=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey('group.id', ondelete="SET NULL"), nullable=True)
    salary_format: Mapped[str] = mapped_column(String(50), nullable=True)  # Работник, Водитель, Оператор поддержки
    department: Mapped["Department"] = relationship('Department', back_populates='users')
    documents: Mapped["Department"] = relationship('Document', back_populates='user')
    salary: Mapped["Salary"] = relationship('Salary', back_populates='user')
    group: Mapped["Group"] = relationship('Group', back_populates='users')
    salary_calculation: Mapped["SalaryCalculation"] = relationship('SalaryCalculation',
                                                                          back_populates='user')

    # рабочий график
    work_schedules: Mapped[list["WorkSchedule"]] = relationship('WorkSchedule', back_populates='user')

    # напарники для водителей
    partners: Mapped[list["Partner"]] = relationship('Partner', foreign_keys=[Partner.user_id], back_populates='user')
    permissions: Mapped[list["Permission"]] = relationship('Permission', back_populates='user')

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.last_name or ''} {self.first_name or ''}"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    @staticmethod
    def generate_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def create_salary_obj(self):
        salary = Salary(user_id=self.id)
        session.add(salary)


class SalaryCalculation(Base):
    __tablename__ = "salary_calculation"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))

    # зарплата и KPI
    fixed_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    kpi_movement: Mapped[int] = mapped_column(Integer, nullable=True)
    kpi_sales: Mapped[int] = mapped_column(Integer, nullable=True)
    bonus_sales_percent: Mapped[int] = mapped_column(Integer, nullable=True)
    bonus_sales_units: Mapped[int] = mapped_column(Integer, nullable=True)
    auto_bonus: Mapped[int] = mapped_column(Integer, nullable=True)
    total_bonus: Mapped[int] = mapped_column(Integer, nullable=True)
    total_kpi: Mapped[int] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship('User', back_populates='salary_calculation')


class Department(Base):
    __tablename__ = "department"

    name: Mapped[str] = mapped_column(String, nullable=False)

    groups: Mapped[list["Group"]] = relationship('Group', back_populates='department')
    users: Mapped[list["User"]] = relationship('User', back_populates='department')


class Group(Base):
    __tablename__ = "group"

    name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('department.id', ondelete='SET NULL'), nullable=True)

    department: Mapped["Department"] = relationship('Department', back_populates='groups')
    users: Mapped[list["User"]] = relationship('User', back_populates='group')


class Document(Base):
    __tablename__ = "document"

    filename: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped["User"] = relationship('User', back_populates='documents')


class WorkSchedule(Base):
    __tablename__ = "work_schedule"

    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # Явка, Пропуск, Опоздание, Отпуск, Выходной

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped["User"] = relationship('User', back_populates='work_schedules')


class Salary(Base):
    __tablename__ = "salary"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    user: Mapped["User"] = relationship('User', back_populates='salary')

    current_balance: Mapped[float] = mapped_column(Float, default=0)
    fixed_payment: Mapped[float] = mapped_column(Float, default=0)


class PermissionGroup(Base):
    __tablename__ = 'permission_group'

    name: Mapped[str] = mapped_column(String,
                                      nullable=False)  # Название группы, например "Склад", "Производство", "Отчеты"

    permissions: Mapped[list["Permission"]] = relationship('Permission', back_populates='group')


class Permission(Base):
    __tablename__ = 'permission'

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey('permission_group.id'))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))

    permission_name: Mapped[str] = mapped_column(String, nullable=False)  # Название права, например "create_nakladnaya"
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False)  # Значение права доступа (разрешено/не разрешено)

    group: Mapped["PermissionGroup"] = relationship('PermissionGroup', back_populates='permissions')
    user: Mapped["User"] = relationship('User', back_populates='permissions')
