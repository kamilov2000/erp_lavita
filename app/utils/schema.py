import marshmallow as ma


class ResponseSchema(ma.Schema):
    ok = ma.fields.Bool()
    data = ma.fields.Raw()
    error = ma.fields.Raw()


class TokenSchema(ma.Schema):
    x_access_token = ma.fields.Str(
        data_key="x-access-token",
        required=True,
        description="Access token for authentication",
        example="your_access_token_here",
    )
