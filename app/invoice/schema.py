from collections import defaultdict
from datetime import datetime
from typing import List
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
import marshmallow as ma
from sqlalchemy.orm import joinedload

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
    Markup,
    Part,
    PartLot,
    Product,
    ProductLot,
    ProductUnit,
    Container,
)
from app.utils.exc import ItemNotFoundError, NotRightQuantity, ValidateError
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
    price = auto_field(dump_only=True)
    product_name = ma.fields.Method("get_product_name")
    markups = ma.fields.List(ma.fields.Str())

    @staticmethod
    def get_product_name(obj):
        return obj.product.name

    @ma.post_load
    def calc_price(self, data, **kwargs):
        quantity = data.get("quantity")
        product_id = data.get("product_id")
        product = (
            session.query(Product)
            .options(joinedload(Product.containers_r), joinedload(Product.parts_r))
            .get(product_id)
        )
        if not product:
            raise ItemNotFoundError("Product not found")
        total_cost = 0.0

        # Calculate cost for containers
        for product_container in product.containers_r:
            required_quantity = product_container.quantity * quantity
            cost = ContainerLot.calculate_fifo_cost(
                ContainerLot.container_id == product_container.container_id,
                required_quantity,
                product_container.container_id,
            )
            total_cost += cost

        # Calculate cost for parts
        for product_part in product.parts_r:
            required_quantity = product_part.quantity * quantity
            cost = PartLot.calculate_fifo_cost(
                PartLot.part_id == product_part.part_id,
                required_quantity,
                product_part.part_id,
            )
            total_cost += cost

        data["price"] = total_cost / quantity if quantity else 0.0
        data["total_sum"] = total_cost
        if len(data["markups"]) != quantity:
            raise NotRightQuantity("Not right quantity and markups list of array")
        exist_markups = Markup.query.where(Markup.id.in_(data["markups"])).all()
        for ex_m in exist_markups:
            if ex_m.is_used:
                raise ValidateError("Markup is already used")
            ex_m.is_used = True
            ex_m.date_of_use = datetime.now()
        units_arr = [ProductUnit(id=markup) for markup in data["markups"]]
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
        container_id = data.get("container_id")
        if data.get("price") is not None:
            data["total_sum"] = quantity * data.get("price")
        else:
            container = (
                session.query(Container)
                .options(joinedload(Container.parts_r))
                .get(container_id)
            )
            if not container:
                raise ItemNotFoundError("Container not found")
            total_cost = 0.0
            for container_part in container.parts_r:
                required_quantity = container_part.quantity * quantity
                cost = PartLot.calculate_fifo_cost(
                    PartLot.part_id == container_part.part_id,
                    required_quantity,
                    container_part.part_id,
                )
                total_cost += cost
            data["price"] = total_cost / quantity if quantity else 0.0
            data["total_sum"] = total_cost
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
        return data


class InvoiceQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    number = ma.fields.Str(required=False)
    status = ma.fields.Enum(InvoiceStatuses, by_value=True, required=False)
    warehouse_sender_id = ma.fields.Int(required=False)
    warehouse_receiver_id = ma.fields.Int(required=False)
    user_id = ma.fields.Int(required=False)


class ProductUnitMoveWebSchema(ma.Schema):
    markup = ma.fields.Str()
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
    warehouse_receiver_name = ma.fields.Method("get_warehouse_receiver_name")


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
    warehouse_receiver_name = ma.fields.Method("get_warehouse_receiver_name")


class ExpenseSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        exclude = ["warehouse_receiver_id"]
        sqla_session = session
        unknown = ma.INCLUDE  # Add this line to include unknown fields

    product_unit_markups = ma.fields.Nested(
        ProductUnitMoveWebSchema(many=True), required=False, load_only=True
    )
    container_ids = ma.fields.Nested(
        ContainerMoveSchema(many=True), required=False, load_only=True
    )
    part_ids = ma.fields.Nested(
        PartMoveSchema(many=True), required=False, load_only=True
    )
    warehouse_sender_address = ma.fields.Method("get_warehouse_sender_address")
    warehouse_sender_name = ma.fields.Method("get_warehouse_sender_name")

    @ma.pre_load
    def clear_products(self, data, **kwargs):
        product_unit_markups = data.pop("product_unit_markups", [])
        with session.no_autoflush:
            if product_unit_markups:
                expended_products = {}
                for obj in product_unit_markups:
                    unit: ProductUnit | None = ProductUnit.query.get(obj["markup"])
                    if unit:
                        old_lot = unit.product_lot
                        old_lot.quantity -= 1
                        old_lot.calc_total_sum()
                        if not expended_products.get(old_lot.product_id):
                            expended_products[old_lot.product_id] = {}
                            expended_products[old_lot.product_id]["quantity"] = 1
                            expended_products[old_lot.product_id][
                                "price"
                            ] = old_lot.price
                            expended_products[old_lot.product_id]["units"] = [unit]
                        else:
                            expended_products[old_lot.product_id]["quantity"] += 1
                            expended_products[old_lot.product_id]["units"].append(unit)
                        if obj["with_container"] is False:
                            for container_r in old_lot.product.containers_r:
                                c_lot = (
                                    ContainerLot.query.join(
                                        Invoice, Invoice.id == ContainerLot.invoice_id
                                    )
                                    .filter(
                                        ContainerLot.container_id
                                        == container_r.container_id,
                                        # Invoice.warehouse_receiver_id
                                        # == data["warehouse_sender_id"],
                                        Invoice.type != InvoiceTypes.EXPENSE,
                                    )
                                    .order_by(ContainerLot.created_at.desc())
                                    .first()
                                )
                                if c_lot:
                                    c_lot.quantity += container_r.quantity
                if expended_products:
                    product_lots = []
                    for product_id, obj in expended_products.items():
                        lot = ProductLot(
                            product_id=product_id,
                            quantity=obj.get("quantity"),
                            price=obj.get("price"),
                            units=obj.get("units"),
                        )
                        lot.calc_total_sum()
                        product_lots.append(lot)
                    data["product_lots"] = product_lots

            # container SECTION
            container_ids = data.pop("container_ids", [])
            if container_ids:
                expended_containers = []
                for obj in container_ids:
                    expended_containers.extend(
                        Container.decrease(
                            container_id=obj["container_id"],
                            decrease_quantity=obj["quantity"],
                            transfer=False,
                        )
                    )
                data["container_lots"] = expended_containers
            part_ids = data.pop("part_ids", [])
            if part_ids:
                expended_parts = []
                for obj in part_ids:
                    expended_parts.extend(
                        Part.decrease(
                            part_id=obj["part_id"],
                            decrease_quantity=obj["quantity"],
                            transfer=False,
                        )
                    )
                data["part_lots"] = expended_parts
        return data


class TransferSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True
        load_instance = True
        sqla_session = session
        unknown = ma.INCLUDE  # Add this line to include unknown fields

    product_unit_markups = ma.fields.List(
        ma.fields.Str(), required=False, load_only=True
    )
    container_ids = ma.fields.Nested(
        ContainerMoveSchema(many=True), required=False, load_only=True
    )
    part_ids = ma.fields.Nested(
        PartMoveSchema(many=True), required=False, load_only=True
    )
    # container_lots = ma.fields.Raw(dump_only=True, required=False)  # Add this line
    # part_lots = ma.fields.Raw(dump_only=True, required=False)  # Add this line

    warehouse_receiver_address = ma.fields.Method("get_warehouse_receiver_address")
    warehouse_sender_address = ma.fields.Method("get_warehouse_sender_address")
    warehouse_receiver_name = ma.fields.Method("get_warehouse_receiver_name")
    warehouse_sender_name = ma.fields.Method("get_warehouse_sender_name")

    @ma.pre_load
    def clear_products(self, data, **kwargs):
        data.pop("additionalProp1", [])
        product_unit_markups = data.pop("product_unit_markups", [])
        with session.no_autoflush:
            units: List[ProductUnit] = ProductUnit.query.filter(
                ProductUnit.id.in_(product_unit_markups)
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
                    quantity=total_quantity,
                    price=price,
                    product_id=product_id,
                    units=units,
                )
                new_lot.calc_total_sum()
                new_lots.append(new_lot)

                # Update units to reference the new lot
                for unit in units:
                    old_lot = unit.product_lot
                    old_lot.quantity -= 1
                    old_lot.calc_total_sum()
                    unit.product_lot = new_lot
            data["product_lots"] = new_lots

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
                data["container_lots"] = transferring_containers
            part_ids = data.pop("part_ids", [])
            if part_ids:
                transferring_parts = []
                for obj in part_ids:
                    transferring_parts.extend(
                        Part.decrease(
                            part_id=obj["part_id"],
                            decrease_quantity=obj["quantity"],
                            transfer=True,
                        )
                    )
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


class InvoiceDetailSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema, BaseInvoiceSchema):
    class Meta:
        model = Invoice
        include_fk = True

    warehouse_receiver_address = ma.fields.Method("get_warehouse_receiver_address")
    warehouse_sender_address = ma.fields.Method("get_warehouse_sender_address")
    comments = ma.fields.Nested(InvoiceCommentSchema, many=True)
    logs = ma.fields.Nested(InvoiceLogSchema, many=True)
    products = ma.fields.Method("get_products")
    containers = ma.fields.Method("get_containers")
    parts = ma.fields.Method("get_parts")

    def get_products(self, obj):
        products = {}
        for lot in obj.product_lots:
            product_name = lot.product.name
            if product_name not in products:
                products[product_name] = {
                    "name": product_name,
                    "quantity": 0,
                    "total_sum": 0.0,
                    "markups": [],
                    "updated_at": lot.updated_at,
                }
            products[product_name]["quantity"] += lot.quantity
            products[product_name]["total_sum"] += lot.total_sum or 0.0
            products[product_name]["markups"].extend(
                ProductUnitSchema().dump(lot.units, many=True)
            )
        return list(products.values())

    def get_containers(self, obj):
        containers = {}
        for lot in obj.container_lots:
            container_name = lot.container.name
            if container_name not in containers:
                containers[container_name] = {
                    "name": container_name,
                    "quantity": 0,
                    "total_sum": 0.0,
                }
            containers[container_name]["quantity"] += lot.quantity
            containers[container_name]["total_sum"] += lot.total_sum or 0.0
        return list(containers.values())

    def get_parts(self, obj):
        parts = {}
        for lot in obj.part_lots:
            part_name = lot.part.name
            if part_name not in parts:
                parts[part_name] = {
                    "name": part_name,
                    "quantity": 0,
                    "total_sum": 0.0,
                }
            parts[part_name]["quantity"] += lot.quantity
            parts[part_name]["total_sum"] += lot.total_sum or 0.0
        return list(parts.values())


class InvoiceQueryDraftSchema(ma.Schema):
    draft = ma.fields.Bool(default=False, required=False)
