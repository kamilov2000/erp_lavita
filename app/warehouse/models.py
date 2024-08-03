from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, TYPE_CHECKING
from app.base import Base

if TYPE_CHECKING:
    from app.user.models import User
    from app.invoice.models import Invoice


class Warehouse(Base):
    __tablename__ = "warehouse"

    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(100))
    # responsible staffs
    users: Mapped[List["User"]] = relationship(
        back_populates="warehouses", secondary="warehouse_user"
    )
    invoice_senders: Mapped[List["Invoice"]] = relationship(
        back_populates="warehouse_sender", foreign_keys="[Invoice.warehouse_sender_id]"
    )
    invoice_receivers: Mapped[List["Invoice"]] = relationship(
        back_populates="warehouse_receiver",
        foreign_keys="[Invoice.warehouse_receiver_id]",
    )

    def calc_capacity(self):
        sent = 0
        receive = 0
        if self.invoice_senders:
            sent = sum([inv.quantity for inv in self.invoice_senders])
        if self.invoice_receivers:
            receive = sum([inv.quantity for inv in self.invoice_receivers])
        return receive - sent
