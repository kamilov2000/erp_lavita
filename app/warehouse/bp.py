from app.utils.func import msg_response, token_required
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.warehouse.models import Warehouse
from app.warehouse.schema import WarehouseQueryArgSchema, WarehouseSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema, TokenSchema


warehouse = Blueprint(
    "warehouse", __name__, url_prefix="/warehouse", description="Операции на Скаладах"
)


@warehouse.route("/")
class WarehouseAllView(MethodView):
    @token_required
    @warehouse.arguments(WarehouseQueryArgSchema, location="query")
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema(many=True))
    def get(c, self, args, token):
        """List warehouses"""
        return Warehouse.query.filter_by(**args).all()

    @token_required
    @warehouse.arguments(WarehouseSchema)
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(400, ResponseSchema)
    @warehouse.response(201, WarehouseSchema)
    def post(c, self, new_data, token):
        """Add a new warehouse"""
        try:
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@warehouse.route("/<warehouse_id>/")
class WarehouseById(MethodView):
    @token_required
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema)
    def get(c, self, token, warehouse_id):
        """Get warehouse by ID"""
        try:
            item = Warehouse.get_by_id(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @warehouse.arguments(WarehouseSchema)
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(200, WarehouseSchema)
    def put(c, self, update_data, token, warehouse_id):
        """Update existing warehouse"""
        try:
            item = Warehouse.get_by_id(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = warehouse_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @warehouse.arguments(TokenSchema, location="headers")
    @warehouse.response(204)
    def delete(c, self, token, warehouse_id):
        """Delete warehouse"""
        try:
            Warehouse.delete(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
