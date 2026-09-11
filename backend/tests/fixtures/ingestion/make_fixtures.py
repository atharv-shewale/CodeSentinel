"""
CodeSentinel Test Fixtures Builder: Ingestion & Profiler.

Generates realistic repository structures and test ZIP archives (including security test cases).
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile


def create_python_fastapi_repo(target_dir: str) -> str:
    """Create a sample Python + FastAPI repository."""
    os.makedirs(os.path.join(target_dir, "app"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "tests"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, ".github", "workflows"), exist_ok=True)

    # requirements.txt
    with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("fastapi>=0.111.0\nuvicorn==0.30.0\npydantic>=2.7.0\npytest>=8.0.0\n")

    # pyproject.toml
    with open(os.path.join(target_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(
            '[project]\nname = "fastapi-sample"\nversion = "0.1.0"\n'
            'dependencies = [\n    "fastapi>=0.111.0",\n    "uvicorn>=0.30.0"\n]\n\n'
            '[project.optional-dependencies]\ndev = ["pytest>=8.0.0"]\n'
        )

    # app/main.py with FastAPI routes
    with open(os.path.join(target_dir, "app", "main.py"), "w", encoding="utf-8") as f:
        f.write(
            "from fastapi import FastAPI, APIRouter\n\n"
            "app = FastAPI()\n"
            "router = APIRouter()\n\n"
            "@app.get('/health')\n"
            "def health_check():\n"
            "    return {'status': 'healthy'}\n\n"
            "@router.post('/items')\n"
            "async def create_item(item: dict):\n"
            "    return item\n\n"
            "@app.delete('/items/{item_id}')\n"
            "def delete_item(item_id: int):\n"
            "    return {'deleted': item_id}\n\n"
            "app.include_router(router)\n"
        )

    # tests/test_main.py
    with open(os.path.join(target_dir, "tests", "test_main.py"), "w", encoding="utf-8") as f:
        f.write(
            "import pytest\n"
            "from app.main import app\n\n"
            "def test_health():\n"
            "    assert True\n"
        )

    # Dockerfile
    with open(os.path.join(target_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write("FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nCMD ['uvicorn', 'app.main:app']\n")

    # .github/workflows/ci.yml
    with open(os.path.join(target_dir, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
        f.write("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n")

    # .gitignore
    with open(os.path.join(target_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("__pycache__/\n*.pyc\n.venv/\n")

    return target_dir


def create_node_express_repo(target_dir: str) -> str:
    """Create a sample Node.js + Express repository."""
    os.makedirs(os.path.join(target_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "__tests__"), exist_ok=True)

    # package.json
    with open(os.path.join(target_dir, "package.json"), "w", encoding="utf-8") as f:
        f.write(
            '{\n  "name": "express-sample",\n  "version": "1.0.0",\n'
            '  "dependencies": {\n    "express": "^4.19.2",\n    "cors": "^2.8.5"\n  },\n'
            '  "devDependencies": {\n    "jest": "^29.7.0",\n    "supertest": "^6.3.4"\n  }\n}\n'
        )

    # src/server.js
    with open(os.path.join(target_dir, "src", "server.js"), "w", encoding="utf-8") as f:
        f.write(
            "const express = require('express');\n"
            "const app = express();\n\n"
            "app.get('/api/users', (req, res) => {\n"
            "    res.json([{ id: 1, name: 'Alice' }]);\n"
            "});\n\n"
            "app.post('/api/users', (req, res) => {\n"
            "    res.status(201).json({ success: true });\n"
            "});\n"
        )

    # __tests__/server.test.js
    with open(os.path.join(target_dir, "__tests__", "server.test.js"), "w", encoding="utf-8") as f:
        f.write(
            "describe('User API', () => {\n"
            "    it('should fetch users', () => {\n"
            "        expect(true).toBe(true);\n"
            "    });\n"
            "});\n"
        )

    # Dockerfile
    with open(os.path.join(target_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write("FROM node:20-alpine\nWORKDIR /app\nCOPY . .\nCMD ['node', 'src/server.js']\n")

    return target_dir


def create_mixed_repo(target_dir: str) -> str:
    """Create a monorepo with Python backend and React frontend."""
    backend_dir = os.path.join(target_dir, "backend")
    frontend_dir = os.path.join(target_dir, "frontend")
    os.makedirs(backend_dir, exist_ok=True)
    os.makedirs(frontend_dir, exist_ok=True)

    # Backend
    create_python_fastapi_repo(backend_dir)

    # Frontend
    with open(os.path.join(frontend_dir, "package.json"), "w", encoding="utf-8") as f:
        f.write(
            '{\n  "name": "frontend-ui",\n  "dependencies": {\n    "react": "^18.3.1",\n    "react-dom": "^18.3.1"\n  }\n}\n'
        )
    with open(os.path.join(frontend_dir, "App.tsx"), "w", encoding="utf-8") as f:
        f.write("import React from 'react';\nexport function App() { return <div>Hello</div>; }\n")

    # Root docker-compose.yml
    with open(os.path.join(target_dir, "docker-compose.yml"), "w", encoding="utf-8") as f:
        f.write("version: '3.8'\nservices:\n  backend:\n    build: ./backend\n  frontend:\n    build: ./frontend\n")

    return target_dir


def create_empty_repo(target_dir: str) -> str:
    """Create a repository with no recognizable code or frameworks."""
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Plain Documentation Repo\nNo code here, only docs.\n")
    with open(os.path.join(target_dir, "NOTES.txt"), "w", encoding="utf-8") as f:
        f.write("Just some notes.\n")
    return target_dir


def create_zip_from_dir(dir_path: str) -> bytes:
    """Create in-memory ZIP bytes from a directory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for file in files:
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, dir_path)
                zf.write(abs_f, rel_f)
    return buf.getvalue()


def create_malicious_zip_slip() -> bytes:
    """Create a malicious ZIP containing a path-traversal entry ('../evil.sh')."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("safe.txt", "This is safe.")
        # Inject malicious entry
        zf.writestr("../evil.sh", "#!/bin/sh\necho pwned > /tmp/pwned")
    return buf.getvalue()


def create_malicious_absolute_path_zip() -> bytes:
    """Create a malicious ZIP containing an absolute path entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("/etc/passwd", "root:x:0:0:root:/root:/bin/bash")
    return buf.getvalue()


def create_oversized_zip(file_count: int = 10, file_size_bytes: int = 1000) -> bytes:
    """Create a ZIP with custom file count/size."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(file_count):
            zf.writestr(f"file_{i}.dat", "A" * file_size_bytes)
    return buf.getvalue()
