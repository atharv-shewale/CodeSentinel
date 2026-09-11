/**
 * CodeSentinel TypeScript Schema Mirror.
 * Derived 1:1 from shared/schemas/ Pydantic contracts.
 */

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, any>;
  trace_id?: string;
}

export interface PaginationMeta {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data: T | null;
  error: APIError | null;
  pagination?: PaginationMeta | null;
  timestamp: string;
}

export type TestProvenance =
  | 'REQUIREMENT_VERIFIED'
  | 'SCHEMA_DERIVED'
  | 'COVERAGE_ONLY'
  | 'AI_INFERRED'
  | 'MUTATION_TARGETED';

export type TestType =
  | 'UNIT'
  | 'INTEGRATION'
  | 'E2E'
  | 'PROPERTY_BASED'
  | 'MUTATION'
  | 'SECURITY'
  | 'PERFORMANCE'
  | 'API_CONTRACT';

export type ProjectStatus =
  | 'INITIALIZING'
  | 'ACTIVE'
  | 'INDEXING'
  | 'ANALYZING'
  | 'READY'
  | 'FAILED'
  | 'ARCHIVED';

export type JobState =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface Project {
  id: string;
  name: string;
  description?: string;
  repository_url: string;
  default_branch: string;
  provider: 'GITHUB' | 'GITLAB' | 'BITBUCKET' | 'LOCAL';
  tags: string[];
  status: ProjectStatus;
  last_indexed_commit?: string;
  total_files: number;
  total_lines_of_code: number;
  created_at: string;
  updated_at: string;
}

export interface Requirement {
  id: string;
  project_id: string;
  identifier: string;
  title: string;
  description: string;
  req_type: 'FUNCTIONAL' | 'NON_FUNCTIONAL' | 'SECURITY' | 'PERFORMANCE' | 'API_CONTRACT' | 'COMPLIANCE';
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'DRAFT' | 'APPROVED' | 'IMPLEMENTED' | 'VERIFIED' | 'FAILED' | 'DEPRECATED';
  acceptance_criteria: string[];
  linked_entity_ids: string[];
  verification_coverage_pct: number;
  created_at: string;
}

export interface TestCase {
  id: string;
  project_id: string;
  name: string;
  description: string;
  test_type: TestType;
  provenance: TestProvenance;
  file_path: string;
  test_code: string;
  status: 'ACTIVE' | 'DRAFT' | 'QUARANTINED' | 'DEPRECATED' | 'FLAKY';
  execution_count: number;
  pass_count: number;
  fail_count: number;
  flakiness_score: number;
  created_at: string;
}

export interface JobProgress {
  current_step: number;
  total_steps: number;
  percentage: number;
  status_message: string;
}

export interface JobStatus {
  job_id: string;
  job_type: string;
  status: JobState;
  progress: JobProgress;
  result?: Record<string, any> | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface CodeLocation {
  file_path: string;
  start_line: number;
  end_line: number;
  start_column?: number;
  end_column?: number;
}

export interface AuditFinding {
  id: string;
  project_id: string;
  rule_id: string;
  title: string;
  description: string;
  category: 'SECURITY_VULNERABILITY' | 'CODE_SMELL' | 'PERFORMANCE_HOTSPOT' | 'API_CONTRACT_VIOLATION' | 'ARCHITECTURE_DRIFT' | 'TYPE_SAFETY' | 'DOCUMENTATION_DEFICIT' | 'COMPLIANCE_NON_CONFORMANCE';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  status: 'OPEN' | 'CONFIRMED' | 'SUPPRESSED' | 'FALSE_POSITIVE' | 'FIX_IN_PROGRESS' | 'RESOLVED';
  standard?: string;
  standard_reference_id?: string;
  location: CodeLocation;
  remediation_suggestion?: string;
  cvss_score?: number;
  detected_by?: string[];
  created_at: string;
  updated_at: string;
}

export interface TestResultItem {
  test_case_id: string;
  test_name: string;
  status: 'PASSED' | 'FAILED' | 'ERROR' | 'TIMED_OUT';
  duration_ms: number;
  error_message?: string;
  stack_trace?: string;
}

export interface TestExecution {
  id: string;
  project_id: string;
  status: 'PASSED' | 'FAILED' | 'ERROR' | 'TIMED_OUT';
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  duration_ms: number;
  results: TestResultItem[];
  created_at: string;
}

export interface Failure {
  id: string;
  project_id: string;
  test_case_id?: string;
  title: string;
  error_message: string;
  stack_trace?: string;
  category: string;
  severity: 'BLOCKER' | 'CRITICAL' | 'MAJOR' | 'MINOR' | 'TRIVIAL';
  status: 'DETECTED' | 'TRIAGED' | 'INVESTIGATING' | 'ROOT_CAUSE_IDENTIFIED' | 'FIX_PROPOSED' | 'RESOLVED' | 'IGNORED';
  root_cause?: {
    summary: string;
    root_cause_category: string;
    is_grounded: boolean;
    confidence_score: number;
    recommended_fix_diff?: string;
  };
}

export interface HealthScoreComponent {
  weight: number;
  score: number;
  penalty?: number;
}

export interface HealthScoreData {
  health_score: number;
  grade: string;
  formula: string;
  components: {
    requirement_coverage: HealthScoreComponent;
    requirement_pass_rate: HealthScoreComponent;
    code_quality: HealthScoreComponent;
    security: HealthScoreComponent;
    architecture: HealthScoreComponent;
  };
}

export interface TierPassStats {
  total_runs: number;
  passed: number;
  failed: number;
  errors: number;
  pass_rate_pct: number;
}

export interface AnalyticsData {
  project_id: string;
  health: HealthScoreData;
  pass_rates: {
    overall_pass_rate_pct: number;
    total_executions: number;
    total_passed: number;
    by_provenance: Record<string, TierPassStats>;
  };
  coverage: {
    requirement_coverage_pct: number;
    total_requirements: number;
    verified_requirements: number;
    code_coverage_per_language: Record<string, number>;
  };
  findings_summary: {
    total: number;
    by_severity: Record<string, number>;
    top_findings: AuditFinding[];
  };
}

export interface TraceabilityItem {
  requirement_id?: string;
  requirement_identifier: string;
  requirement_title: string;
  module: string;
  entity_name: string;
  entity_file_path: string;
  test_case_id?: string;
  test_name: string;
  provenance: TestProvenance | 'NONE';
  execution_status: string;
  duration_ms: number;
}

export interface AIAssistantResponse {
  answer: string;
  is_grounded: boolean;
  confidence_score: number;
  cited_evidence?: Array<{
    source_type: string;
    identifier: string;
    snippet: string;
  }>;
  citations?: string[];
}
