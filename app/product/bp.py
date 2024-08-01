import os
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Product
from app.product.schema import PhotoSchema, ProductQueryArgSchema, ProductSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema


product = Blueprint(
    "product", __name__, url_prefix="/product", description="Операции на Продуктах"
)


@product.route("/")
class ProductAllView(MethodView):
    @product.arguments(ProductQueryArgSchema, location="query")
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, ProductSchema(many=True))
    def get(self, args, token):
        """List products"""
        return Product.query.filter_by(**args).all()

    @product.arguments(ProductSchema)
    @product.arguments(TokenSchema, location="headers")
    @product.response(400, ResponseSchema)
    @product.response(201, ProductSchema)
    def post(self, new_data, token):
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
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, ProductSchema)
    def get(self, token, product_id):
        """Get product by ID"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @product.arguments(ProductSchema)
    @product.arguments(TokenSchema, location="headers")
    @product.response(200, ProductSchema)
    def put(self, update_data, token, product_id):
        """Update existing product"""
        try:
            item = Product.get_by_id(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = product_id
        session.merge(update_data)
        session.commit()
        return item

    @product.arguments(TokenSchema, location="headers")
    @product.response(204)
    def delete(self, token, product_id):
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
    print(cur_user)
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
