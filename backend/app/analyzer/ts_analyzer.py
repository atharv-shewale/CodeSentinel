"""
CodeSentinel Analyzer: JavaScript / TypeScript Code Entity Extractor.

Extracts classes, interfaces, methods, functions, arrow functions, parameters,
imports, and internal call structures for JS/TS codebases.
All extracted entities are strictly validated as `CodeEntity` Pydantic models.
"""

from __future__ import annotations

import hashlib
import os
import re
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


def _get_ts_visibility(line: str) -> Visibility:
    """Determine visibility modifier from TypeScript keyword."""
    if "private " in line:
        return Visibility.PRIVATE
    elif "protected " in line:
        return Visibility.PROTECTED
    return Visibility.PUBLIC


class TypeScriptCodeAnalyzer:
    """Extracts CodeEntity objects from JS/TS source files."""

    @classmethod
    def analyze_file(
        cls,
        file_path: str,
        source_code: str,
        project_id: uuid.UUID,
        module_prefix: str = "",
    ) -> List[CodeEntity]:
        """
        Analyze a JS/TS source file and return validated CodeEntity objects.
        """
        entities: List[CodeEntity] = []
        rel_path = file_path.replace("\\", "/")
        file_id = uuid.uuid4()
        now = utc_now()
        is_ts = rel_path.endswith((".ts", ".tsx"))
        language = "typescript" if is_ts else "javascript"

        lines = source_code.splitlines()
        ast_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()

        # 1. Extract Imports
        imports: List[str] = []
        import_pattern = r"(?:import\s+(?:(?:[\w*\s{},]+)\s+from\s+)?['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))"
        for match in re.finditer(import_pattern, source_code):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.append(imp)

        # 2. Extract Top-Level Declarations for static call matching
        declared_callables: Set[str] = set()
        for m in re.finditer(r"\bfunction\s+([a-zA-Z0-9_$]+)\s*\(", source_code):
            declared_callables.add(m.group(1))
        for m in re.finditer(r"(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", source_code):
            declared_callables.add(m.group(1))

        # 3. Create Root FILE Entity
        file_entity = CodeEntity(
            id=file_id,
            project_id=project_id,
            name=os.path.basename(rel_path),
            qualified_name=rel_path,
            entity_type=EntityType.FILE,
            language=language,
            location=CodeLocation(
                file_path=rel_path,
                start_line=1,
                end_line=max(1, len(lines)),
            ),
            dependencies=imports,
            created_at=now,
            updated_at=now,
            ast_hash=ast_hash,
            metadata={"total_lines": len(lines), "imports": imports},
        )
        entities.append(file_entity)

        # 4. Extract Classes & Interfaces + their Methods (using brace depth tracking)
        class_pattern = r"(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$.]+))?(?:\s+implements\s+([a-zA-Z0-9_$,\s]+))?"
        in_class = False
        class_brace_depth = 0
        current_class_id: Optional[uuid.UUID] = None
        current_class_name = ""

        for line_idx, line in enumerate(lines, start=1):
            class_match = re.search(class_pattern, line)
            if class_match and not in_class:
                class_name = class_match.group(1)
                extends_name = class_match.group(2)
                class_id = uuid.uuid4()
                qname = f"{module_prefix}.{class_name}" if module_prefix else class_name
                docstring = cls._extract_preceding_jsdoc(lines, line_idx - 1)

                class_entity = CodeEntity(
                    id=class_id,
                    project_id=project_id,
                    name=class_name,
                    qualified_name=qname,
                    entity_type=EntityType.CLASS,
                    language=language,
                    location=CodeLocation(
                        file_path=rel_path,
                        start_line=line_idx,
                        end_line=min(line_idx + 20, max(1, len(lines))),
                    ),
                    parent_entity_id=file_id,
                    docstring=docstring,
                    visibility=_get_ts_visibility(line),
                    created_at=now,
                    updated_at=now,
                    metadata={"extends": extends_name},
                )
                entities.append(class_entity)
                in_class = True
                current_class_id = class_id
                current_class_name = class_name
                class_brace_depth = line.count("{") - line.count("}")
                continue

            if in_class and current_class_id:
                class_brace_depth += line.count("{") - line.count("}")
                if class_brace_depth <= 0:
                    in_class = False
                    current_class_id = None
                    continue

                # Check for Class Method: (public/private/protected/async) methodName(params): returnType {
                method_pattern = r"^\s*(?:public\s+|private\s+|protected\s+)?(?:async\s+)?(?:static\s+)?([a-zA-Z0-9_$]+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*\{?"
                method_match = re.search(method_pattern, line)
                if method_match:
                    m_name = method_match.group(1)
                    if m_name not in ("constructor", "if", "for", "while", "switch", "catch"):
                        m_params = method_match.group(2)
                        m_return = method_match.group(3)
                        m_docstring = cls._extract_preceding_jsdoc(lines, line_idx - 1)
                        m_id = uuid.uuid4()
                        m_qname = f"{current_class_name}.{m_name}"

                        calls_res, calls_unres = cls._find_calls(source_code, declared_callables)

                        method_entity = CodeEntity(
                            id=m_id,
                            project_id=project_id,
                            name=m_name,
                            qualified_name=m_qname,
                            entity_type=EntityType.METHOD,
                            language=language,
                            location=CodeLocation(
                                file_path=rel_path,
                                start_line=line_idx,
                                end_line=min(line_idx + 10, max(1, len(lines))),
                            ),
                            parent_entity_id=current_class_id,
                            docstring=m_docstring,
                            parameters=cls._parse_params(m_params),
                            return_type=m_return.strip() if m_return else None,
                            visibility=_get_ts_visibility(line),
                            dependencies=calls_res,
                            created_at=now,
                            updated_at=now,
                            metadata={"resolved_calls": calls_res, "unresolved_calls": calls_unres},
                        )
                        entities.append(method_entity)

            # 5. Extract Standalone Named Functions
            if not in_class:
                func_pattern = r"(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?"
                func_match = re.search(func_pattern, line)
                if func_match:
                    func_name = func_match.group(1)
                    raw_params = func_match.group(2)
                    raw_return = func_match.group(3)

                    func_id = uuid.uuid4()
                    qname = f"{module_prefix}.{func_name}" if module_prefix else func_name
                    docstring = cls._extract_preceding_jsdoc(lines, line_idx - 1)
                    parameters = cls._parse_params(raw_params)
                    calls_resolved, calls_unresolved = cls._find_calls(source_code, declared_callables)

                    func_entity = CodeEntity(
                        id=func_id,
                        project_id=project_id,
                        name=func_name,
                        qualified_name=qname,
                        entity_type=EntityType.FUNCTION,
                        language=language,
                        location=CodeLocation(
                            file_path=rel_path,
                            start_line=line_idx,
                            end_line=min(line_idx + 15, max(1, len(lines))),
                        ),
                        parent_entity_id=file_id,
                        docstring=docstring,
                        parameters=parameters,
                        return_type=raw_return.strip() if raw_return else None,
                        visibility=Visibility.PUBLIC if "export" in line else Visibility.INTERNAL,
                        dependencies=calls_resolved,
                        created_at=now,
                        updated_at=now,
                        metadata={
                            "is_async": "async" in line,
                            "resolved_calls": calls_resolved,
                            "unresolved_calls": calls_unresolved,
                        },
                    )
                    entities.append(func_entity)

                # 6. Extract Arrow Functions bound to const/let
                arrow_pattern = r"(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)(?:\s*:\s*([^=]+))?\s*=>"
                arrow_match = re.search(arrow_pattern, line)
                if arrow_match:
                    arrow_name = arrow_match.group(1)
                    raw_params = arrow_match.group(2)
                    raw_return = arrow_match.group(3)

                    arrow_id = uuid.uuid4()
                    qname = f"{module_prefix}.{arrow_name}" if module_prefix else arrow_name
                    docstring = cls._extract_preceding_jsdoc(lines, line_idx - 1)
                    parameters = cls._parse_params(raw_params)
                    calls_resolved, calls_unresolved = cls._find_calls(source_code, declared_callables)

                    arrow_entity = CodeEntity(
                        id=arrow_id,
                        project_id=project_id,
                        name=arrow_name,
                        qualified_name=qname,
                        entity_type=EntityType.FUNCTION,
                        language=language,
                        location=CodeLocation(
                            file_path=rel_path,
                            start_line=line_idx,
                            end_line=min(line_idx + 15, max(1, len(lines))),
                        ),
                        parent_entity_id=file_id,
                        docstring=docstring,
                        parameters=parameters,
                        return_type=raw_return.strip() if raw_return else None,
                        visibility=Visibility.PUBLIC if "export" in line else Visibility.INTERNAL,
                        dependencies=calls_resolved,
                        created_at=now,
                        updated_at=now,
                        metadata={
                            "is_async": "async" in line,
                            "is_arrow": True,
                            "resolved_calls": calls_resolved,
                            "unresolved_calls": calls_unresolved,
                        },
                    )
                    entities.append(arrow_entity)

        return entities

    @classmethod
    def _parse_params(cls, raw_params: str) -> List[CodeParameter]:
        """Parse raw parameter string into CodeParameter list."""
        parameters: List[CodeParameter] = []
        if not raw_params.strip():
            return parameters

        parts = raw_params.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue

            param_name = part
            type_hint = None
            default_val = None

            if "=" in part:
                p_left, p_right = part.split("=", 1)
                param_name = p_left.strip()
                default_val = p_right.strip()

            if ":" in param_name:
                p_id, p_type = param_name.split(":", 1)
                param_name = p_id.strip()
                type_hint = p_type.strip()

            is_opt = param_name.endswith("?")
            if is_opt:
                param_name = param_name[:-1].strip()

            parameters.append(
                CodeParameter(
                    name=param_name,
                    type_annotation=type_hint,
                    default_value=default_val,
                    is_required=(not is_opt and default_val is None),
                )
            )

        return parameters

    @classmethod
    def _extract_preceding_jsdoc(cls, lines: List[str], end_line_idx: int) -> Optional[str]:
        """Extract preceding JSDoc comment block (/** ... */) if present."""
        if end_line_idx < 1 or end_line_idx > len(lines):
            return None

        idx = end_line_idx - 1
        if idx >= 0 and "*/" in lines[idx]:
            comment_lines = []
            while idx >= 0:
                line = lines[idx].strip()
                comment_lines.insert(0, line)
                if "/**" in line or "/*" in line:
                    break
                idx -= 1
            if comment_lines:
                clean = "\n".join(comment_lines)
                clean = re.sub(r"^/\*\*|\*/$|^\s*\*\s?", "", clean, flags=re.MULTILINE).strip()
                return clean
        return None

    @classmethod
    def _find_calls(cls, source_code: str, declared_callables: Set[str]) -> Tuple[List[str], List[str]]:
        """Identify resolved and unresolved function calls."""
        resolved: List[str] = []
        unresolved: List[str] = []

        for m in re.finditer(r"\b([a-zA-Z0-9_$]+)\s*\(", source_code):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch", "import", "require", "function"):
                continue
            if name in declared_callables:
                resolved.append(name)
            else:
                unresolved.append(f"{name} (unresolved)")

        return sorted(list(set(resolved))), sorted(list(set(unresolved)))
