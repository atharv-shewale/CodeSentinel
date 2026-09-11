"""
CodeSentinel Analyzer: Python AST Code Entity Extractor.

Extracts deep structural code entities (classes, methods, functions, parameters,
type annotations, docstrings, internal calls, and complexity metrics) using Python's built-in `ast`.
All extracted entities are strictly validated as `CodeEntity` Pydantic models.
"""

from __future__ import annotations

import ast
import hashlib
import os
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
from shared.schemas.code_entity import (
    CodeEntity,
    CodeLocation,
    CodeParameter,
    EntityType,
    Visibility,
)
from shared.schemas.common import utc_now


def _get_visibility(name: str) -> Visibility:
    """Determine entity visibility based on Python naming conventions."""
    if name.startswith("__") and not name.endswith("__"):
        return Visibility.PRIVATE
    elif name.startswith("_") and not name.endswith("__"):
        return Visibility.PROTECTED
    return Visibility.PUBLIC


def _format_type_annotation(annotation: Optional[ast.AST]) -> Optional[str]:
    """Convert AST type annotation node to human-readable string."""
    if annotation is None:
        return None
    try:
        return ast.unparse(annotation)
    except Exception:
        return None


def _format_default_value(default_node: Optional[ast.AST]) -> Optional[str]:
    """Convert AST default argument node to string."""
    if default_node is None:
        return None
    try:
        return ast.unparse(default_node)
    except Exception:
        return None


def _calculate_complexity(node: ast.AST) -> float:
    """Calculate cyclomatic complexity of an AST node."""
    complexity = 1.0
    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.While,
                ast.AsyncFor,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
                ast.Assert,
            ),
        ):
            complexity += 1.0
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


class PythonCodeAnalyzer:
    """Extracts CodeEntity objects from Python source files via AST parsing."""

    @classmethod
    def analyze_file(
        cls,
        file_path: str,
        source_code: str,
        project_id: uuid.UUID,
        module_prefix: str = "",
    ) -> List[CodeEntity]:
        """
        Analyze a single Python source file and return a list of validated CodeEntity records.
        """
        entities: List[CodeEntity] = []
        rel_path = file_path.replace("\\", "/")
        file_id = uuid.uuid4()
        now = utc_now()

        # Compute file AST hash
        ast_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()

        try:
            tree = ast.parse(source_code, filename=rel_path)
        except SyntaxError:
            # If there's a syntax error, still produce a top-level FILE entity
            lines = source_code.splitlines()
            file_entity = CodeEntity(
                id=file_id,
                project_id=project_id,
                name=os.path.basename(rel_path),
                qualified_name=rel_path,
                entity_type=EntityType.FILE,
                language="python",
                location=CodeLocation(
                    file_path=rel_path,
                    start_line=1,
                    end_line=max(1, len(lines)),
                ),
                created_at=now,
                updated_at=now,
                metadata={"parse_error": "SyntaxError"},
                ast_hash=ast_hash,
            )
            return [file_entity]

        lines = source_code.splitlines()
        file_docstring = ast.get_docstring(tree)

        # 1. Extract File-Level Imports
        imports: List[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)

        # 2. Build map of all declared top-level and class-level functions in this file for static call resolution
        declared_callables: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                declared_callables.add(node.name)

        # 3. Create Root FILE Entity
        file_entity = CodeEntity(
            id=file_id,
            project_id=project_id,
            name=os.path.basename(rel_path),
            qualified_name=rel_path,
            entity_type=EntityType.FILE,
            language="python",
            location=CodeLocation(
                file_path=rel_path,
                start_line=1,
                end_line=max(1, len(lines)),
            ),
            docstring=file_docstring,
            dependencies=imports,
            created_at=now,
            updated_at=now,
            ast_hash=ast_hash,
            metadata={"total_lines": len(lines), "imports": imports},
        )
        entities.append(file_entity)

        # 4. Traverse Classes and Functions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls._extract_class(
                    node=node,
                    file_path=rel_path,
                    lines=lines,
                    project_id=project_id,
                    parent_id=file_id,
                    module_prefix=module_prefix,
                    declared_callables=declared_callables,
                    entities=entities,
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls._extract_function(
                    node=node,
                    file_path=rel_path,
                    lines=lines,
                    project_id=project_id,
                    parent_id=file_id,
                    module_prefix=module_prefix,
                    declared_callables=declared_callables,
                    entities=entities,
                    is_method=False,
                )

        return entities

    @classmethod
    def _extract_class(
        cls,
        node: ast.ClassDef,
        file_path: str,
        lines: List[str],
        project_id: uuid.UUID,
        parent_id: uuid.UUID,
        module_prefix: str,
        declared_callables: Set[str],
        entities: List[CodeEntity],
    ) -> None:
        """Extract Class CodeEntity and recursively its methods."""
        class_id = uuid.uuid4()
        now = utc_now()
        qname = f"{module_prefix}.{node.name}" if module_prefix else node.name

        base_classes: List[str] = []
        for base in node.bases:
            try:
                base_classes.append(ast.unparse(base))
            except Exception:
                pass

        docstring = ast.get_docstring(node)
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        source_snippet = "\n".join(lines[start_line - 1 : end_line]) if lines else None

        class_entity = CodeEntity(
            id=class_id,
            project_id=project_id,
            name=node.name,
            qualified_name=qname,
            entity_type=EntityType.CLASS,
            language="python",
            location=CodeLocation(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_column=node.col_offset,
            ),
            parent_entity_id=parent_id,
            docstring=docstring,
            source_code=source_snippet,
            visibility=_get_visibility(node.name),
            complexity_score=_calculate_complexity(node),
            created_at=now,
            updated_at=now,
            metadata={"base_classes": base_classes},
        )
        entities.append(class_entity)

        # Extract Methods in Class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls._extract_function(
                    node=item,
                    file_path=file_path,
                    lines=lines,
                    project_id=project_id,
                    parent_id=class_id,
                    module_prefix=qname,
                    declared_callables=declared_callables,
                    entities=entities,
                    is_method=True,
                )

    @classmethod
    def _extract_function(
        cls,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        lines: List[str],
        project_id: uuid.UUID,
        parent_id: uuid.UUID,
        module_prefix: str,
        declared_callables: Set[str],
        entities: List[CodeEntity],
        is_method: bool = False,
    ) -> None:
        """Extract Function or Method CodeEntity with parameters, calls, and unresolved bindings."""
        func_id = uuid.uuid4()
        now = utc_now()
        qname = f"{module_prefix}.{node.name}" if module_prefix else node.name
        entity_type = EntityType.METHOD if is_method else EntityType.FUNCTION

        # 1. Parameters
        parameters: List[CodeParameter] = []
        args = node.args

        # Calculate defaults offset
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        defaults_start = num_args - num_defaults

        for idx, arg in enumerate(args.args):
            if is_method and idx == 0 and arg.arg in ("self", "cls"):
                continue  # Skip self / cls in signature parameters

            default_val = None
            if idx >= defaults_start:
                default_val = _format_default_value(args.defaults[idx - defaults_start])

            type_hint = _format_type_annotation(arg.annotation)
            parameters.append(
                CodeParameter(
                    name=arg.arg,
                    type_annotation=type_hint,
                    default_value=default_val,
                    is_required=(default_val is None),
                )
            )

        # 2. Return Type
        return_type = _format_type_annotation(node.returns)

        # 3. Direct Function Calls within file & Unresolved Ambiguous Calls
        calls_resolved: List[str] = []
        calls_unresolved: List[str] = []

        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call):
                if isinstance(subnode.func, ast.Name):
                    target_name = subnode.func.id
                    if target_name in declared_callables:
                        calls_resolved.append(target_name)
                    else:
                        calls_unresolved.append(f"{target_name} (unresolved)")
                elif isinstance(subnode.func, ast.Attribute):
                    attr_name = subnode.func.attr
                    # Mark dynamic / object method calls as unresolved rather than guessing
                    calls_unresolved.append(f"{attr_name} (unresolved)")

        # 4. Decorators
        decorators: List[str] = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                pass

        docstring = ast.get_docstring(node)
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        source_snippet = "\n".join(lines[start_line - 1 : end_line]) if lines else None

        # Build CodeEntity
        func_entity = CodeEntity(
            id=func_id,
            project_id=project_id,
            name=node.name,
            qualified_name=qname,
            entity_type=entity_type,
            language="python",
            location=CodeLocation(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                start_column=node.col_offset,
            ),
            parent_entity_id=parent_id,
            docstring=docstring,
            source_code=source_snippet,
            parameters=parameters,
            return_type=return_type,
            visibility=_get_visibility(node.name),
            complexity_score=_calculate_complexity(node),
            dependencies=sorted(list(set(calls_resolved))),
            created_at=now,
            updated_at=now,
            metadata={
                "decorators": decorators,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "resolved_calls": sorted(list(set(calls_resolved))),
                "unresolved_calls": sorted(list(set(calls_unresolved))),
            },
        )
        entities.append(func_entity)
