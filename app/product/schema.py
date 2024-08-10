import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field
from sqlalchemy import func, select

from app.choices import InvoiceTypes, MeasumentTypes
from app.invoice.models import Invoice
from app.product.models import (
    Container,
    ContainerLot,
    ContainerPart,
    Part,
    PartLot,
    Product,
    ProductContainer,
    ProductLot,
    ProductPart,
)
from app.base import session
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class ProductContainerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ProductContainer
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    product_id = auto_field(dump_only=True)
    name = ma.fields.Method("get_name")
    price = ma.fields.Method("get_price")

    @staticmethod
    def get_name(obj: ProductContainer):
        return obj.container.name

    @staticmethod
    def get_price(obj: ProductContainer):
        return ContainerLot.calculate_fifo_cost(
            ContainerLot.container_id == obj.container_id,
            obj.quantity,
            obj.container_id,
            False,
        )


class ProductPartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ProductPart
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    product_id = auto_field(dump_only=True)
    name = ma.fields.Method("get_name")
    price = ma.fields.Method("get_price")

    @staticmethod
    def get_name(obj: ProductPart):
        return obj.part.name

    @staticmethod
    def get_price(obj: ProductPart):
        return PartLot.calculate_fifo_cost(
            PartLot.part_id == obj.part_id,
            obj.quantity,
            obj.part_id,
            False,
        )


class ContainerPartSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContainerPart
        include_fk = True
        load_instance = True
        sqla_session = session
        exclude = ["created_at", "updated_at", "id"]

    container_id = auto_field(dump_only=True)
    name = ma.fields.Method("get_name")
    price = ma.fields.Method("get_price")

    @staticmethod
    def get_name(obj: ContainerPart):
        return obj.part.name

    @staticmethod
    def get_price(obj: ContainerPart):
        return PartLot.calculate_fifo_cost(
            PartLot.part_id == obj.part_id,
            obj.quantity,
            obj.part_id,
            False,
        )


class ProductSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Product
        include_fk = True
        load_instance = True
        sqla_session = session
        datetimeformat = "%Y-%m-%d, %H:%M"

    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    containers_r = ma.fields.Nested(ProductContainerSchema, many=True)
    parts_r = ma.fields.Nested(ProductPartSchema, many=True)


class ContainerSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Container
        include_fk = True
        load_instance = True
        sqla_session = session

    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    parts_r = ma.fields.Nested(ContainerPartSchema, many=True)


class PartSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Part
        include_fk = True
        load_instance = True
        sqla_session = session

    photo = ma.fields.Raw(type="file")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)


class ProductQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True, required=False)
    name = ma.fields.Str(required=False)


class PhotoSchema(ma.Schema):
    photo = ma.fields.Raw(type="string", format="binary")


class PagProductSchema(ma.Schema):
    data = ma.fields.Nested(ProductSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PagContainerSchema(ma.Schema):
    data = ma.fields.Nested(ContainerSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PagPartSchema(ma.Schema):
    data = ma.fields.Nested(PartSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class ProductStatSchema(SQLAlchemySchema):
    class Meta:
        model = Product

    id = auto_field()
    type = ma.fields.Constant("product")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    photo = auto_field()
    name = auto_field()
    total_quantity = ma.fields.Method("get_product_total_quantity")
    total_sum = ma.fields.Method("get_product_total_sum")

    @staticmethod
    def get_product_total_quantity(obj):
        res = session.execute(
            select(func.sum(ProductLot.quantity))
            .join(Invoice, Invoice.id == ProductLot.invoice_id)
            .where(
                ProductLot.product_id == obj.id,
                Invoice.type.in_([InvoiceTypes.TRANSFER, InvoiceTypes.PRODUCTION]),
            )
        ).scalar()
        return res

    @staticmethod
    def get_product_total_sum(obj):
        res = session.execute(
            select(func.sum(ProductLot.price))
            .join(Invoice, Invoice.id == ProductLot.invoice_id)
            .where(
                ProductLot.product_id == obj.id,
                Invoice.type.in_([InvoiceTypes.TRANSFER, InvoiceTypes.PRODUCTION]),
            )
        ).scalar()
        return res


class ContainerStatSchema(SQLAlchemySchema):
    class Meta:
        model = Container

    id = auto_field()
    type = ma.fields.Constant("container")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    photo = auto_field()
    name = auto_field()
    total_quantity = ma.fields.Method("get_container_total_quantity")
    total_sum = ma.fields.Method("get_container_total_sum")

    @staticmethod
    def get_container_total_quantity(obj):
        res = session.execute(
            select(func.sum(ContainerLot.quantity))
            .join(Invoice, Invoice.id == ContainerLot.invoice_id)
            .where(
                ContainerLot.container_id == obj.id,
                Invoice.type != InvoiceTypes.EXPENSE,
            )
        ).scalar()
        return res

    @staticmethod
    def get_container_total_sum(obj):
        res = session.execute(
            select(func.sum(ContainerLot.price))
            .join(Invoice, Invoice.id == ContainerLot.invoice_id)
            .where(
                ContainerLot.container_id == obj.id,
                Invoice.type != InvoiceTypes.EXPENSE,
            )
        ).scalar()
        return res


class PartStatSchema(SQLAlchemySchema):
    class Meta:
        model = Part

    id = auto_field()
    type = ma.fields.Constant("part")
    measurement = ma.fields.Enum(MeasumentTypes, by_value=True)
    photo = auto_field()
    name = auto_field()
    total_quantity = ma.fields.Method("get_part_total_quantity")
    total_sum = ma.fields.Method("get_part_total_sum")

    @staticmethod
    def get_part_total_quantity(obj):
        res = session.execute(
            select(func.sum(PartLot.quantity))
            .join(Invoice, Invoice.id == PartLot.invoice_id)
            .where(
                PartLot.part_id == obj.id,
                Invoice.type.in_([InvoiceTypes.TRANSFER, InvoiceTypes.INVOICE]),
            )
        ).scalar()
        print(res)
        return res

    @staticmethod
    def get_part_total_sum(obj):
        res = session.execute(
            select(func.sum(PartLot.price))
            .join(Invoice, Invoice.id == PartLot.invoice_id)
            .where(
                PartLot.part_id == obj.id,
                Invoice.type.in_([InvoiceTypes.TRANSFER, InvoiceTypes.INVOICE]),
            )
        ).scalar()
        return res


class AllProductsStats(ma.Schema):
    products = ma.fields.Nested(ProductStatSchema, many=True)
    containers = ma.fields.Nested(ContainerStatSchema, many=True)
    parts = ma.fields.Nested(PartStatSchema, many=True)


class MarkupsArray(ma.Schema):
    markups = ma.fields.List(ma.fields.Str())
