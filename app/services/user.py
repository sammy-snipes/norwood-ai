"""User service for managing user data and options."""

import logging
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import User
from app.schemas import UserOptions

logger = logging.getLogger(__name__)


def get_or_create_from_google(
    google_id: str,
    email: str,
    name: str | None,
    avatar_url: str | None,
    db: Session,
) -> User:
    """
    Find or create a user from Google OAuth data.

    Args:
        google_id: Google's unique user ID
        email: User's email from Google
        name: User's display name
        avatar_url: User's profile picture URL
        db: Database session

    Returns:
        User instance (existing or newly created)
    """
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        default_options = UserOptions().model_dump()
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            options=default_options,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.id} ({email})")
    else:
        # Update existing user info
        user.email = email
        user.name = name
        user.avatar_url = avatar_url
        db.commit()
        logger.debug(f"Updated user info: {user.id}")

    return user


def update_option(user: User, key: str, value: Any, db: Session) -> None:
    """
    Update a single user option.

    Args:
        user: User instance
        key: Option key to update
        value: New value for the option
        db: Database session
    """
    options = user.options or {}
    options[key] = value
    user.options = options
    flag_modified(user, "options")
    db.commit()
    logger.debug(f"Updated user {user.id} option {key}={value}")
