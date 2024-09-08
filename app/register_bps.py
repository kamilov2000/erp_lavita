from app.finance.bp import finance
from app.user.bp import user
from app.product.bp import product
from app.warehouse.bp import warehouse
from app.product.part.bp import part
from app.product.container.bp import container
from app.invoice.bp import invoice
from app.invoice.expense.bp import expense
from app.invoice.production.bp import production
from app.invoice.transfer.bp import transfer
from app.product.filter.bp import filter


def reg_bps(app):
    app.register_blueprint(user)
    app.register_blueprint(product)
    app.register_blueprint(warehouse)
    app.register_blueprint(part)
    app.register_blueprint(container)
    app.register_blueprint(invoice)
    app.register_blueprint(expense)
    app.register_blueprint(production)
    app.register_blueprint(transfer)
    app.register_blueprint(filter)
    app.register_blueprint(finance)
    return app
