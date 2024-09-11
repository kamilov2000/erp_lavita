import datetime

import jwt
from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.base import session
from app.user.models import (
    Department,
    Document,
    Group,
    Partner,
    Permission,
    SalaryCalculation,
    User,
    WorkingDay,
)
from app.user.schema import (
    DepartmentArgsSchema,
    DepartmentCreateSchema,
    DepartmentRetrieveSchema,
    DepartmentSchema,
    DepartmentUpdateSchema,
    DocumentCreateSchema,
    DocumentUpdateListSchema,
    GroupArgsSchema,
    GroupCreateSchema,
    GroupSchema,
    GroupUpdateSchema,
    LoginResponseSchema,
    LoginSchema,
    PagDepartmentSchema,
    PagGroupSchema,
    PagUserSchema,
    UserCreateSchema,
    UserIdSchema,
    UserQueryArgSchema,
    UserSchema,
)
from app.utils.func import (
    accept_to_system_permission,
    hash_image_save,
    msg_response,
    sql_exception_handler,
    token_required,
)
from app.utils.mixins import CustomMethodPaginationView
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
    if not user.is_accepted_to_system:
        return msg_response("You do not have permission to enter the system!"), 403
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
    user = User(**data)
    try:
        session.add(user)
        session.flush()
        user.create_salary_abd_permission_obj()
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
    @accept_to_system_permission
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def get(c, self, token, id):
        user = User.get_or_404(id)
        return user

    @token_required
    @accept_to_system_permission
    # @sql_exception_handler
    @user.arguments(UserSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, UserSchema)
    def patch(c, self, update_data, token, id):
        """
        partly or whole updates for user segments.
        Send only that data which is need to update!

        ВАЖНО: Swagger UI некорректно обрабатывает загрузку файлов через 'multipart/form-data'.
        Для отправки файла используйте Postman или другой инструмент, поддерживающий отправку файлов через форму.
        Обязательно передавайте файл в поле 'photo', и укажите остальные параметры.
        """
        photo = update_data.pop("photo", None)
        if photo:
            path = hash_image_save(uploaded_file=photo, model_name="user", ident=id)
            update_data["photo"] = path
        salary_calculation = update_data.pop("salary_calculation", {})
        permissions = update_data.pop("permissions", {})
        working_days = update_data.pop("working_days", [])

        user = User.get_or_404(id)
        permission_obj = Permission.query.filter_by(user_id=id).first()
        salary_calc_obj = SalaryCalculation.query.filter_by(user_id=id).first()

        for k, v in update_data.items():
            setattr(user, k, v)

        for k, v in salary_calculation.items():
            setattr(salary_calc_obj, k, v)

        for k, v in permissions.items():
            setattr(permission_obj, k, v)

        for data in working_days:
            id = data.get("id", None)
            partners_ids = data.pop("partners_ids", [])
            working_day = WorkingDay.query.get(id)
            if partners_ids:
                working_day.partners.clear()
                users = User.query.filter(User.id.in_(partners_ids)).all()
                partners = []

                for user in users:
                    partners.append(Partner(user_id=user.id))
                data["partners"] = partners

            for k, v in data.items():
                setattr(working_day, k, v)

        session.commit()
        return user


@user.route("/")
class UserView(CustomMethodPaginationView):
    model = User

    @token_required
    @accept_to_system_permission
    @user.arguments(UserQueryArgSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, PagUserSchema)
    def get(c, self, args, token):
        """get user list"""
        lst = []
        search = args.get("search")
        department = args.get("department")
        status = args.get("status")
        role = args.get("role")
        if search:
            lst.append(
                or_(
                    self.model.last_name.ilike(f"%{search}%"),
                    self.model.first_name.ilike(f"%{search}%"),
                ),
            )
        if department:
            lst.append(User.department.has(Department.name == department))
        if status:
            lst.append(self.model.status == status)
        if role:
            lst.append(self.model.role == role)
        return super(UserView, self).get(args, token, lst)

    @token_required
    @accept_to_system_permission
    @sql_exception_handler
    @user.arguments(UserCreateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(201, UserCreateSchema)
    def post(c, self, new_data, token):
        """Add a new user"""
        user = User(**new_data)
        session.add(user)
        session.flush()
        user.create_salary_abd_permission_obj()
        session.commit()
        return user


@user.route("/department")
class DepartmentView(CustomMethodPaginationView):
    model = Department

    @user.arguments(DepartmentArgsSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(200, PagDepartmentSchema)
    @token_required
    @accept_to_system_permission
    def get(c, self, args, token):
        """get list department"""

        return super(DepartmentView, self).get(args, token)

    @token_required
    @accept_to_system_permission
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
    @accept_to_system_permission
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, DepartmentRetrieveSchema)
    def get(c, self, token, id):
        """Get department by ID"""

        item = Department.get_or_404(id)
        return item

    @token_required
    @accept_to_system_permission
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
    @accept_to_system_permission
    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.response(204)
    def delete(c, self, token, id):
        """Delete department"""
        Department.delete_with_get(id)


@user.route("/group")
class GroupView(CustomMethodPaginationView):
    model = Group

    @user.arguments(GroupArgsSchema, location="query")
    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(200, PagGroupSchema)
    @token_required
    @accept_to_system_permission
    def get(c, self, args, token):
        """get list group"""
        department_id = args.get("department_id")
        lst = []
        if department_id:
            lst.append((self.model.department_id == department_id))
        return super(GroupView, self).get(args, token, lst)

    @token_required
    @accept_to_system_permission
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
        new_data["users"] = users
        item = Group(**new_data)
        session.add(item)
        session.commit()
        return item


@user.route("/group/<int:id>")
class GroupIdView(MethodView):

    @token_required
    @accept_to_system_permission
    @sql_exception_handler
    @user.arguments(GroupUpdateSchema)
    @user.arguments(TokenSchema, location="headers")
    @user.response(200, GroupSchema)
    def put(c, self, update_data, token, id):
        department_id = update_data.get("department_id")
        user_ids = update_data.pop("user_ids", None)
        users = User.query.filter(User.id.in_(user_ids)).all()
        update_data["users"] = users
        # assign users to department
        for user in users:
            setattr(user, "department_id", department_id)
        update_data["users"] = users

        item = Group.get_or_404(id)

        schema = GroupSchema()
        schema.load(update_data, instance=item, partial=True)
        session.commit()
        return schema.dump(item)

    @token_required
    @accept_to_system_permission
    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.response(204)
    def delete(c, self, token, id):
        """Delete group"""
        Group.delete_with_get(id)


@user.route("/document/<int:id>/")
class DocumentView(MethodView):

    @user.arguments(TokenSchema, location="headers")
    @user.response(400, ResponseSchema)
    @user.response(200, DocumentUpdateListSchema)
    @token_required
    @accept_to_system_permission
    def get(c, self, token, id):

        documents = Document.get_or_404(id)
        return documents

    @sql_exception_handler
    @user.arguments(TokenSchema, location="headers")
    @user.arguments(DocumentUpdateListSchema, location="form")
    @user.response(400, ResponseSchema)
    @user.response(200, DocumentUpdateListSchema)
    @token_required
    def put(c, self, token, update_data, id):
        """update document for user

        ВАЖНО: Swagger UI некорректно обрабатывает загрузку файлов через 'multipart/form-data'.
        Для отправки файла используйте Postman или другой инструмент, поддерживающий отправку файлов через форму.
        Обязательно передавайте файл в поле 'file', и укажите остальные параметры, такие как 'filename' и 'description'.
        """
        file = request.files.get("file", None)
        if not file:
            return jsonify({"message": "file field is required!"}), 400
        user_id = update_data.get("user_id")

        path = hash_image_save(uploaded_file=file, model_name="user", ident=user_id)
        update_data["filepath"] = path
        file = Document.get_or_404(id)

        for col, val in update_data.items():
            setattr(file, col, val)

        session.merge(file)
        session.commit()
        return file

    @token_required
    @sql_exception_handler
    @user.response(204)
    @user.arguments(TokenSchema, location="headers")
    def delete(c, self, token, id):
        """Delete attached_file"""
        Document.delete_with_get(id)


@user.post("/document")
@token_required
@sql_exception_handler
@user.arguments(DocumentCreateSchema, location="form")
@user.arguments(TokenSchema, location="headers")
@user.response(200, DocumentCreateSchema)
def create_document(c, new_data, token):
    """
    Add a new document to a user

     ВАЖНО: Swagger UI некорректно обрабатывает загрузку файлов через 'multipart/form-data'.
     Для отправки файла используйте Postman или другой инструмент, поддерживающий отправку файлов через форму.
     Обязательно передавайте файл в поле 'file', и укажите остальные параметры, такие как 'filename' и 'description'.
    """
    file = request.files.get("file", None)
    if not file:
        return jsonify({"message": "file field is required!"}), 400
    user_id = new_data.get("user_id")
    path = hash_image_save(uploaded_file=file, model_name="user", ident=user_id)
    item = Document(**new_data, filepath=path)

    session.add(item)
    session.commit()
    return item


@user.get("/document")
@token_required
@user.arguments(UserIdSchema, location="query")
@sql_exception_handler
@user.arguments(TokenSchema, location="headers")
def list_document(c, args, token):
    user_id = args.get("user_id")
    documents = Document.query.filter_by(user_id=user_id).all()
    schema = DocumentUpdateListSchema()
    return schema.dump(documents, many=True)
