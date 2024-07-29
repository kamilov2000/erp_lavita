import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

from app.choices import MeasumentTypes
from app.product.models import Container, Part, Product
from app.base import session


class ProductSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        include_fk = True
        load_instance = True
        sqla_session = session
        datetimeformat = "%Y-%m-%d, %H:%M"

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)


class ContainerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Container
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)


class PartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Part
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)


class ProductQueryArgSchema(ma.Schema):
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True, required=False)
    name = ma.fields.Str(required=False)
