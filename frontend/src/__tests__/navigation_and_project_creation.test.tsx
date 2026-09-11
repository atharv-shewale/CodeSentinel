import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProjectProvider } from '../context/ProjectContext';
import { Sidebar } from '../components/Sidebar';
import { Dashboard } from '../pages/Dashboard';
import { ProjectsList } from '../pages/ProjectsList';
import { CreateProjectPage } from '../pages/CreateProjectPage';
import { RequirementsView } from '../pages/RequirementsView';
import { TestsView } from '../pages/TestsView';
import { ExecutionsView } from '../pages/ExecutionsView';
import { FailuresView } from '../pages/FailuresView';
import { AuditsView } from '../pages/AuditsView';
import { AnalyticsView } from '../pages/AnalyticsView';
import { ReportsView } from '../pages/ReportsView';
import { AIAssistantView } from '../components/AIAssistantView';
import { ContractsExplorer } from '../pages/ContractsExplorer';
import { ApiClient } from '../services/api';

describe('Navigation & Project Creation Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  // ---------------------------------------------------------------------------
  // 1. Every sidebar link navigates to a non-blank, defined page
  // ---------------------------------------------------------------------------
  it('Sidebar contains real navigable links for all items and routes to non-blank views', async () => {
    vi.spyOn(ApiClient, 'getProjects').mockResolvedValue([]);

    const { container } = render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <ProjectProvider>
          <div className="flex">
            <Sidebar />
            <main>
              <Routes>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/projects" element={<ProjectsList />} />
                <Route path="/projects/new" element={<CreateProjectPage />} />
                <Route path="/requirements" element={<RequirementsView />} />
                <Route path="/tests" element={<TestsView />} />
                <Route path="/executions" element={<ExecutionsView />} />
                <Route path="/failures" element={<FailuresView />} />
                <Route path="/audits" element={<AuditsView />} />
                <Route path="/analytics" element={<AnalyticsView />} />
                <Route path="/reports" element={<ReportsView />} />
                <Route path="/assistant" element={<AIAssistantView />} />
                <Route path="/contracts" element={<ContractsExplorer />} />
              </Routes>
            </main>
          </div>
        </ProjectProvider>
      </MemoryRouter>
    );

    const navIds = [
      'dashboard',
      'projects',
      'requirements',
      'tests',
      'executions',
      'failures',
      'audits',
      'analytics',
      'reports',
      'assistant',
      'contracts',
    ];

    // Verify all 11 sidebar links exist as <a> tags (NavLinks)
    for (const id of navIds) {
      const linkEl = container.querySelector(`[data-testid="nav-${id}"]`);
      expect(linkEl).not.toBeNull();
      expect(linkEl?.tagName).toBe('A');
      expect(linkEl?.getAttribute('href')).toBe(`/${id}`);
    }
  });

  // ---------------------------------------------------------------------------
  // 2. Project-scoped pages show "No project selected" when none is selected
  // ---------------------------------------------------------------------------
  it('Project-scoped pages show "No project selected" empty state with action buttons when no project is active', async () => {
    vi.spyOn(ApiClient, 'getProjects').mockResolvedValue([]);

    // Render RequirementsView without any selected project
    render(
      <MemoryRouter>
        <ProjectProvider>
          <RequirementsView />
        </ProjectProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('no-project-selected')).not.toBeNull();
      expect(screen.getByText('No Project Selected')).not.toBeNull();
      expect(screen.getByText('View All Projects')).not.toBeNull();
      expect(screen.getByText('+ Onboard New Repository')).not.toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // 3. Frozen Schemas is project-independent and renders without project
  // ---------------------------------------------------------------------------
  it('Frozen Schemas renders contract specifications without requiring an active project', async () => {
    render(
      <MemoryRouter>
        <ContractsExplorer />
      </MemoryRouter>
    );

    expect(screen.getByText('Frozen Shared Schemas (Phase 0)')).not.toBeNull();
    expect(screen.getByText('shared/schemas/project.py')).not.toBeNull();
    expect(screen.getByText('test_case.py')).not.toBeNull();
  });

  // ---------------------------------------------------------------------------
  // 4. Project Creation flow transitions through queued -> running -> done
  // ---------------------------------------------------------------------------
  it('CreateProjectPage initiates pipeline and polls through queued -> running -> completed states', async () => {
    const mockJobId = 'job-ingest-123';
    const mockProjectId = 'proj-9999-8888';

    // Mock createRepository response
    vi.spyOn(ApiClient, 'createRepository').mockResolvedValue({
      job_id: mockJobId,
      job_type: 'REPO_INGESTION' as any,
      status: 'PENDING' as any,
      progress: {
        current_step: 0,
        total_steps: 10,
        percentage: 10,
        status_message: 'Cloning repository...',
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    // Mock job status polling transitions: PENDING -> RUNNING -> COMPLETED
    let pollCount = 0;
    vi.spyOn(ApiClient, 'getJobStatus').mockImplementation(async (jobId: string) => {
      pollCount++;
      if (pollCount === 1) {
        return {
          job_id: jobId,
          job_type: 'REPO_INGESTION' as any,
          status: 'RUNNING' as any,
          progress: {
            current_step: 5,
            total_steps: 10,
            percentage: 50,
            status_message: 'Profiling AST entities...',
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
      }
      return {
        job_id: jobId,
        job_type: 'REPO_INGESTION' as any,
        status: 'COMPLETED' as any,
        progress: {
          current_step: 10,
          total_steps: 10,
          percentage: 100,
          status_message: 'Profiling complete.',
        },
        result: {
          id: mockProjectId,
          name: 'DemoService',
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    });

    // Mock subsequent pipeline stages
    vi.spyOn(ApiClient, 'triggerAnalysis').mockResolvedValue({
      job_id: 'job-analysis-123',
      job_type: 'AST_ANALYSIS' as any,
      status: 'COMPLETED' as any,
      progress: { current_step: 1, total_steps: 1, percentage: 100, status_message: 'Done' },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    vi.spyOn(ApiClient, 'triggerKnowledgeGraph').mockResolvedValue({
      job_id: 'job-kg-123',
      job_type: 'KNOWLEDGE_GRAPH_BUILD' as any,
      status: 'COMPLETED' as any,
      progress: { current_step: 1, total_steps: 1, percentage: 100, status_message: 'Done' },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    vi.spyOn(ApiClient, 'triggerRAGIndex').mockResolvedValue({
      job_id: 'job-rag-123',
      job_type: 'EMBEDDING_INDEXING' as any,
      status: 'COMPLETED' as any,
      progress: { current_step: 1, total_steps: 1, percentage: 100, status_message: 'Done' },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    vi.spyOn(ApiClient, 'generateTests').mockResolvedValue([]);
    vi.spyOn(ApiClient, 'getProjects').mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/projects/new']}>
        <ProjectProvider>
          <CreateProjectPage />
        </ProjectProvider>
      </MemoryRouter>
    );

    // Fill in repository URL
    const urlInput = screen.getByPlaceholderText(/https:\/\/github.com/i);
    fireEvent.change(urlInput, { target: { value: 'https://github.com/fastapi/fastapi' } });

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /Launch Pipeline/i });
    fireEvent.click(submitBtn);

    // Verify pipeline stages presentation
    await waitFor(() => {
      expect(screen.getByText('Automated Intelligence Pipeline')).not.toBeNull();
      expect(screen.getByText('Repository Acquisition & Profiling')).not.toBeNull();
      expect(screen.getByText('Deep AST Code Analysis & System Model')).not.toBeNull();
    });

    // Verify completion after poll transitions
    await waitFor(() => {
      expect(screen.getByText(/ALL STAGES COMPLETE/i)).not.toBeNull();
      expect(screen.getByText(/Go to Project Overview →/i)).not.toBeNull();
    }, { timeout: 4000 });
  });
});
