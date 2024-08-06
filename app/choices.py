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
