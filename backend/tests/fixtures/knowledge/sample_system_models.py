"""
CodeSentinel Test Fixtures: Sample Software System Models for Knowledge Graph & RAG.

Provides deterministic test fixtures for Project A (Auth & Token Service) and Project B (Payment Service)
with files, classes, functions, requirements, call graph dependencies, test cases, executions, failures,
findings, and commits.
"""

import uuid

PROJECT_A_ID = "aaaaaaaa-1111-2222-3333-444444444444"
PROJECT_B_ID = "bbbbbbbb-5555-6666-7777-888888888888"

SAMPLE_SYSTEM_MODEL_PROJECT_A = {
    "project_id": PROJECT_A_ID,
    "project_name": "AuthSentinel",
    "repository_url": "https://github.com/codesentinel/auth-service.git",
    "default_branch": "main",
    "files": [
        {
            "id": f"{PROJECT_A_ID}-file-auth",
            "path": "app/services/auth_service.py",
            "language": "python",
            "name": "auth_service.py",
        },
        {
            "id": f"{PROJECT_A_ID}-file-token",
            "path": "app/core/token_generator.py",
            "language": "python",
            "name": "token_generator.py",
        },
        {
            "id": f"{PROJECT_A_ID}-file-test-auth",
            "path": "tests/test_auth_service.py",
            "language": "python",
            "name": "test_auth_service.py",
        },
    ],
    "classes": [
        {
            "id": f"{PROJECT_A_ID}-cls-auth",
            "name": "AuthenticationService",
            "qualified_name": "app.services.auth_service.AuthenticationService",
            "file_path": f"{PROJECT_A_ID}-file-auth",
            "docstring": "Handles authentication workflow and JWT token generation.",
            "source_code": "class AuthenticationService:\n    def authenticate_user(self, u, p):\n        pass",
        },
        {
            "id": f"{PROJECT_A_ID}-cls-token",
            "name": "TokenGenerator",
            "qualified_name": "app.core.token_generator.TokenGenerator",
            "file_path": f"{PROJECT_A_ID}-file-token",
            "docstring": "Generates cryptographically secure HMAC/JWT tokens.",
            "source_code": "class TokenGenerator:\n    def generate_access_token(self, u):\n        pass",
        },
    ],
    "functions": [
        {
            "id": f"{PROJECT_A_ID}-fn-auth",
            "name": "authenticate_user",
            "qualified_name": "app.services.auth_service.AuthenticationService.authenticate_user",
            "file_path": f"{PROJECT_A_ID}-file-auth",
            "return_type": "Optional[Dict[str, str]]",
            "complexity_score": 3.0,
            "docstring": "Verify credentials against user database and issue session JWT.",
            "source_code": "def authenticate_user(self, username: str, password_hash: str) -> Optional[Dict[str, str]]:\n    if not username:\n        return None\n    token = self.token_gen.generate_access_token(username)\n    return {'token': token, 'username': username}",
            "location": {"file_path": "app/services/auth_service.py", "start_line": 15, "end_line": 28},
        },
        {
            "id": f"{PROJECT_A_ID}-fn-token",
            "name": "generate_access_token",
            "qualified_name": "app.core.token_generator.TokenGenerator.generate_access_token",
            "file_path": f"{PROJECT_A_ID}-file-token",
            "return_type": "str",
            "complexity_score": 2.0,
            "docstring": "Mint a signed JWT access token for the subject.",
            "source_code": "def generate_access_token(self, username: str) -> str:\n    return f'jwt_token_{username}'",
            "location": {"file_path": "app/core/token_generator.py", "start_line": 10, "end_line": 20},
        },
        {
            "id": f"{PROJECT_A_ID}-fn-verify",
            "name": "verify_session",
            "qualified_name": "app.services.auth_service.AuthenticationService.verify_session",
            "file_path": f"{PROJECT_A_ID}-file-auth",
            "return_type": "bool",
            "complexity_score": 1.5,
            "docstring": "Validate session token expiration and signature.",
            "source_code": "def verify_session(self, token: str) -> bool:\n    return True",
            "location": {"file_path": "app/services/auth_service.py", "start_line": 30, "end_line": 40},
        },
    ],
    "dependencies": [
        {
            "caller": f"{PROJECT_A_ID}-fn-auth",
            "callee": f"{PROJECT_A_ID}-fn-token",
            "type": "CALLS",
        },
        {
            "caller": f"{PROJECT_A_ID}-fn-verify",
            "callee": f"{PROJECT_A_ID}-fn-token",
            "type": "CALLS",
        },
    ],
    "requirements": [
        {
            "id": f"{PROJECT_A_ID}-req-001",
            "identifier": "REQ-AUTH-001",
            "title": "User Authentication via JWT",
            "description": "System shall authenticate username and password and issue a signed session JWT token.",
            "req_type": "FUNCTIONAL",
            "priority": "CRITICAL",
            "status": "IMPLEMENTED",
            "linked_entity_ids": [f"{PROJECT_A_ID}-fn-auth"],
            "acceptance_criteria": [
                "Valid credentials return 200 with JWT access token.",
                "Empty username returns None.",
            ],
        },
        {
            "id": f"{PROJECT_A_ID}-req-002",
            "identifier": "REQ-AUTH-002",
            "title": "Multi-Factor Authentication Check",
            "description": "System shall enforce 2FA verification before issuing permanent credentials (Untested Spec).",
            "req_type": "SECURITY",
            "priority": "HIGH",
            "status": "DRAFT",
            "linked_entity_ids": [f"{PROJECT_A_ID}-fn-verify"],
            "acceptance_criteria": ["2FA code validation must reject expired TOTP."],
        },
    ],
    "test_cases": [
        {
            "id": f"{PROJECT_A_ID}-test-auth-001",
            "name": "test_authenticate_user_success",
            "description": "Verify that authenticate_user returns a valid JWT token when given correct credentials.",
            "provenance": "REQUIREMENT_VERIFIED",
            "test_type": "UNIT",
            "file_path": "tests/test_auth_service.py",
            "requirement_id": f"{PROJECT_A_ID}-req-001",
            "test_code": "def test_authenticate_user_success():\n    auth = AuthenticationService()\n    res = auth.authenticate_user('admin', 'hash')\n    assert res['token'].startswith('jwt_token_')",
        },
    ],
    "executions": [
        {
            "id": f"{PROJECT_A_ID}-exec-001",
            "status": "FAILED",
            "environment": "DOCKER_SANDBOX",
            "total_tests": 5,
            "passed_tests": 4,
            "failed_tests": 1,
            "test_case_id": f"{PROJECT_A_ID}-test-auth-001",
        },
    ],
    "failures": [
        {
            "id": f"{PROJECT_A_ID}-fail-001",
            "execution_id": f"{PROJECT_A_ID}-exec-001",
            "title": "JWT Signature Verification Expired Exception",
            "error_message": "TokenExpiredError: Signature has expired at timestamp 1700000000",
            "category": "ASSERTION_FAILED",
            "severity": "CRITICAL",
            "related_functions": [f"{PROJECT_A_ID}-fn-auth", f"{PROJECT_A_ID}-fn-token"],
        },
    ],
    "findings": [
        {
            "id": f"{PROJECT_A_ID}-find-001",
            "rule_id": "SEC-OWASP-A02-CRYPTOGRAPHIC-FAILURES",
            "title": "Hardcoded secret key in token generator",
            "category": "SECURITY_VULNERABILITY",
            "severity": "HIGH",
            "location": {"file_path": "app/core/token_generator.py", "start_line": 5, "end_line": 5},
            "description": "Hardcoded secret token string found in generator class.",
        }
    ],
    "commits": [
        {
            "id": f"{PROJECT_A_ID}-commit-001",
            "commit_hash": "c0ffee1234567890abcdef1234567890abcdef12",
            "message": "fix(auth): update token signing logic and payload expiration",
            "author": "Alice Dev <alice@example.com>",
            "modified_files": [f"{PROJECT_A_ID}-file-auth", f"{PROJECT_A_ID}-file-token"],
        }
    ],
}


SAMPLE_SYSTEM_MODEL_PROJECT_B = {
    "project_id": PROJECT_B_ID,
    "project_name": "PaymentSentinel",
    "repository_url": "https://github.com/codesentinel/payment-service.git",
    "default_branch": "main",
    "files": [
        {
            "id": f"{PROJECT_B_ID}-file-stripe",
            "path": "app/gateways/stripe_gateway.py",
            "language": "python",
            "name": "stripe_gateway.py",
        },
    ],
    "classes": [
        {
            "id": f"{PROJECT_B_ID}-cls-stripe",
            "name": "StripePaymentGateway",
            "qualified_name": "app.gateways.stripe_gateway.StripePaymentGateway",
            "file_path": f"{PROJECT_B_ID}-file-stripe",
            "docstring": "Handles credit card charging and webhook reconciliations.",
            "source_code": "class StripePaymentGateway:\n    def process_charge(self, amount):\n        pass",
        },
    ],
    "functions": [
        {
            "id": f"{PROJECT_B_ID}-fn-charge",
            "name": "process_charge",
            "qualified_name": "app.gateways.stripe_gateway.StripePaymentGateway.process_charge",
            "file_path": f"{PROJECT_B_ID}-file-stripe",
            "return_type": "Dict[str, Any]",
            "complexity_score": 4.0,
            "docstring": "Charge credit card via Stripe REST API endpoint.",
            "source_code": "def process_charge(self, amount: int, currency: str = 'usd') -> Dict[str, Any]:\n    return {'status': 'succeeded', 'amount': amount}",
            "location": {"file_path": "app/gateways/stripe_gateway.py", "start_line": 10, "end_line": 25},
        },
    ],
    "dependencies": [],
    "requirements": [
        {
            "id": f"{PROJECT_B_ID}-req-pay-001",
            "identifier": "REQ-PAY-001",
            "title": "Credit Card Charge Processing",
            "description": "System shall process PCI-compliant charges via payment gateway.",
            "req_type": "FUNCTIONAL",
            "priority": "CRITICAL",
            "status": "IMPLEMENTED",
            "linked_entity_ids": [f"{PROJECT_B_ID}-fn-charge"],
            "acceptance_criteria": ["Charge returns 200 with receipt ID."],
        },
    ],
    "test_cases": [
        {
            "id": f"{PROJECT_B_ID}-test-charge-001",
            "name": "test_process_charge_success",
            "description": "Verify successful Stripe charge processing.",
            "provenance": "REQUIREMENT_VERIFIED",
            "test_type": "UNIT",
            "file_path": "tests/test_stripe_gateway.py",
            "requirement_id": f"{PROJECT_B_ID}-req-pay-001",
            "test_code": "def test_process_charge_success():\n    pass",
        },
    ],
    "executions": [],
    "failures": [],
    "findings": [],
    "commits": [],
}
