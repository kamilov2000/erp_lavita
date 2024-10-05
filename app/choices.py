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
    User = "user"
    CLIENT = "client"


class CrudOperations(Enum):
    CREATED = "created"
    UPDATED = "updated"


class SalaryFormat(Enum):
    EMPLOYEE = "employee"
    DRIVER = "driver"
    SUPPORT_OPERATOR = "support_operator"


class DaysOfWeekShort(Enum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


class WorkScheduleStatus(Enum):
    PRESENCE = "presence"
    SKIP = "skip"
    LATENESS = "lateness"
    VACATION = "vacation"
    DAY_OFF = "day_off"


class UserTransactionAction(Enum):
    BONUS = "bonus"
    PENALTY = "penalty"


class ClientEntityType(Enum):
    INDIVIDUAL = "individual"
    LEGAL = "legal"
