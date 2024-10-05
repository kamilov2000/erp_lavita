from flask.views import MethodView
from app.finance.schema import ByNameSearchSchema
from app.region.models import Region
from app.region.schema import PagRegionSchema, RegionJsonSchema, RegionLoadSchema
from app.base import session
from app.utils.func import sql_exception_handler, token_required
from flask_smorest import Blueprint

from app.utils.mixins import CustomMethodPaginationView
from app.utils.schema import ResponseSchema

region = Blueprint(
    "region", __name__, url_prefix="/region", description="Операции на Регионах"
)


@region.route("/region")
class RegionView(CustomMethodPaginationView):
    model = Region

    @token_required
    @sql_exception_handler
    @region.arguments(RegionLoadSchema)
    @region.response(400, ResponseSchema)
    @region.response(201, RegionJsonSchema)
    def post(c, self, new_data):
        """Add a new region"""

        session.add(region)
        session.commit()
        schema = RegionLoadSchema()
        return schema.dump(region), 201

    @region.arguments(ByNameSearchSchema, location="query")
    @region.response(400, ResponseSchema)
    @region.response(200, PagRegionSchema)
    @token_required
    def get(c, self, args):
        """List region"""
        return super(RegionView, self).get(args)


@region.route("/region/<int:id>")
class RegionByIdView(MethodView):
    @token_required
    @region.response(200, RegionJsonSchema)
    def get(c, self, id):
        """Get region by ID"""

        item = Region.get_or_404(id)
        return item

    @token_required
    @sql_exception_handler
    @region.arguments(RegionJsonSchema)
    @region.response(200, RegionJsonSchema)
    def put(c, self, update_data, id):
        """Update existing region"""
        item = Region.get_or_404(id)
        schema = RegionJsonSchema()

        item.update(**update_data)
        session.commit()

        return schema.dump(item)

    @token_required
    @sql_exception_handler
    @region.response(204)
    def delete(c, self, id):
        """Delete region"""
        Region.delete_with_get(id)
