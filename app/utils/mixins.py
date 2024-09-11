from flask.views import MethodView
from sqlalchemy import JSON, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app import CrudOperations


class CustomMethodPaginationView(MethodView):
    model = None

    def get(self, args, token, query_args=None, custom_query=None, matched_lst=None):

        page = args.pop("page", 1)
        limit = int(args.pop("limit", 10))
        if limit <= 0:
            limit = 10

        name = args.pop("name", None)
        if custom_query:
            query = custom_query
        else:
            query = self.model.query.order_by(self.model.created_at.desc())
        default_query_args = []
        if name:
            default_query_args.append(self.model.name.ilike(f"%{name}%"))
        if query_args:
            default_query_args.extend(query_args)
        query = query.filter(*default_query_args)
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit
        data = query.limit(limit).offset((page - 1) * limit).all()
        response = {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_count": total_count,
            },
        }

        return response


class HistoryMixin:

    @declared_attr
    def operation_status(cls):
        return mapped_column(Enum(CrudOperations))

    @declared_attr
    def user_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def user(cls):
        return relationship("User")

    @declared_attr
    def data(cls):
        return mapped_column(JSON, nullable=True)

    @declared_attr
    def user_full_name(cls) -> Mapped[str]:
        return mapped_column(String(100), nullable=True)


class BalanceMixin:
    """Добавление поля баланс к объекту"""

    @declared_attr
    def balance(cls) -> Mapped[float]:
        return mapped_column(Float, default=0, nullable=True)


class TempDataMixin:
    _temp_data = {}

    def add_temp_data(self, key, value):
        """Добавляем временные данные в словарь"""
        self._temp_data[key] = value

    def get_temp_data(self, key):
        """Получаем временные данные по ключу"""
        return self._temp_data.get(key, None)

    def remove_temp_data(self, key):
        """Удаляем временные данные по ключу"""
        if key in self._temp_data:
            del self._temp_data[key]

    def clear_temp_data(self):
        """Очищаем временный словарь"""
        self._temp_data.clear()
