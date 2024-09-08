from marshmallow import validate, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
import marshmallow as ma
from werkzeug.datastructures import FileStorage

from app.choices import Statuses, TaxRateCategories, AccountCategories, AccountTypes, TransactionStatuses
from app import CrudOperations
from app.finance.models import PaymentType, CashRegister, Transaction, BalanceAccount, CashRegisterHistory, \
    TransactionHistory, TransactionComment, Counterparty, TaxRate
from app.finance.utils import CATEGORY_COLLECTION, CATEGORY_LIST, check_all_strs_is_nums
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class ByNameSearchSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search by name")
    page = ma.fields.Int()
    limit = ma.fields.Int()


class ByNameAndCategorySearchSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search by name")
    category = ma.fields.Enum(enum=AccountCategories, description="Filter by Category")
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
    category = ma.fields.Enum(enum=TaxRateCategories)


class TaxRateArgsSchema(ma.Schema):
    name = ma.fields.String(required=False, description="Search")
    page = ma.fields.Int()
    limit = ma.fields.Int()
    created_date = ma.fields.Date()
    category = ma.fields.Enum(enum=TaxRateCategories)


class PaymentTypeListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PaymentType
        fields = ["id", "name", "commission_percentage"]


class PaymentTypeCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PaymentType


class PaymentTypeForRelationsSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PaymentType
        fields = ["id", "name"]


class PagPaymentTypeSchema(ma.Schema):
    data = ma.fields.Nested(PaymentTypeListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class PaymentTypeRetrieveUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = PaymentType
        fields = ["id", "name", "has_commissioner", "commission_percentage"]


class CashRegisterCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    payment_types_ids = ma.fields.List(ma.fields.Int(), required=True, load_only=True,
                                       validate=[validate.Length(min=1)])

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
    number_transaction = ma.fields.Method("get_number_transaction")
    status = ma.fields.Enum(enum=TransactionStatuses)

    class Meta:
        model = Transaction
        fields = ["id", "number_transaction", "amount", "created_at", "status"]

    def get_number_transaction(self, obj):
        return f"№{obj.id}"


class CashRegisterHistorySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M")
    user_name = ma.fields.Method("get_user_name")
    operation_status = ma.fields.Enum(enum=CrudOperations)

    class Meta:
        model = CashRegisterHistory
        fields = ["operation_status", "created_at", "user_name", "data"]

    def get_user_name(self, obj):
        return obj.user_full_name


class CashRegisterRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    histories = ma.fields.Nested(CashRegisterHistorySchema, many=True)
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)

    class Meta:
        model = CashRegister
        fields = ["id", "name", "payment_types", "balance", "histories"]


class CashRegisterUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=False)
    payment_types_ids = ma.fields.List(ma.fields.Int(), required=False, load_only=True,
                                       validate=[validate.Length(min=1)])

    class Meta:
        model = CashRegister
        fields = ["id", "name", "payment_types_ids"]


class BalanceAccountCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    code = ma.fields.Str(required=True, validate=[validate.Length(4), check_all_strs_is_nums])
    account_type = ma.fields.Enum(required=True, enum=AccountTypes)

    class Meta:
        model = BalanceAccount
        fields = ["id", "name", "code", "account_type"]


class BalanceAccountListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = BalanceAccount
        fields = ["id", "name", "code", "category", "account_type"]


class PagBalanceAccountSchema(ma.Schema):
    data = ma.fields.Nested(CashRegisterListSchema(many=True))
    pagination = ma.fields.Nested(BalanceAccountListSchema)


class BalanceAccountRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = BalanceAccount
        fields = ["id", "name", "code", "category", "account_type", "balance"]


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
        fields = ["operation_status", "created_at", "user_name", "data", "status"]

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
            "credit_category",
            "debit_category",
            "credit_object_id",
            "debit_object_id",
            "amount",
            "status"
        ]


class TransactionListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    credit_category = ma.fields.Method("get_credit_category")
    debit_category = ma.fields.Method("get_debit_category")
    number_transaction = ma.fields.Method("get_number_transaction")
    status = ma.fields.Enum(enum=TransactionStatuses)

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
            "credit_category",
            "debit_category",
            "created_at"
        ]

    def get_number_transaction(self, obj):
        return f"№{obj.id}"

    def get_credit_category(self, obj):
        return CATEGORY_COLLECTION[obj.credit_content_type]

    def get_debit_category(self, obj):
        return CATEGORY_COLLECTION[obj.debit_content_type]


class PagTransactionSchema(ma.Schema):
    data = ma.fields.Nested(TransactionListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class TransactionCommentSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    created_at = ma.fields.DateTime(format="%d %b %Y, %H:%M", dump_only=True)
    user_name = ma.fields.Method("get_user_name")

    class Meta:
        model = TransactionComment
        fields = ["comment", "created_at", "user_name"]

    def get_user_name(self, obj):
        return obj.user_full_name


class TransactionRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    credit_category = ma.fields.Method("get_credit_category")
    debit_category = ma.fields.Method("get_debit_category")
    number_transaction = ma.fields.Method("get_number_transaction")
    status = ma.fields.Enum(enum=TransactionStatuses)
    histories = ma.fields.Method("get_sorted_histories")
    comments = ma.fields.Nested(TransactionCommentSchema, many=True)

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
        sorted_histories = sorted(obj.histories, key=lambda x: x.created_at, reverse=True)
        return TransactionHistorySchema(many=True).dump(sorted_histories)

    def get_number_transaction(self, obj):
        return f"№{obj.id}"

    def get_credit_category(self, obj):
        return CATEGORY_COLLECTION[obj.credit_content_type]

    def get_debit_category(self, obj):
        return CATEGORY_COLLECTION[obj.debit_content_type]


class FileField(ma.fields.Field):
    default_error_messages = {
        "invalid": "Not a valid file."
    }

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        if not isinstance(value, FileStorage):
            raise ValidationError(self.error_messages["invalid"])
        return value


class AttachedFileSchema(ma.Schema):
    id = ma.fields.Int(dump_only=True)
    filename = ma.fields.String(description='Name of the file', required=True)
    description = ma.fields.String(description='Description of the file', required=True)
    filepath = ma.fields.String(dump_only=True, description="Get a static file from url")


class CounterpartyForTransaction(ma.Schema):
    id = ma.fields.Int()
    name = ma.fields.Str()


class CounterpartySchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    name = ma.fields.Str(required=True)
    code = ma.fields.Str(required=True, validate=[validate.Length(4), check_all_strs_is_nums])
    status = ma.fields.Enum(enum=Statuses, required=True)
    balance = ma.fields.Float(required=True)

    class Meta:
        model = Counterparty
        fields = [
            "name", "code", "status", "balance", "id"
        ]


class CounterpartyListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)
    category = ma.fields.Enum(enum=AccountCategories)

    class Meta:
        model = Counterparty
        fields = [
            "name", "code", "status", "balance", "id", "auto_charge", "category", "created_at"
        ]


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
        fields = ["operation_status", "created_at", "user_name", "data", "status"]

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
            "name", "code", "status", "balance", "id", "auto_charge", "category", "created_at",
            "address", "legal_name", "inn_or_pinfl", "mfo", "legal_address", "contact", "files",
            "auto_charge", "charge_period_months", "charge_amount", "can_delete_and_edit",
            "histories",
        ]


class CounterpartyUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    status = ma.fields.Enum(enum=Statuses)
    category = ma.fields.Enum(enum=AccountCategories, dump_only=True)

    class Meta:
        model = Counterparty
        fields = [
            "name", "code", "status", "id", "auto_charge", "category"
                                                           "address", "legal_name", "inn_or_pinfl", "mfo",
            "legal_address", "contact",
            "auto_charge", "charge_period_months", "charge_amount",
        ]


class TaxRateCreateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    payment_types_ids = ma.fields.List(
        ma.fields.Int(), required=True, load_only=True,
        validate=[validate.Length(min=1)]
    )
    category = ma.fields.Enum(enum=TaxRateCategories, required=True)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "payment_types_ids"]


class TaxRateListSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    category = ma.fields.Enum(enum=TaxRateCategories)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "balance", "id", "code"]


class PagTaxRateSchema(ma.Schema):
    data = ma.fields.Nested(TaxRateListSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)


class TaxRateRetrieveSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    category = ma.fields.Enum(enum=TaxRateCategories)
    status = ma.fields.Enum(enum=Statuses)
    payment_types = ma.fields.Nested(PaymentTypeForRelationsSchema, many=True)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "balance", "status", "id", "code", "payment_types"]


class TaxRateUpdateSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    payment_types_ids = ma.fields.List(
        ma.fields.Int(), required=True, load_only=True,
        validate=[validate.Length(min=1)]
    )
    category = ma.fields.Enum(enum=TaxRateCategories, required=True)
    status = ma.fields.Enum(enum=Statuses)

    class Meta:
        model = TaxRate
        fields = ["name", "rate", "category", "payment_types_ids", "status", "id"]
