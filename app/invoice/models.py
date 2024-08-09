from sqlalchemy import Float, ForeignKey, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


from typing import List, Optional, TYPE_CHECKING
import enum
from app.choices import InvoiceTypes, InvoiceStatuses
from app.base import Base, session

if TYPE_CHECKING:
    from app.warehouse.models import Warehouse
    from app.user.models import User
    from app.product.models import ContainerLot, PartLot, ProductLot


class File(Base):
    __tablename__ = "file"
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="SET NULL")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="files")
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(511))
    is_photo: Mapped[bool] = mapped_column(default=False)


class InvoiceBase:
    def calc_container_lots_price(self):
        if self.container_lots:
            return sum([i.price * i.quantity for i in self.container_lots])
        return 0

    def calc_part_lots_price(self):
        if self.part_lots:
            return sum([i.price * i.quantity for i in self.part_lots])
        return 0

    def calc_product_lots_price(self):
        if self.product_lots:
            return sum([i.price * i.quantity for i in self.product_lots])
        return 0

    def calc_container_lots_quantity(self):
        if self.container_lots:
            return sum([i.quantity for i in self.container_lots])
        return 0

    def calc_part_lots_quantity(self):
        if self.part_lots:
            return sum([i.quantity for i in self.part_lots])
        return 0

    def calc_product_lots_quantity(self):
        if self.product_lots:
            return sum([i.quantity for i in self.product_lots])
        return 0

    def write_history(self, prev_status=None):
        log = InvoiceLog(
            curr_status=self.status,
            prev_status=None,
            user_id=self.user_id,
            invoice_id=self.id,
        )
        session.add(log)
        session.commit()

    def get_products(self):
        return [item.product for item in self.product_lots]

    def get_containers(self):
        return [item.container for item in self.container_lots]

    def get_parts(self):
        return [item.part for item in self.part_lots]


class Invoice(Base, InvoiceBase):
    __tablename__ = "invoice"

    type: Mapped[enum.Enum] = mapped_column(
        Enum(InvoiceTypes), default=InvoiceTypes.INVOICE
    )
    number: Mapped[str]
    status: Mapped[enum.Enum] = mapped_column(
        Enum(InvoiceStatuses), default=InvoiceStatuses.DRAFT
    )
    warehouse_sender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("warehouse.id", ondelete="SET NULL")
    )
    warehouse_sender: Mapped["Warehouse"] = relationship(
        foreign_keys=[warehouse_sender_id], back_populates="invoice_senders"
    )
    warehouse_receiver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("warehouse.id", ondelete="SET NULL")
    )
    warehouse_receiver: Mapped["Warehouse"] = relationship(
        foreign_keys=[warehouse_receiver_id], back_populates="invoice_receivers"
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    user: Mapped["User"] = relationship(back_populates="invoices")
    files: Mapped[List["File"]] = relationship(back_populates="invoice")
    price: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    quantity: Mapped[Optional[int]]
    comments: Mapped[List["InvoiceComment"]] = relationship(back_populates="invoice")
    logs: Mapped[List["InvoiceLog"]] = relationship(back_populates="invoice")
    product_lots: Mapped[List["ProductLot"]] = relationship(back_populates="invoice")
    container_lots: Mapped[List["ContainerLot"]] = relationship(
        back_populates="invoice"
    )
    part_lots: Mapped[List["PartLot"]] = relationship(back_populates="invoice")


class InvoiceComment(Base):
    __tablename__ = "invoice_comment"

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="comments")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    user: Mapped["User"] = relationship()
    text: Mapped[str]


class InvoiceLog(Base):
    __tablename__ = "invoice_log"

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="logs")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    user: Mapped["User"] = relationship()
    curr_status: Mapped[Optional[enum.Enum]] = mapped_column(Enum(InvoiceStatuses))
    prev_status: Mapped[Optional[enum.Enum]] = mapped_column(Enum(InvoiceStatuses))
