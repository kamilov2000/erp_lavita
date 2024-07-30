import os
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Part
from app.product.schema import PhotoSchema, ProductQueryArgSchema, PartSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema


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
        session.add(new_data)
        session.commit()
        return new_data


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
        PartSchema().load(update_data, instance=item, partial=True)
        session.commit()
        return item

    @part.arguments(TokenSchema, location="headers")
    @part.response(204)
    def delete(self, token, part_id):
        """Delete part"""
        try:
            Part.delete(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@part.post("/<part_id>/update_photo/")
@token_required
@part.arguments(PhotoSchema, location="files")
@part.arguments(TokenSchema, location="headers")
@part.response(400, ResponseSchema)
@part.response(200, PartSchema)
def change_photo(cur_user, photo, token, part_id):
    print(cur_user)
    part = Part.get_by_id(part_id)
    try:
        path = hash_image_save(photo.get("photo"), "part", part_id)
    except ItemNotFoundError:
        return msg_response("Photo not found", False), 400
    if part.photo is not None and part.photo != path:
        try:
            os.remove(part.photo)
        except FileNotFoundError:
            pass
    part.photo = path
    session.commit()
    return part
