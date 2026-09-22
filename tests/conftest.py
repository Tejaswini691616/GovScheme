# PATH: GovScheme/tests/conftest.py
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """
    Session-scoped, autouse: every test in this run shares ONE throwaway
    SQLite database, built fresh from schema.sql and seeded with the real
    scheme catalogue - so the test suite never writes test/dummy users into
    the actual development database (database/YojanaBharath.db), and every
    test file gets a working DB regardless of whether it uses the `client`
    fixture directly (audit finding: tests were previously polluting the
    shared dev DB, and DB-touching tests without `client` could fail once
    isolation was added without this session-scoped setup).
    """
    tmp_dir = tempfile.mkdtemp(prefix="smartgov_test_")
    tmp_db_path = os.path.join(tmp_dir, "test.db")

    from config import Config
    Config.DATABASE_PATH = tmp_db_path

    from database.build_db import build_database
    build_database()

    yield

    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def client():
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c
