SQLALCHEMY_URI = "postgresql+psycopg2://username:password@localhost/db_name"
SECRET_KEY = "klfahojaoigheohrO@H$O@Q%21"
DEBUG = True
API_TITLE = "ERP API"
API_VERSION = "v1"
OPENAPI_VERSION = "3.0.2"
OPENAPI_URL_PREFIX = "/openapi"
OPENAPI_SWAGGER_UI_PATH = "/swagger"
OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
OPENAPI_REDOC_URL = "/redoc"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
UPLOAD_FOLDER = "uploads"
SCHEDULER_API_ENABLED = False
API_SPEC_OPTIONS = {
    "components": {
        "securitySchemes": {
            "Bearer Auth": {
                "type": "apiKey",
                "in": "header",
                "name": "x-access-token",
                "bearerFormat": "JWT",
                "description": "Enter: **'&lt;JWT&gt;'**, where JWT is the access token",
            }
        }
    },
}
