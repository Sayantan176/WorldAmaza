from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.services.auth_service import COOKIE_NAME, verify_session_token


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieves authenticated user if valid session exists, otherwise None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    payload = verify_session_token(token)
    if not payload:
        return None

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Enforces authentication. Redirects web requests to /login, raises 401 for API."""
    user = get_current_user_optional(request, db)
    if not user:
        is_api = request.url.path.startswith("/api/")
        if is_api:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please log in.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/login"}
            )
    return user
