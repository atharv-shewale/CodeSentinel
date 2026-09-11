"""
CodeSentinel Profiler: Framework Detector.

Identifies software frameworks (FastAPI, Flask, Django, Express, Next.js, React, NestJS, etc.)
from package manifests and source code AST/imports across the repository tree.
"""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, Optional
from app.ingestion.file_scanner import ScanResult

PYTHON_FRAMEWORKS = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "tornado": "Tornado",
    "aiohttp": "AioHTTP",
    "starlette": "Starlette",
    "pyramid": "Pyramid",
    "sanic": "Sanic",
}

JS_FRAMEWORKS = {
    "express": "Express",
    "next": "Next.js",
    "react": "React",
    "vue": "Vue.js",
    "@nestjs/core": "NestJS",
    "svelte": "Svelte",
    "fastify": "Fastify",
    "@angular/core": "Angular",
    "koa": "Koa",
    "hono": "Hono",
}


class FrameworkInfo:
    """Detected framework metadata item."""
    def __init__(
        self,
        name: str,
        category: str,
        confidence_basis: str,
        version: Optional[str] = None,
    ):
        self.name = name
        self.category = category  # "backend_web", "frontend_ui", "fullstack"
        self.confidence_basis = confidence_basis
        self.version = version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "confidence_basis": self.confidence_basis,
            "version": self.version,
        }


class FrameworkDetector:
    """Detects backend and frontend frameworks across multiple ecosystems."""

    @classmethod
    def detect(cls, root_dir: str, scan_result: ScanResult) -> List[Dict[str, Any]]:
        """
        Scan repository manifests and source code files to discover frameworks.
        """
        detected: Dict[str, FrameworkInfo] = {}

        # 1. Walk tree to inspect all Python and JS Manifests
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__", "dist", "build")]
            rel_dir = os.path.relpath(dirpath, root_dir)

            for filename in filenames:
                file_rel = os.path.normpath(os.path.join(rel_dir, filename)) if rel_dir != "." else filename
                file_abs = os.path.join(dirpath, filename)

                if filename.startswith("requirements") and filename.endswith(".txt"):
                    cls._check_requirements_file(file_abs, file_rel, detected)
                elif filename == "pyproject.toml":
                    cls._check_pyproject_toml(file_abs, file_rel, detected)
                elif filename == "Pipfile":
                    cls._check_pipfile(file_abs, file_rel, detected)
                elif filename == "package.json":
                    cls._check_package_json(file_abs, file_rel, detected)

        # 2. Inspect Source Code Imports (AST / regex)
        cls._detect_source_imports(root_dir, scan_result, detected)

        return [fw.to_dict() for fw in detected.values()]

    @classmethod
    def _check_requirements_file(cls, abs_path: str, rel_path: str, detected: Dict[str, FrameworkInfo]) -> None:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    clean_line = line.strip().lower()
                    if clean_line and not clean_line.startswith("#"):
                        for key, name in PYTHON_FRAMEWORKS.items():
                            if re.match(rf"^{re.escape(key)}([<>=!~].*)?$", clean_line):
                                ver_match = re.search(r"([<>=!~]+.*)", clean_line)
                                version = ver_match.group(1).strip() if ver_match else None
                                detected[name] = FrameworkInfo(
                                    name=name,
                                    category="backend_web",
                                    confidence_basis=f"found in {rel_path}",
                                    version=version,
                                )
        except Exception:
            pass

    @classmethod
    def _check_pyproject_toml(cls, abs_path: str, rel_path: str, detected: Dict[str, FrameworkInfo]) -> None:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                for key, name in PYTHON_FRAMEWORKS.items():
                    if f'"{key}"' in content or f"'{key}'" in content or f"{key} =" in content or f"{key}>=" in content:
                        detected[name] = FrameworkInfo(
                            name=name,
                            category="backend_web",
                            confidence_basis=f"found in {rel_path}",
                        )
        except Exception:
            pass

    @classmethod
    def _check_pipfile(cls, abs_path: str, rel_path: str, detected: Dict[str, FrameworkInfo]) -> None:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                for key, name in PYTHON_FRAMEWORKS.items():
                    if key in content:
                        detected[name] = FrameworkInfo(
                            name=name,
                            category="backend_web",
                            confidence_basis=f"found in {rel_path}",
                        )
        except Exception:
            pass

    @classmethod
    def _check_package_json(cls, abs_path: str, rel_path: str, detected: Dict[str, FrameworkInfo]) -> None:
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))

                for key, name in JS_FRAMEWORKS.items():
                    if key in deps:
                        category = "frontend_ui" if name in ("React", "Vue.js", "Svelte", "Angular") else "backend_web"
                        if name == "Next.js":
                            category = "fullstack"
                        detected[name] = FrameworkInfo(
                            name=name,
                            category=category,
                            confidence_basis=f"found in {rel_path}",
                            version=str(deps[key]),
                        )
        except Exception:
            pass

    @classmethod
    def _detect_source_imports(
        cls,
        root_dir: str,
        scan_result: ScanResult,
        detected: Dict[str, FrameworkInfo],
    ) -> None:
        """Inspect source code files to infer frameworks from import statements."""
        for file in scan_result.files:
            if file.language == "python" and file.size_bytes < 500 * 1024:
                try:
                    with open(file.absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=file.relative_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                for key, name in PYTHON_FRAMEWORKS.items():
                                    if alias.name == key or alias.name.startswith(f"{key}."):
                                        if name not in detected:
                                            detected[name] = FrameworkInfo(
                                                name=name,
                                                category="backend_web",
                                                confidence_basis=f"inferred from imports in {file.relative_path}",
                                            )
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                for key, name in PYTHON_FRAMEWORKS.items():
                                    if node.module == key or node.module.startswith(f"{key}."):
                                        if name not in detected:
                                            detected[name] = FrameworkInfo(
                                                name=name,
                                                category="backend_web",
                                                confidence_basis=f"inferred from imports in {file.relative_path}",
                                            )
                except Exception:
                    pass

            elif file.language in ("javascript", "typescript") and file.size_bytes < 500 * 1024:
                try:
                    with open(file.absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for key, name in JS_FRAMEWORKS.items():
                        pattern = rf"(from\s+['\"]{re.escape(key)}['\"]|require\(\s*['\"]{re.escape(key)}['\"]\s*\))"
                        if re.search(pattern, content):
                            if name not in detected:
                                category = "frontend_ui" if name in ("React", "Vue.js", "Svelte", "Angular") else "backend_web"
                                if name == "Next.js":
                                    category = "fullstack"
                                detected[name] = FrameworkInfo(
                                    name=name,
                                    category=category,
                                    confidence_basis=f"inferred from imports in {file.relative_path}",
                                )
                except Exception:
                    pass
