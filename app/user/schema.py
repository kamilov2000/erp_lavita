import marshmallow as ma
from marshmallow import validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field

from app.base import session
from app.choices import DaysOfWeek, SalaryFormat, Statuses
from app.user.models import (
    Department,
    Document,
    Group,
    Permission,
    SalaryCalculation,
    User,
    WorkingDay,
)
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class SalaryCalculationSchema(DefaultDumpsSchema, SQLAlchemyAutoSchema):
    salary_format = ma.fields.Enum(enum=SalaryFormat)

    class Meta:
        model = SalaryCalculation
        exclude = ["created_at", "updated_at", "user_id"]


class PermissionForUserSchema(DefaultDumpsSchema, SQLAlchemyAutoSchema):
    class Meta:
        model = Permission
        exclude = ["created_at", "updated_at"]


class PartnerSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = User
        fields = ["id", "full_name", "role"]


class WorkingDaySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    day_of_week = ma.fields.Enum(enum=DaysOfWeek, dump_only=True)
    is_working_day = ma.fields.Bool(required=True)
    start_time = ma.fields.Time(required=True)
    end_time = ma.fields.Time(required=True)
    id = ma.fields.Int(required=True)
    partners = ma.fields.Nested(PartnerSchema(many=True), dump_only=True)
    partners_ids = ma.fields.List(
        ma.fields.Int(),
        required=True,
        load_only=True,
        validate=[validate.Length(min=1)],
    )

    class Meta:
        model = WorkingDay
        fields = [
            "id",
            "is_working_day",
            "start_time",
            "end_time",
            "partners_ids",
            "partners",
            "day_of_week",
        ]


class UserSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    salary_calculation = ma.fields.Nested(SalaryCalculationSchema())
    status = ma.fields.Enum(enum=Statuses)
    department_name = ma.fields.Method("get_department", dump_only=True)
    permissions = ma.fields.Nested(PermissionForUserSchema())
    working_days = ma.fields.Nested(WorkingDaySchema(many=True))

    class Meta:
        model = User
        fields = [
            "id",
            "last_name",
            "first_name",
            "role",
            "phone_number",
            "department_name",
            "salary_calculation",
            "password",
            "username",
            "permissions",
            "working_days",
        ]

    role = auto_field(dump_only=True)
    password = auto_field(load_only=True)

    @ma.pre_load
    def hash_password(self, in_data, **kwargs):
        # Проверяем, что in_data является словарём
        if isinstance(in_data, dict) and in_data.get("password"):
            in_data["password"] = User.generate_password(in_data["password"])
        return in_data

    def get_department(self, obj):
        return obj.department.name if obj.department else None


class UserListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "role",
            "status",
            "is_accepted_to_system",
        ]


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
    phone_number = ma.fields.Str(required=True)
    department_id = ma.fields.Int()
    group_id = ma.fields.Int()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "id",
            "phone_number",
            "department_id",
            "group_id",
        ]


class DocumentCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    filename = ma.fields.Str(required=True)
    user_id = ma.fields.Int(required=True)

    class Meta:
        model = Document
        fields = ["filename", "description", "user_id"]


class DocumentUpdateListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    filepath = ma.fields.Str(dump_only=True)
    user_id = ma.fields.Int(load_only=True)

    class Meta:
        model = Document
        fields = ["filename", "filepath", "description", "user_id", "id"]


class UserIdSchema(ma.Schema):
    counterparty_id = ma.fields.Int(
        data_key="user_id",
        required=True,
        description="for attaching to User",
    )
