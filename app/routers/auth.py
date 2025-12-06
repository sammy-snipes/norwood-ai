"""Google OAuth authentication router."""

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

settings = get_settings()

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


# Schemas
class UserOptionsResponse(BaseModel):
    completed_captcha: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    avatar_url: str | None
    is_premium: bool
    is_admin: bool
    free_analyses_remaining: int
    options: UserOptionsResponse = UserOptionsResponse()

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """Convert User model to response, handling JSONB options."""
        opts = user.options or {}
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_premium=user.is_premium,
            is_admin=user.is_admin,
            free_analyses_remaining=user.free_analyses_remaining,
            options=UserOptionsResponse(**opts),
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# JWT helpers
def create_access_token(user_id: str) -> str:
    """Create a JWT token for the user."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str | None:
    """Decode JWT and return user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# Dependencies
def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = None,
) -> User | None:
    """Get current user from JWT token. Returns None if not authenticated."""
    if not token:
        return None

    user_id = decode_token(token)
    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()


def require_auth(
    db: Session = Depends(get_db),
    token: str = Depends(lambda: None),  # Will be replaced with proper header extraction
) -> User:
    """Require authentication. Raises 401 if not authenticated."""
    # Extract token from Authorization header
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Routes
@router.get("/google")
def google_login():
    """Redirect to Google OAuth."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.FRONTEND_URL}/api/auth/google/callback",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token",
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google",
            )

        google_user = userinfo_response.json()

    # Find or create user
    google_id = google_user["id"]
    email = google_user["email"]
    name = google_user.get("name")
    avatar_url = google_user.get("picture")

    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing user info
        user.email = email
        user.name = name
        user.avatar_url = avatar_url
        db.commit()

    # Create JWT
    jwt_token = create_access_token(user.id)

    # Redirect to frontend with token
    # Frontend will store this token and use it for subsequent requests
    redirect_url = f"{settings.FRONTEND_URL}/?token={jwt_token}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserResponse)
def get_me(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Get current authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return UserResponse.from_user(user)


@router.post("/captcha-completed")
def mark_captcha_completed(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """Mark the donate captcha as completed for the current user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Update options
    options = user.options or {}
    options["completed_captcha"] = True
    user.options = options
    db.commit()

    return {"success": True}
