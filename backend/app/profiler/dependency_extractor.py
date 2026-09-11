"""
CodeSentinel Profiler: Dependency Extractor.

Extracts and normalizes production and development dependencies across
Python (requirements.txt, pyproject.toml, Pipfile) and JS/TS (package.json),
including multi-tier monorepo subdirectories.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
try:
    import tomllib  # Python 3.11+ built-in
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11


class DependencyItem:
    """Normalized package dependency record."""
    def __init__(
        self,
        name: str,
        specifier: Optional[str] = None,
        dep_type: str = "production",  # "production" or "development"
        manifest_file: str = "",
    ):
        self.name = name.strip()
        self.specifier = specifier.strip() if specifier else None
        self.dep_type = dep_type
        self.manifest_file = manifest_file.replace("\\", "/")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "specifier": self.specifier,
            "type": self.dep_type,
            "manifest_file": self.manifest_file,
        }


class DependencyExtractor:
    """Parses manifest files to extract declared package dependencies."""

    @classmethod
    def extract_all(cls, root_dir: str) -> Dict[str, Any]:
        """
        Extract dependencies from all discovered manifest files across the repository tree.
        """
        production_deps: List[Dict[str, Any]] = []
        development_deps: List[Dict[str, Any]] = []
        manifests_found: List[str] = []

        # Find all manifest files across directory tree (max depth 4, ignoring common ignore dirs)
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__", "dist", "build")]

            rel_dir = os.path.relpath(dirpath, root_dir)

            for filename in filenames:
                file_rel = os.path.normpath(os.path.join(rel_dir, filename)) if rel_dir != "." else filename
                file_abs = os.path.join(dirpath, filename)

                # requirements*.txt
                if filename.startswith("requirements") and filename.endswith(".txt"):
                    manifests_found.append(file_rel)
                    is_dev = "dev" in filename.lower() or "test" in filename.lower()
                    cls._parse_requirements_file(file_abs, file_rel, is_dev, production_deps, development_deps)

                # pyproject.toml
                elif filename == "pyproject.toml":
                    manifests_found.append(file_rel)
                    cls._parse_pyproject_toml_file(file_abs, file_rel, production_deps, development_deps)

                # Pipfile
                elif filename == "Pipfile":
                    manifests_found.append(file_rel)
                    cls._parse_pipfile_file(file_abs, file_rel, production_deps, development_deps)

                # package.json
                elif filename == "package.json":
                    manifests_found.append(file_rel)
                    cls._parse_package_json_file(file_abs, file_rel, production_deps, development_deps)

        return {
            "production": production_deps,
            "development": development_deps,
            "total_dependencies": len(production_deps) + len(development_deps),
            "manifests": manifests_found,
        }

    @classmethod
    def _parse_requirements_file(
        cls,
        abs_path: str,
        rel_path: str,
        is_dev: bool,
        prod_deps: List[Dict[str, Any]],
        dev_deps: List[Dict[str, Any]],
    ) -> None:
        """Parse a single requirements.txt file."""
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-r") or line.startswith("-i"):
                        continue

                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([<>=!~].*)?$", line)
                    if match:
                        pkg_name = match.group(1)
                        spec = match.group(2)
                        dep = DependencyItem(
                            name=pkg_name,
                            specifier=spec,
                            dep_type="development" if is_dev else "production",
                            manifest_file=rel_path,
                        )
                        if is_dev:
                            dev_deps.append(dep.to_dict())
                        else:
                            prod_deps.append(dep.to_dict())
        except Exception:
            pass

    @classmethod
    def _parse_pyproject_toml_file(
        cls,
        abs_path: str,
        rel_path: str,
        prod_deps: List[Dict[str, Any]],
        dev_deps: List[Dict[str, Any]],
    ) -> None:
        """Parse a single pyproject.toml file."""
        try:
            with open(abs_path, "rb") as f:
                data = tomllib.load(f)

            project_data = data.get("project", {})
            if "dependencies" in project_data and isinstance(project_data["dependencies"], list):
                for dep_str in project_data["dependencies"]:
                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([<>=!~].*)?$", dep_str)
                    if match:
                        prod_deps.append(
                            DependencyItem(
                                name=match.group(1),
                                specifier=match.group(2),
                                dep_type="production",
                                manifest_file=f"{rel_path} (PEP 621)",
                            ).to_dict()
                        )

            opt_deps = project_data.get("optional-dependencies", {})
            for group_name, group_list in opt_deps.items():
                if isinstance(group_list, list):
                    for dep_str in group_list:
                        match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([<>=!~].*)?$", dep_str)
                        if match:
                            dev_deps.append(
                                DependencyItem(
                                    name=match.group(1),
                                    specifier=match.group(2),
                                    dep_type="development",
                                    manifest_file=f"{rel_path} [{group_name}]",
                                ).to_dict()
                            )

            poetry_data = data.get("tool", {}).get("poetry", {})
            if "dependencies" in poetry_data:
                for name, spec in poetry_data["dependencies"].items():
                    if name.lower() != "python":
                        spec_str = spec if isinstance(spec, str) else str(spec.get("version", ""))
                        prod_deps.append(
                            DependencyItem(
                                name=name,
                                specifier=spec_str,
                                dep_type="production",
                                manifest_file=f"{rel_path} (Poetry)",
                            ).to_dict()
                        )

            if "dev-dependencies" in poetry_data:
                for name, spec in poetry_data["dev-dependencies"].items():
                    spec_str = spec if isinstance(spec, str) else str(spec.get("version", ""))
                    dev_deps.append(
                        DependencyItem(
                            name=name,
                            specifier=spec_str,
                            dep_type="development",
                            manifest_file=f"{rel_path} (Poetry dev)",
                        ).to_dict()
                    )
        except Exception:
            pass

    @classmethod
    def _parse_pipfile_file(
        cls,
        abs_path: str,
        rel_path: str,
        prod_deps: List[Dict[str, Any]],
        dev_deps: List[Dict[str, Any]],
    ) -> None:
        """Parse a Pipfile."""
        try:
            with open(abs_path, "rb") as f:
                data = tomllib.load(f)

            for name, spec in data.get("packages", {}).items():
                spec_str = spec if isinstance(spec, str) else str(spec)
                prod_deps.append(
                    DependencyItem(
                        name=name,
                        specifier=spec_str,
                        dep_type="production",
                        manifest_file=rel_path,
                    ).to_dict()
                )

            for name, spec in data.get("dev-packages", {}).items():
                spec_str = spec if isinstance(spec, str) else str(spec)
                dev_deps.append(
                    DependencyItem(
                        name=name,
                        specifier=spec_str,
                        dep_type="development",
                        manifest_file=f"{rel_path} (dev)",
                    ).to_dict()
                )
        except Exception:
            pass

    @classmethod
    def _parse_package_json_file(
        cls,
        abs_path: str,
        rel_path: str,
        prod_deps: List[Dict[str, Any]],
        dev_deps: List[Dict[str, Any]],
    ) -> None:
        """Parse a package.json file."""
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            for name, ver in data.get("dependencies", {}).items():
                prod_deps.append(
                    DependencyItem(
                        name=name,
                        specifier=str(ver),
                        dep_type="production",
                        manifest_file=rel_path,
                    ).to_dict()
                )

            for name, ver in data.get("devDependencies", {}).items():
                dev_deps.append(
                    DependencyItem(
                        name=name,
                        specifier=str(ver),
                        dep_type="development",
                        manifest_file=f"{rel_path} (devDependencies)",
                    ).to_dict()
                )
        except Exception:
            pass
