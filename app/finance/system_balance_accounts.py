from app.finance.models import BalanceAccount

SYSTEM_BALANCE_COUNTS = [
    {"name": "Постоянные расходы",
     "code": "9430"},
    {"name": "Переменные расходы",
     "code": "9435"},
    {"name": "Выручка",
     "code": "9030"},
    {"name": "Себестоимость",
     "code": "9130"},
    {"name": "Амортизация",
     "code": "9450"},
    {"name": "Прибыль",
     "code": "9910"},
    {"name": "Зарплаты постоянные",
     "code": "9420"},
    {"name": "Зарплаты переменные",
     "code": "9425"},
    {"name": "Основные средства",
     "code": "0100"},
    {"name": "Посредники",
     "code": "4030"},
    {"name": "Диведенды",
     "code": "9910"},
    {"name": "Займы",
     "code": "6800"}
]


def create_system_balance_accounts(session):
    item = BalanceAccount.query.filter_by(name=SYSTEM_BALANCE_COUNTS[0]['name']).first()

    if item:
        return
    lst = []
    for data in SYSTEM_BALANCE_COUNTS:
        bal_acc = BalanceAccount(**data)
        lst.append(bal_acc)
    session.add_all(lst)
    session.commit()


