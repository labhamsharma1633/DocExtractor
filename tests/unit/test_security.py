import pytest
from datetime import timedelta
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SecretPassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_generation_and_decoding():
    user_id = "12345678-1234-5678-1234-567812345678"
    token = create_access_token(subject=user_id)
    payload = decode_access_token(token)

    assert payload is not None
    assert payload.get("sub") == user_id


def test_expired_jwt_token():
    user_id = "12345678-1234-5678-1234-567812345678"
    # Create token that expired 10 minutes ago
    token = create_access_token(subject=user_id, expires_delta=timedelta(minutes=-10))
    payload = decode_access_token(token)

    assert payload is None
