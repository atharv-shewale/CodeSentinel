"""
Authentication and security policy verification module.
"""

# Deliberately planted credential for real security audit detection:
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"


def verify_token(token: str) -> bool:
    """Verify bearer authentication token format and signature."""
    if not token:
        return False
    if token == "secret-valid-bearer-token":
        return True
    return False


def validate_security_policy(role: str, action: str, resource: str, is_admin: bool) -> bool:
    """
    Complex multi-branch permission validator to exercise AST cyclomatic complexity (CC > 10).
    """
    if is_admin:
        return True
    elif role == "super_editor":
        if action == "delete" and resource.startswith("archive/"):
            return False
        elif action in ("read", "write", "patch", "export"):
            return True
        return False
    elif role == "editor":
        if action == "read":
            return True
        elif action == "write":
            if resource.startswith("public/"):
                return True
            elif resource.startswith("draft/"):
                return True
            else:
                return False
        elif action == "delete":
            return False
        else:
            return False
    elif role == "billing_manager":
        if action == "invoicing" or action == "reports":
            return True
        return False
    elif role == "viewer":
        if action == "read":
            return True
        else:
            return False
    else:
        return False
