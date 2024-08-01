from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import marshmallow as ma
from app.base import session
from app.invoice.models import (
    File,
    Invoice,
    InvoiceComment,
    InvoiceLog,
    InvoiceStatuses,
    InvoiceTypes,
)
from app.product.models import ContainerLot, PartLot, ProductLot


class ProductLotSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ProductLot
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    invoice_id = auto_field(dump_only=True)


class ContainerLotSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContainerLot
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    invoice_id = auto_field(dump_only=True)


class PartLotSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PartLot
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    invoice_id = auto_field(dump_only=True)


class InvoiceQueryArgSchema(ma.Schema):
    type = ma.fields.Enum(InvoiceTypes, by_value=True, required=False)
    number = ma.fields.Str(required=False)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, required=False)
    warehouse_sender_id = ma.fields.Int(required=False)
    warehouse_receiver_id = ma.fields.Int(required=False)
    user_id = ma.fields.Int(required=False)


class InvoiceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    part_lots = ma.fields.Nested(PartLotSchema, many=True)
    files = ma.fields.Nested("FileSchema", many=True, dump_only=True)

    @ma.post_load
    def calc_price(self, data, **kwargs):
        invoice = Invoice(**data)
        invoice.price = (
            invoice.calc_container_lots_price() + invoice.calc_part_lots_price()
        )
        session.commit()
        return data


class ProductionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    product_lots = ma.fields.Nested(ProductLotSchema, many=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    files = ma.fields.Nested("FileSchema", many=True, dump_only=True)

    @ma.post_load
    def calc_price(self, data, **kwargs):
        invoice = Invoice(**data)
        invoice.price = (
            invoice.calc_container_lots_price() + invoice.calc_product_lots_price()
        )
        session.commit()
        return data


class ExpenseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    product_lots = ma.fields.Nested(ProductLotSchema, many=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    part_lots = ma.fields.Nested(PartLotSchema, many=True)
    files = ma.fields.Nested("FileSchema", many=True, dump_only=True)

    @ma.post_load
    def calc_price(self, data, **kwargs):
        invoice = Invoice(**data)
        invoice.price = (
            invoice.calc_container_lots_price()
            + invoice.calc_product_lots_price()
            + invoice.calc_part_lots_price()
        )
        session.commit()
        return data


class TransferSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    product_lots = ma.fields.Nested(ProductLotSchema, many=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    part_lots = ma.fields.Nested(PartLotSchema, many=True)
    files = ma.fields.Nested("FileSchema", many=True, dump_only=True)

    @ma.post_load
    def calc_price(self, data, **kwargs):
        invoice = Invoice(**data)
        invoice.price = (
            invoice.calc_container_lots_price()
            + invoice.calc_product_lots_price()
            + invoice.calc_part_lots_price
        )
        session.commit()
        return data


class InvoiceCommentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceComment
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class InvoiceLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceLog
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    curr_status = ma.fields.Enum(InvoiceStatuses, by_value=True)
    prev_status = ma.fields.Enum(InvoiceStatuses, by_value=True)


class FileWebSchema(ma.Schema):
    files = ma.fields.List(ma.fields.Raw(type="file"))


class FileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = File
        include_fk = True
        load_instance = True
        sqla_session = session

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
