from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from . import config


@lru_cache
def get_engine():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Run python -m app.setup_local.")
    url = make_url(config.DATABASE_URL)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("This project requires PostgreSQL.")
    url = url.set(drivername="postgresql+psycopg")
    return create_engine(
        url, pool_pre_ping=True, pool_size=5, max_overflow=5,
        connect_args={"connect_timeout": 10}, hide_parameters=True,
    )


def get_db():
    try:
        engine = get_engine()
    except (RuntimeError, ValueError):
        raise HTTPException(503, "Database is not configured. Contact the helpdesk administrator.") from None
    with Session(engine, expire_on_commit=False) as db:
        yield db
