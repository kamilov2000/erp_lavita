from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import marshmallow as ma
from sqlalchemy import func

from app.base import session
from app.invoice.models import Invoice
from app.product.models import (
    Container,
    ContainerLot,
    Part,
    PartLot,
    Product,
    ProductLot,
)
from app.user.models import User
from app.utils.schema import DefaultDumpsSchema, PaginationSchema
from app.warehouse.models import Warehouse


class WarehouseSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True
        sqla_session = session

    users = ma.fields.Nested("UserSchema", many=True, dump_only=True)
    capacity = ma.fields.Method("get_capacity")
    user_ids = ma.fields.List(ma.fields.Int(), required=False, load_only=True)
    container_total_quantity = ma.fields.Method("get_calc_container_invoices_quantity")
    part_total_quantity = ma.fields.Method("get_calc_part_invoices_quantity")
    product_total_quantity = ma.fields.Method("get_calc_product_invoices_quantity")

    @staticmethod
    def get_calc_container_invoices_quantity(obj):
        return obj.calc_container_invoices_quantity()

    @staticmethod
    def get_calc_part_invoices_quantity(obj):
        return obj.calc_part_invoices_quantity()

    @staticmethod
    def get_calc_product_invoices_quantity(obj):
        return obj.calc_product_invoices_quantity()

    @ma.post_load
    def append_users(self, data, **kwargs):
        data["users"] = User.query.filter(User.id.in_(data.pop("user_ids", []))).all()
        return data

    @staticmethod
    def get_capacity(obj):
        return obj.calc_capacity()


class WarehouseDetailSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Warehouse
        include_fk = True
        load_instance = True
        sqla_session = session

    users = ma.fields.Nested("UserSchema", many=True, dump_only=True)
    capacity = ma.fields.Method("get_capacity")
    user_ids = ma.fields.List(ma.fields.Int(), required=False, load_only=True)
    total_price = ma.fields.Method("get_calc_total_price")
    container_total_price = ma.fields.Method("get_calc_container_invoices_price")
    part_total_price = ma.fields.Method("get_calc_part_invoices_price")
    product_total_price = ma.fields.Method("get_calc_product_invoices_price")
    container_total_quantity = ma.fields.Method("get_calc_container_invoices_quantity")
    part_total_quantity = ma.fields.Method("get_calc_part_invoices_quantity")
    product_total_quantity = ma.fields.Method("get_calc_product_invoices_quantity")
    products = ma.fields.Method("get_get_products")
    containers = ma.fields.Method("get_get_containers")
    parts = ma.fields.Method("get_get_parts")

    @ma.post_load
    def append_users(self, data, **kwargs):
        data["users"] = User.query.filter(User.id.in_(data.pop("user_ids", []))).all()
        return data

    @staticmethod
    def get_capacity(obj):
        return obj.calc_capacity()

    @staticmethod
    def get_calc_total_price(obj):
        return obj.calc_total_price()

    @staticmethod
    def get_calc_container_invoices_price(obj):
        return obj.calc_container_invoices_price()

    @staticmethod
    def get_calc_part_invoices_price(obj):
        return obj.calc_part_invoices_price()

    @staticmethod
    def get_calc_product_invoices_price(obj):
        return obj.calc_product_invoices_price()

    @staticmethod
    def get_calc_container_invoices_quantity(obj):
        return obj.calc_container_invoices_quantity()

    @staticmethod
    def get_calc_part_invoices_quantity(obj):
        return obj.calc_part_invoices_quantity()

    @staticmethod
    def get_calc_product_invoices_quantity(obj):
        return obj.calc_product_invoices_quantity()

    @staticmethod
    def get_get_products(obj):
        res = []
        product_info = (
            session.query(
                Product.name,
                func.sum(ProductLot.quantity),
                func.max(ContainerLot.updated_at),
            )
            .join(ProductLot)
            .join(Invoice)
            .filter(Invoice.warehouse_receiver_id == obj.id)
            .group_by(Product.name)
            .all()
        )
        for name, quantity, updated_at in product_info:
            res.append(
                {
                    "name": name,
                    "quantity": quantity,
                    "updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                }
            )
        return res

    @staticmethod
    def get_get_containers(obj):
        res = []
        container_info = (
            session.query(
                Container.name,
                func.sum(ContainerLot.quantity),
                func.max(ContainerLot.updated_at),
            )
            .join(ContainerLot)
            .join(Invoice)
            .filter(Invoice.warehouse_receiver_id == obj.id)
            .group_by(Container.name)
            .all()
        )
        for name, quantity, updated_at in container_info:
            res.append(
                {
                    "name": name,
                    "quantity": quantity,
                    "updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                }
            )
        return res

    @staticmethod
    def get_get_parts(obj):
        res = []
        part_info = (
            session.query(
                Part.name, func.sum(PartLot.quantity), func.max(ContainerLot.updated_at)
            )
            .join(PartLot)
            .join(Invoice)
            .filter(Invoice.warehouse_receiver_id == obj.id)
            .group_by(Part.name)
            .all()
        )
        for name, quantity, updated_at in part_info:
            res.append(
                {
                    "name": name,
                    "quantity": quantity,
                    "updated_at": updated_at.strftime(
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ),
                }
            )
        return res


class WarehouseQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    name = ma.fields.Str(required=False)
    user_ids = ma.fields.List(ma.fields.Int(), required=False)


class PagWarehouseSchema(ma.Schema):
    data = ma.fields.Nested(WarehouseSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
