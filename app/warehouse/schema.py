from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import marshmallow as ma

from app.warehouse.models import Warehouse


class WarehouseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class WarehouseQueryArgSchema(ma.Schema):
    name = ma.fields.Str(required=False)
