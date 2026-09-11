import React, { useState } from 'react';

export const ContractsExplorer: React.FC = () => {
  const contracts = [
    {
      name: 'Project',
      file: 'shared/schemas/project.py',
      description: 'Root container for codebase intelligence, Git repository metadata, branch indexing, and LOC telemetry.',
      fields: ['id: UUID', 'name: str', 'repository_url: str', 'default_branch: str', 'provider: RepoProvider', 'status: ProjectStatus', 'total_files: int'],
    },
    {
      name: 'Requirement',
      file: 'shared/schemas/requirement.py',
      description: 'Business requirements, user stories, acceptance criteria, and traceability linkages to verified tests.',
      fields: ['id: UUID', 'project_id: UUID', 'identifier: str', 'title: str', 'req_type: RequirementType', 'priority: RequirementPriority', 'acceptance_criteria: List[str]'],
    },
    {
      name: 'CodeEntity',
      file: 'shared/schemas/code_entity.py',
      description: 'Parsed structural AST entities (file, class, function, method) extracted via Tree-sitter.',
      fields: ['id: UUID', 'name: str', 'qualified_name: str', 'entity_type: EntityType', 'location: CodeLocation', 'visibility: Visibility', 'complexity_score: float'],
    },
    {
      name: 'APIRoute',
      file: 'shared/schemas/api_route.py',
      description: 'Discovered REST endpoints, parameters, JSON schemas, and authorization requirements.',
      fields: ['id: UUID', 'path: str', 'http_method: HTTPMethod', 'summary: str', 'auth_requirement: AuthRequirement', 'parameters: List[RouteParameter]'],
    },
    {
      name: 'TestCase',
      file: 'shared/schemas/test_case.py',
      description: 'Actionable test cases with mandatory provenance tracking: REQUIREMENT_VERIFIED, SCHEMA_DERIVED, COVERAGE_ONLY, AI_INFERRED.',
      fields: ['id: UUID', 'name: str', 'provenance: TestProvenance (MANDATORY)', 'test_type: TestType', 'test_code: str', 'assertions: List[AssertionSpec]'],
    },
    {
      name: 'TestExecution',
      file: 'shared/schemas/test_execution.py',
      description: 'Isolated Docker sandbox execution runs, logs, coverage telemetry, and test results.',
      fields: ['id: UUID', 'environment: ExecutionEnvironment', 'status: ExecutionStatus', 'results: List[TestResultItem]', 'coverage: CoverageMetrics'],
    },
    {
      name: 'Failure',
      file: 'shared/schemas/failure.py',
      description: 'Recorded test defects, exception traces, severity classifications, and automated Root Cause Analysis (RCA).',
      fields: ['id: UUID', 'category: FailureCategory', 'severity: FailureSeverity', 'error_message: str', 'root_cause: RootCauseAnalysis'],
    },
    {
      name: 'AuditFinding',
      file: 'shared/schemas/audit.py',
      description: 'Security vulnerabilities (OWASP/CWE), code smells, and architecture drift findings.',
      fields: ['id: UUID', 'rule_id: str', 'category: AuditCategory', 'severity: AuditSeverity', 'standard: ComplianceStandard', 'location: CodeLocation'],
    },
  ];

  const [selected, setSelected] = useState(contracts[0]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Frozen Shared Schemas (Phase 0)</h2>
        <p className="text-sm text-slate-400">
          5 later independent modules will build strictly against these schemas without direct internal imports.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-2">
          {contracts.map((c) => (
            <button
              key={c.name}
              onClick={() => setSelected(c)}
              className={`w-full text-left p-3.5 rounded-xl border transition ${
                selected.name === c.name
                  ? 'bg-sentinel-card border-blue-500 shadow-md text-white'
                  : 'bg-sentinel-card/50 border-sentinel-border hover:border-slate-700 text-slate-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm">{c.name}</span>
                <span className="text-[11px] font-mono text-slate-500">{c.file.split('/')[2]}</span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-1 mt-1">{c.description}</p>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 p-6 rounded-xl bg-sentinel-card border border-sentinel-border space-y-5">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-4">
            <div>
              <h3 className="text-lg font-bold text-white font-mono">{selected.name}</h3>
              <p className="text-xs text-blue-400 font-mono mt-0.5">{selected.file}</p>
            </div>
            <span className="px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
              FROZEN CONTRACT
            </span>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Description & Invariants</h4>
            <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              {selected.description}
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Core Typed Fields</h4>
            <div className="space-y-1.5 font-mono text-xs">
              {selected.fields.map((f, i) => (
                <div key={i} className="px-3 py-2 rounded bg-slate-900/80 border border-slate-800 text-slate-200">
                  {f}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
