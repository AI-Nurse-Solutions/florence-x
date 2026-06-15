"""SQLAlchemy engine/session factory. Used when FLORENCE_DATABASE_URL is set."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import settings

engine = create_engine(settings.database_url, future=True) if settings.database_url else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False) if engine else None
