"""
MediRAG AI – Pytest Configuration
Uses an isolated SQLite test database created fresh each session.
Does NOT override os.environ globally (that breaks the production server).
"""

import os
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Point SQLAlchemy at a test-only DB for the duration of this session,
    then restore the original URL and delete the test file afterward.
    """
    from app import config as cfg_module

    TEST_DB_PATH = "test_medirag_session.db"
    TEST_DB_URL = f"sqlite+aiosqlite:///./{TEST_DB_PATH}"

    # Patch the singleton settings object in-place
    original_url = cfg_module.settings.database_url
    object.__setattr__(cfg_module.settings, "database_url", TEST_DB_URL)

    # Also patch the engine used by the models module
    from app.models import database as db_module
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    test_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
    test_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    original_engine = db_module.engine
    original_session = db_module.AsyncSessionLocal

    db_module.engine = test_engine
    db_module.AsyncSessionLocal = test_session_factory

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(db_module.Base.metadata.create_all)

    yield

    # Teardown
    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.AsyncSessionLocal = original_session
    object.__setattr__(cfg_module.settings, "database_url", original_url)

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
