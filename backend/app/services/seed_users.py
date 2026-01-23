"""
Seed users utility script.
Creates the initial admin user for the system.

Usage:
    cd backend
    PYTHONPATH=$PWD python -m app.services.seed_users

Or with custom credentials:
    PYTHONPATH=$PWD python -m app.services.seed_users --email admin@example.com --password secretpass123
"""

import argparse
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import User, UserRole
from app.utils.auth import get_password_hash


def create_admin_user(
    db: Session,
    email: str,
    password: str,
    full_name: str = "System Administrator"
) -> User | None:
    """Create an admin user if one doesn't exist."""
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"User with email '{email}' already exists.")
        if existing.role == UserRole.ADMIN.value:
            print("User is already an admin.")
        else:
            print(f"User has role: {existing.role}. Upgrading to ADMIN...")
            existing.role = UserRole.ADMIN.value
            db.commit()
            db.refresh(existing)
            print("User upgraded to admin successfully.")
        return existing

    # Create new admin user
    admin_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=UserRole.ADMIN.value,
        is_active=True,
        is_verified=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    print(f"Created admin user: {email}")
    return admin_user


def main():
    parser = argparse.ArgumentParser(description="Create initial admin user")
    parser.add_argument(
        "--email",
        default="admin@newspaper-intel.local",
        help="Admin email address (default: admin@newspaper-intel.local)"
    )
    parser.add_argument(
        "--password",
        default="changeme123!",
        help="Admin password (default: changeme123!)"
    )
    parser.add_argument(
        "--name",
        default="System Administrator",
        help="Admin full name (default: System Administrator)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Creating Admin User")
    print("=" * 50)

    db = SessionLocal()
    try:
        user = create_admin_user(
            db,
            email=args.email,
            password=args.password,
            full_name=args.name
        )
        if user:
            print()
            print("Admin user ready!")
            print(f"  Email: {args.email}")
            print(f"  Password: {args.password}")
            print()
            print("IMPORTANT: Change the password after first login!")
            print("=" * 50)
    finally:
        db.close()


if __name__ == "__main__":
    main()
