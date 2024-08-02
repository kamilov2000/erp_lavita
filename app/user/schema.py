import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

from app.user.models import User
from app.base import session
from app.utils.schema import DefaultDumpsSchema


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
        in_data["password"] = User.generate_password(in_data["password"])
        return in_data


class LoginSchema(ma.Schema):
    username = ma.fields.Str()
    password = ma.fields.Str()


class LoginResponseSchema(ma.Schema):
    token = ma.fields.Str()
    role = ma.fields.Str()
