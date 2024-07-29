from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Part
from app.product.schema import ProductQueryArgSchema, PartSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import TokenSchema


part = Blueprint(
    "part", __name__, url_prefix="/part", description="Операции на Деталях"
)


@part.route("/")
class PartAllView(MethodView):
    @part.arguments(ProductQueryArgSchema, location="query")
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PartSchema(many=True))
    def get(self, args, token):
        """List parts"""
        return Part.query.filter_by(**args).all()

    @part.arguments(PartSchema)
    @part.arguments(TokenSchema, location="headers")
    @part.response(201, PartSchema)
    def post(self, new_data, token):
        """Add a new part"""
        item = Part.create(**new_data)
        session.commit()
        return item


@part.route("/<part_id>/")
class PartById(MethodView):
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PartSchema)
    def get(self, token, part_id):
        """Get part by ID"""
        try:
            item = Part.get_by_id(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @part.arguments(PartSchema)
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PartSchema)
    def put(self, update_data, token, part_id):
        """Update existing part"""
        try:
            item = Part.get_by_id(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        item.update(update_data)
        item.commit()
        return item

    @part.arguments(TokenSchema, location="headers")
    @part.response(204)
    def delete(self, token, part_id):
        """Delete part"""
        try:
            Part.delete(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
