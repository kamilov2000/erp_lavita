import os
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import ProductUnitSchema
from app.product.models import Container, Part, Product, ProductLot, ProductUnit
from app.product.schema import (
    AllProductsStats,
    MarkupsArray,
    PagProductSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    ProductSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema
from app.warehouse.models import Warehouse


product = Blueprint(
    "product", __name__, url_prefix="/product", description="Операции на Продуктах"
)


@product.route("/")
class ProductAllView(MethodView):
    @token_required
    @product.arguments(ProductQueryArgSchema, location="query")
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, PagProductSchema)
    def get(c, self, args, token):
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
        try:
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
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
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
    @product.arguments(ProductSchema)
    @product.arguments(TokenSchema, location="headers")
    @product.response(400, ResponseSchema)
    @product.response(201, ProductSchema)
    def post(c, self, new_data, token):
        """Add a new product"""
        try:
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@product.route("/<product_id>/")
class ProductById(MethodView):
    @token_required
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, ProductSchema)
    def get(c, self, token, product_id):
        """Get product by ID"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @product.arguments(ProductSchema)
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, ProductSchema)
    def put(c, self, update_data, token, product_id):
        """Update existing product"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        try:
            update_data.id = product_id
            session.merge(update_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return item

    @token_required
    @product.arguments(TokenSchema, location="headers")
    @product.response(204)
    def delete(c, self, token, product_id):
        """Delete product"""
        try:
            Product.delete(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@product.post("/<product_id>/update_photo/")
@token_required
@product.arguments(PhotoSchema, location="files")
@product.arguments(TokenSchema, location="headers")
@product.response(400, ResponseSchema)
@product.response(200, ProductSchema)
def change_photo(cur_user, photo, token, product_id):
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
@product.arguments(TokenSchema, location="headers")
@product.response(400, ResponseSchema)
@product.response(200, ProductUnitSchema(many=True))
def get_product_units(cur_user, token, product_id, warehouse_id):
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
@product.arguments(TokenSchema, location="headers")
@product.response(200, AllProductsStats)
def all_product_stats(cur_user, token):
    return {
        "products": Product.query.all(),
        "containers": Container.query.all(),
        "parts": Part.query.all(),
    }


@product.post("/check_markups/")
@token_required
@product.arguments(TokenSchema, location="headers")
@product.arguments(MarkupsArray)
@product.response(200, ResponseSchema)
def check_markup(c, token, data):
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
