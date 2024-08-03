from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import marshmallow as ma

from app.base import session
from app.user.models import User
from app.utils.schema import DefaultDumpsSchema
from app.warehouse.models import Warehouse


class WarehouseSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True
        sqla_session = session

    users = ma.fields.Nested("UserSchema", many=True, dump_only=True)
    capacity = ma.fields.Method("get_capacity")
    user_ids = ma.fields.List(ma.fields.Int(), required=False, load_only=True)

    @ma.post_load
    def append_users(self, data, **kwargs):
        data["users"] = User.query.filter(User.id.in_(data.pop("user_ids", []))).all()
        return data

    @staticmethod
    def get_capacity(obj):
        return obj.calc_capacity()


class WarehouseQueryArgSchema(ma.Schema):
    name = ma.fields.Str(required=False)
    user_ids = ma.fields.List(ma.fields.Int(), required=False)
