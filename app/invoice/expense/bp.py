from app.utils.func import msg_response, token_required
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import InvoiceQueryArgSchema, ExpenseSchema
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
    @expense.response(200, ExpenseSchema(many=True))
    def get(self, c, args, token):
        """List expenses"""
        return Invoice.query.filter_by(**args).all()

    @token_required
    @expense.arguments(ExpenseSchema)
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(400, ResponseSchema)
    @expense.response(201, ExpenseSchema)
    def post(self, c, new_data, token):
        """Add a new expense"""
        try:
            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@expense.route("/<expense_id>/")
class InvoiceById(MethodView):
    @token_required
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, ExpenseSchema)
    def get(self, c, token, expense_id):
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
    def put(self, c, update_data, token, expense_id):
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
    def delete(self, c, token, expense_id):
        """Delete expense"""
        try:
            Invoice.delete(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
