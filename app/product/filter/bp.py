from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from flask import current_app, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.utils import secure_filename
import pandas as pd

from app.base import session
from app.choices import InvoiceStatuses, InvoiceTypes
from app.invoice.models import Invoice
from app.product.filter.schema import (
    FileMarkupFilter,
    FilterQueryArgSchema,
    MarkupFilterDetailSchema,
    MarkupFilterLoadSchema,
    MarkupFilterUpdateSchema,
    MarkupSchema,
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
class MarkupFilterAllView(MethodView):
    @token_required
    @filter.arguments(FilterQueryArgSchema, location="query")
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
class MarkupFilterById(MethodView):
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
    # Check if the filter_id is valid
    markup_filter = MarkupFilter.get_by_id(filter_id)
    if not markup_filter:
        return msg_response("Invalid filter ID", 0), 400
    
    # Extract file from data
    file = data.get("file")
    if not file:
        return msg_response("Invalid file input", 0), 400
    
    # Read file based on its extension
    filename = secure_filename(file.filename)
    if filename.endswith(".csv"):
        df = pd.read_csv(file, usecols=[0], names=["id"], encoding="utf-8", sep="\s+|;|:|,")
    elif filename.endswith(".xls") or filename.endswith(".xlsx"):
        df = pd.read_excel(file, usecols=[0], names=["id"], engine="openpyxl")
    else:
        return msg_response("Unsupported file format", 0), 400

    # Clean up data
    df = df.drop_duplicates().dropna()
    markup_ids = df["id"].astype(str).tolist()

    # Batch query to check existing markups
    existing_markups = Markup.query.filter(Markup.id.in_(markup_ids)).all()
    existing_markup_ids = {markup.id for markup in existing_markups}

    # Batch query to check ProductUnit existence
    existing_units = (
        ProductUnit.query
        .join(ProductLot, ProductLot.id == ProductUnit.product_lot_id)
        .join(Invoice, Invoice.id == ProductLot.invoice_id)
        .filter(
            Invoice.type == InvoiceTypes.PRODUCTION,
            Invoice.status == InvoiceStatuses.PUBLISHED,
            ProductUnit.id.in_(markup_ids),
        )
        .options(joinedload(ProductUnit.product_lot).joinedload(ProductLot.invoice))
        .all()
    )
    existing_units_ids = {unit.id: unit for unit in existing_units}

    # Collect new markups to add
    new_markups = []
    for markup_id in markup_ids:
        if markup_id in existing_markup_ids:
            if markup_id not in [markup.id for markup in markup_filter.markups]:
                markup_filter.markups.append(Markup(id=markup_id))
        else:
            unit = existing_units_ids.get(markup_id)
            if unit:
                new_markups.append(Markup(id=markup_id, is_used=True, date_of_use=unit.created_at))
            else:
                new_markups.append(Markup(id=markup_id, is_used=False))

    # Add new markups in bulk
    markup_filter.markups.extend(new_markups)

    # Commit the transaction
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        return msg_response(str(e), 0), 500

    return msg_response(markup_filter.to_dict()), 200


@filter.get("/<filter_id>/unused-markups/")
@token_required
@filter.arguments(TokenSchema, location="headers")
@filter.response(400, ResponseSchema)
@filter.response(200, MarkupSchema(many=True))
def detail_unused(c, token, filter_id):
    MarkupFilter.get_by_id(filter_id)
    res = MarkupFilter.get_unused_markups_by_filter_id(session, filter_id)
    return res
