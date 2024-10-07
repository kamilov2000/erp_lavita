import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field

from app.base import session
from app.choices import (
    CrudOperations,
    DaysOfWeekShort,
    SalaryFormat,
    Statuses,
    UserTransactionAction,
    WorkScheduleStatus,
)
from app.user.models import (
    Department,
    Document,
    Group,
    Partner,
    Permission,
    SalaryCalculation,
    User,
    UserHistory,
    WorkingDay,
    WorkSchedule,
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
    full_name = ma.fields.Method("get_full_name")

    class Meta:
        model = Partner
        fields = ["id", "full_name", "start_time", "end_time", "for_half_day"]

    def get_full_name(self, obj):
        return obj.user.full_name if obj.user else None


class WorkingDaySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    day_of_week = ma.fields.Enum(enum=DaysOfWeekShort, dump_only=True)
    is_working_day = ma.fields.Bool(required=True)
    start_time = ma.fields.Time(required=True)
    end_time = ma.fields.Time(required=True)
    id = ma.fields.Int(required=True)

    class Meta:
        model = WorkingDay
        fields = [
            "id",
            "is_working_day",
            "start_time",
            "end_time",
            "day_of_week",
        ]


class UserHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    operation_status = ma.fields.Enum(enum=CrudOperations)

    class Meta:
        model = UserHistory


class UserSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    salary_calculation = ma.fields.Nested(SalaryCalculationSchema())
    status = ma.fields.Enum(enum=Statuses)
    department_name = ma.fields.Method("get_department", dump_only=True)
    permissions = ma.fields.Nested(PermissionForUserSchema())
    working_days = ma.fields.Nested(WorkingDaySchema(many=True))
    photo = ma.fields.Str(dump_only=True)
    is_driver_salary_format = ma.fields.Bool(dump_only=True)
    histories = ma.fields.Nested(UserHistorySchema(many=True), dump_only=True)

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
            "is_driver_salary_format",
            "photo",
            "histories",
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


class UserSalaryQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    search = ma.fields.Str()
    department = ma.fields.Str()
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
        include_fk = True

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


class CreateTransactionSchema(ma.Schema):
    amount = ma.fields.Float(required=True)
    action = ma.fields.Enum(enum=UserTransactionAction, required=True)
    comment = ma.fields.Str(required=False)


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


class WorkSchedulerList(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    start_time = ma.fields.Method("get_start_time")
    end_time = ma.fields.Method("get_end_time")
    day_of_week = ma.fields.Method("get_day_of_week")
    status = ma.fields.Enum(enum=WorkScheduleStatus)

    class Meta:
        model = WorkSchedule
        fields = ["id", "date", "status", "start_time", "end_time", "day_of_week"]

    def get_start_time(self, obj):
        return obj.working_day.start_time.strftime("%H:%M") if obj.working_day else None

    def get_end_time(self, obj):
        return obj.working_day.end_time.strftime("%H:%M") if obj.working_day else None

    def get_day_of_week(self, obj):
        return obj.working_day.day_of_week.value.upper() if obj.working_day else None


class UsersWorkScheduleList(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    work_schedules = ma.fields.Nested(WorkSchedulerList(many=True))

    class Meta:
        model = User
        fields = ["id", "full_name", "work_schedules"]


class PagWorkScheduleSchema(ma.Schema):
    data = ma.fields.Nested(UsersWorkScheduleList(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class WorkScheduleArgsSchema(ma.Schema):
    start_date = ma.fields.Date(required=False)
    end_date = ma.fields.Date(required=False)
    department_id = ma.fields.Int(required=False)
    group_id = ma.fields.Int(required=False)
    search = ma.fields.Str(required=False)


class PartnerCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = Partner
        fields = ["id", "user_id", "for_half_day", "start_time", "end_time"]


class WorkScheduleUpdate(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=WorkScheduleStatus)
    partners = ma.fields.Nested(PartnerCreateSchema(many=True))

    class Meta:
        model = WorkSchedule
        fields = ["id", "status", "partners"]


class WorkScheduleRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=WorkScheduleStatus)
    partners = ma.fields.Nested(PartnerSchema(many=True))

    class Meta:
        model = WorkSchedule
        fields = ["id", "status", "partners"]


class UserSalaryListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    department_name = ma.fields.Method("get_department_name")
    group_name = ma.fields.Method("get_group_name")
    balance = ma.fields.Method("get_balance")
    fixed_payment = ma.fields.Method("get_fixed_payment")

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "department_name",
            "group_name",
            "balance",
            "fixed_payment",
        ]

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    def get_balance(self, obj):
        return obj.salary.balance if obj.salary else None

    def get_fixed_payment(self, obj):
        return obj.salary.fixed_payment if obj.salary else None


class PagUserSalarySchema(ma.Schema):
    data = ma.fields.Nested(UserSalaryListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class UserSalaryRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    balance = ma.fields.Method("get_balance")

    class Meta:
        model = User
        fields = ["id", "balance"]

    def get_balance(self, obj):
        return obj.salary.balance if obj.salary else None
