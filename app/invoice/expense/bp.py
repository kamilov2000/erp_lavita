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
    ExpenseSchema,
    InvoiceQueryDraftSchema,
    PagExpenseSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema, TokenSchema


expense = Blueprint(
    "expense", __name__, url_prefix="/expense", description="Операции на Списания"
)


@expense.route("/")
class InvoiceAllView(MethodView):
    @token_required
    @expense.arguments(InvoiceQueryArgSchema, location="query")
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, PagExpenseSchema)
    def get(c, self, args, token):
        """List expenses"""
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
            number = args.pop("number", None)
            query = Invoice.query.filter_by(type=InvoiceTypes.EXPENSE, **args).order_by(
                Invoice.created_at.desc()
            )
            if number:
                query = query.filter(Invoice.number.ilike(f"%{number}%"))
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
    @expense.arguments(ExpenseSchema)
    @expense.arguments(TokenSchema, location="headers")
    @expense.arguments(InvoiceQueryDraftSchema, location="query")
    @expense.response(400, ResponseSchema)
    @expense.response(201, ExpenseSchema)
    def post(c, self, new_data, token, is_draft):
        """Add a new published expense"""
        try:
            if is_draft:
                new_data.status = InvoiceStatuses.DRAFT
            else:
                new_data.status = InvoiceStatuses.PUBLISHED
            new_data.type = InvoiceTypes.EXPENSE
            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
            new_data.write_history()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@expense.route("/<expense_id>/")
class InvoiceById(MethodView):
    @token_required
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, InvoiceDetailSchema)
    def get(c, self, token, expense_id):
        """Get expense by ID"""
        try:
            item = Invoice.get_by_id(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @expense.arguments(ExpenseSchema)
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, ExpenseSchema)
    def put(c, self, update_data, token, expense_id):
        """Update existing expense"""
        try:
            item = Invoice.get_by_id(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = expense_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(204)
    def delete(c, self, token, expense_id):
        """Delete expense"""
        try:
            Invoice.delete(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
