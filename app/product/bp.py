import os
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.invoice.schema import ProductUnitSchema
from app.product.models import Container, ContainerPart, Part, Product, ProductLot, ProductPart, ProductUnit
from app.product.schema import (
    AllProductsStats,
    MarkupsArray,
    OneProductInvoiceStatsQuery,
    PagProductSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    ProductSchema,
    StandaloneProductInvoiceStats,
    StandaloneProductWarehouseStats,
)
from app.base import session
from app.user.models import User
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, sql_exception_handler, token_required
from app.utils.schema import ResponseSchema
from app.warehouse.models import Warehouse


product = Blueprint(
    "product", __name__, url_prefix="/product", description="Операции на Продуктах"
)


@product.route("/")
class ProductAllView(MethodView):
    @token_required
    @sql_exception_handler
    @product.arguments(ProductQueryArgSchema, location="query")
    @product.response(200, PagProductSchema)
    def get(c, self, args):
        """List products"""
        page = args.pop("page", 1)
        warehouse_id = args.pop("warehouse_id", None)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        query = Product.query.filter_by(**args).order_by(Product.created_at.desc())
        if warehouse_id:
            query = (
                query.join(ProductLot, ProductLot.product_id == Product.id)
                .join(Invoice, Invoice.id == ProductLot.invoice_id)
                .where(Invoice.warehouse_receiver_id == warehouse_id)
            )
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit
        data = query.limit(limit).offset((page - 1) * limit).all()
        response = {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_count": total_count,
            },
        }

        return response

    @token_required
    @sql_exception_handler
    @product.arguments(ProductSchema)
    @product.response(400, ResponseSchema)
    @product.response(201, ProductSchema)
    def post(c, self, new_data):
        """Add a new product"""
        session.add(new_data)
        session.commit()
        return new_data


@product.route("/<product_id>/")
class ProductById(MethodView):
    @token_required
    @sql_exception_handler
    @product.response(200, ProductSchema)
    def get(c, self, product_id):
        """Get product by ID"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @sql_exception_handler
    @product.arguments(ProductSchema)
    @product.response(200, ProductSchema)
    def put(c, self, update_data, product_id):
        """Update existing product"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        for pr in item.parts_r:
            session.delete(pr)
        for pr in item.containers_r:
            session.delete(pr)
        update_data.id = product_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @sql_exception_handler
    @product.response(204)
    def delete(c, self, product_id):
        """Delete product"""
        try:
            Product.delete(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@product.post("/<product_id>/update_photo/")
@token_required
@sql_exception_handler
@product.arguments(PhotoSchema, location="files")
@product.response(400, ResponseSchema)
@product.response(200, ProductSchema)
def change_photo(cur_user, photo, product_id):
    product = Product.get_by_id(product_id)
    try:
        path = hash_image_save(photo.get("photo"), "product", product_id)
    except ItemNotFoundError:
        return msg_response("Photo not found", False), 400
    if product.photo is not None and product.photo != path:
        try:
            os.remove(product.photo)
        except FileNotFoundError:
            pass
    product.photo = path
    session.commit()
    return product


@product.get("/<product_id>/markups/from_warehouse/<warehouse_id>/")
@token_required
@sql_exception_handler
@product.response(400, ResponseSchema)
@product.response(200, ProductUnitSchema(many=True))
def get_product_units(cur_user, product_id, warehouse_id):
    try:
        Product.get_by_id(product_id)
    except ItemNotFoundError:
        return msg_response("Product not found", False), 400
    try:
        Warehouse.get_by_id(warehouse_id)
    except ItemNotFoundError:
        return msg_response("Product not found", False), 400
    units = session.execute(
        select(ProductUnit)
        .join(
            ProductLot,
            (ProductUnit.product_lot_id == ProductLot.id)
            & (ProductLot.product_id == product_id),
        )
        .join(
            Invoice,
            (Invoice.warehouse_receiver_id == warehouse_id)
            & (Invoice.id == ProductLot.invoice_id),
        )
        .filter()
    ).scalars()
    return units


@product.get("/stats/")
@token_required
@sql_exception_handler
@product.response(200, AllProductsStats)
def all_product_stats(cur_user):
    return {
        "products": Product.query.all(),
        "containers": Container.query.all(),
        "parts": Part.query.all(),
    }


@product.post("/check_markups/")
@token_required
@sql_exception_handler
@product.arguments(MarkupsArray)
@product.response(200, ResponseSchema)
def check_markup(c, data):
    problem_markups = []
    for markup in data["markups"]:
        try:
            ProductUnit.get_by_id(markup, str)
            problem_markups.append(markup)
        except ItemNotFoundError:
            problem_markups.append(markup)
    # ok = true if no problem markups
    ok = not bool(problem_markups)
    response = {"ok": ok, "data": None, "error": problem_markups if not ok else None}
    return response


@product.get("/<product_id>/warehouse-stats/")
@token_required
@sql_exception_handler
@product.response(200, StandaloneProductWarehouseStats)
def standalone_product_warehouse_stats(c, product_id):
    Product.get_by_id(product_id)
    total_quantity_sum = (
        session.query(func.sum(ProductLot.quantity), func.sum(ProductLot.total_sum))
        .join(Invoice, ProductLot.invoice_id == Invoice.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            ProductLot.quantity != 0,
            ProductLot.product_id == product_id,
        )
        .all()
    )
    total_quantity, total_sum = total_quantity_sum[0]
    warehouse_data = (
        session.query(
            Warehouse.id.label("warehouse_id"),
            Warehouse.name.label("warehouse_name"),
            func.sum(ProductLot.quantity).label("total_quantity"),
            func.sum(ProductLot.total_sum).label("total_sum"),
        )
        .join(Invoice, ProductLot.invoice_id == Invoice.id)
        .join(Warehouse, Invoice.warehouse_receiver_id == Warehouse.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            ProductLot.quantity != 0,
            ProductLot.product_id == product_id,
        )
        .group_by(Warehouse.id, Warehouse.name)
        .all()
    )
    response = {
        "total_quantity": total_quantity,
        "total_sum": total_sum,
        "warehouse_data": warehouse_data,
    }
    return response


@product.get("/<product_id>/invoice-stats/")
@token_required
@sql_exception_handler
@product.arguments(OneProductInvoiceStatsQuery, location="query")
@product.response(200, StandaloneProductInvoiceStats(many=True))
def standalone_product_invoice_stats(c, args, product_id):
    status_filter = args.pop("status", None)
    type_filter = args.pop("type", None)
    user_id_filter = args.pop("user_id", None)
    date_filter = args.pop("date", None)
    query = (
        session.query(
            Invoice.id.label("invoice_id"),
            Invoice.number.label("invoice_number"),
            Invoice.status.label("invoice_status"),
            Invoice.type.label("invoice_type"),
            Invoice.created_at.label("invoice_created_at"),
            func.concat(User.last_name, " ", User.first_name).label("user_full_name"),
            func.sum(ProductLot.total_sum).label("product_sum"),
            Invoice.price.label("invoice_total_sum"),
        )
        .join(ProductLot, ProductLot.invoice_id == Invoice.id)
        .join(User, Invoice.user_id == User.id)
        .filter(ProductLot.product_id == product_id)
    )

    # Добавление фильтров
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if type_filter:
        query = query.filter(Invoice.type == type_filter)
    if user_id_filter:
        query = query.filter(Invoice.user_id == user_id_filter)
    if date_filter:
        query = query.filter(func.date(Invoice.created_at) == date_filter)

    invoices_with_product = query.group_by(
        Invoice.id,
        Invoice.number,
        Invoice.status,
        Invoice.type,
        Invoice.created_at,
        func.concat(User.last_name, " ", User.first_name).label("responsible"),
        Invoice.price,
    ).all()
    current_app.logger.error(invoices_with_product)
    return invoices_with_product
