"""
Sample Microservice Main Application.
"""

from fastapi import FastAPI, Header, HTTPException
from app.auth import verify_token
from app.calculator import add

app = FastAPI(title="Sample Microservice")


@app.get("/")
def read_root():
    return {"status": "ok", "service": "sample-microservice"}


@app.post("/login")
def login(payload: dict):
    if payload.get("username") == "admin" and payload.get("password") == "secret":
        return {"token": "secret-valid-bearer-token"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/items")
def list_items(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"items": ["item-alpha", "item-beta"], "count": add(1, 1)}


@app.get("/api/admin/users")
def get_admin_users():
    """
    Planted defect: Sensitive admin route under /api/ with zero authentication check.
    Should be flagged by SEC-ROUTE-MISSING-AUTH.
    """
    return {"users": ["root", "admin", "system"]}

