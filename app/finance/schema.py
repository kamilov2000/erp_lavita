import marshmallow as ma
from marshmallow import ValidationError, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func
from werkzeug.datastructures import FileStorage

from app import session
from app.choices import (
    AccountCategories,
    AccountTypes,
    CrudOperations,
    Statuses,
    TaxRateCategories,
    TransactionStatuses,
)
from app.finance.models import (
    BalanceAccount,
    CashRegister,
    CashRegisterHistory,
    Counterparty,
    PaymentType,
    TaxRate,
    Transaction,
    TransactionComment,
    TransactionHistory,
)
from app.finance.utils import CATEGORY_COLLECTION, CATEGORY_LIST, check_all_strs_is_nums
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class ByNameSearchSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search by name")
    page = ma.fields.Int()
    limit = ma.fields.Int()


class ByNameAndCategorySearchSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search by name")
    category = ma.fields.Enum(enum=AccountCategories, description="Filter by Category")
    type = ma.fields.Enum(enum=AccountTypes, description="Filter by Type")
    page = ma.fields.Int()
    limit = ma.fields.Int()


class TransactionArgsSchema(ma.Schema):
    search = ma.fields.String(required=False, description="Search")
    page = ma.fields.Int()
    limit = ma.fields.Int()
    created_date = ma.fields.Date()
    status = ma.fields.Enum(enum=TransactionStatuses)
    category_name = ma.fields.Str(
        validate=validate.OneOf(CATEGORY_LIST, error="Invalid debit category")
    )
    category_object_id = ma.fields.Int()


class CounterpartyArgsSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search")
    page = ma.fields.Int()
    limit = ma.fields.Int()
    created_date = ma.fields.Date()
    category = ma.fields.Enum(enum=AccountCategories)
    status = ma.fields.Enum(enum=Statuses)


class TaxRateArgsSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search")
    page = ma.fields.Int()
    limit = ma.fields.Int()
    category = ma.fields.Enum(enum=TaxRateCategories)
    status = ma.fields.Enum(enum=Statuses)
    payment_type_name = ma.fields.Str(required=False)


class PaymentTypeListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    fiscal = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = PaymentType
        fields = ["id", "name", "commission_percentage", "fiscal"]


class PaymentTypeCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    fiscal = ma.fields.Enum(enum=Statuses)
    commission_percentage = ma.fields.Float(required=False)

    class Meta:
        model = PaymentType
        fields = ["name", "has_commissioner", "fiscal", "commission_percentage", "id"]


class PaymentTypeForRelationsSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PaymentType
        fields = ["id", "name"]


class PagPaymentTypeSchema(ma.Schema):
    data = ma.fields.Nested(PaymentTypeListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PaymentTypeRetrieveUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    fiscal = ma.fields.Enum(enum=Statuses, required=False)

    class Meta:
        model = PaymentType
        fields = ["id", "name", "has_commissioner", "commission_percentage", "fiscal"]


class CashRegisterCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    payment_types_ids = ma.fields.List(
        ma.fields.Int(),
        required=True,
        load_only=True,
        validate=[validate.Length(min=1)],
    )

    class Meta:
        model = CashRegister
        fields = ["id", "name", "payment_types_ids"]


class CashRegisterListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)

    class Meta:
        model = CashRegister
        fields = ["id", "name", "balance", "payment_types"]


class PagCashRegisterSchema(ma.Schema):
    data = ma.fields.Nested(CashRegisterListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class TransactionSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=TransactionStatuses)

    class Meta:
        model = Transaction
        fields = ["id", "number_transaction", "amount", "created_at", "status"]


class CashRegisterHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")
    user_name = ma.fields.Method("get_user_name")
    operation_status = ma.fields.Enum(enum=CrudOperations)

    class Meta:
        model = CashRegisterHistory
        fields = ["operation_status", "created_at", "user_name", "data", "id"]

    def get_user_name(self, obj):
        return obj.user_full_name


class CashRegisterRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    histories = ma.fields.Nested(CashRegisterHistorySchema, many=True)
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)
    incomes = ma.fields.Method("get_incomes")
    expenses = ma.fields.Method("get_expenses")

    class Meta:
        model = CashRegister
        fields = [
            "id",
            "name",
            "payment_types",
            "balance",
            "histories",
            "incomes",
            "expenses",
        ]

    def get_incomes(self, obj):
        total_amount = (
            session.query(func.sum(Transaction.amount))
            .filter_by(
                debit_content_type="CashRegister",
                debit_object_id=obj.id,
                status=TransactionStatuses.PUBLISHED,
            )
            .scalar()
        )
        return total_amount if total_amount else 0

    def get_expenses(self, obj):
        total_amount = (
            session.query(func.sum(Transaction.amount))
            .filter_by(
                credit_content_type="CashRegister",
                credit_object_id=obj.id,
                status=TransactionStatuses.PUBLISHED,
            )
            .scalar()
        )
        return total_amount if total_amount else 0


class CashRegisterUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=False)
    payment_types_ids = ma.fields.List(
        ma.fields.Int(),
        required=False,
        load_only=True,
        validate=[validate.Length(min=1)],
    )

    class Meta:
        model = CashRegister
        fields = ["id", "name", "payment_types_ids"]


class BalanceAccountCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    code = ma.fields.Str(
        required=True, validate=[validate.Length(max=4), check_all_strs_is_nums]
    )
    account_type = ma.fields.Enum(required=True, enum=AccountTypes)

    class Meta:
        model = BalanceAccount
        fields = ["id", "name", "code", "account_type"]


class BalanceAccountListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    account_type = ma.fields.Enum(enum=AccountTypes)
    category = ma.fields.Enum(enum=AccountCategories)

    class Meta:
        model = BalanceAccount
        fields = [
            "id",
            "name",
            "code",
            "category",
            "account_type",
            "balance",
            "can_edit_delete",
        ]


class PagBalanceAccountSchema(ma.Schema):
    data = ma.fields.Nested(BalanceAccountListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class BalanceAccountRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    account_type = ma.fields.Enum(enum=AccountTypes)
    category = ma.fields.Enum(enum=AccountCategories)

    class Meta:
        model = BalanceAccount
        fields = [
            "id",
            "name",
            "code",
            "category",
            "account_type",
            "balance",
            "can_edit_delete",
        ]


class BalanceAccountUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    account_type = ma.fields.Enum(enum=AccountTypes)

    class Meta:
        model = BalanceAccount
        fields = ["id", "name", "code", "account_type"]


class TransactionHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")
    user_name = ma.fields.Method("get_user_name")
    operation_status = ma.fields.Enum(enum=CrudOperations)
    status = ma.fields.Enum(enum=TransactionStatuses)

    class Meta:
        model = TransactionHistory
        fields = ["operation_status", "created_at", "user_name", "data", "status", "id"]

    def get_user_name(self, obj):
        return obj.user_full_name


class TransactionCreateUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    credit_category = ma.fields.Str(
        required=True,
        validate=validate.OneOf(CATEGORY_LIST, error="Invalid credit category"),
    )
    debit_category = ma.fields.Str(
        required=True,
        validate=validate.OneOf(CATEGORY_LIST, error="Invalid debit category"),
    )
    status = ma.fields.Enum(enum=TransactionStatuses)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "number_transaction",
            "credit_category",
            "debit_category",
            "credit_object_id",
            "debit_object_id",
            "amount",
            "status",
        ]


class TransactionListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    credit_category = ma.fields.Method("get_credit_category")
    debit_category = ma.fields.Method("get_debit_category")
    status = ma.fields.Enum(enum=TransactionStatuses)
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")

    class Meta:
        model = Transaction
        fields = [
            "id",
            "credit_name",
            "debit_name",
            "amount",
            "created_at",
            "number_transaction",
            "status",
            "created_at",
            "can_edit",
            "can_cancel",
        ]


class PagTransactionSchema(ma.Schema):
    data = ma.fields.Nested(TransactionListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class TransactionCommentCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = TransactionComment
        fields = ["comment", "id"]


class TransactionCommentSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M", dump_only=True)
    user_name = ma.fields.Method("get_user_name")

    class Meta:
        model = TransactionComment
        fields = ["comment", "created_at", "user_name", "id"]

    def get_user_name(self, obj):
        return obj.user_full_name


class TransactionRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    credit_category = ma.fields.Method("get_credit_category")
    debit_category = ma.fields.Method("get_debit_category")
    status = ma.fields.Enum(enum=TransactionStatuses)
    histories = ma.fields.Method("get_sorted_histories")
    comments = ma.fields.Nested(TransactionCommentSchema, many=True)
    category = ma.fields.Enum(AccountCategories)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "category",
            "credit_name",
            "debit_name",
            "credit_object_id",
            "debit_object_id",
            "amount",
            "created_at",
            "number_transaction",
            "status",
            "credit_category",
            "debit_category",
            "published_date",
            "can_edit",
            "can_cancel",
            "histories",
            "comments",
        ]

    def get_sorted_histories(self, obj):
        # Сортируем связанные объекты histories по created_at (в порядке убывания)
        sorted_histories = sorted(
            obj.histories, key=lambda x: x.created_at, reverse=True
        )
        return TransactionHistorySchema(many=True).dump(sorted_histories)

    def get_credit_category(self, obj):
        if obj.credit_content_type == "Salary":
            return "User"
        return obj.credit_content_type

    def get_debit_category(self, obj):
        if obj.debit_content_type == "Salary":
            return "User"
        return obj.debit_content_type


class FileField(ma.fields.Field):
    default_error_messages = {"invalid": "Not a valid file."}

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        if not isinstance(value, FileStorage):
            raise ValidationError(self.error_messages["invalid"])
        return value


class AttachedFileSchema(ma.Schema):
    id = ma.fields.Int(dump_only=True)
    filename = ma.fields.String(description="Name of the file", required=True)
    description = ma.fields.String(
        description="Description of the file", required=False
    )
    filepath = ma.fields.String(
        dump_only=True, description="Get a static file from url"
    )
    counterparty_id = ma.fields.Int(required=True)


class CounterpartyForTransaction(ma.Schema):
    id = ma.fields.Int()
    name = ma.fields.Str()


class CounterpartySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    code = ma.fields.Str(
        required=True, validate=[validate.Length(4), check_all_strs_is_nums]
    )
    status = ma.fields.Enum(enum=Statuses, required=True)
    balance = ma.fields.Float(required=True)

    class Meta:
        model = Counterparty
        fields = ["name", "code", "status", "balance", "id"]


class CounterpartyListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)
    category = ma.fields.Enum(enum=AccountCategories)
    auto_charge = ma.fields.Method("get_charge_amount")
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")

    class Meta:
        model = Counterparty
        fields = [
            "name",
            "code",
            "status",
            "balance",
            "id",
            "charge_amount",
            "category",
            "created_at",
            "can_delete_and_edit",
        ]

    def get_charge_amount(self, obj):
        return obj.charge_amount / obj.charge_period_months


class PagCounterpartySchema(ma.Schema):
    data = ma.fields.Nested(CounterpartyListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class CounterpartyHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")
    user_name = ma.fields.Method("get_user_name")
    operation_status = ma.fields.Enum(enum=CrudOperations)
    status = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = TransactionHistory
        fields = ["operation_status", "created_at", "user_name", "data", "status", "id"]

    def get_user_name(self, obj):
        return obj.user_full_name


class CounterpartyRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)
    category = ma.fields.Enum(enum=AccountCategories, dump_only=True)
    files = ma.fields.Nested(AttachedFileSchema, many=True, dump_only=True)
    balance = ma.fields.Float(dump_only=True)
    can_delete_and_edit = ma.fields.Bool(dump_only=True)
    histories = ma.fields.Nested(CounterpartyHistorySchema, many=True)

    class Meta:
        model = Counterparty
        fields = [
            "id",
            "name",
            "code",
            "status",
            "balance",
            "auto_charge",
            "category",
            "created_at",
            "address",
            "legal_name",
            "inn_or_pinfl",
            "mfo",
            "legal_address",
            "contact",
            "files",
            "auto_charge",
            "charge_period_months",
            "charge_amount",
            "can_delete_and_edit",
            "histories",
        ]


class CounterpartyUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses, required=False)
    category = ma.fields.Enum(enum=AccountCategories, dump_only=True)
    name = ma.fields.Str(required=False)
    auto_charge = ma.fields.Bool(required=False)
    code = ma.fields.Str(
        required=False, validate=[validate.Length(4), check_all_strs_is_nums]
    )
    address = ma.fields.Str(required=False)
    legal_name = ma.fields.Str(required=False)
    inn_or_pinfl = ma.fields.Str(required=False)
    mfo = ma.fields.Str(required=False)
    legal_address = ma.fields.Str(required=False)
    contact = ma.fields.Str(required=False)
    charge_period_months = ma.fields.Int(required=False)
    charge_amount = ma.fields.Float(required=False)

    class Meta:
        model = Counterparty
        fields = [
            "name",
            "code",
            "status",
            "id",
            "auto_charge",
            "category",
            "address",
            "legal_name",
            "inn_or_pinfl",
            "mfo",
            "legal_address",
            "contact",
            "auto_charge",
            "charge_period_months",
            "charge_amount",
        ]


class TaxRateCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    payment_types_ids = ma.fields.List(
        ma.fields.Int(),
        required=True,
        load_only=True,
        validate=[validate.Length(min=1)],
    )
    category = ma.fields.Enum(enum=TaxRateCategories, required=True)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "payment_types_ids"]


class TaxRateListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    category = ma.fields.Enum(enum=TaxRateCategories)
    status = ma.fields.Enum(enum=Statuses)
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)

    class Meta:
        model = TaxRate
        fields = [
            "name",
            "rate",
            "category",
            "balance",
            "id",
            "code",
            "status",
            "payment_types",
        ]


class PagTaxRateSchema(ma.Schema):
    data = ma.fields.Nested(TaxRateListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class TaxRateRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    category = ma.fields.Enum(enum=TaxRateCategories)
    status = ma.fields.Enum(enum=Statuses)
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)

    class Meta:
        model = TaxRate
        fields = [
            "name",
            "rate",
            "category",
            "balance",
            "status",
            "id",
            "code",
            "payment_types",
        ]


class TaxRateUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    payment_types_ids = ma.fields.List(
        ma.fields.Int(),
        required=True,
        load_only=True,
        validate=[validate.Length(min=1)],
    )
    category = ma.fields.Enum(enum=TaxRateCategories, required=True)
    status = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "payment_types_ids", "status", "id"]


class CounterpartyIdSchema(ma.Schema):
    counterparty_id = ma.fields.Int(
        data_key="counterparty_id",
        required=True,
        description="for attaching to Counterparty",
    )
