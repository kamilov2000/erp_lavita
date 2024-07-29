from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.product.models import Container
from app.product.schema import ProductQueryArgSchema, ContainerSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import TokenSchema


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
    @container.response(201, ContainerSchema)
    def post(self, new_data, token):
        """Add a new container"""
        item = Container.create(**new_data)
        session.commit()
        return item


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
        item.update(update_data)
        item.commit()
        return item

    @container.arguments(TokenSchema, location="headers")
    @container.response(204)
    def delete(self, token, container_id):
        """Delete container"""
        try:
            Container.delete(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
