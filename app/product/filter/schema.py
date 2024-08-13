from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field
import marshmallow as ma

from app.product.models import Markup, MarkupFilter
from app.base import session
from app.utils.schema import PaginationSchema


class FilterQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    is_active = ma.fields.Bool(required=False)


class MarkupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Markup
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at"]


class MarkupFilterDetailSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = MarkupFilter
        include_fk = True

    id = auto_field(dump_ony=True)
    updated_at = auto_field(dump_ony=True)
    markups = ma.fields.Nested(MarkupSchema(many=True))


class MarkupFilterLoadSchema(SQLAlchemySchema):
    class Meta:
        model = MarkupFilter
        include_fk = True
        load_instance = True
        sqla_session = session

    name = auto_field()
    product_id = auto_field()
    date_of_receive = auto_field()


class MarkupFilterUpdateSchema(SQLAlchemySchema):
    class Meta:
        model = MarkupFilter
        include_fk = True
        load_instance = True
        sqla_session = session

    name = auto_field()
    date_of_receive = auto_field()


class FileMarkupFilter(ma.Schema):
    file = ma.fields.Raw(type="string", format="binary")


class MarkupFilterListSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = MarkupFilter

    id = auto_field(dump_ony=True)
    updated_at = auto_field(dump_ony=True)


class PagMarkupFilterSchema(ma.Schema):
    data = ma.fields.Nested(MarkupFilterListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
