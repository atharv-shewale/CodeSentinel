# Test Plan & Sandbox Isolation Specification - CodeSentinel

## 1. Testing Strategy
1. **Contract Integrity Tests (`test_contracts.py`)**:
   - Enforce that all domain models in `shared/schemas/` have non-empty docstrings, strict type annotations, and validate defaults and serialization.
   - Enforce `TestProvenance` mandatory 4-state enum validation.
2. **Envelope Standardization Tests (`test_envelope.py`)**:
   - Verify `APIResponse[T]` success envelope structure, pagination metadata, and error payload consistency.
3. **Route Coverage Tests (`test_routes.py`)**:
   - Query all 16 API route groups through FastAPI `TestClient` to verify status codes (200, 201, 202, 404).
4. **Job Manager Tests (`test_jobs.py`)**:
   - Verify state machine transitions: PENDING -> RUNNING -> COMPLETED / FAILED with real-time percentage progress updates.

## 2. Sandbox Execution Isolation
- **Sandbox Container Boundary**: Test execution sandbox containers run in a dedicated, ephemeral Docker network (`codesentinel_sandbox_net`).
- **Security Constraint**: Test execution sandboxes MUST NEVER share network namespaces or direct access with application databases (`postgres`, `neo4j`, `qdrant`).
