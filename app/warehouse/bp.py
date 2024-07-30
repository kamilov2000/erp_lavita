from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.warehouse.models import Warehouse
from app.warehouse.schema import WarehouseQueryArgSchema, WarehouseSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import TokenSchema


warehouse = Blueprint(
    "warehouse", __name__, url_prefix="/warehouse", description="Операции на Скаладах"
)


@warehouse.route("/")
class WarehouseAllView(MethodView):
    @warehouse.arguments(WarehouseQueryArgSchema, location="query")
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema(many=True))
    def get(self, args, token):
        """List warehouses"""
        return Warehouse.query.filter_by(**args).all()

    @warehouse.arguments(WarehouseSchema)
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(201, WarehouseSchema)
    def post(self, new_data, token):
        """Add a new warehouse"""
        session.add(new_data)
        session.commit()
        return new_data


@warehouse.route("/<warehouse_id>/")
class WarehouseById(MethodView):
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema)
    def get(self, token, warehouse_id):
        """Get warehouse by ID"""
        try:
            item = Warehouse.get_by_id(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @warehouse.arguments(WarehouseSchema)
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema)
    def put(self, update_data, token, warehouse_id):
        """Update existing warehouse"""
        try:
            item = Warehouse.get_by_id(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        WarehouseSchema().load(update_data, instance=item, partial=True)
        session.commit()
        return item

    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(204)
    def delete(self, token, warehouse_id):
        """Delete warehouse"""
        try:
            Warehouse.delete(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
