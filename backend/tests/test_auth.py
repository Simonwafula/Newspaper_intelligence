import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.schemas import UserCreate
from app.services.auth_service import create_user, authenticate_user
from app.utils.auth import get_password_hash, verify_password, create_access_token

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def db():
    Base.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.drop_all(bind=engine)


def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    # Verify password works
    assert verify_password(password, hashed) == True
    
    # Verify wrong password fails
    assert verify_password("wrongpassword", hashed) == False


def test_jwt_token_creation():
    """Test JWT token creation"""
    data = {"sub": "1", "email": "test@example.com"}
    token = create_access_token(data)
    
    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0


def test_user_creation(db):
    """Test user creation in database"""
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    user = create_user(db, user_data)
    
    # Check user was created correctly
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active == True
    assert user.id is not None
    assert user.hashed_password != "testpassword123"  # Should be hashed


def test_user_authentication(db):
    """Test user authentication"""
    # First create a user
    user_data = UserCreate(
        email="auth@example.com",
        password="authpassword123",
        full_name="Auth User"
    )
    create_user(db, user_data)
    
    # Test successful authentication
    user = authenticate_user(db, "auth@example.com", "authpassword123")
    assert user is not None
    assert user.email == "auth@example.com"
    
    # Test failed authentication with wrong password
    user = authenticate_user(db, "auth@example.com", "wrongpassword")
    assert user is None
    
    # Test failed authentication with non-existent user
    user = authenticate_user(db, "nonexistent@example.com", "anypassword")
    assert user is None


def test_user_registration_api():
    """Test user registration via API"""
    client = TestClient(app)
    
    response = client.post("/api/users/register", json={
        "email": "apitest@example.com",
        "password": "apipassword123",
        "full_name": "API Test User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "apitest@example.com"
    assert data["full_name"] == "API Test User"
    assert data["is_active"] == True
    assert "id" in data


def test_user_login_api():
    """Test user login via API"""
    client = TestClient(app)
    
    # First register a user
    client.post("/api/users/register", json={
        "email": "login@example.com",
        "password": "loginpassword123",
        "full_name": "Login User"
    })
    
    # Test successful login
    response = client.post("/api/users/login", json={
        "email": "login@example.com",
        "password": "loginpassword123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    
    # Test failed login with wrong password
    response = client.post("/api/users/login", json={
        "email": "login@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    
    # Test failed login with non-existent user
    response = client.post("/api/users/login", json={
        "email": "nonexistent@example.com",
        "password": "anypassword"
    })
    
    assert response.status_code == 401


def test_protected_endpoints():
    """Test that protected endpoints require authentication"""
    client = TestClient(app)
    
    # Test accessing protected endpoint without token
    response = client.get("/api/users/me")
    assert response.status_code == 401
    
    # Test accessing protected endpoint with invalid token
    response = client.get("/api/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401