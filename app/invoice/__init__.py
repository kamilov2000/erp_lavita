import os
from app.invoice.models import File, Invoice
from app.invoice.schema import (
    ExpenseSchema,
    FileWebSchema,
    InvoiceCommentSchema,
    InvoiceSchema,
    ProductionSchema,
    TransferSchema,
)
from app.utils.exc import ItemNotFoundError
from app.utils.func import hash_image_save, token_required
from app.utils.schema import ResponseSchema, TokenSchema
from app.base import session
from .bp import invoice as invoice_bp
from app.invoice.expense.bp import expense as expense_bp
from app.invoice.transfer.bp import transfer as transfer_bp
from app.invoice.production.bp import production as production_bp


def register_update_photos_route(bp, route, response_schema):
    @bp.route(route, methods=["POST"])
    @token_required
    @bp.arguments(FileWebSchema, location="files")
    @bp.arguments(TokenSchema, location="headers")
    @bp.response(400, ResponseSchema)
    @bp.response(200, response_schema)
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


def register_add_comment_route(bp, route):
    @bp.post(route)
    @token_required
    @bp.arguemnts(InvoiceCommentSchema)
    @bp.arguemnts(TokenSchema, location="headers")
    @bp.response(400, ResponseSchema)
    @bp.response(200, InvoiceCommentSchema)
    def add_comment(cur_user, data, token, invoice_id):
        pass

register_update_photos_route(invoice_bp, "/<invoice_id>/update_photos/", InvoiceSchema)
register_update_photos_route(expense_bp, "/<expense_id>/update_photos/", ExpenseSchema)
register_update_photos_route(
    transfer_bp, "/<transfer_id>/update_photos/", TransferSchema
)
register_update_photos_route(
    production_bp, "/<production_id>/update_photos/", ProductionSchema
)
