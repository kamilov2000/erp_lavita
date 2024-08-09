import os
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Part
from app.product.schema import (
    PagPartSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    PartSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema


part = Blueprint(
    "part", __name__, url_prefix="/part", description="Операции на Деталях"
)


@part.route("/")
class PartAllView(MethodView):
    @token_required
    @part.arguments(ProductQueryArgSchema, location="query")
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PagPartSchema)
    def get(c, self, args, token):
        """List parts"""
        page = args.pop("page", 1)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        try:
            query = Part.query.filter_by(**args)
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
    @part.arguments(PartSchema)
    @part.arguments(TokenSchema, location="headers")
    @part.response(400, ResponseSchema)
    @part.response(201, PartSchema)
    def post(c, self, new_data, token):
        """Add a new part"""
        try:
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@part.route("/<part_id>/")
class PartById(MethodView):
    @token_required
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PartSchema)
    def get(c, self, token, part_id):
        """Get part by ID"""
        try:
            item = Part.get_by_id(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @part.arguments(PartSchema)
    @part.arguments(TokenSchema, location="headers")
    @part.response(200, PartSchema)
    def put(c, self, update_data, token, part_id):
        """Update existing part"""
        try:
            item = Part.get_by_id(part_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = part_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @part.arguments(TokenSchema, location="headers")
    @part.response(204)
    def delete(c, self, token, part_id):
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
