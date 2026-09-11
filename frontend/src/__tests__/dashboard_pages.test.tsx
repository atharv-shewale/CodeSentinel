import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ApiClient } from '../services/api';
import { RequirementsView } from '../pages/RequirementsView';
import { FailuresView } from '../pages/FailuresView';
import { ExecutionsView } from '../pages/ExecutionsView';
import { Requirement, Failure, TestExecution } from '../types';

describe('Frontend Pages & ApiClient Coverage', () => {
  const sampleProjectId = '11111111-2222-3333-4444-555555555555';

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('ApiClient handles API error envelopes by rejecting with error message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({
        status: 'error',
        data: null,
        message: 'Target project not found.',
        error: { code: 'PROJECT_NOT_FOUND', message: 'Target project not found.' },
        timestamp: '2026-09-03T04:00:00Z',
      }),
    } as Response);

    await expect(ApiClient.getProject(sampleProjectId)).rejects.toThrow('Target project not found.');
  });

  it('RequirementsView renders requirements and handles criteria display cleanly', async () => {
    const mockReqs: Requirement[] = [
      {
        id: 'req-1',
        project_id: sampleProjectId,
        identifier: 'REQ-AUTH-01',
        title: 'Authentication Specification',
        description: 'System must authenticate users.',
        req_type: 'FUNCTIONAL',
        priority: 'HIGH',
        status: 'APPROVED',
        acceptance_criteria: ['Valid token returns 200', 'Invalid token returns 401'],
        linked_entity_ids: [],
        verification_coverage_pct: 100,
        created_at: '2026-09-03T04:00:00Z',
      },
    ];

    vi.spyOn(ApiClient, 'getRequirements').mockResolvedValueOnce(mockReqs);

    render(<RequirementsView projectId={sampleProjectId} />);

    await waitFor(() => {
      expect(screen.getByText('REQ-AUTH-01')).not.toBeNull();
      expect(screen.getByText('Authentication Specification')).not.toBeNull();
      expect(screen.getByText('Valid token returns 200')).not.toBeNull();
    });
  });

  it('FailuresView renders detected test anomalies with severity and title', async () => {
    const mockFailures: Failure[] = [
      {
        id: 'fail-1',
        project_id: sampleProjectId,
        title: 'AssertionError: 401 != 200 during authenticated request',
        category: 'ASSERTION_FAILED',
        severity: 'CRITICAL',
        status: 'DETECTED',
        error_message: 'AssertionError: status code mismatch',
      },
    ];

    vi.spyOn(ApiClient, 'getFailures').mockResolvedValueOnce(mockFailures);

    render(<FailuresView projectId={sampleProjectId} />);

    await waitFor(() => {
      expect(screen.getByText('AssertionError: 401 != 200 during authenticated request')).not.toBeNull();
      expect(screen.getByText('CRITICAL')).not.toBeNull();
    });
  });

  it('ExecutionsView renders test execution runs and pass rates', async () => {
    const mockExecutions: TestExecution[] = [
      {
        id: 'exec-1',
        project_id: sampleProjectId,
        status: 'PASSED',
        total_tests: 10,
        passed_tests: 10,
        failed_tests: 0,
        error_tests: 0,
        duration_ms: 120.5,
        results: [],
        created_at: '2026-09-03T04:00:00Z',
      },
    ];

    vi.spyOn(ApiClient, 'getExecutions').mockResolvedValueOnce(mockExecutions);

    render(<ExecutionsView projectId={sampleProjectId} />);

    await waitFor(() => {
      expect(screen.getByText('PASSED')).not.toBeNull();
      expect(screen.getAllByText('10').length).toBeGreaterThanOrEqual(1);
    });
  });
});
