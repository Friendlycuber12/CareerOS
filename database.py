import os

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg:///careeros")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

_initialized = False


class DatabaseUnavailableError(RuntimeError):
    """Raised when PostgreSQL is unavailable for API-backed features."""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"ok": True, "database_url": DATABASE_URL}
    except SQLAlchemyError as exc:
        return {"ok": False, "error": str(exc), "database_url": DATABASE_URL}


def ensure_database_initialized():
    global _initialized

    if _initialized:
        return

    try:
        import models

        Base.metadata.create_all(bind=engine)
        _initialized = True
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError(str(exc)) from exc
