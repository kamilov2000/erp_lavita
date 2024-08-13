from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.utils import secure_filename
import pandas as pd

from app.base import session
from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.product.filter.schema import (
    FileMarkupFilter,
    MarkupFilterDetailSchema,
    MarkupFilterLoadSchema,
    MarkupFilterUpdateSchema,
    PagMarkupFilterSchema,
)
from app.product.models import Markup, MarkupFilter, ProductLot, ProductUnit
from app.utils.func import msg_response, token_required
from app.utils.exc import ItemNotFoundError
from app.utils.schema import ResponseSchema, TokenSchema

filter = Blueprint(
    "filter", __name__, url_prefix="/filter", description="Операции на Фильтрах"
)


@filter.route("/")
class PartAllView(MethodView):
    @token_required
    # @filter.arguments(FilterQueryArgSchema, location="query")
    @filter.arguments(TokenSchema, location="headers")
    @filter.response(200, PagMarkupFilterSchema)
    def get(c, self, args, token):
        """List filters"""
        page = args.pop("page", 1)
        try:
            limit = int(args.pop("limit", 10))
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        if limit <= 0:
            limit = 10
        try:
            query = MarkupFilter.query.filter_by(**args).order_by(
                MarkupFilter.created_at.desc()
            )
            total_count = query.count()
            total_pages = (total_count + limit - 1) // limit
            data = query.limit(limit).offset((page - 1) * limit).all()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
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
    @filter.arguments(MarkupFilterLoadSchema)
    @filter.arguments(TokenSchema, location="headers")
    @filter.response(400, ResponseSchema)
    @filter.response(201, MarkupFilterDetailSchema)
    def post(c, self, new_data, token):
        """Add a new filter"""
        try:
            session.add(new_data)
            session.commit()
        except SQLAlchemyError as e:
            current_app.logger.error(str(e.args))
            session.rollback()
            return msg_response("Something went wrong", False), 400
        return new_data


@filter.route("/<filter_id>/")
class PartById(MethodView):
    @token_required
    @filter.arguments(TokenSchema, location="headers")
    @filter.response(200, MarkupFilterDetailSchema)
    def get(c, self, token, filter_id):
        """Get filter by ID"""
        try:
            item = MarkupFilter.get_by_id(filter_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        return item

    @token_required
    @filter.arguments(MarkupFilterUpdateSchema)
    @filter.arguments(TokenSchema, location="headers")
    @filter.response(200, MarkupFilterDetailSchema)
    def put(c, self, update_data, token, filter_id):
        """Update existing filter"""
        try:
            item = MarkupFilter.get_by_id(filter_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")
        update_data.id = filter_id
        session.merge(update_data)
        session.commit()
        return item

    @token_required
    @filter.arguments(TokenSchema, location="headers")
    @filter.response(204)
    def delete(c, self, token, filter_id):
        """Delete filter"""
        try:
            MarkupFilter.delete(filter_id)
        except ItemNotFoundError:
            abort(404, message="Item not found.")


@filter.post("/<filter_id>/add-markups/")
@token_required
@filter.arguments(TokenSchema, location="headers")
@filter.arguments(FileMarkupFilter, location="files")
@filter.response(400, ResponseSchema)
@filter.response(200, MarkupFilterDetailSchema)
def add_markups_from_excel(c, token, data, filter_id):
    markup_filter = MarkupFilter.get_by_id(filter_id)
    file = data.get("file")
    if not data or not file:
        return msg_response("Invalid file input"), 400
    filename = secure_filename(file.filename)
    if filename.endswith(".csv"):
        df = pd.read_csv(file, usecols=[0], names=["id"], encoding="utf-8")
    elif filename.endswith(".xls") or filename.endswith(".xlsx"):
        df = pd.read_excel(file, usecols=[0], names=["id"], engine="openpyxl")
    else:
        return msg_response("Unsupported file format"), 400
    df = df.drop_duplicates()
    markup_ids = df["id"].tolist()

    for markup_id in markup_ids:
        exist = Markup.query.get(markup_id)
        if exist:
            if exist not in markup_filter.markups:
                markup_filter.markups.append(exist)
            continue
        existing_unit = (
            ProductUnit.query.join(
                ProductLot, ProductLot.id == ProductUnit.product_lot_id
            )
            .join(Invoice, Invoice.id == ProductLot.invoice_id)
            .filter(
                Invoice.type == InvoiceTypes.PRODUCTION,
                Invoice.status == InvoiceStatuses.PUBLISHED,
                ProductUnit.id == markup_id,
            )
            .first()
        )
        if existing_unit:
            markup_filter.markups.append(
                Markup(id=markup_id, is_used=True, date_of_use=existing_unit.created_at)
            )
        else:
            markup_filter.markups.append(Markup(id=markup_id, is_used=False))

    session.commit()
    return markup_filter
