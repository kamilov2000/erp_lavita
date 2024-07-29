from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Product
from app.product.schema import ProductQueryArgSchema, ProductSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import TokenSchema


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
    @product.response(201, ProductSchema)
    def post(self, new_data, token):
        """Add a new product"""
        session.add(new_data)
        session.commit()
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
        item.update(update_data)
        item.commit()
        return item

    @product.arguments(TokenSchema, location="headers")
    @product.response(204)
    def delete(self, token, product_id):
        """Delete product"""
        try:
            Product.delete(product_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
