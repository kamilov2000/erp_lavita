from app.warehouse.models import Warehouse
from app.user.models import User
from app.invoice.models import Invoice
from app.product.models import Product
from app.base import Base, engine


def init_db():
    Base.metadata.create_all(bind=engine)
