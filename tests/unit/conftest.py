import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from server.utils.db import Base, SessionLocal, engine


@pytest.fixture(scope="function")
def session():
    """
    Provides a test DB session in a savepoint.
    Rolls back after each test for full isolation.
    """
    from domains.saas import schema as saas_schema  # noqa: F401
    from domains.hr import schema as hr_schema  # noqa: F401
    from domains.legal import schema as legal_schema  # noqa: F401

    Base.metadata.create_all(engine)

    conn = engine.connect()
    trans = conn.begin()
    sess = SessionLocal(bind=conn)
    sess.begin_nested()

    yield sess

    sess.rollback()
    sess.close()
    trans.rollback()
    conn.close()
