import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models import User, UserRole

# Use an in-memory SQLite database for all tests for speed and simplicity
# StaticPool is required for in-memory DB shared across threads
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once for the entire test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    """Provide a clean database session for each test, with transaction rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def override_get_db(db):
    """Override the get_db dependency for all tests in the session."""
    def _get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    yield
    # No need to clear here as it's autouse, but could if needed
    # app.dependency_overrides.clear()

@pytest.fixture
def client():
    """Provide a TestClient for all tests."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_admin_user():
    return User(
        id=999,
        email="admin@example.com",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )

@pytest.fixture
def mock_reader_user():
    return User(
        id=888,
        email="reader@example.com",
        full_name="Reader User",
        role=UserRole.READER,
        is_active=True
    )
