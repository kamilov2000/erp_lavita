import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field

from app.choices import Statuses
from app.user.models import User, Department, Group
from app.base import session
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class UserSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = True
        sqla_session = session

    role = auto_field(dump_only=True)
    password = auto_field(load_only=True)

    @ma.pre_load
    def hash_password(self, in_data, **kwargs):
        if in_data.get("password"):
            in_data["password"] = User.generate_password(in_data["password"])
        return in_data


class UserListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)
    class Meta:
        model = User
        fields = ["id", "full_name", "role", "status"]


class UserUpdateSchema(SQLAlchemySchema):
    class Meta:
        model = User
        include_fk = True

    first_name = auto_field(required=False)
    last_name = auto_field(required=False)
    password = auto_field(required=False)


class LoginSchema(ma.Schema):
    username = ma.fields.Str()
    password = ma.fields.Str()


class LoginResponseSchema(ma.Schema):
    token = ma.fields.Str()
    role = ma.fields.Str()


class UserQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    search = ma.fields.Str()
    department = ma.fields.Str()
    status = ma.fields.Enum(enum=Statuses)
    role = ma.fields.Str()


class UserSearchSchema(ma.Schema):
    search = ma.fields.Str(required=True)


class PagUserSchema(ma.Schema):
    data = ma.fields.Nested(UserListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class DepartmentListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    users_count = ma.fields.Method("get_user_count")

    class Meta:
        model = Department
        fields = ["id", "name", "users_count"]

    def get_user_count(self, obj):
        return len(obj.users)


class DepartmentCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)

    class Meta:
        model = Department
        fields = ["id", "name"]


class DepartmentUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str()

    class Meta:
        model = Department
        fields = ["id", "name"]


class DepartmentSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Department
        fields = ["id", "name"]
        load_instance = True
        sqla_session = session


class UserListForGroupSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = User
        fields = ["id", "full_name", "role", "status"]


class GroupSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Group
        load_instance = True
        sqla_session = session


class GroupListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    users = ma.fields.Nested(UserListForGroupSchema, many=True)
    payment_group = ma.fields.Method("get_payment_group")

    class Meta:
        model = Group
        fields = ["id", "name", "users", "payment_group"]

    def get_payment_group(self, obj):
        if not obj.users:
            return 0
        return sum([user.salary.current_balance for user in obj.users])


class PagGroupSchema(ma.Schema):
    data = ma.fields.Nested(GroupListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
class GroupCreateSchema(ma.Schema):
    name = ma.fields.Str(required=True)
    user_ids = ma.fields.List(ma.fields.Int())
    department_id = ma.fields.Int(required=True)


class GroupUpdateSchema(ma.Schema):
    name = ma.fields.Str()
    user_ids = ma.fields.List(ma.fields.Int())
    department_id = ma.fields.Int(required=True)


class DepartmentRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    groups = ma.fields.Nested(GroupListSchema, many=True)
    overall_payments = ma.fields.Method("get_payments")

    class Meta:
        model = Department
        fields = ["id", "name", "groups", "overall_payments"]

    def get_payments(self, obj):
        return sum([user.salary.current_balance for user in obj.users])


class PagDepartmentSchema(ma.Schema):
    data = ma.fields.Nested(DepartmentListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class DepartmentArgsSchema(ma.Schema):
    page = ma.fields.Int()
    limit = ma.fields.Int()


class GroupArgsSchema(ma.Schema):
    department_id = ma.fields.Int(required=False)


class UserCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    first_name = ma.fields.Str(required=True)
    last_name = ma.fields.Str(required=True)
    phone = ma.fields.Str(required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "id", "phone", "department_id", "group_id"]