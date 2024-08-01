import os
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Container
from app.product.schema import PhotoSchema, ProductQueryArgSchema, ContainerSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema


container = Blueprint(
    "container", __name__, url_prefix="/container", description="Операции на Тарах"
)


@container.route("/")
class ContainerAllView(MethodView):
    @container.arguments(ProductQueryArgSchema, location="query")
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, ContainerSchema(many=True))
    def get(self, args, token):
        """List containers"""
        return Container.query.filter_by(**args).all()

    @container.arguments(ContainerSchema)
    @container.arguments(TokenSchema, location="headers")
    @container.response(400, ResponseSchema)
    @container.response(201, ContainerSchema)
    def post(self, new_data, token):
        """Add a new container"""
        try:
            session.add(new_data)
            session.commit()
        except:
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@container.route("/<container_id>/")
class ContainerById(MethodView):
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, ContainerSchema)
    def get(self, token, container_id):
        """Get container by ID"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @container.arguments(ContainerSchema)
    @container.arguments(TokenSchema, location="headers")
    @container.response(200, ContainerSchema)
    def put(self, update_data, token, container_id):
        """Update existing container"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = container_id
        session.merge(update_data)
        session.commit()
        return item

    @container.arguments(TokenSchema, location="headers")
    @container.response(204)
    def delete(self, token, container_id):
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
    print(cur_user)
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
