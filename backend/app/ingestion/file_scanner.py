"""
CodeSentinel Ingestion Module: File Tree Scanner & Language Classifier.

Performs deterministic repository directory walking, .gitignore pattern matching,
language detection by extension & content sniffing, LOC calculation, and size limit enforcement.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from app.core.logging import logger

DEFAULT_IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",
    ".gitlab",
    ".vscode",
    ".idea",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "out",
    "bin",
    "obj",
    "vendor",
    ".turbo",
    ".next",
    ".nuxt",
    ".cache",
    "coverage",
    ".tox",
}

DEFAULT_IGNORED_EXTENSIONS: Set[str] = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".mp4", ".mp3", ".wav", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".docx", ".xlsx", ".woff", ".woff2", ".ttf", ".eot",
    ".db", ".sqlite", ".sqlite3", ".class", ".jar", ".war", ".lock",
}

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".dockerfile": "dockerfile",
    "dockerfile": "dockerfile",
}


class ScanLimitExceededError(Exception):
    """Raised when repository exceeds maximum allowed files or size."""
    def __init__(self, message: str, code: str = "SCAN_LIMIT_EXCEEDED"):
        super().__init__(message)
        self.message = message
        self.code = code


class ScannedFile:
    """Represents a scanned source or configuration file."""
    def __init__(
        self,
        relative_path: str,
        absolute_path: str,
        language: str,
        size_bytes: int,
        lines_of_code: int,
    ):
        self.relative_path = relative_path.replace("\\", "/")
        self.absolute_path = absolute_path
        self.language = language
        self.size_bytes = size_bytes
        self.lines_of_code = lines_of_code


class ScanResult:
    """Aggregated result of file tree scanning."""
    def __init__(self):
        self.files: List[ScannedFile] = []
        self.total_files: int = 0
        self.total_lines_of_code: int = 0
        self.total_size_bytes: int = 0
        self.language_breakdown: Dict[str, Dict[str, any]] = {}
        self.primary_language: str = "unknown"


class FileScanner:
    """Scans and analyzes directory trees for source files and language distribution."""

    @staticmethod
    def _parse_gitignore(root_dir: str) -> List[str]:
        """Read .gitignore rules from root directory."""
        gitignore_path = os.path.join(root_dir, ".gitignore")
        patterns: List[str] = []
        if os.path.isfile(gitignore_path):
            try:
                with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
            except Exception as e:
                logger.debug(f"Could not read .gitignore: {e}")
        return patterns

    @staticmethod
    def _is_ignored(rel_path: str, gitignore_patterns: List[str]) -> bool:
        """Check if relative file path matches default or custom ignore patterns."""
        parts = rel_path.replace("\\", "/").split("/")
        for part in parts:
            if part in DEFAULT_IGNORED_DIRS:
                return True

        filename = parts[-1]
        _, ext = os.path.splitext(filename)
        if ext.lower() in DEFAULT_IGNORED_EXTENSIONS:
            return True

        for pattern in gitignore_patterns:
            pattern = pattern.rstrip("/")
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(filename, pattern):
                return True
            if pattern.startswith("/") and fnmatch.fnmatch(f"/{rel_path}", pattern):
                return True
        return False

    @staticmethod
    def detect_language(file_path: str, file_name: str) -> str:
        """
        Classify programming language by extension or shebang content sniffing.
        """
        lower_name = file_name.lower()
        if lower_name == "dockerfile" or lower_name.startswith("dockerfile."):
            return "dockerfile"
        if lower_name in ("jenkinsfile", "vagrantfile", "makefile"):
            return lower_name

        _, ext = os.path.splitext(lower_name)
        if ext in EXTENSION_TO_LANGUAGE:
            return EXTENSION_TO_LANGUAGE[ext]

        # Content sniffing for extensionless scripts or ambiguous files
        if not ext and os.path.isfile(file_path) and os.path.getsize(file_path) < 1024 * 1024:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#!"):
                        if "python" in first_line:
                            return "python"
                        if "node" in first_line or "js" in first_line:
                            return "javascript"
                        if "sh" in first_line or "bash" in first_line or "zsh" in first_line:
                            return "shell"
                        if "ruby" in first_line:
                            return "ruby"
                        if "perl" in first_line:
                            return "perl"
            except Exception:
                pass

        return "other"

    @staticmethod
    def count_loc(file_path: str) -> int:
        """Count non-empty lines of code in file safely."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    @classmethod
    def scan_directory(
        cls,
        root_dir: str,
        max_files: int = 10000,
        max_total_bytes: int = 100 * 1024 * 1024,
    ) -> ScanResult:
        """
        Walk directory tree, filter ignored files, detect languages, and enforce quotas.
        """
        result = ScanResult()
        gitignore_patterns = cls._parse_gitignore(root_dir)
        lang_counts: Dict[str, Dict[str, int]] = {}

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Prune ignored directory branches in-place
            dirnames[:] = [
                d for d in dirnames
                if d not in DEFAULT_IGNORED_DIRS and not any(fnmatch.fnmatch(d, p) for p in gitignore_patterns)
            ]

            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root_dir)

                if cls._is_ignored(rel_path, gitignore_patterns):
                    continue

                try:
                    file_size = os.path.getsize(abs_path)
                except OSError:
                    continue

                result.total_files += 1
                result.total_size_bytes += file_size

                if result.total_files > max_files:
                    raise ScanLimitExceededError(
                        f"Repository exceeded maximum allowed file count ({max_files} files).",
                        code="MAX_FILE_COUNT_EXCEEDED"
                    )

                if result.total_size_bytes > max_total_bytes:
                    raise ScanLimitExceededError(
                        f"Repository exceeded maximum allowed size ({max_total_bytes} bytes).",
                        code="MAX_REPO_SIZE_EXCEEDED"
                    )

                language = cls.detect_language(abs_path, filename)
                loc = cls.count_loc(abs_path)
                result.total_lines_of_code += loc

                scanned = ScannedFile(
                    relative_path=rel_path,
                    absolute_path=abs_path,
                    language=language,
                    size_bytes=file_size,
                    lines_of_code=loc,
                )
                result.files.append(scanned)

                if language != "other":
                    if language not in lang_counts:
                        lang_counts[language] = {"files": 0, "loc": 0, "bytes": 0}
                    lang_counts[language]["files"] += 1
                    lang_counts[language]["loc"] += loc
                    lang_counts[language]["bytes"] += file_size

        # Compute percentages and primary language
        primary_lang = "unknown"
        max_loc = -1

        for lang, stats in lang_counts.items():
            pct = round((stats["loc"] / result.total_lines_of_code * 100), 2) if result.total_lines_of_code > 0 else 0.0
            result.language_breakdown[lang] = {
                "file_count": stats["files"],
                "lines_of_code": stats["loc"],
                "size_bytes": stats["bytes"],
                "percentage": pct,
            }
            if stats["loc"] > max_loc:
                max_loc = stats["loc"]
                primary_lang = lang

        result.primary_language = primary_lang
        return result
