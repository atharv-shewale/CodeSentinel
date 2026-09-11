"""
Unit tests for authentication logic.
"""

from app.auth import verify_token

def test_verify_token_valid():
    assert verify_token("secret-valid-bearer-token") is True

def test_verify_token_invalid():
    assert verify_token("invalid-token-123") is False
    assert verify_token("") is False
