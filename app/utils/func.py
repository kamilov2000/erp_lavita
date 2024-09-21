from copy import deepcopy
import datetime
import os
from functools import wraps
from hashlib import sha256

import jwt
from flask import current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app.base import session
from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.product.models import Container, Part
from app.user.models import User
from app.utils.exc import ItemNotFoundError


def msg_response(content, ok=True):
    if ok:
        return jsonify({"ok": True, "error": None, "data": content})
    else:
        return jsonify({"ok": False, "error": content, "data": None})


def sql_exception_handler(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            res = f(*args, **kwargs)
        except (AttributeError, SQLAlchemyError) as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        finally:
            session.close()
        return res

    return decorated


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "x-access-token" in request.headers:
            token = request.headers["x-access-token"]
        if not token:
            return jsonify({"message": "Token is missing !!"}), 401
        try:
            data = jwt.decode(
                token, current_app.config.get("SECRET_KEY"), algorithms=["HS256"]
            )
            try:
                current_user = session.execute(
                    select(User).filter_by(id=data.get("public_id"))
                ).scalar()
                if not current_user:
                    return jsonify({"message": "User not found !!"}), 401
            except SQLAlchemyError as e:
                current_app.logger.error(str(e.args))
                session.rollback()
                return msg_response("Something went wrong", False), 400
        except Exception as E:
            return jsonify({"message": str(E)}), 401

        return f(
            current_user, *args, **kwargs
        )  # вот здесь декоратор возврашает модель пользователя

    decorated._apidoc = deepcopy(getattr(f, "_apidoc", {}))
    decorated._apidoc.setdefault("manual_doc", {})
    decorated._apidoc["manual_doc"]["security"] = [{"Bearer Auth": []}]
    return decorated


def accept_to_system_permission(f):
    @wraps(f)
    def decorated(c, *args, **kwargs):
        if not c.is_accepted_to_system:
            return msg_response("You do not have permission to enter the system!"), 403

        return f(
            c, *args, **kwargs
        )  # вот здесь декоратор возврашает модель пользователя

    return decorated


def hash_image_save(
    uploaded_file, model_name: str, ident: int, allowed_extensions=None
):
    if uploaded_file is None:
        raise ItemNotFoundError
    ident_str = f"{ident}_"
    UPLOAD_FOLDER = current_app.config["UPLOAD_FOLDER"]
    model_upload_path = os.path.join(UPLOAD_FOLDER, model_name)
    if not os.path.exists(model_upload_path):
        os.makedirs(model_upload_path, exist_ok=True)
    now = datetime.datetime.now().strftime("%f")
    filename = uploaded_file.filename
    if " ." in uploaded_file.filename:
        filename = uploaded_file.filename.replace(" .", f"{now}.")
    secured_filename = secure_filename(filename)
    file_ext = secured_filename.rsplit(".", 1)
    if len(file_ext) > 1:
        extension = file_ext[1]
    else:
        extension = file_ext[0]
    # if allowed_extensions is not None and extension.lower() not in allowed_extensions:
    #     raise CustomError("Not allowed extension!")
    hashed_filename = (
        f"{ident_str}{sha256(secured_filename.encode('utf-8')).hexdigest()}.{extension}"
    )
    file_path = os.path.join(model_upload_path, hashed_filename)
    uploaded_file.save(file_path)
    return file_path


def cancel_invoice(invoice_id):
    invoice = Invoice.get_by_id(invoice_id)

    if invoice.status == InvoiceStatuses.PUBLISHED:
        if invoice.type == InvoiceTypes.EXPENSE:
            # Восстановление количества продуктов
            for product_lot in invoice.product_lots:
                for unit in product_lot.units:
                    old_lot = unit.product_lot
                    old_lot.quantity += 1
                    old_lot.calc_total_sum()
                    unit.product_lot = old_lot

            # Восстановление количества контейнеров
            for container_lot in invoice.container_lots:
                Container.increase(container_lot.container_id, container_lot.quantity)

            # Восстановление количества частей
            for part_lot in invoice.part_lots:
                Part.increase(part_lot.part_id, part_lot.quantity)
        if invoice.type in [InvoiceTypes.INVOICE, InvoiceTypes.PRODUCTION]:
            for product_lot in invoice.product_lots:
                for unit in product_lot.units:
                    old_lot = unit.product_lot
                    old_lot.quantity -= 1
                    old_lot.calc_total_sum()
                    unit.product_lot = old_lot

            # Восстановление количества контейнеров
            for container_lot in invoice.container_lots:
                Container.decrease(
                    container_lot.container_id,
                    container_lot.quantity,
                    warehouse_id=invoice.warehouse_sender_id,
                )

            # Восстановление количества частей
            for part_lot in invoice.part_lots:
                Part.decrease(
                    part_lot.part_id,
                    part_lot.quantity,
                    invoice.warehouse_sender_id,
                )
        if invoice.type == InvoiceTypes.TRANSFER:
            invoice.warehouse_sender_id, invoice.warehouse_receiver_id = (
                invoice.warehouse_receiver_id,
                invoice.warehouse_sender_id,
            )

    # Изменение статуса инвойса на "отменён"
    invoice.status = InvoiceStatuses.CANCELED
    session.commit()
