from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash

from typing import List, Optional, TYPE_CHECKING
from app.base import Base

if TYPE_CHECKING:
    from app.warehouse.models import Warehouse
    from app.invoice.models import Invoice


warehouse_user = Table(
    "warehouse_user",
    Base.metadata,
    Column("warehouse_id", ForeignKey("warehouse.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    role: Mapped[str] = mapped_column(String(50), default="staff")
    password: Mapped[str] = mapped_column(String(200))
    warehouses: Mapped[List["Warehouse"]] = relationship(
        back_populates="users", secondary=warehouse_user
    )
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")

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
