import logging
from flask import Flask, request, make_response
from flask_smorest import Api
from app.init_db import init_db


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

    @app.get("/ping")
    def ping():
        return "pong"

    return app
