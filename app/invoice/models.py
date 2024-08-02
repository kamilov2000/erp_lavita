from sqlalchemy import Float, ForeignKey, Enum, String, event, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import get_history


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


class Invoice(Base):
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
        foreign_keys=[warehouse_sender_id]
    )
    warehouse_receiver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("warehouse.id", ondelete="SET NULL")
    )
    warehouse_receiver: Mapped["Warehouse"] = relationship(
        foreign_keys=[warehouse_receiver_id]
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


class InvoiceComment(Base):
    __tablename__ = "invoice_comment"

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="SET NULL")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="comments")
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    user: Mapped["User"] = relationship()
    text: Mapped[str]


class InvoiceLog(Base):
    __tablename__ = "invoice_log"

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="SET NULL")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="logs")
    curr_status: Mapped[Optional[enum.Enum]] = mapped_column(Enum(InvoiceStatuses))
    prev_status: Mapped[Optional[enum.Enum]] = mapped_column(Enum(InvoiceStatuses))


def log_invoice_changes(mapper, connection, target):
    sess = session.object_session(target)
    inspection = inspect(target)
    if sess.is_modified(target) or target.id is None:
        prev_status = None

        if getattr(inspection.attrs, "status").history.has_changes():
            if get_history(target, "status")[2]:
                prev_status = get_history(target, "status")[2].pop()

        log_entry = InvoiceLog(
            invoice_id=target.id,
            curr_status=target.status,
            prev_status=prev_status,
        )
        sess.add(log_entry)


event.listen(Invoice, "before_update", log_invoice_changes)
event.listen(Invoice, "after_insert", log_invoice_changes)
