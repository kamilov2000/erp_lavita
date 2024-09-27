import os
from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.product.models import Container, ContainerLot, ContainerPart
from app.product.schema import (
    ContainerUpdateSchema,
    OneProductInvoiceStatsQuery,
    PagContainerSchema,
    PhotoSchema,
    ProductQueryArgSchema,
    ContainerSchema,
    StandaloneProductInvoiceStats,
    StandaloneProductWarehouseStats,
)
from app.base import session
from app.user.models import User
from app.utils.exc import ItemNotFoundError
from app.utils.func import (
    hash_image_save,
    msg_response,
    sql_exception_handler,
    token_required,
)
from app.utils.schema import ResponseSchema
from app.warehouse.models import Warehouse


container = Blueprint(
    "container", __name__, url_prefix="/container", description="Операции на Тарах"
)


@container.route("/")
class ContainerAllView(MethodView):
    @token_required
    @sql_exception_handler
    @container.arguments(ProductQueryArgSchema, location="query")
    @container.response(200, PagContainerSchema)
    def get(c, self, args):
        """List containers"""
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
        query = Container.query.filter_by(**args).order_by(Container.created_at.desc())
        if warehouse_id:
            query = (
                query.join(ContainerLot, ContainerLot.container_id == Container.id)
                .join(Invoice, Invoice.id == ContainerLot.invoice_id)
                .where(Invoice.warehouse_receiver_id == warehouse_id)
            )
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit
        data = query.limit(limit).offset((page - 1) * limit).all()
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
    @sql_exception_handler
    @container.arguments(ContainerSchema)
    @container.response(400, ResponseSchema)
    @container.response(201, ContainerSchema)
    def post(c, self, new_data):
        """Add a new container"""
        session.add(new_data)
        session.commit()
        return new_data


@container.route("/<container_id>/")
class ContainerById(MethodView):
    @token_required
    @sql_exception_handler
    @container.response(200, ContainerSchema)
    def get(c, self, container_id):
        """Get container by ID"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @sql_exception_handler
    @container.arguments(ContainerUpdateSchema)
    @container.response(200, ContainerSchema)
    def put(c, self, update_data, container_id):
        """Update existing container"""
        try:
            item = Container.get_by_id(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        parts_r = update_data.pop("parts_r", [])
        if parts_r:
            for pr in item.parts_r:
                session.delete(pr)
            for part in parts_r:
                session.add(ContainerPart(container_id=container_id, **part))
        ContainerUpdateSchema().load(update_data, instance=item, partial=True)
        current_app.logger.error(item.__dict__)
        session.commit()
        return item

    @token_required
    @sql_exception_handler
    @container.response(204)
    def delete(c, self, container_id):
        """Delete container"""
        try:
            Container.delete(container_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@container.post("/<container_id>/update_photo/")
@token_required
@sql_exception_handler
@container.arguments(PhotoSchema, location="files")
@container.response(400, ResponseSchema)
@container.response(200, ContainerSchema)
def change_photo(cur_user, photo, container_id):
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


@container.get("/<container_id>/warehouse-stats/")
@token_required
@sql_exception_handler
@container.response(200, StandaloneProductWarehouseStats)
def standalone_container_warehouse_stats(c, container_id):
    Container.get_by_id(container_id)
    total_quantity_sum = (
        session.query(func.sum(ContainerLot.quantity), func.sum(ContainerLot.total_sum))
        .join(Invoice, ContainerLot.invoice_id == Invoice.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            ContainerLot.quantity != 0,
            ContainerLot.container_id == container_id,
        )
        .all()
    )
    total_quantity, total_sum = total_quantity_sum[0]
    warehouse_data = (
        session.query(
            Warehouse.id,
            Warehouse.name,
            func.sum(ContainerLot.quantity).label("total_quantity"),
            func.sum(ContainerLot.total_sum).label("total_sum"),
        )
        .join(Invoice, ContainerLot.invoice_id == Invoice.id)
        .join(Warehouse, Invoice.warehouse_receiver_id == Warehouse.id)
        .filter(
            Invoice.warehouse_receiver_id.isnot(None),
            Invoice.status == InvoiceStatuses.PUBLISHED,
            Invoice.type != InvoiceTypes.EXPENSE,
            ContainerLot.quantity != 0,
            ContainerLot.container_id == container_id,
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


@container.get("/<container_id>/invoice-stats/")
@token_required
@sql_exception_handler
@container.arguments(OneProductInvoiceStatsQuery, location="query")
@container.response(200, StandaloneProductInvoiceStats(many=True))
def standalone_container_invoice_stats(c, args, container_id):
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
            func.sum(ContainerLot.total_sum).label("container_total_sum"),
            Invoice.price.label("invoice_total_sum"),
        )
        .join(ContainerLot, ContainerLot.invoice_id == Invoice.id)
        .join(User, Invoice.user_id == User.id)
        .filter(ContainerLot.container_id == container_id)
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

    invoices_with_container = query.group_by(
        Invoice.id,
        Invoice.number,
        Invoice.status,
        Invoice.type,
        Invoice.created_at,
        User.full_name,
        Invoice.price,
    ).all()
    return invoices_with_container
