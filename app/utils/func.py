import datetime
from functools import wraps
from hashlib import sha256
import os
from flask import current_app, jsonify, request
import jwt
from sqlalchemy import select
from werkzeug.utils import secure_filename

from app.user.models import User
from app.base import session
from app.utils.exc import ItemNotFoundError


def msg_response(content, ok=True):
    if ok:
        return jsonify({"ok": True, "error": None, "data": content})
    else:
        return jsonify({"ok": False, "error": content, "data": None})


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
            current_user = session.execute(
                select(User).filter_by(id=data["public_id"])
            ).scalar()
        except Exception as E:
            return jsonify({"message": str(E)}), 401
        return f(
            current_user, *args, **kwargs
        )  # вот здесь декоратор возврашает модель пользователя

    return decorated


def hash_image_save(
    uploaded_file, model_name: str, ident: int, allowed_extensions=None
):
    if uploaded_file is None:
        raise ItemNotFoundError
    ident_str = str(ident) + "_"
    UPLOAD_FOLDER = current_app.config["UPLOAD_FOLDER"]
    model_upload_path = os.path.join(UPLOAD_FOLDER, model_name)
    if not os.path.exists(model_upload_path):
        os.makedirs(model_upload_path, exist_ok=True)
    now = datetime.datetime.now().strftime("%f")
    print("filename", uploaded_file.filename, flush=True)
    filename = uploaded_file.filename
    if " ." in uploaded_file.filename:
        filename = uploaded_file.filename.replace(" .", f"{now}.")
    secured_filename = secure_filename(filename)
    print("securedd", secured_filename, flush=True)
    file_ext = secured_filename.rsplit(".", 1)
    print("file_ext", file_ext, flush=True)
    if len(file_ext) > 1:
        extension = file_ext[1]
    else:
        extension = file_ext[0]
    print("extension", extension, flush=True)
    # if allowed_extensions is not None and extension.lower() not in allowed_extensions:
    #     raise CustomError("Not allowed extension!")
    hashed_filename = (
        ident_str
        + sha256(secured_filename.encode("utf-8")).hexdigest()
        + "."
        + extension
    )
    print(hashed_filename, flush=True)
    file_path = os.path.join(model_upload_path, hashed_filename)
    uploaded_file.save(file_path)
    return file_path
