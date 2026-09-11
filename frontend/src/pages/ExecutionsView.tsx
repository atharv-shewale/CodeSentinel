import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { TestExecution } from '../types';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface ExecutionsViewProps {
  projectId?: string;
}

export const ExecutionsView: React.FC<ExecutionsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [runs, setRuns] = useState<TestExecution[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [runningSuite, setRunningSuite] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback((id: string) => {
    setLoading(true);
    setError(null);
    ApiClient.getExecutions(id)
      .then((data) => setRuns(data || []))
      .catch((err) => setError(err.message || 'Failed to fetch test executions'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchRuns(effectiveProjectId);
    } else {
      setRuns([]);
      setError(null);
    }
  }, [effectiveProjectId, fetchRuns]);

  const handleRunExecution = async () => {
    if (!effectiveProjectId) return;
    try {
      setRunningSuite(true);
      setError(null);
      await ApiClient.runExecution(effectiveProjectId);
      fetchRuns(effectiveProjectId);
    } catch (err: any) {
      setError(`Sandbox execution trigger failed: ${err.message}`);
    } finally {
      setRunningSuite(false);
    }
  };

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Docker Sandbox Executions" />;
  }

  return (
    <div data-testid="executions-view" className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Docker Sandbox Executions</h2>
          <p className="text-sm text-slate-400 mt-0.5">Isolated ephemeral test execution history and telemetry.</p>
        </div>
        <button
          onClick={handleRunExecution}
          disabled={runningSuite}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono disabled:opacity-50 transition shadow-lg shadow-blue-500/20"
        >
          {runningSuite ? 'Executing in Container...' : '+ Run Sandbox Suite'}
        </button>
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading execution history...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          {error}
        </div>
      )}

      {!loading && runs.length === 0 && !error && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
          <div className="text-3xl">⚡</div>
          <h3 className="text-sm font-bold text-white">No Executions Run Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Dispatch test suites into hardened, ephemeral Docker sandboxes with zero-network isolation.
          </p>
          <button
            onClick={handleRunExecution}
            disabled={runningSuite}
            className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition"
          >
            {runningSuite ? 'Executing...' : 'Dispatch Sandbox Run Now'}
          </button>
        </div>
      )}

      <div className="space-y-3">
        {runs.map((r) => (
          <div
            key={r.id}
            className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-3"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm font-semibold text-white">{r.id.substring(0, 8)}...</span>
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold border ${
                    r.status === 'PASSED'
                      ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                      : r.status === 'FAILED'
                      ? 'bg-rose-950 text-rose-400 border-rose-800'
                      : 'bg-amber-950 text-amber-400 border-amber-800'
                  }`}
                >
                  {r.status}
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  {r.created_at ? new Date(r.created_at).toLocaleString() : ''}
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-300">
                <div>Total: <span className="text-white font-bold">{r.total_tests}</span></div>
                <div>Passed: <span className="text-emerald-400 font-bold">{r.passed_tests}</span></div>
                <div>Failed: <span className="text-rose-400 font-bold">{r.failed_tests}</span></div>
                <div>Duration: <span className="text-white">{r.duration_ms || 0}ms</span></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
