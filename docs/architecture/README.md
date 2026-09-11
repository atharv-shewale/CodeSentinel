# System Architecture & Modularity Principles - CodeSentinel

## 1. Zero Direct Cross-Module Dependencies Rule
Modules within `backend/app/` (such as `ingestion`, `profiler`, `analyzer`, `requirements`, `testing`, etc.) MUST NEVER import directly from each other's private submodules.

```
[ Ingestion Module ]        [ Testing Module ]
        \                        /
         \                      /
     [ shared/schemas/ (FROZEN CONTRACTS) ]
```

All interoperability occurs exclusively through:
1. **Pydantic Contract Schemas** in `shared/schemas/`
2. **REST APIs** over standard endpoints
3. **Redis Background Job Tasks** and event streams

## 2. Provenance Trust Model
```
[ Requirement Spec ] -> REQUIREMENT_VERIFIED (Highest Trust)
[ OpenAPI / AST Sig ] -> SCHEMA_DERIVED (High Trust)
[ Branch Coverage ]  -> COVERAGE_ONLY (Medium Trust)
[ LLM Heuristics ]   -> AI_INFERRED (Requires Review)
```
