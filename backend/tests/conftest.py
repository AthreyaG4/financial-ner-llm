import pytest
from db import Base, get_db
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session():
    """An isolated in-memory SQLite DB per test - no real Postgres/network involved."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    """A TestClient wired to the in-memory DB, with real startup DB init disabled."""

    def override_get_db():
        yield db_session

    monkeypatch.setattr("main.init_db", lambda: None)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_background_tasks(monkeypatch):
    """Prevent the real placeholder tasks (which use the prod DB) from running during route tests."""
    monkeypatch.setattr(
        "routes.extractions.simulate_llamaparse", lambda extraction_id: None
    )
    monkeypatch.setattr(
        "routes.extractions.simulate_vllm_extraction", lambda extraction_id: None
    )
