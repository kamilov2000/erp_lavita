from app.utils.func import msg_response
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
    @transfer.arguments(InvoiceQueryArgSchema, location="query")
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema(many=True))
    def get(self, args, token):
        """List transfers"""
        return Invoice.query.filter_by(**args).all()

    @transfer.arguments(TransferSchema)
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(400, ResponseSchema)
    @transfer.response(201, TransferSchema)
    def post(self, new_data, token):
        """Add a new transfer"""
        try:
            session.add(new_data)
            session.commit()
        except:
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@transfer.route("/<transfer_id>/")
class InvoiceById(MethodView):
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema)
    def get(self, token, transfer_id):
        """Get transfer by ID"""
        try:
            item = Invoice.get_by_id(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @transfer.arguments(TransferSchema)
    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(200, TransferSchema)
    def put(self, update_data, token, transfer_id):
        """Update existing transfer"""
        try:
            item = Invoice.get_by_id(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = transfer_id
        session.merge(update_data)
        session.commit()
        return item

    @transfer.arguments(TokenSchema, location="headers")
    @transfer.response(204)
    def delete(self, token, transfer_id):
        """Delete transfer"""
        try:
            Invoice.delete(transfer_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
