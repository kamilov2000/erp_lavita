from enum import Enum


class MeasumentTypes(Enum):
    QUANTITY = "q"
    LITERS = "l"
    KILOGRAMS = "kg"


class InvoiceStatuses(Enum):
    DRAFT = "draft"
    PUBLIC = "public"
    CANCELED = "canceled"


class InvoiceTypes(Enum):
    INVOICE = "invoice"
    PRODUCTION = "production"
    EXPENSE = "expense"
    TRANSFER = "transfer"
