"""
Test Audit Planted Secret and Vulnerability Detection End-to-End.

Validates FIX 2:
- Retained source workspace allows AuditEngine to inspect files on disk.
- Planted secret (AWS Access Key ID) in app/auth.py is detected (SEC-SECRET-AWS-KEY).
- Planted unauthenticated route (/api/admin/users) is detected (SEC-ROUTE-MISSING-AUTH).
- Planted vulnerable dependencies (urllib3, pyyaml) are flagged.
"""

import asyncio
import io
import os
import zipfile
import pytest
from fastapi.testclient import TestClient


def _create_sample_project_zip() -> bytes:
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample_project")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(sample_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, sample_dir)
                zf.write(full_path, rel_path)
    return zip_buffer.getvalue()


@pytest.mark.asyncio
async def test_audit_detects_planted_secret_and_defects_in_pipeline(client: TestClient):
    zip_bytes = _create_sample_project_zip()

    # 1. Upload repository zip
    upload_res = client.post(
        "/api/v1/repositories/upload",
        data={"project_name": "Test-Audit-Planted-Defects"},
        files={"file": ("sample_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 202, f"Upload failed: {upload_res.text}"
    job_id = upload_res.json()["data"]["job_id"]

    # Poll until ingestion completes
    project_id = None
    for i in range(40):
        await asyncio.sleep(0.5)
        job_res = client.get(f"/api/v1/jobs/{job_id}")
        if job_res.status_code == 200:
            job_data = job_res.json()["data"]
            print(f"DEBUG iteration {i}: status={job_data.get('status')}, error={job_data.get('error')}, progress={job_data.get('progress')}")
            if job_data.get("status") == "COMPLETED":
                project_id = job_data.get("result", {}).get("id")
                break
            elif job_data.get("status") == "FAILED":
                pytest.fail(f"Ingestion job failed: {job_data.get('error')}")

    assert project_id is not None, "Ingestion did not produce a project ID"

    # 2. Run AST analysis
    client.post("/api/v1/analysis", json={"project_id": project_id})
    await asyncio.sleep(1.0)

    # 3. Run audit synchronously
    audit_res = client.post(f"/api/v1/audits/{project_id}/run?sync=true")
    assert audit_res.status_code == 200, f"Audit failed: {audit_res.text}"

    # 4. Fetch findings
    findings_res = client.get(f"/api/v1/audits/{project_id}")
    assert findings_res.status_code == 200
    findings = findings_res.json().get("data", [])
    assert len(findings) > 0, "Expected audit findings, got none"

    rule_ids = [f.get("rule_id") for f in findings]

    # Assert planted secret was detected
    assert "SEC-SECRET-AWS-KEY" in rule_ids, f"Planted AWS Secret Key not detected! Findings: {rule_ids}"

    # Assert missing authentication on /api/admin/users was detected
    assert "SEC-ROUTE-MISSING-AUTH" in rule_ids, f"Missing route authentication not detected! Findings: {rule_ids}"

    # Assert vulnerable dependencies were detected
    has_urllib3 = any("URLLIB3" in r for r in rule_ids)
    has_pyyaml = any("PYYAML" in r for r in rule_ids)
    assert has_urllib3 or has_pyyaml, f"Vulnerable dependencies not detected! Findings: {rule_ids}"
