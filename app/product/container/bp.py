import os
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Container
from app.product.schema import (
    PagContainerSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    ContainerSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema


container = Blueprint(
    "container", __name__, url_prefix="/container", description="Операции на Тарах"
)


@container.route("/")
class ContainerAllView(MethodView):
    @token_required
    @container.arguments(ProductQueryArgSchema, location="query")
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, PagContainerSchema)
    def get(c, self, args, token):
        """List containers"""
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
            query = Container.query.filter_by(**args).order_by(
                Container.created_at.desc()
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
    @container.arguments(ContainerSchema)
    @container.arguments(TokenSchema, location="headers")
    @container.response(400, ResponseSchema)
    @container.response(201, ContainerSchema)
    def post(c, self, new_data, token):
        """Add a new container"""
        try:
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@container.route("/<container_id>/")
class ContainerById(MethodView):
    @token_required
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, ContainerSchema)
    def get(c, self, token, container_id):
        """Get container by ID"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @container.arguments(ContainerSchema)
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, ContainerSchema)
    def put(c, self, update_data, token, container_id):
        """Update existing container"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = container_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @container.arguments(TokenSchema, location="headers")
    @container.response(204)
    def delete(c, self, token, container_id):
        """Delete container"""
        try:
            Container.delete(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@container.post("/<container_id>/update_photo/")
@token_required
@container.arguments(PhotoSchema, location="files")
@container.arguments(TokenSchema, location="headers")
@container.response(400, ResponseSchema)
@container.response(200, ContainerSchema)
def change_photo(cur_user, photo, token, container_id):
    container = Container.get_by_id(container_id)
    try:
        path = hash_image_save(photo.get("photo"), "container", container_id)
    except ItemNotFoundError:
        return msg_response("Photo not found", False), 400
    if container.photo is not None and container.photo != path:
        try:
            os.remove(container.photo)
        except FileNotFoundError:
            pass
    container.photo = path
    session.commit()
    return container
