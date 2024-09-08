import logging
import os

import jwt
from flask import (
    Flask,
    current_app,
    g,
    jsonify,
    make_response,
    request,
    send_from_directory,
)
from flask_apscheduler import APScheduler
from flask_smorest import Api
from jwt import ExpiredSignatureError, InvalidTokenError

from app.base import drop_db, session
from app.choices import CrudOperations
from app.events import register_events
from app.finance.models import Transaction, TransactionHistory
from app.finance.system_balance_accounts import create_system_balance_accounts
from app.init_db import init_db
from app.jobs import scheduled_auto_charge_task
from app.user.models import User
from app.utils.exc import CustomError

scheduler = APScheduler()


def create_app():
    app = Flask(__name__)

    scheduler.init_app(app)

    def sync_with_main():
        with app.app_context():
            scheduled_auto_charge_task()

    if not scheduler.get_job("auto_charge_job"):
        scheduler.add_job(
            id="auto_charge_job",
            func=sync_with_main,
            trigger="cron",
            minute="0",
            hour="0",
        )

    if not scheduler.running:
        scheduler.start()

    app.logger.setLevel(logging.DEBUG)
    app.config.from_pyfile("config/main.py")
    api = Api(app)

    init_db()

    create_system_balance_accounts(session)

    from app.register_bps import reg_bps

    api = reg_bps(api)

    register_events()

    @app.after_request
    def after_request_func(response):
        origin = request.headers.get("Origin")
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Credentials", "true")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type")
            response.headers.add("Access-Control-Allow-Headers", "x-access-token")
            response.headers.add("Access-Control-Allow-Headers", "X-Access-Token")
            response.headers.add("Access-Control-Allow-Headers", "Authorization")
            response.headers.add(
                "Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, PATCH, DELETE"
            )
            if origin:
                response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            response.headers.add("Access-Control-Allow-Credentials", "true")
            response.headers.add("Access-Control-Allow-Headers", "x-access-token")
            if origin:
                response.headers.add("Access-Control-Allow-Origin", origin)

        return response

    @app.errorhandler(CustomError)
    def errorhandler_custom(error):
        app.logger.error("Handled CustomException: %s", error)
        return jsonify({"ok": False, "data": None, "error": error.args[0]}), 400

    @app.before_request
    def load_user():
        token = request.headers.get("x-access-token")
        if token:
            try:
                data = jwt.decode(
                    token, current_app.config.get("SECRET_KEY"), algorithms=["HS256"]
                )
                user_id = data["public_id"]
                g.user = User.query.get(user_id)
            except (ExpiredSignatureError, InvalidTokenError) as e:
                app.logger.error(f"JWT Error: {e}")
                g.user = None

    @app.get("/ping")
    def ping():
        return "pong"

    @app.get("/uploads/<path:name>")
    def download_file(name):
        path = os.path.abspath(app.config["UPLOAD_FOLDER"])
        return send_from_directory(path, name)

    # drop_db()

    return app
