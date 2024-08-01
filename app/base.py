from sqlalchemy import DateTime, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    scoped_session,
)
from flask import current_app
from datetime import datetime, date
from typing import Optional
import enum

from app.config.main import SQLALCHEMY_URI
from app.utils.exc import ItemNotFoundError

engine = create_engine(SQLALCHEMY_URI)
session = scoped_session(sessionmaker(engine))


class Base(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    query = session.query_property()

    def save(self):
        try:
            session.add(self)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
        return self

    def to_dict(self, creation=True, with_id=True, with_relations=False):
        res = {col.key: self.correct_columns(col.key) for col in self.__table__.c}
        if not creation:
            del res["created_at"]
            del res["updated_at"]
        if not with_id:
            del res["id"]
        if with_relations:
            for attr, _ in self.__mapper__.relationships.items():
                value = getattr(self, attr)
                if value is None:
                    res[attr] = None
                elif isinstance(value, list):
                    res[attr] = [
                        item.to_dict(creation=creation, with_id=with_id)
                        for item in value
                    ]
                else:
                    res[attr] = value.to_dict(creation=creation, with_id=with_id)
        return res

    def correct_columns(self, key):
        res = getattr(self, key)
        if isinstance(res, enum.Enum):
            return res.value
        elif isinstance(res, datetime):
            return res.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(res, date):
            return res.strftime("%Y-%m-%d")
        return res

    @staticmethod
    def create(cls, **kwargs):
        for kw in kwargs:
            if hasattr(cls, kw):
                setattr(cls, kw, kwargs.get(kw))
        return cls

    def update(self, **kwargs):
        updated_columns = {}
        for kw, value in kwargs.items():
            if not hasattr(self, kw):
                continue
            if isinstance(getattr(self, kw), datetime) and isinstance(value, str):
                setattr(self, kw, datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))
            elif isinstance(getattr(self, kw), date) and isinstance(value, str):
                setattr(self, kw, datetime.strptime(value, "%Y-%m-%d").date())
            elif isinstance(self, kw, enum.Enum):
                print("ENUM UPDATING")
                setattr(self, kw, value)
            else:
                setattr(self, kw, value)
            updated_columns[kw] = value
        return updated_columns

    @classmethod
    def get_by_id(cls, ident):
        res = cls.query.get(ident)
        if not res:
            raise ItemNotFoundError(f"not found {cls.__tablename__} with id: {ident}")
        return res

    @classmethod
    def delete(cls, ident):
        res = cls.query.get(ident)
        if not res:
            raise ItemNotFoundError(f"not found {cls.__tablename__} with id: {ident}")
        session.delete(res)
        session.commit()


for tbl in reversed(Base.metadata.sorted_tables):
    engine.execute(tbl.delete())
