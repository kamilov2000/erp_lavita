from sqlalchemy.orm import Mapped
from app.base import Base


class Region(Base):
    name: Mapped[str]
