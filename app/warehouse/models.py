from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, TYPE_CHECKING
from app.base import Base

if TYPE_CHECKING:
    from app.user.models import User


class Warehouse(Base):
    __tablename__ = "warehouse"

    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(100))
    # responsible staffs
    users: Mapped[List["User"]] = relationship(
        back_populates="warehouses", secondary="warehouse_user"
    )
    # products: Mapped[List["Product"]] = relationship()
    # containers: Mapped[List["Container"]] = relationship()
    # parts: Mapped[List["Part"]] = relationship()
