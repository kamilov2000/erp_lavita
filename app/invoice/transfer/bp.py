from app.utils.func import msg_response, token_required
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import InvoiceQueryArgSchema, TransferSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema, TokenSchema


transfer = Blueprint(
    "transfer", __name__, url_prefix="/transfer", description="Операции на Трансфер"
)


@transfer.route("/")
class InvoiceAllView(MethodView):
    @token_required
    @transfer.arguments(InvoiceQueryArgSchema, location="query")
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema(many=True))
    def get(c, self, args, token):
        """List transfers"""
        return Invoice.query.filter_by(**args).all()

    @token_required
    @transfer.arguments(TransferSchema)
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(400, ResponseSchema)
    @transfer.response(201, TransferSchema)
    def post(c, self, new_data, token):
        """Add a new transfer"""
        try:
            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@transfer.route("/<transfer_id>/")
class InvoiceById(MethodView):
    @token_required
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema)
    def get(c, self, token, transfer_id):
        """Get transfer by ID"""
        try:
            item = Invoice.get_by_id(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @transfer.arguments(TransferSchema)
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema)
    def put(c, self, update_data, token, transfer_id):
        """Update existing transfer"""
        try:
            item = Invoice.get_by_id(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = transfer_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(204)
    def delete(c, self, token, transfer_id):
        """Delete transfer"""
        try:
            Invoice.delete(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
