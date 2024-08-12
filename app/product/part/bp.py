import os
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.product.models import Part, PartLot
from app.product.schema import (
    OneProductInvoiceStatsQuery,
    PagPartSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    PartSchema,
    StandaloneProductInvoiceStats,
    StandaloneProductWarehouseStats,
)
from app.base import session
from app.user.models import User
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, msg_response, token_required
from app.utils.schema import ResponseSchema, TokenSchema
from app.warehouse.models import Warehouse


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
        warehouse_id = args.pop("warehouse_id", None)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        try:
            query = Part.query.filter_by(**args).order_by(Part.created_at.desc())
            if warehouse_id:
                query = (
                    query.join(PartLot, PartLot.part_id == Part.id)
                    .join(Invoice, Invoice.id == PartLot.invoice_id)
                    .where(Invoice.warehouse_receiver_id == warehouse_id)
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


@part.get("/<part_id>/warehouse-stats/")
@token_required
@part.arguments(TokenSchema, location="headers")
@part.response(200, StandaloneProductWarehouseStats)
def standalone_part_warehouse_stats(c, token, part_id):
    Part.get_by_id(part_id)
    total_quantity_sum = (
        session.query(func.sum(PartLot.quantity), func.sum(PartLot.total_sum))
        .join(Invoice, PartLot.invoice_id == Invoice.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            PartLot.quantity != 0,
            PartLot.part_id == part_id,
        )
        .all()
    )
    total_quantity, total_sum = total_quantity_sum[0]
    warehouse_data = (
        session.query(
            Warehouse.id,
            Warehouse.name,
            func.sum(PartLot.quantity).label("total_quantity"),
            func.sum(PartLot.total_sum).label("total_sum"),
        )
        .join(Invoice, PartLot.invoice_id == Invoice.id)
        .join(Warehouse, Invoice.warehouse_receiver_id == Warehouse.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            PartLot.quantity != 0,
            PartLot.part_id == part_id,
        )
        .group_by(Warehouse.id, Warehouse.name)
        .all()
    )
    response = {
        "total_quantity": total_quantity,
        "total_sum": total_sum,
        "warehouse_data": warehouse_data,
    }
    return response


@part.get("/<part_id>/invoice-stats/")
@token_required
@part.arguments(TokenSchema, location="headers")
@part.arguments(OneProductInvoiceStatsQuery, location="query")
@part.response(200, StandaloneProductInvoiceStats(many=True))
def standalone_part_invoice_stats(c, token, args, part_id):
    status_filter = args.pop("status", None)
    type_filter = args.pop("type", None)
    user_id_filter = args.pop("user_id", None)
    date_filter = args.pop("date", None)
    query = (
        session.query(
            Invoice.id,
            Invoice.number,
            Invoice.status,
            Invoice.type,
            Invoice.created_at,
            User.full_name.label("responsible"),
            func.sum(PartLot.total_sum).label("part_total_sum"),
            Invoice.price.label("invoice_total_sum"),
        )
        .join(PartLot, PartLot.invoice_id == Invoice.id)
        .join(User, Invoice.user_id == User.id)
        .filter(PartLot.part_id == part_id)
    )

    # Добавление фильтров
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if type_filter:
        query = query.filter(Invoice.type == type_filter)
    if user_id_filter:
        query = query.filter(Invoice.user_id == user_id_filter)
    if date_filter:
        query = query.filter(func.date(Invoice.created_at) == date_filter)

    invoices_with_part = query.group_by(
        Invoice.id,
        Invoice.number,
        Invoice.status,
        Invoice.type,
        Invoice.created_at,
        User.full_name,
        Invoice.price,
    ).all()
    return invoices_with_part
