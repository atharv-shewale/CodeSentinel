"""
CodeSentinel Analysis Test Fixtures: Sample Source Codes.
"""

SAMPLE_PYTHON_SOURCE = '''"""Authentication Service Module."""

import os
from typing import Optional, Dict, List
from datetime import datetime

class AuthenticationService:
    """Handles user authentication and JWT token lifecycle."""

    def __init__(self, secret_key: str, token_ttl: int = 3600):
        self.secret_key = secret_key
        self.token_ttl = token_ttl

    def authenticate_user(self, username: str, password_hash: str) -> Optional[Dict[str, str]]:
        """
        Verify credentials and issue session token.
        Requirement: REQ-AUTH-001
        """
        if not username or not password_hash:
            return None
        token = self._generate_token(username)
        return {"token": token, "username": username}

    def _generate_token(self, username: str) -> str:
        """Internal helper to generate signed token."""
        return f"token_{username}_{self.token_ttl}"


def hash_password(plain_text: str, salt: Optional[str] = None) -> str:
    """
    Hash plain text password with optional salt.
    Requirement: REQ-SEC-002
    """
    if salt:
        return f"hashed_{plain_text}_{salt}"
    return f"hashed_{plain_text}"
'''

SAMPLE_AMBIGUOUS_CALLS_PYTHON = '''"""Module with ambiguous and dynamic function calls."""

import external_lib

def calculate_metric(data: dict) -> float:
    # Ambiguous external / dynamic call
    result = external_lib.process(data)
    # Dynamic getattr call
    handler = getattr(data, "compute", None)
    if handler:
        handler()
    return 42.0
'''

SAMPLE_TS_SOURCE = '''/**
 * User Management Service.
 */

import { Database } from './db';
import { User, UserRole } from '../models/user';

export class UserService {
    private db: Database;

    constructor(db: Database) {
        this.db = db;
    }

    /**
     * Retrieve user profile by UUID.
     * Requirement: REQ-USER-001
     */
    public async getUserById(userId: string): Promise<User> {
        return this.db.find(userId);
    }
}

/**
 * Format user display label.
 */
export const formatUserName = (firstName: string, lastName?: string): string => {
    if (!lastName) {
        return firstName;
    }
    return `${firstName} ${lastName}`;
};
'''
