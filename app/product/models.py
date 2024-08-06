import uuid
from sqlalchemy import Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, Optional, TYPE_CHECKING
import enum
from app.choices import DebtTypes, MeasumentTypes
from app.base import Base, session
from app.utils.exc import NotAvailableQuantity

if TYPE_CHECKING:
    from app.invoice.models import Invoice


class LotBase:
    def calc_total_sum(self):
        self.total_sum = self.quantity * self.price
        session.commit()


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
    self_cost: Mapped[Optional[float]]
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
    self_cost: Mapped[Optional[float]]
    parts_r: Mapped[List["ContainerPart"]] = relationship(back_populates="container")

    @staticmethod
    def decrease(container_id, decrease_quantity, possible_debt=False):
        if decrease_quantity <= 0:
            return
        lots = (
            ContainerLot.query.where(ContainerLot.container_id == container_id)
            .order_by(ContainerLot.created_at.desc())
            .all()
        )
        res_lots = []
        for lot in lots:
            if lot.quantity >= decrease_quantity:
                lot.quantity -= decrease_quantity
                session.commit()
                return [lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                lot.quantity = 0
                res_lots.append(lot)
        if decrease_quantity > 0 and possible_debt:
            debt = Debt(
                quantity=decrease_quantity,
                type=DebtTypes.CONTAINER,
                type_id=container_id,
            )
            session.add(debt)
        else:
            raise NotAvailableQuantity("Quantity is more than expected")
        session.commit()
        return res_lots


class Part(Base):
    __tablename__ = "part"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(Enum(MeasumentTypes))
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    self_cost: Mapped[Optional[float]]

    @staticmethod
    def decrease(part_id, decrease_quantity, possible_debt=False):
        if decrease_quantity <= 0:
            return
        lots = (
            PartLot.query.where(PartLot.container_id == part_id)
            .order_by(PartLot.created_at.desc())
            .all()
        )
        res_lots = []
        for lot in lots:
            if lot.quantity >= decrease_quantity:
                lot.quantity -= decrease_quantity
                session.commit()
                return [lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                lot.quantity = 0
                res_lots.append(lot)
        if decrease_quantity > 0 and possible_debt:
            debt = Debt(
                quantity=decrease_quantity,
                type=DebtTypes.PART,
                type_id=part_id,
            )
            session.add(debt)
        else:
            raise NotAvailableQuantity("Quantity is more than expected")
        session.commit()
        return res_lots


class ProductUnit(Base):
    __tablename__ = "product_unit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_lot_id: Mapped[int] = mapped_column(
        ForeignKey("product_lot.id", ondelete="CASCADE")
    )
    product_lot: Mapped["ProductLot"] = relationship(back_populates="units")


# class ContainerUnit(Base):
#     __tablename__ = "container_unit"

#     id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
#     container_lot_id: Mapped[int] = mapped_column(
#         ForeignKey("container_lot.id", ondelete="CASCADE")
#     )
#     container_lot: Mapped["ContainerLot"] = relationship(back_populates="units")


# class PartUnit(Base):
#     __tablename__ = "part_unit"

#     id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
#     part_lot_id: Mapped[int] = mapped_column(
#         ForeignKey("part_lot.id", ondelete="CASCADE")
#     )
#     part_lot: Mapped["PartLot"] = relationship(back_populates="units")


class ProductLot(Base, LotBase):
    __tablename__ = "product_lot"

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
    # units: Mapped[List["ContainerUnit"]] = relationship(
    #     back_populates="container_lot", cascade="all, delete-orphan"
    # )


class PartLot(Base, LotBase):
    __tablename__ = "part_lot"

    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[float] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"))
    part: Mapped["Part"] = relationship()
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="part_lots")
    # units: Mapped[List["PartUnit"]] = relationship(
    #     back_populates="part_lot", cascade="all, delete-orphan"
    # )


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
