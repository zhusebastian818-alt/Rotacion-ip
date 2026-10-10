"""Database session manager, base model, and PostgreSQL/SQLite configuration using SQLAlchemy 2.0."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.core.config import settings

# Retrieve database URL from environment or configuration, fallback to SQLite if needed
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./saas.db"
)

# Create SQLAlchemy engine with connection parameters appropriate for SQLite or PostgreSQL
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    engine_args.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_engine(
    DATABASE_URL,
    future=True,
    **engine_args
)

# Session maker factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
