from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, TYPE_CHECKING
from app.base import Base
from app.choices import InvoiceStatuses

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
        receive = 0
        if self.invoice_receivers:
            receive = sum(
                [
                    inv.quantity
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return receive

    def calc_total_price(self):
        res = (
            self.calc_container_invoices_price()
            + self.calc_part_invoices_price()
            + self.calc_product_invoices_price()
        )
        return res

    def calc_container_invoices_price(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_container_lots_price()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def calc_part_invoices_price(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_part_lots_price()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def calc_product_invoices_price(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_product_lots_price()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def calc_container_invoices_quantity(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_container_lots_quantity()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def calc_part_invoices_quantity(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_part_lots_quantity()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def calc_product_invoices_quantity(self):
        if self.invoice_receivers:
            return sum(
                [
                    inv.calc_product_lots_quantity()
                    for inv in self.invoice_receivers
                    if inv.status == InvoiceStatuses.PUBLISHED
                ]
            )
        return 0

    def get_products(self):
        arr = []
        if self.invoice_receivers:
            for invoice in self.invoice_receivers:
                if invoice.status == InvoiceStatuses.PUBLISHED:
                    arr.extend(invoice.get_products())
        return list(set(arr))

    def get_containers(self):
        arr = []
        if self.invoice_receivers:
            for invoice in self.invoice_receivers:
                if invoice.status == InvoiceStatuses.PUBLISHED:
                    arr.extend(invoice.get_containers())
        return list(set(arr))

    def get_parts(self):
        arr = []
        if self.invoice_receivers:
            for invoice in self.invoice_receivers:
                if invoice.status == InvoiceStatuses.PUBLISHED:
                    arr.extend(invoice.get_parts())
        return list(set(arr))
