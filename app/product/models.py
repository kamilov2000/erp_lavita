from sqlalchemy import JSON, Column, ForeignKey, Enum, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List, Optional
import enum
from app.choices import MeasumentTypes
from app.base import Base


product_container = Table(
    "product_container",
    Base.metadata,
    Column("product_id", ForeignKey("product.id"), primary_key=True),
    Column("container_id", ForeignKey("container.id"), primary_key=True),
)

product_part = Table(
    "product_part",
    Base.metadata,
    Column("product_id", ForeignKey("product.id"), primary_key=True),
    Column("part_id", ForeignKey("part.id"), primary_key=True),
)

container_part = Table(
    "container_part",
    Base.metadata,
    Column("container_id", ForeignKey("container.id"), primary_key=True),
    Column("part_id", ForeignKey("part.id"), primary_key=True),
)


class Product(Base):
    __tablename__ = "product"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(
        Enum(MeasumentTypes), default=MeasumentTypes.QUANTITY
    )
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    self_cost: Mapped[Optional[float]]
    markup: Mapped[str]
    containers: Mapped[List["Container"]] = relationship(
        back_populates="products", secondary=product_container
    )
    parts: Mapped[List["Part"]] = relationship(
        back_populates="products", secondary=product_part
    )


class Container(Base):
    __tablename__ = "container"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(
        Enum(MeasumentTypes), default=MeasumentTypes.QUANTITY
    )
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    self_cost: Mapped[Optional[float]]
    markup: Mapped[JSON] = mapped_column(JSON)
    parts: Mapped[List["Part"]] = relationship(
        back_populates="containers", secondary=container_part
    )
    products: Mapped[List["Product"]] = relationship(
        back_populates="containers", secondary=product_container
    )


class Part(Base):
    __tablename__ = "part"

    name: Mapped[str]
    measurement: Mapped[enum.Enum] = mapped_column(Enum(MeasumentTypes))
    photo: Mapped[Optional[str]]
    description: Mapped[str]
    self_cost: Mapped[Optional[float]]
    markup: Mapped[JSON] = mapped_column(JSON)
    products: Mapped[List["Product"]] = relationship(
        back_populates="parts", secondary=product_part
    )
    containers: Mapped[List["Container"]] = relationship(
        back_populates="parts", secondary=container_part
    )
