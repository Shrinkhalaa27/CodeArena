from alembic import context

from app import models  # noqa: F401  (register tables)
from app.db import Base, make_engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = make_engine()  # DATABASE_URL from the environment
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
