from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import marshmallow as ma
from app.invoice.models import (
    Invoice,
    InvoiceComment,
    InvoiceLog,
    InvoiceStatuses,
    InvoceTypes,
)


class InvoiceQueryArgSchema(ma.Schema):
    type = ma.fields.Enum(InvoceTypes, by_value=True, required=False)
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

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    containers = ma.fields.Nested("ContainerSchema", many=True)
    parts = ma.fields.Nested("PartSchema", many=True)


class ProductionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    type = ma.fields.Constant(InvoceTypes.PRODUCTION.value)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    containers = ma.fields.Nested("ContainerSchema", many=True)
    products = ma.fields.Nested("ProductSchema", many=True)


class ExpenseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    type = ma.fields.Constant(InvoceTypes.EXPENSE.value)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    containers = ma.fields.Nested("ContainerSchema", many=True)
    products = ma.fields.Nested("ProductSchema", many=True)
    parts = ma.fields.Nested("PartSchema", many=True)


class TransferSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    type = ma.fields.Constant(InvoceTypes.TRANSFER.value)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    containers = ma.fields.Nested("ContainerSchema", many=True)
    products = ma.fields.Nested("ProductSchema", many=True)
    parts = ma.fields.Nested("PartSchema", many=True)


class InvoiceCommentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceComment
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class InvoiceLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = InvoiceLog
        include_fk = True
        load_instance = True

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)
    curr_status = ma.fields.Enum(InvoiceStatuses, by_value=True)
    prev_status = ma.fields.Enum(InvoiceStatuses, by_value=True)
