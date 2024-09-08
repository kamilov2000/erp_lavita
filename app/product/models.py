from sqlalchemy import Column, Float, ForeignKey, Enum, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, Optional
import enum
import datetime as dt
from app.choices import DebtTypes, InvoiceStatuses, InvoiceTypes, MeasumentTypes
from app.base import Base, session
from app.utils.exc import NotAvailableQuantity

from app.invoice.models import Invoice

# if TYPE_CHECKING:


class LotBase:
    def calc_total_sum(self):
        self.total_sum = self.quantity * self.price
        return self.total_sum

    @classmethod
    def calculate_fifo_cost(
        LotModel,
        statement,
        required_quantity,
        item_id,
        expense=True,
    ):
        total_cost = 0.0
        remaining_quantity = required_quantity

        # Query lots ordered by creation date (FIFO)
        lots = (
            session.query(LotModel)
            .filter(statement, LotModel.quantity > 0)
            .order_by(LotModel.created_at)
            .all()
        )

        for lot in lots:
            if lot.quantity >= remaining_quantity:
                total_cost += remaining_quantity * lot.price
                if expense:
                    lot.quantity -= remaining_quantity
                remaining_quantity = 0
                break
            else:
                total_cost += lot.quantity * lot.price
                remaining_quantity -= lot.quantity
                if expense:
                    lot.quantity = 0
        if remaining_quantity > 0 and expense:
            model_name = str(LotModel.__tablename__).split("_")[0]
            debt = Debt(
                type=DebtTypes(model_name), type_id=item_id, quantity=remaining_quantity
            )
            session.add(debt)

        return total_cost


class Debt(Base):
    __tablename__ = "debt"
    type: Mapped[enum.Enum] = mapped_column(Enum(DebtTypes))
    type_id: Mapped[int]
    quantity: Mapped[int]


class Product(Base):
    __tablename__ = "product"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(
        Enum(MeasumentTypes), default=MeasumentTypes.QUANTITY
    )
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    containers_r: Mapped[List["ProductContainer"]] = relationship(
        back_populates="product"
    )
    parts_r: Mapped[List["ProductPart"]] = relationship(back_populates="product")


class Container(Base):
    __tablename__ = "container"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(
        Enum(MeasumentTypes), default=MeasumentTypes.QUANTITY
    )
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    parts_r: Mapped[List["ContainerPart"]] = relationship(back_populates="container")

    @staticmethod
    def decrease(container_id, decrease_quantity, transfer=False):
        if decrease_quantity <= 0:
            return
        lots = (
            ContainerLot.query.join(Invoice, Invoice.id == ContainerLot.invoice_id)
            .where(
                ContainerLot.container_id == container_id,
                Invoice.status == InvoiceStatuses.PUBLISHED,
                Invoice.type != InvoiceTypes.EXPENSE,
            )
            .order_by(ContainerLot.created_at.asc())
            .all()
        )
        res_lots = []
        for lot in lots:
            if lot.quantity >= decrease_quantity:
                lot.quantity -= decrease_quantity
                lot.calc_total_sum()
                new_lot = ContainerLot(
                    quantity=decrease_quantity,
                    price=lot.price,
                    container_id=container_id,
                )
                new_lot.calc_total_sum()
                return [new_lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                new_lot = ContainerLot(
                    quantity=lot.quantity,
                    price=lot.price,
                    container_id=container_id,
                )
                new_lot.calc_total_sum()
                lot.quantity = 0
                lot.calc_total_sum()
                res_lots.append(new_lot)
        if decrease_quantity > 0 and not transfer:
            debt = Debt(
                quantity=decrease_quantity,
                type=DebtTypes.CONTAINER,
                type_id=container_id,
            )
            session.add(debt)
        else:
            raise NotAvailableQuantity("Quantity is more than expected")
        return res_lots

    @staticmethod
    def increase(container_id, increase_quantity):
        if increase_quantity <= 0:
            return
        lot = (
            ContainerLot.query.join(Invoice, Invoice.id == ContainerLot.invoice_id)
            .where(
                ContainerLot.container_id == container_id,
                Invoice.status == InvoiceStatuses.PUBLISHED,
                Invoice.type != InvoiceTypes.EXPENSE,
            )
            .order_by(ContainerLot.created_at.asc())
            .first()
        )
        lot.quantity += increase_quantity


class Part(Base):
    __tablename__ = "part"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(Enum(MeasumentTypes))
    photo: Mapped[Optional[str]]
    description: Mapped[str]

    @staticmethod
    def decrease(part_id, decrease_quantity, transfer=False):
        if decrease_quantity <= 0:
            return
        lots = (
            PartLot.query.where(PartLot.part_id == part_id)
            .order_by(PartLot.created_at.asc())
            .all()
        )
        res_lots = []
        for lot in lots:
            if lot.quantity >= decrease_quantity:
                lot.calc_total_sum()
                lot.quantity -= decrease_quantity
                new_lot = PartLot(
                    quantity=decrease_quantity,
                    price=lot.price,
                    part_id=lot.part_id,
                )
                new_lot.calc_total_sum()
                return [new_lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                new_lot = PartLot(
                    quantity=lot.quantity,
                    price=lot.price,
                    part_id=lot.part_id,
                )
                new_lot.calc_total_sum()
                res_lots.append(new_lot)
                lot.quantity = 0
                lot.calc_total_sum()
        if decrease_quantity > 0 and not transfer:
            debt = Debt(
                quantity=decrease_quantity,
                type=DebtTypes.PART,
                type_id=part_id,
            )
            session.add(debt)
        else:
            raise NotAvailableQuantity("Quantity is more than expected")
        return res_lots

    @staticmethod
    def increase(part_id, increase_quantity):
        if increase_quantity <= 0:
            return
        lot = (
            PartLot.query.join(Invoice, Invoice.id == PartLot.invoice_id)
            .where(
                PartLot.part_id == part_id,
                Invoice.status == InvoiceStatuses.PUBLISHED,
                Invoice.type != InvoiceTypes.EXPENSE,
            )
            .order_by(PartLot.created_at.asc())
            .first()
        )
        lot.quantity += increase_quantity


class ProductUnit(Base):
    __tablename__ = "product_unit"

    id: Mapped[str] = mapped_column(primary_key=True)
    product_lot_id: Mapped[int] = mapped_column(
        ForeignKey("product_lot.id", ondelete="CASCADE")
    )
    product_lot: Mapped["ProductLot"] = relationship(back_populates="units")


class ProductLot(Base, LotBase):
    __tablename__ = "product_lot"

    const_quantity: Mapped[Optional[int]] = mapped_column(default=1)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship()
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="product_lots")
    units: Mapped[List["ProductUnit"]] = relationship(
        back_populates="product_lot", cascade="all, delete-orphan"
    )


class ContainerLot(Base, LotBase):
    __tablename__ = "container_lot"

    const_quantity: Mapped[Optional[int]] = mapped_column(default=1)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    container_id: Mapped[int] = mapped_column(
        ForeignKey("container.id", ondelete="CASCADE")
    )
    container: Mapped["Container"] = relationship()
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="container_lots")


class PartLot(Base, LotBase):
    __tablename__ = "part_lot"

    const_quantity: Mapped[Optional[int]] = mapped_column(default=1)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[float] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"))
    part: Mapped["Part"] = relationship()
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="part_lots")


class ProductContainer(Base):
    __tablename__ = "product_container"
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="containers_r")
    container_id: Mapped[int] = mapped_column(
        ForeignKey("container.id", ondelete="CASCADE")
    )
    container: Mapped["Container"] = relationship()
    quantity: Mapped[int] = mapped_column(default=1)


class ProductPart(Base):
    __tablename__ = "product_part"
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="parts_r")
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"))
    part: Mapped["Part"] = relationship()
    quantity: Mapped[int] = mapped_column(default=1)


class ContainerPart(Base):
    __tablename__ = "container_part"
    container_id: Mapped[int] = mapped_column(
        ForeignKey("container.id", ondelete="CASCADE")
    )
    container: Mapped["Container"] = relationship(back_populates="parts_r")
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"))
    part: Mapped["Part"] = relationship()
    quantity: Mapped[int] = mapped_column(default=1)


markup_markup_filter = Table(
    "markup_markup_filter",
    Base.metadata,
    Column("markup_id", ForeignKey("markup.id"), primary_key=True),
    Column("markup_filter_id", ForeignKey("markup_filter.id"), primary_key=True),
)


class Markup(Base):
    __tablename__ = "markup"
    id: Mapped[str] = mapped_column(primary_key=True)
    is_used: Mapped[bool] = mapped_column(default=False)
    date_of_use: Mapped[Optional[dt.datetime]]
    filters: Mapped[List["MarkupFilter"]] = relationship(
        back_populates="markups",
        secondary="markup_markup_filter",
        cascade="all",
    )


class MarkupFilter(Base):
    __tablename__ = "markup_filter"
    name: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    date_of_receive: Mapped[Optional[dt.datetime]]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship()
    markups: Mapped[List["Markup"]] = relationship(
        back_populates="filters", secondary="markup_markup_filter"
    )

    @staticmethod
    def get_unused_markups_by_filter_id(session, markup_filter_id: int):
        return (
            session.query(Markup)
            .join(markup_markup_filter, Markup.id == markup_markup_filter.c.markup_id)
            .filter(
                markup_markup_filter.c.markup_filter_id == markup_filter_id,
                Markup.is_used == False,
            )
            .all()
        )
