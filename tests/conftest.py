import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import Base, engine, sync_schema_columns
from backend.app.seed_data import seed_database


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Initializes schema and seeds baseline database if uninitialized."""
    Base.metadata.create_all(bind=engine)
    sync_schema_columns()
    seed_database()
