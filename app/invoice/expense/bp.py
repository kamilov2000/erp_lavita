from app.utils.func import msg_response
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
    @expense.arguments(InvoiceQueryArgSchema, location="query")
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, ExpenseSchema(many=True))
    def get(self, args, token):
        """List expenses"""
        return Invoice.query.filter_by(**args).all()

    @expense.arguments(ExpenseSchema)
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(400, ResponseSchema)
    @expense.response(201, ExpenseSchema)
    def post(self, new_data, token):
        """Add a new expense"""
        try:
            session.add(new_data)
            session.commit()
        except:
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@expense.route("/<expense_id>/")
class InvoiceById(MethodView):
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, ExpenseSchema)
    def get(self, token, expense_id):
        """Get expense by ID"""
        try:
            item = Invoice.get_by_id(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @expense.arguments(ExpenseSchema)
    @expense.arguments(TokenSchema, location="headers")
    @expense.response(200, ExpenseSchema)
    def put(self, update_data, token, expense_id):
        """Update existing expense"""
        try:
            item = Invoice.get_by_id(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = expense_id
        session.merge(update_data)
        session.commit()
        return item

    @expense.arguments(TokenSchema, location="headers")
    @expense.response(204)
    def delete(self, token, expense_id):
        """Delete expense"""
        try:
            Invoice.delete(expense_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
