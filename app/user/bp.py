import datetime
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
import jwt
from sqlalchemy import select

from app.user.models import User
from app.user.schema import LoginResponseSchema, LoginSchema, UserSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import msg_response
from app.utils.schema import ResponseSchema, TokenSchema

user = Blueprint(
    "user", __name__, url_prefix="/user", description="operations on users"
)


@user.post("/login")
@user.arguments(LoginSchema)
@user.response(200, LoginResponseSchema)
@user.response(400, ResponseSchema)
def login_user(data):
    username = data.get("username")
    password = data.get("password")
    user = session.execute(select(User).where(User.username == username)).scalar()
    if not user:
        return msg_response("Login or password is incorrect", False), 400
    if not user.check_password(password):
        return msg_response("Login or password is incorrect", False), 400
    token = jwt.encode(
        {
            "public_id": user.id,
            "exp": datetime.datetime.now() + datetime.timedelta(days=365),
        },
        current_app.config.get("SECRET_KEY"),
    )
    return msg_response({"token": token, "role": user.role})


@user.post("/register")
@user.arguments(LoginSchema)
@user.response(200, LoginResponseSchema)
@user.response(400, ResponseSchema)
def register(data):
    username = data.get("username")
    user = session.execute(select(User).where(User.username == username)).scalar()
    if user:
        return msg_response("Username is already in use", False), 400
    user = UserSchema().load(data, session=session)
    try:
        session.add(user)
        session.commit()
    except:
        session.rollback()
        return msg_response("Something went wrong", False), 400
    token = jwt.encode(
        {
            "public_id": user.id,
            "exp": datetime.datetime.now() + datetime.timedelta(days=365),
        },
        current_app.config.get("SECRET_KEY"),
    )
    return msg_response({"token": token, "role": user.role})


@user.route("/<int:id>/")
class UserByIdView(MethodView):
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def get(self, token, id):
        try:
            user = User.get_by_id(id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return user

    @user.arguments(UserSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def patch(self, update_data, token, id):
        try:
            user = User.get_by_id(id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        UserSchema().load(update_data, session=session, instance=user)
        session.commit()
        return user
