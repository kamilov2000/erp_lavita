from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import marshmallow as ma

from app.base import session
from app.warehouse.models import Warehouse


class WarehouseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class WarehouseQueryArgSchema(ma.Schema):
    name = ma.fields.Str(required=False)
