from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List

from app.choices import ClientEntityType
from app.utils.mixins import BalanceMixin, HistoryMixin
from app.base import Base, session

if TYPE_CHECKING:
    from app.region.models import Region


class Client(Base, BalanceMixin):
    """Клиент"""

    __tablename__ = "client"

    entity_type: Mapped[ClientEntityType] = mapped_column(Enum(ClientEntityType))
    name: Mapped[str]
    phone: Mapped[str]
    inn: Mapped[str]
    pinfl: Mapped[str]
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"))
    region: Mapped["Region"] = relationship()
    histories: Mapped[List["ClientHistory"]] = relationship(back_populates="client")


class ClientHistory(Base, HistoryMixin):
    """История Клиента"""

    __tablename__ = "client_history"

    client_id: Mapped[int] = mapped_column(ForeignKey("client.id", ondelete="CASCADE"))
    client: Mapped[Client] = relationship(back_populates="histories")
