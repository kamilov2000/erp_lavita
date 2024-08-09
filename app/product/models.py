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
            ContainerLot.query.where(ContainerLot.container_id == container_id)
            .order_by(ContainerLot.created_at.asc())
            .all()
        )
        res_lots = []
        for lot in lots:
            if lot.quantity >= decrease_quantity:
                lot.quantity -= decrease_quantity
                lot.calc_total_sum()
                if transfer:
                    new_lot = ContainerLot(
                        quantity=decrease_quantity,
                        price=lot.price,
                        container_id=container_id,
                    )
                    new_lot.calc_total_sum()
                    return [new_lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                lot.quantity = 0
                lot.calc_total_sum()
                if transfer:
                    res_lots.append(lot)
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
                if transfer:
                    new_lot = PartLot(
                        quantity=decrease_quantity,
                        price=lot.price,
                        part_id=lot.part_id,
                    )
                    new_lot.calc_total_sum()
                    return [new_lot]
            elif lot.quantity < decrease_quantity:
                decrease_quantity -= lot.quantity
                if transfer:
                    res_lots.append(lot)
                    continue
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


class ProductUnit(Base):
    __tablename__ = "product_unit"

    id: Mapped[str] = mapped_column(primary_key=True)
    product_lot_id: Mapped[int] = mapped_column(
        ForeignKey("product_lot.id", ondelete="CASCADE")
    )
    product_lot: Mapped["ProductLot"] = relationship(back_populates="units")


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
