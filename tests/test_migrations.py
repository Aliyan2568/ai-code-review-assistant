from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.database import Base, _alembic_config, run_migrations


def make_engine(tmp_path):
    return create_engine(f"sqlite:///{tmp_path / 'test.db'}")


def test_migrations_match_models(tmp_path):
    engine = make_engine(tmp_path)
    run_migrations(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []


def test_downgrade_removes_tables(tmp_path):
    engine = make_engine(tmp_path)
    run_migrations(engine)
    cfg = _alembic_config()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()


def test_existing_database_without_alembic_is_stamped(tmp_path):
    engine = make_engine(tmp_path)
    Base.metadata.create_all(engine)  # simulates a database made by the old create_all startup
    run_migrations(engine)
    with engine.connect() as conn:
        assert MigrationContext.configure(conn).get_current_revision() == "0001"
    engine.dispose()
