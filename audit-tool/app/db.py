from sqlalchemy import create_engine, Engine
from app.config import settings

_engine: Engine | None = None

def get_engine() -> Engine:
    """Returns a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.supabase_db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    return _engine

def get_connection():
    """Context manager that yields a database connection and handles cleanup."""
    engine = get_engine()
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()
