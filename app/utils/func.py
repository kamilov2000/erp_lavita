from functools import wraps
from flask import current_app, jsonify, request
import jwt
from sqlalchemy import select

from app.user.models import User
from app.base import session


def msg_response(content, ok=True):
    if ok:
        return jsonify({"ok": True, "error": None, "data": content})
    else:
        return jsonify({"ok": False, "error": content, "data": None})


def token_user(f):
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
