from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import marshmallow as ma

from app.base import session
from app.utils.schema import DefaultDumpsSchema
from app.warehouse.models import Warehouse


class WarehouseSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True
        sqla_session = session


class WarehouseQueryArgSchema(ma.Schema):
    name = ma.fields.Str(required=False)
