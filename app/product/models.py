import uuid
from sqlalchemy import JSON, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, Optional, TYPE_CHECKING
import enum
from app.choices import MeasumentTypes
from app.base import Base, session

if TYPE_CHECKING:
    from app.invoice.models import Invoice


class LotBase:
    def calc_total_sum(self):
        self.total_sum = self.quantity * self.price
        session.commit()


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


class Part(Base):
    __tablename__ = "part"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(Enum(MeasumentTypes))
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    self_cost: Mapped[Optional[float]]


class ProductLot(Base, LotBase):
    __tablename__ = "product_lot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    markup: Mapped[Optional[str]]
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship()
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE")
    )
    invoice: Mapped["Invoice"] = relationship(back_populates="product_lots")


class ContainerLot(Base, LotBase):
    __tablename__ = "container_lot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    markup: Mapped[Optional[JSON]] = mapped_column(JSON)
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

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quantity: Mapped[int] = mapped_column(default=1)
    price: Mapped[float] = mapped_column(Float(decimal_return_scale=2))
    total_sum: Mapped[Optional[float]] = mapped_column(Float(decimal_return_scale=2))
    markup: Mapped[Optional[JSON]] = mapped_column(JSON)
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
