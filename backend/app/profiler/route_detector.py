"""
CodeSentinel Profiler: API Route Detector.

Extracts declared HTTP routes from Python (FastAPI/Flask AST decorators)
and JS/TS (Express/Router HTTP verbs) safely without executing or importing any code.
"""

from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, List, Optional
from app.ingestion.file_scanner import ScanResult

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


class DetectedRoute:
    """Discovered API route endpoint."""
    def __init__(
        self,
        method: str,
        path: str,
        file_path: str,
        line_number: int,
        handler_name: Optional[str] = None,
        framework: str = "unknown",
    ):
        self.method = method.upper()
        self.path = path if path.startswith("/") else f"/{path}"
        self.file_path = file_path.replace("\\", "/")
        self.line_number = line_number
        self.handler_name = handler_name
        self.framework = framework

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "handler_name": self.handler_name,
            "framework": self.framework,
        }


class RouteDetector:
    """Detects HTTP API routes across Python and JS/TS codebases."""

    @classmethod
    def detect_all(cls, root_dir: str, scan_result: ScanResult) -> List[Dict[str, Any]]:
        """
        Scan all parsed files to discover declared HTTP routes.
        """
        routes: List[DetectedRoute] = []

        for file in scan_result.files:
            if file.language == "python" and file.size_bytes < 1024 * 1024:
                cls._detect_python_routes(file.absolute_path, file.relative_path, routes)
            elif file.language in ("javascript", "typescript") and file.size_bytes < 1024 * 1024:
                cls._detect_js_routes(file.absolute_path, file.relative_path, routes)

        return [r.to_dict() for r in routes]

    @classmethod
    def _detect_python_routes(
        cls,
        abs_path: str,
        rel_path: str,
        routes: List[DetectedRoute],
    ) -> None:
        """
        Parse Python source into AST and identify FastAPI / Flask route decorators.
        Zero code execution.
        """
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()

            tree = ast.parse(source, filename=rel_path)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        # Case 1: @app.get("/path"), @router.post("/path"), @api_router.put("/path")
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            attr_name = decorator.func.attr.lower()

                            # FastAPI style: @<router>.<method>("/path")
                            if attr_name in HTTP_METHODS and decorator.args:
                                path_arg = decorator.args[0]
                                if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
                                    routes.append(
                                        DetectedRoute(
                                            method=attr_name,
                                            path=path_arg.value,
                                            file_path=rel_path,
                                            line_number=decorator.lineno,
                                            handler_name=node.name,
                                            framework="FastAPI",
                                        )
                                    )

                            # Flask style: @app.route("/path", methods=["GET", "POST"])
                            elif attr_name == "route" and decorator.args:
                                path_arg = decorator.args[0]
                                if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
                                    # Extract methods keyword argument if provided
                                    methods = ["GET"]
                                    for kw in decorator.keywords:
                                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                            extracted_methods = [
                                                elt.value for elt in kw.value.elts
                                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                            ]
                                            if extracted_methods:
                                                methods = extracted_methods

                                    for m in methods:
                                        routes.append(
                                            DetectedRoute(
                                                method=m,
                                                path=path_arg.value,
                                                file_path=rel_path,
                                                line_number=decorator.lineno,
                                                handler_name=node.name,
                                                framework="Flask",
                                            )
                                        )
        except Exception:
            pass

    @classmethod
    def _detect_js_routes(
        cls,
        abs_path: str,
        rel_path: str,
        routes: List[DetectedRoute],
    ) -> None:
        """
        Detect Express / Router HTTP route definitions in JS/TS files.
        e.g. app.get('/users', ...), router.post('/login', ...)
        """
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_idx, line in enumerate(lines, start=1):
                # Pattern: (app|router|server|api)\.(get|post|put|delete|patch|options|head)\s*\(\s*['"`]([^'"`]+)['"`]
                pattern = r"(?:app|router|server|api|route)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"`]([^'\"`]+)['\"`]"
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    method = match.group(1).lower()
                    path = match.group(2)
                    routes.append(
                        DetectedRoute(
                            method=method,
                            path=path,
                            file_path=rel_path,
                            line_number=line_idx,
                            framework="Express",
                        )
                    )
        except Exception:
            pass
