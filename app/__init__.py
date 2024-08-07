import logging
import os
from flask import Flask, jsonify, request, make_response, send_from_directory
from flask_smorest import Api
from app.init_db import init_db
from app.utils.exc import CustomError


def create_app():
    app = Flask(__name__)

    app.logger.setLevel(logging.DEBUG)
    app.config.from_pyfile("config/main.py")
    api = Api(app)

    init_db()

    from app.register_bps import reg_bps

    api = reg_bps(api)

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
        return jsonify({"ok": False, "data": None, "error": error.args[0]})

    @app.get("/ping")
    def ping():
        return "pong"

    @app.get("/uploads/<path:name>")
    def download_file(name):
        path = os.path.abspath(app.config["UPLOAD_FOLDER"])
        return send_from_directory(path, name)

    return app
