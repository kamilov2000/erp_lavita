from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field
import marshmallow as ma
from sqlalchemy import func

from app.product.models import Markup, MarkupFilter
from app.base import session
from app.utils.schema import PaginationSchema


class FilterQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    is_active = ma.fields.Bool(required=False)
    product_id = ma.fields.Int(required=False)


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
    product_name = ma.fields.Method("get_product_name")
    markups_quantity = ma.fields.Method("get_markups_quantity")
    used_markups_quantity = ma.fields.Method("get_used_markups_quantity")
    unused_markups_quantity = ma.fields.Method("get_unused_markups_quantity")
    markups = ma.fields.Nested(MarkupSchema(many=True))

    @staticmethod
    def get_product_name(obj):
        return obj.product.name

    @staticmethod
    def get_markups_quantity(obj):
        return len(obj.markups)

    @staticmethod
    def get_used_markups_quantity(obj):
        return (
            session.query(func.count(Markup.id))
            .join(Markup.filters)
            .where(Markup.is_used.is_(True), MarkupFilter.id == obj.id)
            .scalar()
        )

    @staticmethod
    def get_unused_markups_quantity(obj):
        return (
            session.query(func.count(Markup.id))
            .join(Markup.filters)
            .where(Markup.is_used.is_(False), MarkupFilter.id == obj.id)
            .scalar()
        )


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
