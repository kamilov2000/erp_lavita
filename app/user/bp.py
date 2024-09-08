import datetime
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
import jwt
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError

from app.utils.mixins import CustomMethodPaginationView
from app.user.models import User, Department, Group
from app.user.schema import (
    LoginResponseSchema,
    LoginSchema,
    PagUserSchema,
    UserQueryArgSchema,
    UserSchema,
    UserUpdateSchema, PagDepartmentSchema, DepartmentCreateSchema, DepartmentRetrieveSchema, DepartmentArgsSchema,
    DepartmentSchema, DepartmentUpdateSchema, GroupArgsSchema, GroupListSchema, GroupCreateSchema, GroupSchema,
    GroupUpdateSchema, UserSearchSchema, UserListSchema, PagGroupSchema, UserCreateSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.func import msg_response, token_required, sql_exception_handler
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
        session.flush()
        user.create_salary_obj()
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
    @user.arguments(UserUpdateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def put(c, self, update_data, token, id):
        try:
            user = User.get_by_id(id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        try:
            UserSchema().load(update_data, instance=user, partial=True)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return user


@user.get("/")
class UserView(CustomMethodPaginationView):
    model = User

    @token_required
    @sql_exception_handler
    @user.arguments(UserQueryArgSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, PagUserSchema)
    def get(c, self, args, token):
        """get user list"""
        lst = []
        search = args.get('search')
        department = args.get('department')
        status = args.get('status')
        role = args.get('role')
        if search:
            lst.append(
                    or_(
                        self.model.last_name.ilike(f"%{search}%"),
                        self.model.first_name.ilike(f"%{search}%")
                    ),
            )
        if department:
            lst.append(User.department.has(Department.name == department))
        if status:
            lst.append(
                self.model.status == status
            )
        if role:
            lst.append(
                self.model.role == role
            )
        return super(UserView, self).get(args, token, lst)

    @token_required
    @sql_exception_handler
    @user.arguments(UserCreateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(201, UserCreateSchema)
    def post(c, self, new_data, token):
        """Add a new user"""
        user = User(**new_data)
        session.add(user)
        session.commit()
        return user


@user.route("/department")
class DepartmentView(CustomMethodPaginationView):
    model = Department

    @sql_exception_handler
    @user.arguments(DepartmentArgsSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(200, PagDepartmentSchema)
    @token_required
    def get(c, self, args, token):
        """get list department"""

        return super(DepartmentView, self).get(args, token)

    @token_required
    @sql_exception_handler
    @user.arguments(DepartmentCreateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(201, DepartmentCreateSchema)
    def post(c, self, new_data, token):
        """Add a new department"""
        item = Department(**new_data)
        session.add(item)
        session.commit()
        return item




@user.route("/department/<int:id>")
class DepartmentIdView(MethodView):
    @token_required
    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, DepartmentRetrieveSchema)
    def get(c, self, token, id):
        """Get department by ID"""

        item = Department.get_or_404(id)
        return item

    @token_required
    @sql_exception_handler
    @user.arguments(DepartmentUpdateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, DepartmentSchema)
    def put(c, self, update_data, token, id):
        """Update existing department"""
        item = Department.get_or_404(id)

        schema = DepartmentSchema()
        schema.load(update_data, instance=item, partial=True)
        session.commit()
        return schema.dump(item)

    @token_required
    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.response(204)
    def delete(c, self, token, id):
        """Delete department"""
        Department.delete_with_get(id)


@user.route("/group")
class GroupView(CustomMethodPaginationView):
    model = Group

    @sql_exception_handler
    @user.arguments(GroupArgsSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(200, PagGroupSchema)
    @token_required
    def get(c, self, args, token):
        """get list group"""
        department_id = args.get("department_id")
        lst = []
        if department_id:
            lst.append(
                (self.model.department_id == department_id)
            )
        return super(GroupView, self).get(args, token, lst)

    @token_required
    @sql_exception_handler
    @user.arguments(GroupCreateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(201, GroupCreateSchema)
    def post(c, self, new_data, token):
        """Add a new group"""
        department_id = new_data.get("department_id")
        user_ids = new_data.pop("user_ids", None)
        users = User.query.filter(User.id.in_(user_ids)).all()
        # assign users to department
        for user in users:
            setattr(user, "department_id", department_id)
        new_data['users'] = users
        item = Group(**new_data)
        session.add(item)
        session.commit()
        return item


@user.route("/group/<int:id>")
class GroupIdView(MethodView):

    @token_required
    @sql_exception_handler
    @user.arguments(GroupUpdateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, GroupSchema)
    def put(c, self, update_data, token, id):
        department_id = update_data.get("department_id")
        user_ids = update_data.pop("user_ids", None)
        users = User.query.filter(User.id.in_(user_ids)).all()
        update_data['users'] = users
        # assign users to department
        for user in users:
            setattr(user, "department_id", department_id)
        update_data['users'] = users

        item = Group.get_or_404(id)

        schema = GroupSchema()
        schema.load(update_data, instance=item, partial=True)
        session.commit()
        return schema.dump(item)

    @token_required
    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.response(204)
    def delete(c, self, token, id):
        """Delete group"""
        Group.delete_with_get(id)


