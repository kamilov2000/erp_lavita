import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field

from app.user.models import User
from app.base import session
from app.utils.schema import DefaultDumpsSchema, PaginationSchema


class UserSchema(SQLAlchemyAutoSchema, DefaultDumpsSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = True
        sqla_session = session

    role = auto_field(dump_only=True)
    password = auto_field(load_only=True)

    @ma.pre_load
    def hash_password(self, in_data, **kwargs):
        if in_data.get("password"):
            in_data["password"] = User.generate_password(in_data["password"])
        return in_data


class UserUpdateSchema(SQLAlchemySchema):
    class Meta:
        model = User
        include_fk = True

    first_name = auto_field(required=False)
    last_name = auto_field(required=False)
    password = auto_field(required=False)


class LoginSchema(ma.Schema):
    username = ma.fields.Str()
    password = ma.fields.Str()


class LoginResponseSchema(ma.Schema):
    token = ma.fields.Str()
    role = ma.fields.Str()


class UserQueryArgSchema(ma.Schema):
    page = ma.fields.Int(default=1)
    limit = ma.fields.Int(default=1)
    username = ma.fields.Str()
    first_name = ma.fields.Str()
    last_name = ma.fields.Str()
    role = ma.fields.Str()


class PagUserSchema(ma.Schema):
    data = ma.fields.Nested(UserSchema(many=True))
    pagination = ma.fields.Nested(PaginationSchema)
