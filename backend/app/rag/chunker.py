"""
CodeSentinel RAG Module: Semantic & AST Chunking Strategy.

Chunking Rules:
1. Code Entities: Chunked strictly at Function, Method, and Class boundaries (never split mid-function).
2. Requirements: Exactly one coherent chunk per requirement specification.
3. Documentation: Chunked by Markdown / text section headings (e.g. #, ##, ===).
4. Tests, Logs, Findings: Chunked per individual entity item.
"""

import re
from typing import Any, Dict, List, Optional
import uuid

from app.rag.models import ChunkType, RAGChunk, RAGCollection


class CodeChunker:
    """Performs semantic and AST-aware chunking over software system models."""

    @classmethod
    def chunk_system_model(cls, project_id: str, system_model: Dict[str, Any]) -> List[RAGChunk]:
        """Convert a complete Software System Model into normalized RAG chunks."""
        chunks: List[RAGChunk] = []

        # 1. Code Chunks (Functions, Methods, Classes)
        functions = system_model.get("functions", [])
        for fn in functions:
            fn_id = str(fn.get("id") or fn.get("qualified_name") or uuid.uuid4())
            name = fn.get("name", "unnamed_function")
            qname = fn.get("qualified_name", name)
            docstring = fn.get("docstring") or ""
            source = fn.get("source_code") or ""
            loc = fn.get("location") if isinstance(fn.get("location"), dict) else {}
            file_path = loc.get("file_path") or fn.get("file_path", "")
            start_l = loc.get("start_line")
            end_l = loc.get("end_line")

            content = f"Function: {qname}\nFile: {file_path}\n"
            if docstring:
                content += f"Docstring: {docstring}\n"
            if source:
                content += f"Source Code:\n{source}"
            else:
                params = fn.get("parameters", [])
                ret_t = fn.get("return_type", "Any")
                content += f"Signature: ({', '.join(str(p) for p in params)}) -> {ret_t}\n"

            chunks.append(RAGChunk(
                chunk_id=f"fn_{fn_id}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_CODE,
                chunk_type=ChunkType.FUNCTION,
                title=f"Function {qname}",
                content=content.strip(),
                file_path=file_path,
                start_line=start_l,
                end_line=end_l,
                metadata={
                    "entity_id": fn_id,
                    "name": name,
                    "qualified_name": qname,
                    "return_type": fn.get("return_type"),
                    "complexity_score": fn.get("complexity_score"),
                }
            ))

        classes = system_model.get("classes", [])
        for c in classes:
            c_id = str(c.get("id") or c.get("qualified_name") or uuid.uuid4())
            name = c.get("name", "unnamed_class")
            qname = c.get("qualified_name", name)
            docstring = c.get("docstring") or ""
            source = c.get("source_code") or ""
            loc = c.get("location") if isinstance(c.get("location"), dict) else {}
            file_path = loc.get("file_path") or c.get("file_path", "")
            start_l = loc.get("start_line")
            end_l = loc.get("end_line")

            content = f"Class: {qname}\nFile: {file_path}\n"
            if docstring:
                content += f"Docstring: {docstring}\n"
            if source:
                content += f"Source Code:\n{source}"

            chunks.append(RAGChunk(
                chunk_id=f"cls_{c_id}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_CODE,
                chunk_type=ChunkType.CLASS,
                title=f"Class {qname}",
                content=content.strip(),
                file_path=file_path,
                start_line=start_l,
                end_line=end_l,
                metadata={"entity_id": c_id, "name": name, "qualified_name": qname}
            ))

        # 2. Requirements Chunks (One per requirement specification)
        requirements = system_model.get("requirements", [])
        for req in requirements:
            req_id = str(req.get("id") or req.get("identifier") or uuid.uuid4())
            ident = req.get("identifier", "REQ-UNKNOWN")
            title = req.get("title", "")
            desc = req.get("description", "")
            rtype = req.get("req_type", "FUNCTIONAL")
            pri = req.get("priority", "MEDIUM")
            status = req.get("status", "DRAFT")
            criteria = req.get("acceptance_criteria", [])

            content = (
                f"Requirement: {ident} - {title}\n"
                f"Type: {rtype} | Priority: {pri} | Status: {status}\n"
                f"Description: {desc}\n"
            )
            if criteria:
                content += "Acceptance Criteria:\n" + "\n".join(f"- {c}" for c in criteria)

            chunks.append(RAGChunk(
                chunk_id=f"req_{req_id}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_REQUIREMENTS,
                chunk_type=ChunkType.REQUIREMENT,
                title=f"{ident}: {title}",
                content=content.strip(),
                metadata={
                    "requirement_id": req_id,
                    "identifier": ident,
                    "title": title,
                    "priority": pri,
                    "status": status,
                    "req_type": rtype,
                }
            ))

        # 3. Test Cases Chunks
        tests = system_model.get("test_cases", []) or system_model.get("tests", [])
        for t in tests:
            t_id = str(t.get("id") or t.get("name") or uuid.uuid4())
            name = t.get("name", "unnamed_test")
            desc = t.get("description", "")
            prov = t.get("provenance", "REQUIREMENT_VERIFIED")
            t_type = t.get("test_type", "UNIT")
            fpath = t.get("file_path", "")
            code = t.get("test_code", "")

            content = (
                f"Test Case: {name}\n"
                f"File: {fpath} | Type: {t_type} | Provenance: {prov}\n"
                f"Description: {desc}\n"
            )
            if code:
                content += f"Test Code:\n{code}"

            chunks.append(RAGChunk(
                chunk_id=f"test_{t_id}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_TESTS,
                chunk_type=ChunkType.TEST,
                title=f"Test {name}",
                content=content.strip(),
                file_path=fpath,
                metadata={"test_id": t_id, "name": name, "provenance": prov, "test_type": t_type}
            ))

        # 4. Findings Chunks
        findings = system_model.get("findings", [])
        for f in findings:
            f_id = str(f.get("id") or uuid.uuid4())
            rule = f.get("rule_id", "SECURITY")
            title = f.get("title", "")
            desc = f.get("description", "")
            cat = f.get("category", "CODE_SMELL")
            sev = f.get("severity", "MEDIUM")
            loc = f.get("location", {}) if isinstance(f.get("location"), dict) else {}
            fpath = loc.get("file_path", "")

            content = f"Finding: [{sev}] {rule} - {title}\nCategory: {cat}\nFile: {fpath}\nDescription: {desc}"

            chunks.append(RAGChunk(
                chunk_id=f"find_{f_id}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_FINDINGS,
                chunk_type=ChunkType.FINDING,
                title=f"Finding: {title}",
                content=content.strip(),
                file_path=fpath,
                metadata={"finding_id": f_id, "rule_id": rule, "severity": sev, "category": cat}
            ))

        # 5. Documentation Chunks (Section/Heading split)
        docs = system_model.get("documentation", []) or system_model.get("docs", [])
        for doc in docs:
            doc_id = str(doc.get("id") or uuid.uuid4())
            doc_title = doc.get("title", "Documentation")
            doc_text = doc.get("content") or doc.get("text") or ""
            fpath = doc.get("file_path", "")
            doc_chunks = cls.chunk_markdown_document(project_id, doc_id, doc_title, doc_text, fpath)
            chunks.extend(doc_chunks)

        return chunks

    @classmethod
    def chunk_markdown_document(
        cls,
        project_id: str,
        doc_id: str,
        doc_title: str,
        content: str,
        file_path: Optional[str] = None
    ) -> List[RAGChunk]:
        """Split a Markdown / text document by section headings (e.g. #, ##, ===)."""
        if not content:
            return []

        # Match markdown headers (# Title, ## Subtitle)
        sections = re.split(r'\n(?=#{1,3}\s+)', content)
        chunks = []
        for idx, section in enumerate(sections):
            clean_sec = section.strip()
            if not clean_sec:
                continue

            # Extract heading title if present
            lines = clean_sec.splitlines()
            header_line = lines[0] if lines else doc_title
            section_title = header_line.lstrip("#").strip() or f"{doc_title} Part {idx+1}"

            chunks.append(RAGChunk(
                chunk_id=f"doc_{doc_id}_{idx}",
                project_id=project_id,
                collection=RAGCollection.PROJECT_DOCUMENTATION,
                chunk_type=ChunkType.DOCUMENTATION,
                title=section_title,
                content=clean_sec,
                file_path=file_path,
                metadata={"doc_id": doc_id, "section_index": idx, "doc_title": doc_title}
            ))

        return chunks
