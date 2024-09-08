TRANSACTION_DEBIT_CREDIT_CATEGORIES = [
    {"name": "Кассы", "value": "CashRegister"},
    {"name": "Счета баланса", "value": "BalanceAccount"},
    {"name": "Контрагенты", "value": "Counterparty"},
    {"name": "Клиенты", "value": "Client"},
    {"name": "Персонал", "value": "User"},
]
CATEGORY_COLLECTION = {
    "CashRegister": "Кассы",
    "BalanceAccount": "Счета баланса",
    "Counterparty": "Контрагенты",
    "Client": "Клиенты",
    "Staff": "Персонал",
}
CATEGORY_LIST = [
    "CashRegister",
    "BalanceAccount",
    "Counterparty",
    "Client",
    "Staff",
]


def check_all_strs_is_nums(data: str):
    return data.isdigit()
