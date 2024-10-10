import datetime
from datetime import time
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.base import Base, session
from app.choices import DaysOfWeekShort, SalaryFormat, Statuses, WorkScheduleStatus
from app.utils.mixins import BalanceMixin, HistoryMixin, TempDataMixin

if TYPE_CHECKING:
    from app.invoice.models import Invoice
    from app.warehouse.models import Warehouse

warehouse_user = Table(
    "warehouse_user",
    Base.metadata,
    Column("warehouse_id", ForeignKey("warehouse.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)

work_scheduler_partner_association = Table(
    "work_schedule_partner",
    Base.metadata,
    Column("work_schedule_id", Integer, ForeignKey("work_schedule.id")),
    Column("partner_id", Integer, ForeignKey("partner.id")),
)


class UserHistory(HistoryMixin, Base):
    __tablename__ = "user_history"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User"] = relationship(back_populates="histories")


class User(TempDataMixin, Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    role: Mapped[str] = mapped_column(String(50), default="staff")
    password: Mapped[str] = mapped_column(String(200), nullable=True)
    identifier: Mapped[str] = mapped_column(String(200), nullable=True, unique=True)

    status: Mapped[Statuses] = mapped_column(Enum(Statuses), nullable=True)
    warehouses: Mapped[List["Warehouse"]] = relationship(
        back_populates="users", secondary=warehouse_user
    )
    photo: Mapped[str] = mapped_column(String(100), nullable=True)
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")
    phone_number: Mapped[str] = mapped_column(String(50), nullable=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("group.id", ondelete="SET NULL"), nullable=True
    )

    department: Mapped["Department"] = relationship(
        "Department", back_populates="users"
    )
    documents: Mapped["Department"] = relationship("Document", back_populates="user")
    working_days: Mapped[List["WorkingDay"]] = relationship(
        "WorkingDay", back_populates="user"
    )
    salary: Mapped["Salary"] = relationship("Salary", back_populates="user")
    group: Mapped["Group"] = relationship("Group", back_populates="users")
    salary_calculation: Mapped["SalaryCalculation"] = relationship(
        "SalaryCalculation", back_populates="user"
    )

    # рабочий график
    work_schedules: Mapped[list["WorkSchedule"]] = relationship(
        "WorkSchedule", back_populates="user"
    )
    permissions: Mapped["Permission"] = relationship(
        "Permission", back_populates="user"
    )
    histories: Mapped[list["UserHistory"]] = relationship(
        "UserHistory", back_populates="user"
    )

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

    def create_salary_abd_permission_obj(self):
        salary = Salary(user_id=self.id)
        salary_calculation = SalaryCalculation(user_id=self.id)
        permission = Permission(user_id=self.id)
        working_days = self.create_working_days()
        session.add_all([salary, permission, salary_calculation] + working_days)

    def create_working_days(self):
        working_days = []
        for day in DaysOfWeekShort:
            working_day = WorkingDay(day_of_week=day, user_id=self.id)
            working_days.append(working_day)
        return working_days

    @property
    def is_accepted_to_system(self):
        return self.permissions.access_to_system if self.permissions else True

    @property
    def is_driver_salary_format(self):
        return self.salary_calculation.salary_format == SalaryFormat.DRIVER


class Partner(Base):
    __tablename__ = "partner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    for_half_day: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Партнер на половину дня
    start_time: Mapped[Time] = mapped_column(
        Time, nullable=True
    )  # Время начала работы партнера
    end_time: Mapped[Time] = mapped_column(
        Time, nullable=True
    )  # Время окончания работы партнера

    def __repr__(self):
        return f"""
            <Partner(user={self.user.full_name},
            for_half_day={self.for_half_day},
            start_time={self.start_time},
            end_time={self.end_time})>
        """


class SalaryCalculation(Base):
    __tablename__ = "salary_calculation"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))

    # зарплата и KPI
    salary_format: Mapped["SalaryFormat"] = mapped_column(
        Enum(SalaryFormat), nullable=True, default=SalaryFormat.EMPLOYEE
    )  # Работник, Водитель, Оператор поддержки
    fixed_salary: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    kpi_movement: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    kpi_sales: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    bonus_sales_percent: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    bonus_sales_units: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    auto_bonus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    total_bonus: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    total_kpi: Mapped[int] = mapped_column(Integer, nullable=True, default=0)

    user: Mapped["User"] = relationship("User", back_populates="salary_calculation")


class DepartmentHistory(HistoryMixin, Base):
    __tablename__ = "department_history"

    department_id: Mapped[int] = mapped_column(
        ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )
    department: Mapped["Department"] = relationship(back_populates="histories")


class Department(TempDataMixin, Base):
    __tablename__ = "department"

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    groups: Mapped[list["Group"]] = relationship("Group", back_populates="department")
    users: Mapped[list["User"]] = relationship("User", back_populates="department")

    histories: Mapped[list["DepartmentHistory"]] = relationship(
        "DepartmentHistory", back_populates="department"
    )


class Group(Base):
    __tablename__ = "group"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )

    department: Mapped["Department"] = relationship(
        "Department", back_populates="groups"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="group")


class Document(Base):
    __tablename__ = "document"

    filename: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=True)
    filepath: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped["User"] = relationship("User", back_populates="documents")


class WorkSchedule(Base):
    __tablename__ = "work_schedule"

    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped["WorkScheduleStatus"] = mapped_column(
        Enum(WorkScheduleStatus), nullable=True
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped["User"] = relationship("User", back_populates="work_schedules")

    working_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("working_day.id"), nullable=True
    )
    working_day: Mapped["WorkingDay"] = relationship(
        "WorkingDay", backref="working_day"
    )

    partners: Mapped[List["Partner"]] = relationship(
        "Partner", secondary=work_scheduler_partner_association, backref="work_schedule"
    )


class Salary(Base, BalanceMixin):
    __tablename__ = "salary"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship("User", back_populates="salary")

    fixed_payment: Mapped[float] = mapped_column(Float, default=0)


class Permission(Base):
    __tablename__ = "permission"

    add_customer: Mapped[bool] = mapped_column(default=False)
    access_to_system: Mapped[bool] = mapped_column(Boolean, default=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped["User"] = relationship("User", back_populates="permissions")


class WorkingDay(Base):
    __tablename__ = "working_day"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    day_of_week: Mapped["DaysOfWeekShort"] = mapped_column(Enum(DaysOfWeekShort))
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=False)

    start_time: Mapped[time] = mapped_column(
        Time, default=time(0, 0)
    )  # Начало рабочего дня
    end_time: Mapped[time] = mapped_column(
        Time, default=time(0, 0)
    )  # Конец рабочего дня

    def __repr__(self):
        return f"""
        <WorkingDay(user_id={self.user_id},
        day_of_week={self.day_of_week},
        is_working_day={self.is_working_day})>
    """
