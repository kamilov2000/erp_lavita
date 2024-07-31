## Migration
```
pip install alembic
alembic init migrations
```
# in *alembic.ini* file change
sqlalchemy.url = postgresql+psycopg2://myuser:mypassword@0.0.0.0:5432/mydb

# then create migration
alembic revision --autogenerate -m "Create a baseline migrations"

# and upgrade

alembic upgrade head
