from sqlalchemy import func, select
from app.choices import InvoiceStatuses, InvoiceTypes
from app.product.models import ProductLot, ProductUnit
from app.utils.func import msg_response, token_required
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import (
    InvoiceDetailSchema,
    InvoiceQueryArgSchema,
    InvoiceQueryDraftSchema,
    PagProductionSchema,
    ProductUnitSchema,
    ProductionSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema


production = Blueprint(
    "production",
    __name__,
    url_prefix="/production",
    description="Операции на Акт производства",
)


@production.route("/")
class InvoiceAllView(MethodView):
    @token_required
    @production.arguments(InvoiceQueryArgSchema, location="query")
    @production.response(200, PagProductionSchema)
    def get(c, self, args):
        """List productions"""
        page = args.pop("page", 1)
        created_at = args.pop("created_at", None)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        try:
            number = args.pop("number", None)
            query = Invoice.query.filter_by(
                type=InvoiceTypes.PRODUCTION, **args
            ).order_by(Invoice.created_at.desc())
            if created_at:
                query = query.where(func.date(Invoice.created_at) == created_at)
            if number:
                query = query.filter(Invoice.number.ilike(f"%{number}%"))
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
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400

        return response

    @token_required
    @production.arguments(ProductionSchema)
    @production.arguments(InvoiceQueryDraftSchema, location="query")
    @production.response(400, ResponseSchema)
    @production.response(201, ProductionSchema)
    def post(c, self, new_data, is_draft):
        """Add a new published/draft production"""
        try:
            if is_draft:
                new_data.status = InvoiceStatuses.DRAFT
            else:
                new_data.status = InvoiceStatuses.PUBLISHED
            new_data.type = InvoiceTypes.PRODUCTION
            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
            new_data.write_history()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@production.route("/<production_id>/")
class InvoiceById(MethodView):
    @token_required
    @production.response(200, InvoiceDetailSchema)
    def get(c, self, production_id):
        """Get production by ID"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @production.arguments(ProductionSchema)
    @production.response(200, ProductionSchema)
    def put(c, self, update_data, production_id):
        """Update existing production"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        try:
            update_data.id = production_id
            session.merge(update_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return item

    @token_required
    @production.response(204)
    def delete(c, self, production_id):
        """Delete production"""
        try:
            Invoice.delete(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@production.get("/<production_id>/markups_of_product/<product_id>/")
@token_required
@production.response(200, ProductUnitSchema(many=True))
def get_markups_of_product(c, production_id, product_id):
    production = Invoice.get_by_id(production_id)
    if production.type != InvoiceTypes.PRODUCTION:
        raise ItemNotFoundError(f"Not found Production with id: {production_id}")
    res = session.execute(
        select(ProductUnit)
        .join(ProductLot, ProductLot.id == ProductUnit.product_lot_id)
        .where(
            ProductLot.product_id == product_id, ProductLot.invoice_id == production_id
        )
    ).scalars()
    return res
