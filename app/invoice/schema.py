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
from app.product.models import (
    ContainerLot,
    Part,
    PartLot,
    ProductLot,
    ProductUnit,
    Container,
)
from app.utils.schema import BaseInvoiceSchema, DefaultDumpsSchema, PaginationSchema


class ProductUnitSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = ProductUnit


class ProductLotSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = ProductLot
        include_fk = True
        load_instance = True
        sqla_session = session

    invoice_id = auto_field(dump_only=True)
    total_sum = auto_field(dump_only=True)
    product_name = ma.fields.Method("get_product_name")

    @staticmethod
    def get_product_name(obj):
        return obj.product.name

    @ma.post_load
    def calc_price(self, data, **kwargs):
        quantity = data.get("quantity")
        data["total_sum"] = quantity * data.get("price")
        units_arr = [ProductUnit() for _ in range(quantity)]
        data["units"] = units_arr
        return data


class ContainerLotSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = ContainerLot
        include_fk = True
        load_instance = True
        sqla_session = session

    invoice_id = auto_field(dump_only=True)
    total_sum = auto_field(dump_only=True)
    container_name = ma.fields.Method("get_container_name")

    @staticmethod
    def get_container_name(obj):
        return obj.container.name

    @ma.post_load
    def calc_price(self, data, **kwargs):
        quantity = data.get("quantity")
        data["total_sum"] = quantity * data.get("price")
        # units_arr = [ContainerUnit() for _ in range(quantity)]
        # data["units"] = units_arr
        return data


class PartLotSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PartLot
        include_fk = True
        load_instance = True
        sqla_session = session

    invoice_id = auto_field(dump_only=True)
    total_sum = auto_field(dump_only=True)
    part_name = ma.fields.Method("get_part_name")

    @staticmethod
    def get_part_name(obj):
        return obj.part.name

    @ma.post_load
    def calc_price(self, data, **kwargs):
        quantity = data.get("quantity")
        data["total_sum"] = quantity * data.get("price")
        # units_arr = [PartUnit() for _ in range(quantity)]
        # data["units"] = units_arr
        return data


class InvoiceQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    number = ma.fields.Str(required=False)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, required=False)
    warehouse_sender_id = ma.fields.Int(required=False)
    warehouse_receiver_id = ma.fields.Int(required=False)
    user_id = ma.fields.Int(required=False)


class InvoiceSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]
        sqla_session = session

    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    part_lots = ma.fields.Nested(PartLotSchema, many=True)
    warehouse_receiver_address = ma.fields.Method("get_warehouse_receiver_address")


class ProductionSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_sender_id"]
        sqla_session = session

    product_lots = ma.fields.Nested(ProductLotSchema, many=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    warehouse_receiver_address = ma.fields.Method("get_warehouse_receiver_address")


class ExpenseSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_receiver_id"]
        sqla_session = session

    product_lots = ma.fields.Nested(ProductLotSchema, many=True)
    container_lots = ma.fields.Nested(ContainerLotSchema, many=True)
    part_lots = ma.fields.Nested(PartLotSchema, many=True)
    warehouse_sender_address = ma.fields.Method("get_warehouse_sender_address")


class ProductUnitMoveSchema(ma.Schema):
    id = ma.fields.Str()
    with_container = ma.fields.Bool()


class ContainerMoveSchema(ma.Schema):
    container_id = ma.fields.Int()
    quantity = ma.fields.Int()


class PartMoveSchema(ma.Schema):
    part_id = ma.fields.Int()
    quantity = ma.fields.Int()


class TransferSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        sqla_session = session

    product_unit_ids = ma.fields.Nested(
        ProductUnitMoveSchema(many=True), required=False, load_only=True
    )
    container_ids = ma.fields.Nested(
        ContainerMoveSchema(many=True), required=False, load_only=True
    )
    part_ids = ma.fields.Nested(
        PartMoveSchema(many=True), required=False, load_only=True
    )
    warehouse_receiver_address = ma.fields.Method("get_warehouse_receiver_address")
    warehouse_sender_name = ma.fields.Method("get_warehouse_sender_address")

    @ma.pre_load
    def clear_products(self, data, **kwargs):
        print(data)
        print("ITS PRE LOAD")
        product_unit_ids = data.pop("product_units", [])
        units = ProductUnit.query.filter(ProductUnit.id.in_(product_unit_ids)).all()
        if units:
            lot = units[0].product_lot
            data["product_lots"] = [
                ProductLot(
                    quantity=len(units),
                    price=lot.price,
                    product_id=lot.product_id,
                    units=units,
                )
            ]
        container_ids = data.pop("container_ids", [])
        if container_ids:
            for obj in container_ids:
                Container.decrease(
                    container_id=obj["container_id"], decrease_quantity=obj["quantity"]
                )
            data["container_lots"] = [ContainerLot(quantity=obj["quantity"], price)]
        part_ids = data.pop("part_ids", [])
        for obj in part_ids:
            Part.decrease(
                part_id=obj["container_id"], decrease_quantity=obj["quantity"]
            )
        return data


class InvoiceCommentSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = InvoiceComment
        include_fk = True
        load_instance = True
        sqla_session = session

    invoice_id = auto_field(dump_only=True)
    user_id = auto_field(dump_only=True)
    user_full_name = ma.fields.Method("get_user_full_name")

    @staticmethod
    def get_user_full_name(obj):
        return obj.user.full_name if obj.user else None


class InvoiceLogSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = InvoiceLog
        include_fk = True
        load_instance = True
        sqla_session = session

    curr_status = ma.fields.Enum(InvoiceStatuses, by_value=True)
    prev_status = ma.fields.Enum(InvoiceStatuses, by_value=True)
    user_full_name = ma.fields.Method("get_user_full_name")

    @staticmethod
    def get_user_full_name(obj):
        return obj.user.full_name if obj.user else None


class FileWebSchema(ma.Schema):
    files = ma.fields.List(ma.fields.Raw(type="file"))


class FileSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = File
        include_fk = True
        load_instance = True
        sqla_session = session


class PagInvoiceSchema(ma.Schema):
    data = ma.fields.Nested(InvoiceSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PagTransferSchema(ma.Schema):
    data = ma.fields.Nested(TransferSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PagExpenseSchema(ma.Schema):
    data = ma.fields.Nested(ExpenseSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PagProductionSchema(ma.Schema):
    data = ma.fields.Nested(ProductionSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class InvoiceHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Invoice
        include_fk = True

    user_id = auto_field(dump_only=True)
    price = auto_field(dump_only=True)
    quantity = auto_field(dump_only=True)
    type = ma.fields.Enum(InvoiceTypes, by_value=True, dump_only=True)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, dump_only=True)
    user_full_name = ma.fields.Method("get_user_full_name")

    @staticmethod
    def get_user_full_name(obj):
        return obj.user.full_name if obj.user else None


class PagWarehouseHistorySchema(ma.Schema):
    data = ma.fields.Nested(InvoiceHistorySchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
