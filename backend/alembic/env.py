from alembic import context

from app.database import get_engine
from app.models import Base

if context.is_offline_mode():
    context.configure(url=get_engine().url, target_metadata=Base.metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    def run_migrations(connection):
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
    else:
        with get_engine().connect() as connection:
            run_migrations(connection)
