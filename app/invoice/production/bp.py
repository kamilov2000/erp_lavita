from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import InvoiceQueryArgSchema, ProductionSchema
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import TokenSchema


production = Blueprint(
    "production",
    __name__,
    url_prefix="/production",
    description="Операции на Акт производства",
)


@production.route("/")
class InvoiceAllView(MethodView):
    @production.arguments(InvoiceQueryArgSchema, location="query")
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, ProductionSchema(many=True))
    def get(self, args, token):
        """List productions"""
        return Invoice.query.filter_by(**args).all()

    @production.arguments(ProductionSchema)
    @production.arguments(TokenSchema, location="headers")
    @production.response(201, ProductionSchema)
    def post(self, new_data, token):
        """Add a new production"""
        session.add(new_data)
        session.commit()
        return new_data


@production.route("/<production_id>/")
class InvoiceById(MethodView):
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, ProductionSchema)
    def get(self, token, production_id):
        """Get production by ID"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @production.arguments(ProductionSchema)
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, ProductionSchema)
    def put(self, update_data, token, production_id):
        """Update existing production"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = production_id
        session.merge(update_data)
        session.commit()
        return item

    @production.arguments(TokenSchema, location="headers")
    @production.response(204)
    def delete(self, token, production_id):
        """Delete production"""
        try:
            Invoice.delete(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
