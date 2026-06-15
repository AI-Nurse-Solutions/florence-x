"""P1-7 acceptance: a fresh database migrates clean and the resulting schema
matches the SQLAlchemy models (no drift between models.py and the migration).
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db.models import Base

API_DIR = Path(__file__).resolve().parents[2] / "apps" / "api"


def _alembic_config(url: str) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_fresh_db_migrates_clean_and_matches_models(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrate.db'}"
    monkeypatch.setenv("FLORENCE_DATABASE_URL", url)

    command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url, future=True)
    migrated = set(inspect(engine).get_table_names())

    expected = set(Base.metadata.tables.keys()) | {"alembic_version"}
    assert migrated == expected, f"schema drift: {expected ^ migrated}"


def test_downgrade_to_base_is_reversible(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'reverse.db'}"
    monkeypatch.setenv("FLORENCE_DATABASE_URL", url)
    cfg = _alembic_config(url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(url, future=True)
    remaining = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert remaining == set(), f"tables left after downgrade: {remaining}"
