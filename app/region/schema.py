import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.region.models import Region
from app.base import session
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class RegionJsonSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Region


class RegionLoadSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Region
        include_fk = True
        load_instance = True
        sqla_session = session


class PagRegionSchema(ma.Schema):
    data = ma.fields.Nested(RegionJsonSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
