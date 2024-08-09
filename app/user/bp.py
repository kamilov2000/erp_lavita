import datetime
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
import jwt
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.user.models import User
from app.user.schema import (
    LoginResponseSchema,
    LoginSchema,
    PagUserSchema,
    UserQueryArgSchema,
    UserSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import msg_response, token_required
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
    try:
        user = session.execute(select(User).where(User.username == username)).scalar()
    except SQLAlchemyError as e:
        current_app.logger.error(str(e.args))
        session.rollback()
        return msg_response("Something went wrong", False), 400
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
    except SQLAlchemyError as e:
        current_app.logger.error(str(e.args))
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
    @token_required
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def get(c, self, token, id):
        try:
            user = User.get_by_id(id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return user

    @token_required
    @user.arguments(UserSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def patch(c, self, update_data, token, id):
        try:
            user = User.get_by_id(id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        try:
            UserSchema().load(update_data, session=session, instance=user)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return user


@user.get("/")
@token_required
@user.arguments(UserQueryArgSchema, location="query")
@user.arguments(TokenSchema, location="headers")
@user.response(200, PagUserSchema)
def get_users(c, args, token):
    try:
        query = User.query

        if "username" in args:
            query = query.filter(User.username.ilike(f"%{args['username']}%"))
        if "first_name" in args:
            query = query.filter(User.first_name.ilike(f"%{args['first_name']}%"))
        if "last_name" in args:
            query = query.filter(User.last_name.ilike(f"%{args['last_name']}%"))
        if "role" in args:
            query = query.filter(User.role.ilike(f"%{args['role']}%"))
        page = args.pop("page", 1)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit
        data = query.limit(limit).offset((page - 1) * limit).all()
    except SQLAlchemyError as e:
        current_app.logger.error(str(e.args))
        session.rollback()
        return msg_response("Something went wrong", False), 400
    response = {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    }

    return response
