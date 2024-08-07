class CustomError(Exception):
    pass


class ItemNotFoundError(CustomError):
    pass


class NotAvailableQuantity(CustomError):
    pass


class NotRightQuantity(CustomError):
    pass
