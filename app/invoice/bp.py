from sqlalchemy import func
from app.choices import InvoiceStatuses, InvoiceTypes
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
    InvoiceSchema,
    PagInvoiceSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema


invoice = Blueprint(
    "invoice", __name__, url_prefix="/invoice", description="Операции на Накладные"
)


@invoice.route("/")
class InvoiceAllView(MethodView):
    @token_required
    @invoice.arguments(InvoiceQueryArgSchema, location="query")
    @invoice.response(400, ResponseSchema)
    @invoice.response(200, PagInvoiceSchema)
    def get(c, self, args):
        """List invoices"""
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
            query = Invoice.query.filter_by(type=InvoiceTypes.INVOICE, **args).order_by(
                Invoice.created_at.desc()
            )
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
    @invoice.arguments(InvoiceSchema)
    @invoice.arguments(InvoiceQueryDraftSchema, location="query")
    @invoice.response(400, ResponseSchema)
    @invoice.response(201, InvoiceSchema)
    def post(c, self, new_data, is_draft):
        """Add a new published/draft invoice"""
        try:
            if is_draft:
                new_data.status = InvoiceStatuses.DRAFT
            else:
                new_data.status = InvoiceStatuses.PUBLISHED

            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
            new_data.write_history()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@invoice.route("/<invoice_id>/")
class InvoiceById(MethodView):
    @token_required
    @invoice.response(200, InvoiceDetailSchema)
    def get(c, self, invoice_id):
        """Get invoice by ID"""
        try:
            item = Invoice.get_by_id(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @invoice.arguments(InvoiceSchema)
    @invoice.response(200, InvoiceSchema)
    def put(c, self, update_data, invoice_id):
        """Update existing invoice"""
        try:
            item = Invoice.get_by_id(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        try:
            update_data.id = invoice_id
            session.merge(update_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return item

    @token_required
    @invoice.response(204)
    def delete(c, self, invoice_id):
        """Delete invoice"""
        try:
            Invoice.delete(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
