"""Integration tests use a fresh, randomly named schema and never delete app tables."""
import os
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

@pytest.fixture(scope="session")
def app_context():
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database.")
    schema = "helpdesk_test_" + uuid.uuid4().hex
    base_url = make_url(raw_url).set(drivername="postgresql+psycopg")
    engine = create_engine(base_url)
    with engine.begin() as conn:
        conn.execute(text('CREATE SCHEMA "' + schema + '"'))
    engine.dispose()
    scoped_url = base_url.update_query_dict({"options": "-csearch_path=" + schema})
    os.environ["DATABASE_URL"] = scoped_url.render_as_string(hide_password=False)
    from app import config
    config.DATABASE_URL = os.environ["DATABASE_URL"]
    from app.database import get_engine
    get_engine.cache_clear()
    from alembic import command
    from alembic.config import Config
    migration_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(migration_config, "head")
    from app.main import app
    yield app
    get_engine().dispose()
    with engine.begin() as conn:
        conn.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
    engine.dispose()

@pytest.fixture
def clients(app_context):
    from fastapi.testclient import TestClient
    from app.security import _attempts
    _attempts.clear()
    clients = []
    def make():
        client = TestClient(app_context, headers={"X-Helpdesk-Request": "1"})
        clients.append(client)
        return client
    yield make
    for client in clients:
        client.close()
