from app.choices import InvoiceTypes
from app.utils.func import msg_response, token_required
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.invoice.models import Invoice
from app.invoice.schema import (
    InvoiceQueryArgSchema,
    PagProductionSchema,
    ProductionSchema,
)
from app.base import session
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema, TokenSchema


production = Blueprint(
    "production",
    __name__,
    url_prefix="/production",
    description="Операции на Акт производства",
)


@production.route("/")
class InvoiceAllView(MethodView):
    @token_required
    @production.arguments(InvoiceQueryArgSchema, location="query")
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, PagProductionSchema)
    def get(c, self, args, token):
        """List productions"""
        page = args.pop("page", 1)
        limit = args.pop("limit", 10)
        query = Invoice.query.filter_by(type=InvoiceTypes.PRODUCTION, **args)
        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit
        data = query.limit(limit).offset((page - 1) * limit).all()
        response = {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_count": total_count,
            },
        }

        return response

    @token_required
    @production.arguments(ProductionSchema)
    @production.arguments(TokenSchema, location="headers")
    @production.response(400, ResponseSchema)
    @production.response(201, ProductionSchema)
    def post(c, self, new_data, token):
        """Add a new production"""
        try:
            new_data.type = InvoiceTypes.PRODUCTION
            new_data.user_id = c.id
            session.add(new_data)
            session.commit()
            new_data.write_history()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@production.route("/<production_id>/")
class InvoiceById(MethodView):
    @token_required
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, ProductionSchema)
    def get(c, self, token, production_id):
        """Get production by ID"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @production.arguments(ProductionSchema)
    @production.arguments(TokenSchema, location="headers")
    @production.response(200, ProductionSchema)
    def put(c, self, update_data, token, production_id):
        """Update existing production"""
        try:
            item = Invoice.get_by_id(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = production_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @production.arguments(TokenSchema, location="headers")
    @production.response(204)
    def delete(c, self, token, production_id):
        """Delete production"""
        try:
            Invoice.delete(production_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
