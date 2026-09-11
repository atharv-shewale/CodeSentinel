"""
CodeSentinel Analyzer: Analysis Service Orchestrator.

Manages deep AST parsing, cross-referencing with profile data, traceability mapping,
and assembling the Software System Model.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional
import uuid
from shared.schemas.code_entity import CodeEntity
from shared.schemas.jobs import JobState, JobStatus, JobType
from shared.schemas.project import Project
from app.analyzer.mapper import TraceabilityMapper
from app.analyzer.python_analyzer import PythonCodeAnalyzer
from app.analyzer.store import AnalysisStore
from app.analyzer.system_model import (
    SoftwareSystemModel,
    SystemModelBuilder,
    SystemModelStore,
)
from app.analyzer.ts_analyzer import TypeScriptCodeAnalyzer
from app.core.logging import logger
from app.requirements.store import RequirementStore
from app.workers.job_manager import JobManager


class CodeAnalyzerService:
    """Orchestrates code AST analysis and Software System Model construction."""

    @classmethod
    def analyze_source_tree(
        cls,
        project_id: uuid.UUID,
        root_dir: str,
    ) -> List[CodeEntity]:
        """
        Recursively scan and analyze all Python and JS/TS files in a directory.
        """
        all_entities: List[CodeEntity] = []

        if not os.path.exists(root_dir):
            return all_entities

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip build and dependency directories
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in ("node_modules", ".venv", "venv", "__pycache__", "dist", "build")
            ]

            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root_dir).replace("\\", "/")

                # Read source
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()
                except Exception:
                    continue

                if filename.endswith(".py"):
                    entities = PythonCodeAnalyzer.analyze_file(
                        file_path=rel_path,
                        source_code=source_code,
                        project_id=project_id,
                    )
                    all_entities.extend(entities)
                elif filename.endswith((".js", ".jsx", ".ts", ".tsx")):
                    entities = TypeScriptCodeAnalyzer.analyze_file(
                        file_path=rel_path,
                        source_code=source_code,
                        project_id=project_id,
                    )
                    all_entities.extend(entities)

        return all_entities

    @classmethod
    async def run_analysis(
        cls,
        project_id: uuid.UUID,
        root_dir: Optional[str] = None,
        project_name: Optional[str] = None,
        profile_metadata: Optional[Dict[str, Any]] = None,
    ) -> SoftwareSystemModel:
        """
        Execute full code analysis, requirement mapping, and software system model generation.
        """
        # 1. Analyze code files if root_dir provided
        entities: List[CodeEntity] = []
        if root_dir and os.path.exists(root_dir):
            entities = cls.analyze_source_tree(project_id, root_dir)
            await AnalysisStore.save(project_id, entities)
        else:
            existing = await AnalysisStore.get(project_id)
            if existing:
                entities = existing

        # 2. Fetch Requirements
        requirements = await RequirementStore.get(project_id)

        # 3. Perform Traceability Mapping
        links, unmapped_reqs, unmapped_ents = TraceabilityMapper.map_requirements_to_code(
            requirements=requirements,
            code_entities=entities,
        )

        # Update requirements in store with new linked_entity_ids if any
        if requirements:
            await RequirementStore.save(project_id, requirements)

        # 4. Extract APIs and Dependencies from profile metadata if provided
        apis = []
        deps = {}
        if profile_metadata:
            apis = profile_metadata.get("apis", [])
            deps = profile_metadata.get("dependencies", {})

        # 5. Assemble Software System Model
        name = project_name or f"Project-{str(project_id)[:8]}"
        system_model = SystemModelBuilder.assemble_system_model(
            project_id=project_id,
            project_name=name,
            code_entities=entities,
            requirements=requirements,
            links=links,
            unmapped_requirements=unmapped_reqs,
            unmapped_entities=unmapped_ents,
            profile_apis=apis,
            profile_dependencies=deps,
        )

        # 6. Persist System Model in PostgreSQL
        await SystemModelStore.save(system_model)
        return system_model

    @classmethod
    async def start_analysis_job(
        cls,
        project_id: uuid.UUID,
        root_dir: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> JobStatus:
        """Enqueue background code analysis and system model construction."""
        job = await JobManager.create_job(
            job_type=JobType.AST_ANALYSIS,
            total_steps=100,
            initial_message=f"Queued deep AST code analysis for project '{project_id}'...",
        )

        async def _pipeline():
            try:
                await JobManager.update_progress(job.job_id, 30, "Parsing AST and extracting CodeEntities...")
                model = await cls.run_analysis(project_id=project_id, root_dir=root_dir, project_name=project_name)
                await JobManager.update_progress(job.job_id, 80, "Mapping requirements and building Software System Model...")
                await JobManager.complete_job(
                    job.job_id,
                    result=model.model_dump(mode="json"),
                    message=f"Analyzed {model.total_classes} classes, {model.total_functions} functions across {model.total_files} files.",
                )
            except Exception as e:
                logger.exception(f"Analysis job {job.job_id} failed: {e}")
                await JobManager.fail_job(job.job_id, str(e))

        asyncio.create_task(_pipeline())
        return job
