from enum import Enum


class MeasumentTypes(Enum):
    QUANTITY = "q"
    LITERS = "l"
    KILOGRAMS = "kg"


class InvoiceStatuses(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELED = "canceled"


class InvoiceTypes(Enum):
    INVOICE = "invoice"
    PRODUCTION = "production"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class DebtTypes(Enum):
    CONTAINER = "container"
    PART = "part"


class Statuses(Enum):
    ON = "on"
    OFF = "off"

class TaxRateCategories(Enum):
    VAT = "vat"
    OTHER = "other"


class AccountCategories(Enum):
    SYSTEM = "system"
    USER = "user"


class AccountTypes(Enum):
    ACTIVE = "active"
    PASSIVE = "passive"


class TransactionStatuses(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class CreditDebitCategories(Enum):
    CASH_REGISTER = "cash_register"
    COUNTERPARTY = "counterparty"
    BALANCE_ACCOUNT = "balance_account"
    STAFF = "staff"
    CLIENTS = "client"


class CrudOperations(Enum):
    CREATED = "created"
    UPDATED = "updated"
