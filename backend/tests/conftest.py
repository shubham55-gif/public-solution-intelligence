"""Test setup using an in-memory SQLite database, never PostgreSQL credentials."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, get_db_session, get_development_user_id
from app.db.base import Base
from app.main import app
from app.models.entities import User, UserRole


@pytest.fixture
def development_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def client(development_user_id: UUID) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSession() as session:
        session.add(
            User(
                id=development_user_id,
                name="Test Citizen",
                email="test-citizen@example.test",
                password_hash="not-a-real-password-hash",
                role=UserRole.CITIZEN,
            )
        )
        authority_user_id = uuid4()
        session.add(
            User(
                id=authority_user_id,
                name="Test Authority",
                email="test-authority@example.test",
                password_hash="not-a-real-password-hash",
                role=UserRole.AUTHORITY,
            )
        )
        session.commit()

    def override_db_session() -> Generator[Session, None, None]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_development_user_id] = lambda: development_user_id

    with TestClient(app) as test_client:
        test_client.headers["X-Development-User-Id"] = str(development_user_id)
        test_client.development_user_id = development_user_id
        test_client.authority_user_id = authority_user_id
        test_client.testing_session_factory = TestingSession
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
