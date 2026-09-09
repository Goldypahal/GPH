import time
from typing import Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

is_sqlite = "sqlite" in settings.DATABASE_URL.lower()

engine_kwargs: Dict[str, Any] = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_health() -> Dict[str, Any]:
    """Tests database connectivity and latency."""
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start) * 1000.0, 2)
        return {
            "status": "READY",
            "dialect": engine.dialect.name,
            "latency_ms": latency
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "dialect": engine.dialect.name,
            "error": str(e)
        }
