from logging.config import fileConfig

from alembic import context

from app.db import engine
from app.models import Base

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations_online() -> None:
    is_sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as connection:
        if is_sqlite:
            # SQLite migrations that change constraints rebuild the table (copy, drop,
            # rename). With foreign keys enforced, dropping the old table would
            # cascade-delete every row that references it, so enforcement is off
            # while migrating. Must run outside a transaction to take effect.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            # Batch mode lets ALTER TABLE migrations work on SQLite too.
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        if is_sqlite:
            problems = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if problems:
                raise RuntimeError(f"Migration left broken references: {problems[:5]}")
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


run_migrations_online()
