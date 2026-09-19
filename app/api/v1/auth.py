from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import AppException, UnauthorizedException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.token import TokenResponse
from app.schemas.user import UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user with an email and password."""
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise AppException(
            message=f"A user with email '{user_in.email}' already exists.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"email": user_in.email},
        )

    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
def login_user(login_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns a Bearer access token."""
    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise UnauthorizedException("Invalid email or password")

    if not user.is_active:
        raise AppException("User account is inactive", status_code=status.HTTP_403_FORBIDDEN)

    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the profile information of the currently authenticated user."""
    return current_user
