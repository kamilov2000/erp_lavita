import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

from app.choices import MeasumentTypes
from app.product.models import (
    Container,
    ContainerPart,
    Part,
    Product,
    ProductContainer,
    ProductPart,
)
from app.base import session


class ProductContainerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ProductContainer
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    product_id = auto_field(required=False)


class ProductPartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ProductPart
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    product_id = auto_field(required=False)


class ContainerPartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContainerPart
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    container_id = auto_field(required=False)


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
    containers_r = ma.fields.Nested(ProductContainerSchema, many=True)
    parts_r = ma.fields.Nested(ProductPartSchema, many=True)


class ContainerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Container
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    parts_r = ma.fields.Nested(ContainerPartSchema, many=True)


class PartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Part
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)


class ProductQueryArgSchema(ma.Schema):
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True, required=False)
    name = ma.fields.Str(required=False)


class PhotoSchema(ma.Schema):
    photo = ma.fields.Raw(type="string", format="binary")
