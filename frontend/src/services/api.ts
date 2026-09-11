/**
 * CodeSentinel Typed API Client.
 *
 * Unwraps APIResponse[T] envelopes consistently across all views.
 * Dispatches real HTTP requests to the live backend endpoints.
 */

import {
  APIResponse,
  Project,
  Requirement,
  TestCase,
  TestExecution,
  Failure,
  AuditFinding,
  AnalyticsData,
  TraceabilityItem,
  AIAssistantResponse,
  JobStatus,
} from '../types';

const API_BASE = '/api/v1';

// ----------------------------------------------------------------------------
// Typed Client Implementation (Real Network Requests)
// ----------------------------------------------------------------------------
export class ApiClient {
  private static async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const isFormData = options?.body instanceof FormData;
    const defaultHeaders: Record<string, string> = {
      Accept: 'application/json',
    };
    if (!isFormData) {
      defaultHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options?.headers as Record<string, string> || {}),
      },
    });

    if (!response.ok) {
      let errorMessage = `HTTP error ${response.status}: ${response.statusText}`;
      try {
        const errorBody = await response.json();
        if (errorBody?.error?.message) {
          errorMessage = errorBody.error.message;
        } else if (errorBody?.message) {
          errorMessage = errorBody.message;
        }
      } catch {
        // use default message
      }
      throw new Error(errorMessage);
    }

    const body: APIResponse<T> = await response.json();
    if (!body.success) {
      throw new Error(body.error?.message || body.message || 'API operation reported failure.');
    }

    return body.data as T;
  }

  // --- Projects ---
  static async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  static async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}`);
  }

  static async createProject(payload: {
    name: string;
    description?: string;
    repository_url: string;
    default_branch?: string;
  }): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // --- Ingestion / Repository Onboarding ---
  static async createRepository(payload: {
    source_type: 'github' | 'local' | 'zip';
    source?: string;
    branch?: string;
    project_name?: string;
  }): Promise<JobStatus> {
    return this.request<JobStatus>('/repositories', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async uploadRepositoryZip(file: File | Blob, projectName?: string): Promise<JobStatus> {
    const formData = new FormData();
    formData.append('file', file, 'repository.zip');
    if (projectName) {
      formData.append('project_name', projectName);
    }

    return this.request<JobStatus>('/repositories/upload', {
      method: 'POST',
      body: formData,
    });
  }

  // --- Jobs ---
  static async getJobStatus(jobId: string): Promise<JobStatus> {
    return this.request<JobStatus>(`/jobs/${jobId}`);
  }

  // --- Requirements ---
  static async getRequirements(projectId: string): Promise<Requirement[]> {
    return this.request<Requirement[]>(`/requirements/${projectId}`);
  }

  static async uploadRequirementsDocument(projectId: string, file: File): Promise<JobStatus> {
    const formData = new FormData();
    formData.append('project_id', projectId);
    formData.append('file', file);

    return this.request<JobStatus>('/requirements/upload', {
      method: 'POST',
      body: formData,
    });
  }

  // --- Deep Code Analysis (Module 2) ---
  static async triggerAnalysis(projectId: string): Promise<JobStatus> {
    return this.request<JobStatus>('/analysis', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId }),
    });
  }

  // --- Knowledge Graph & RAG (Module 3) ---
  static async triggerKnowledgeGraph(projectId: string): Promise<JobStatus> {
    return this.request<JobStatus>(`/knowledge/${projectId}/build`, {
      method: 'POST',
    });
  }

  static async triggerRAGIndex(projectId: string): Promise<JobStatus> {
    return this.request<JobStatus>(`/rag/${projectId}/index`, {
      method: 'POST',
    });
  }

  // --- Tests (Module 4) ---
  static async getTests(projectId: string): Promise<TestCase[]> {
    const res = await this.request<TestCase[] | TestCase>(`/tests/${projectId}`);
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object') return [res];
    return [];
  }

  static async generateTests(projectId: string, includePropertyBased: boolean = false): Promise<TestCase[]> {
    return this.request<TestCase[]>(`/tests/${projectId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, sync: true, include_property_based: includePropertyBased }),
    });
  }

  static async runMutationRun(projectId: string, sync: boolean = true): Promise<any> {
    return this.request<any>(`/tests/${projectId}/mutation-run`, {
      method: 'POST',
      body: JSON.stringify({ sync }),
    });
  }

  static async getMutationScore(projectId: string): Promise<any> {
    return this.request<any>(`/tests/${projectId}/mutation-score`);
  }

  // --- Executions ---
  static async getExecutions(projectId: string): Promise<TestExecution[]> {
    const res = await this.request<TestExecution[] | TestExecution>(`/executions/project/${projectId}`);
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object') return [res];
    return [];
  }

  static async runExecution(projectId: string, testIds?: string[]): Promise<TestExecution> {
    return this.request<TestExecution>(`/executions/${projectId}/run`, {
      method: 'POST',
      body: JSON.stringify({ test_ids: testIds, sync: true }),
    });
  }

  // --- Failures ---
  static async getFailures(projectId: string): Promise<Failure[]> {
    const res = await this.request<Failure[] | Failure>(`/failures/project/${projectId}`);
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object') return [res];
    return [];
  }

  // --- Audits ---
  static async getFindings(projectId: string): Promise<AuditFinding[]> {
    return this.request<AuditFinding[]>(`/audits/${projectId}`);
  }

  static async runAudit(projectId: string): Promise<AuditFinding[]> {
    return this.request<AuditFinding[]>(`/audits/${projectId}/run?sync=true`, {
      method: 'POST',
    });
  }

  // --- Analytics & Traceability ---
  static async getAnalytics(projectId: string): Promise<AnalyticsData> {
    return this.request<AnalyticsData>(`/analytics/${projectId}`);
  }

  static async getTraceability(projectId: string): Promise<TraceabilityItem[]> {
    return this.request<TraceabilityItem[]>(`/analytics/${projectId}/traceability`);
  }

  static async getReport(projectId: string): Promise<{
    project_id: string;
    generated_at: string;
    grade: string;
    health_score: number;
    markdown_content: string;
  }> {
    return this.request<any>(`/analytics/${projectId}/report`);
  }

  // --- AI Assistant ---
  static async askAssistant(
    projectId: string,
    question: string,
    agentType: string = 'QA_TEST_AGENT'
  ): Promise<AIAssistantResponse> {
    return this.request<AIAssistantResponse>(`/agents/${projectId}/ask`, {
      method: 'POST',
      body: JSON.stringify({
        question,
        agent_type: agentType,
      }),
    });
  }
}

export const apiService = {
  getProjects: async (): Promise<APIResponse<Project[]>> => {
    const data = await ApiClient.getProjects();
    return {
      success: true,
      message: 'OK',
      data,
      error: null,
      timestamp: new Date().toISOString(),
    };
  },
  getTests: async (projectId: string = '00000000-0000-0000-0000-000000000001'): Promise<APIResponse<TestCase[]>> => {
    const data = await ApiClient.getTests(projectId);
    return {
      success: true,
      message: 'OK',
      data,
      error: null,
      timestamp: new Date().toISOString(),
    };
  },
  getRequirements: async (projectId: string = '00000000-0000-0000-0000-000000000001'): Promise<APIResponse<Requirement[]>> => {
    const data = await ApiClient.getRequirements(projectId);
    return {
      success: true,
      message: 'OK',
      data,
      error: null,
      timestamp: new Date().toISOString(),
    };
  },
};
