from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.settings import settings


async def verify_admin_token(
    x_admin_token: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db)
):
    """
    Verify admin token for write operations.

    This dependency checks for the X-Admin-Token header and validates it
    against the ADMIN_TOKEN environment variable. If no token is configured,
    check is skipped (useful for development).

    Args:
        x_admin_token: Token from X-Admin-Token header
        db: Database session

    Returns:
        None if authentication is successful

    Raises:
        HTTPException: If authentication fails
    """
    # Skip token check if not configured (development mode)
    if not settings.admin_token:
        return

    # Check if token is provided
    if not x_admin_token:
        raise HTTPException(
            status_code=401,
            detail="Admin token required for this operation",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
