import marshmallow as ma
from marshmallow_sqlalchemy import auto_field

from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice


class ResponseSchema(ma.Schema):
    ok = ma.fields.Bool()
    data = ma.fields.Raw()
    error = ma.fields.Raw()


class TokenSchema(ma.Schema):
    x_access_token = ma.fields.Str(
        data_key="x-access-token",
        required=True,
        description="Access token for authentication",
        example="your_access_token_here",
    )


class DefaultDumpsSchema:

    id = auto_field(dump_only=True)
    created_at = auto_field(dump_only=True)
    updated_at = auto_field(dump_only=True)


class BaseInvoiceSchema:
    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    quantity = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    files = ma.fields.Nested("FileSchema", many=True, dump_only=True)
    user_full_name = ma.fields.Method("get_user_full_name")

    @ma.post_load
    def calc_price(self, data, **kwargs):
        invoice = Invoice(**data)
        data["price"] = (
            invoice.calc_container_lots_price()
            + invoice.calc_product_lots_price()
            + invoice.calc_part_lots_price()
        )
        data["quantity"] = (
            invoice.calc_container_lots_quantity()
            + invoice.calc_part_lots_quantity()
            + invoice.calc_product_lots_quantity()
        )
        return data

    @staticmethod
    def get_user_full_name(obj):
        return obj.user.full_name if obj.user else None

    @staticmethod
    def get_warehouse_receiver_address(obj):
        return obj.warehouse_receiver.address if obj.warehouse_receiver else None

    @staticmethod
    def get_warehouse_sender_address(obj):
        return obj.warehouse_sender.address if obj.warehouse_sender else None
