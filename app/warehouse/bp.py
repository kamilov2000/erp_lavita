from sqlalchemy import select
from app.invoice.models import Invoice
from app.invoice.schema import PagWarehouseHistorySchema
from app.user.models import User
from app.user.schema import UserSchema
from app.utils.func import msg_response, token_required
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.warehouse.models import Warehouse
from app.warehouse.schema import (
    PagWarehouseSchema,
    PaginateQueryArgSchema,
    WarehouseDetailSchema,
    WarehouseQueryArgSchema,
    WarehouseSchema,
    WarehouseStatsSchema,
)
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
    @warehouse.response(200, PagWarehouseSchema)
    def get(c, self, args, token):
        """List warehouses"""
        user_ids = args.pop("user_ids", None)
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
            query = Warehouse.query.filter_by(**args)
            if user_ids:
                query = query.join(Warehouse.users).filter(User.id.in_(user_ids))
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
    @warehouse.response(200, WarehouseDetailSchema)
    def get(c, self, token, warehouse_id):
        """Get warehouse by ID"""
        try:
            item = Warehouse.get_by_id(warehouse_id)
        except ItemNotFoundError:
            abort(404, message="Warehouse not found.")
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
            abort(404, message="Warehouse not found.")
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
            abort(404, message="Warehouse not found.")


@warehouse.get("/<warehouse_id>/responsible_users/")
@token_required
@warehouse.arguments(TokenSchema, location="headers")
@warehouse.response(200, UserSchema(many=True))
def get_responsible_users(c, token, warehouse_id):
    try:
        item = Warehouse.get_by_id(warehouse_id)
    except ItemNotFoundError:
        abort(404, message="Warehouse not found.")
    return item.users


@warehouse.get("/<warehouse_id>/history/")
@token_required
@warehouse.arguments(PaginateQueryArgSchema, location="query")
@warehouse.arguments(TokenSchema, location="headers")
@warehouse.response(200, PagWarehouseHistorySchema)
def get_history(c, args, token, warehouse_id):
    page = args.pop("page", 1)
    try:
        limit = int(args.pop("limit", 10))
        if limit <= 0:
            limit = 10
    except ValueError:
        limit = 10
    try:
        sender_invoices = session.query(Invoice).filter(
            Invoice.warehouse_sender_id == warehouse_id
        )

        # Query for receiver invoices
        receiver_invoices = session.query(Invoice).filter(
            Invoice.warehouse_receiver_id == warehouse_id
        )

        # Combine the queries using union_all
        query = sender_invoices.union_all(receiver_invoices).order_by(
            Invoice.created_at
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


@warehouse.get("/stats/")
@token_required
@warehouse.arguments(TokenSchema, location="headers")
@warehouse.response(200, WarehouseStatsSchema)
def get_stats(c, token):
    warehouses = session.execute(select(Warehouse)).scalars().all()
    total_capacity = 0
    total_price = 0
    for warehouse in warehouses:
        total_capacity += warehouse.calc_capacity()
        total_price += warehouse.calc_total_price()
    res = {
        "total_capacity": total_capacity,
        "total_price": total_price,
        "warehouses": warehouses,
    }
    return res
