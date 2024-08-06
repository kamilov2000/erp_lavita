from collections import defaultdict
from typing import List
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


class ProductUnitMoveSchema(ma.Schema):
    id = ma.fields.Str()
    with_container = ma.fields.Bool()


class ContainerMoveSchema(ma.Schema):
    container_id = ma.fields.Int()
    quantity = ma.fields.Int()


class PartMoveSchema(ma.Schema):
    part_id = ma.fields.Int()
    quantity = ma.fields.Int()


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

    product_unit_ids = ma.fields.Nested(
        ProductUnitMoveSchema(many=True), required=False, load_only=True
    )
    container_ids = ma.fields.Nested(
        ContainerMoveSchema(many=True), required=False, load_only=True
    )
    part_ids = ma.fields.Nested(
        PartMoveSchema(many=True), required=False, load_only=True
    )
    warehouse_sender_address = ma.fields.Method("get_warehouse_sender_address")

    @ma.pre_load
    def clear_products(self, data, **kwargs):
        quantity = 0
        expense_price = 0
        product_unit_ids = data.pop("product_unit_ids", [])
        if product_unit_ids:
            for obj in product_unit_ids:
                unit: ProductUnit | None = ProductUnit.query.get(obj["id"])
                if unit:
                    old_lot = unit.product_lot
                    old_lot.quantity -= 1
                    expense_price += old_lot.product.self_cost
                    old_lot.calc_total_sum()
                    quantity += 1
                    if obj["with_container"] is False:
                        for container_r in old_lot.product.containers_r:
                            c_lot = (
                                ContainerLot.query.join(
                                    Invoice, Invoice.id == ContainerLot.invoice_id
                                )
                                .filter(
                                    ContainerLot.container_id
                                    == container_r.container_id,
                                    Invoice.warehouse_receiver_id
                                    == data["warehouse_sender_id"],
                                    Invoice.type != InvoiceTypes.EXPENSE,
                                )
                                .order_by(ContainerLot.created_at.desc())
                                .first()
                            )
                            c_lot += container_r.quantity

        # container SECTION
        container_ids = data.pop("container_ids", [])
        if container_ids:
            for obj in container_ids:
                Container.decrease(
                    container_id=obj["container_id"],
                    decrease_quantity=obj["quantity"],
                    transfer=False,
                )
                quantity += obj["quantity"]
        part_ids = data.pop("part_ids", [])
        if part_ids:
            for obj in part_ids:
                Part.decrease(
                    part_id=obj["part_id"],
                    decrease_quantity=obj["quantity"],
                    transfer=False,
                )
                quantity += obj["quantity"]
        data["quantity"] = quantity
        return data


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
        product_unit_ids = data.pop("product_units", [])
        units: List[ProductUnit] = ProductUnit.query.filter(
            ProductUnit.id.in_(product_unit_ids)
        ).all()
        # Group units by product_id and price
        grouped_units = defaultdict(list)
        for unit in units:
            key = (unit.product_lot.product_id, unit.product_lot.price)
            grouped_units[key].append(unit)

        new_lots = []
        for (product_id, price), units in grouped_units.items():
            # Calculate the total quantity for the new lot
            total_quantity = sum(unit.product_lot.quantity for unit in units)

            # Create a new ProductLot
            new_lot = ProductLot(
                quantity=total_quantity, price=price, product_id=product_id, units=units
            )
            new_lot.calc_total_sum()
            new_lots.append(new_lot)

            # Update units to reference the new lot
            for unit in units:
                old_lot = unit.product_lot
                old_lot.quantity -= 1
                old_lot.calc_total_sum()
                unit.product_lot = new_lot
        session.add_all(new_lots)

        # container SECTION
        container_ids = data.pop("container_ids", [])
        if container_ids:
            transferring_containers = []
            for obj in container_ids:
                transferring_containers.extend(
                    Container.decrease(
                        container_id=obj["container_id"],
                        decrease_quantity=obj["quantity"],
                        transfer=True,
                    )
                )
            session.add_all(transferring_containers)
            data["container_lots"] = transferring_containers
        part_ids = data.pop("part_ids", [])
        if part_ids:
            transferring_parts = []
            for obj in part_ids:
                transferring_parts.extend(
                    Part.decrease(
                        part_id=obj["container_id"],
                        decrease_quantity=obj["quantity"],
                        transfer=True,
                    )
                )
            session.add_all(transferring_parts)
            data["part_lots"] = transferring_parts
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
