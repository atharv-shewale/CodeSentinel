"""
CodeSentinel Analyzer Test Suite: AST Code Analysis & CodeEntity Extraction.

Tests Python AST extraction, TypeScript parsing, ambiguous call marking,
and PostgreSQL-backed cross-process persistence.
"""

import uuid
import pytest
from shared.schemas.code_entity import CodeEntity, EntityType, Visibility
from app.analyzer.python_analyzer import PythonCodeAnalyzer
from app.analyzer.store import AnalysisStore
from app.analyzer.ts_analyzer import TypeScriptCodeAnalyzer
from app.core.database import get_sessionmaker
from tests.fixtures.analysis.sample_sources import (
    SAMPLE_AMBIGUOUS_CALLS_PYTHON,
    SAMPLE_PYTHON_SOURCE,
    SAMPLE_TS_SOURCE,
)


class TestCodeAnalyzer:
    """Verifies AST parsing and CodeEntity extraction fidelity."""

    def test_python_ast_extraction_exact_structure(self):
        """
        TEST #1: Python file with known classes/functions/imports ->
        assert exact extracted structure (counts, names, parameters, return types, docstrings).
        """
        project_id = uuid.uuid4()
        entities = PythonCodeAnalyzer.analyze_file(
            file_path="app/services/auth.py",
            source_code=SAMPLE_PYTHON_SOURCE,
            project_id=project_id,
        )

        # 1. Total entities count: 1 FILE + 1 CLASS + 3 METHODS + 1 FUNCTION = 6 entities
        assert len(entities) == 6

        # 2. Validate FILE Entity
        file_ent = next(e for e in entities if e.entity_type == EntityType.FILE)
        assert file_ent.name == "auth.py"
        assert file_ent.qualified_name == "app/services/auth.py"
        assert "os" in file_ent.dependencies
        assert "typing.Optional" in file_ent.dependencies or "typing" in str(file_ent.dependencies)

        # 3. Validate CLASS Entity
        class_ent = next(e for e in entities if e.entity_type == EntityType.CLASS)
        assert class_ent.name == "AuthenticationService"
        assert "JWT token lifecycle" in (class_ent.docstring or "")
        assert class_ent.visibility == Visibility.PUBLIC

        # 4. Validate METHODS
        methods = [e for e in entities if e.entity_type == EntityType.METHOD]
        method_names = [m.name for m in methods]
        assert "__init__" in method_names
        assert "authenticate_user" in method_names
        assert "_generate_token" in method_names

        # Check authenticate_user signature
        auth_func = next(m for m in methods if m.name == "authenticate_user")
        assert auth_func.return_type == "Optional[Dict[str, str]]" or "Optional" in str(auth_func.return_type)
        param_names = [p.name for p in auth_func.parameters]
        assert "username" in param_names
        assert "password_hash" in param_names
        assert "REQ-AUTH-001" in (auth_func.docstring or "")

        # Check private method visibility
        token_func = next(m for m in methods if m.name == "_generate_token")
        assert token_func.visibility == Visibility.PROTECTED or token_func.visibility == Visibility.PRIVATE

        # 5. Validate Top-Level FUNCTION
        top_funcs = [e for e in entities if e.entity_type == EntityType.FUNCTION]
        assert len(top_funcs) == 1
        hash_func = top_funcs[0]
        assert hash_func.name == "hash_password"
        assert hash_func.return_type == "str"
        assert "REQ-SEC-002" in (hash_func.docstring or "")

        # All entities must strictly validate against Pydantic schema
        for ent in entities:
            assert isinstance(ent, CodeEntity)
            assert ent.project_id == project_id

    def test_typescript_code_extraction(self):
        """
        TEST #2: JS/TS file with known structure ->
        classes, methods, arrow functions, parameters, return types.
        """
        project_id = uuid.uuid4()
        entities = TypeScriptCodeAnalyzer.analyze_file(
            file_path="src/services/userService.ts",
            source_code=SAMPLE_TS_SOURCE,
            project_id=project_id,
        )

        assert len(entities) >= 3

        # Validate File Entity
        file_ent = next(e for e in entities if e.entity_type == EntityType.FILE)
        assert file_ent.language == "typescript"
        assert "./db" in file_ent.dependencies

        # Validate Class Entity
        class_ent = next(e for e in entities if e.entity_type == EntityType.CLASS)
        assert class_ent.name == "UserService"

        # Validate Functions & Arrow Functions
        funcs = [e for e in entities if e.entity_type in (EntityType.FUNCTION, EntityType.METHOD)]
        func_names = [f.name for f in funcs]
        assert "getUserById" in func_names
        assert "formatUserName" in func_names

        arrow_func = next(f for f in funcs if f.name == "formatUserName")
        assert arrow_func.return_type == "string"
        param_names = [p.name for p in arrow_func.parameters]
        assert "firstName" in param_names
        assert "lastName" in param_names

    def test_ambiguous_call_relationships_marked_unresolved(self):
        """
        TEST #3: A file with ambiguous/unresolvable call relationships ->
        assert they're marked 'unresolved' rather than guessing.
        """
        project_id = uuid.uuid4()
        entities = PythonCodeAnalyzer.analyze_file(
            file_path="app/metrics.py",
            source_code=SAMPLE_AMBIGUOUS_CALLS_PYTHON,
            project_id=project_id,
        )

        calc_func = next(e for e in entities if e.name == "calculate_metric")
        unresolved = calc_func.metadata.get("unresolved_calls", [])
        assert len(unresolved) > 0
        assert any("unresolved" in c for c in unresolved)

    @pytest.mark.asyncio
    async def test_analysis_persistence_cross_process_roundtrip(self):
        """
        TEST #4: Analysis results persisted via one store instance, read back
        via a separate instance (cross-process simulation) -> assert correct round-trip.
        """
        session_maker = get_sessionmaker()
        worker_store = AnalysisStore(session_factory=session_maker)
        web_store = AnalysisStore(session_factory=session_maker)

        project_id = uuid.uuid4()
        entities = PythonCodeAnalyzer.analyze_file(
            file_path="app/services/auth.py",
            source_code=SAMPLE_PYTHON_SOURCE,
            project_id=project_id,
        )

        # Worker persists analysis
        await worker_store.save_entities(project_id, entities)

        # Web reads analysis
        loaded_entities = await web_store.get_entities(project_id)
        assert loaded_entities is not None
        assert len(loaded_entities) == len(entities)

        loaded_names = [e.name for e in loaded_entities]
        assert "AuthenticationService" in loaded_names
        assert "authenticate_user" in loaded_names
        assert "hash_password" in loaded_names
