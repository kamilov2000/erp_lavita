from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
import os
from app.choices import InvoiceStatuses
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
from app.utils.func import hash_image_save, msg_response, token_required
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
    @bp.arguments(InvoiceCommentSchema)
    @bp.arguments(TokenSchema, location="headers")
    @bp.response(400, ResponseSchema)
    @bp.response(200, InvoiceCommentSchema)
    def add_comment(cur_user, data, token, invoice_id):
        try:
            data.user_id = cur_user.id
            session.add(data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return data


def register_publish_invoice_route(bp, route):
    @bp.post(route)
    @token_required
    @bp.arguments(TokenSchema, location="headers")
    @bp.response(400, ResponseSchema)
    @bp.response(200, ResponseSchema)
    def publish_invoice(cur_user, token, invoice_id):
        invoice = Invoice.get_by_id(invoice_id)
        invoice.status = InvoiceStatuses.PUBLISHED
        try:
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return msg_response("ok")


def reg_invoice_routes():
    bps = [
        invoice_bp,
        expense_bp,
        transfer_bp,
        production_bp,
    ]
    id_labels = [
        "invoice_id",
        "expense_id",
        "transfer_id",
        "production_id",
    ]
    schemas = [
        InvoiceSchema,
        ExpenseSchema,
        TransferSchema,
        ProductionSchema,
    ]
    for bp, label, schema in zip(bps, id_labels, schemas):
        register_update_photos_route(bp, f"/<{label}>/update_photos/", schema)
        register_add_comment_route(bp, f"/<{label}>/add_comment/")
        register_publish_invoice_route(bp, f"/<{label}>/publish/")


reg_invoice_routes()
