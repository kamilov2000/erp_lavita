import os
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import File, Invoice
from app.invoice.schema import FileWebSchema, InvoiceQueryArgSchema, InvoiceSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, token_required
from app.utils.schema import ResponseSchema, TokenSchema


invoice = Blueprint(
    "invoice", __name__, url_prefix="/invoice", description="Операции на Накладные"
)


@invoice.route("/")
class InvoiceAllView(MethodView):
    @invoice.arguments(InvoiceQueryArgSchema, location="query")
    @invoice.arguments(TokenSchema, location="headers")
    @invoice.response(200, InvoiceSchema(many=True))
    def get(self, args, token):
        """List invoices"""
        return Invoice.query.filter_by(**args).all()

    @invoice.arguments(InvoiceSchema)
    @invoice.arguments(TokenSchema, location="headers")
    @invoice.response(201, InvoiceSchema)
    def post(self, new_data, token):
        """Add a new invoice"""
        session.add(new_data)
        session.commit()
        return new_data


@invoice.route("/<invoice_id>/")
class InvoiceById(MethodView):
    @invoice.arguments(TokenSchema, location="headers")
    @invoice.response(200, InvoiceSchema)
    def get(self, token, invoice_id):
        """Get invoice by ID"""
        try:
            item = Invoice.get_by_id(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @invoice.arguments(InvoiceSchema)
    @invoice.arguments(TokenSchema, location="headers")
    @invoice.response(200, InvoiceSchema)
    def put(self, update_data, token, invoice_id):
        """Update existing invoice"""
        try:
            item = Invoice.get_by_id(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        InvoiceSchema().load(update_data, instance=item, partial=True)
        session.commit()
        return item

    @invoice.arguments(TokenSchema, location="headers")
    @invoice.response(204)
    def delete(self, token, invoice_id):
        """Delete invoice"""
        try:
            Invoice.delete(invoice_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@invoice.post("/<invoice_id>/update_photos/")
@token_required
@invoice.arguments(FileWebSchema, location="files")
@invoice.arguments(TokenSchema, location="headers")
@invoice.response(400, ResponseSchema)
@invoice.response(200, InvoiceSchema)
def change_photo(cur_user, data, token, invoice_id):
    invoice = Invoice.get_by_id(invoice_id)
    photo_files = data.get("files")
    array = []
    for p_file in photo_files:
        try:
            path = hash_image_save(p_file, "invoice", invoice_id)
            array.append(File(filename=p_file.filename, path=path))
        except ItemNotFoundError:
            pass
            # return msg_response("Photo not found", False), 400
    if invoice.files:
        for file in invoice.files:
            try:
                session.delete(file)
                os.remove(file.path)
            except FileNotFoundError:
                pass
    invoice.files = array
    session.commit()
    return invoice
