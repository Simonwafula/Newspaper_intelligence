from app.schemas import UserCreate
from app.services.auth_service import authenticate_user, create_user
from app.utils.auth import create_access_token, get_password_hash, verify_password


def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_jwt_token_creation():
    """Test JWT token creation"""
    data = {"sub": "1", "email": "test@example.com"}
    token = create_access_token(data)
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
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active
    assert user.id is not None

def test_user_authentication(db):
    """Test user authentication"""
    user_data = UserCreate(
        email="auth@example.com",
        password="authpassword123",
        full_name="Auth User"
    )
    create_user(db, user_data)
    user = authenticate_user(db, "auth@example.com", "authpassword123")
    assert user is not None
    assert user.email == "auth@example.com"

def test_user_registration_api(client):
    """Test user registration via API"""
    response = client.post("/api/users/register", json={
        "email": "apitest@example.com",
        "password": "apipassword123",
        "full_name": "API Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "apitest@example.com"

def test_user_login_api(client):
    """Test user login via API"""
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
    assert "access_token" in response.json()

def test_protected_endpoints(client):
    """Test that protected endpoints require authentication"""
    response = client.get("/api/users/me")
    assert response.status_code == 401
