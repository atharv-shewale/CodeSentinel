import React, { useEffect, useState } from 'react';
import { ApiClient } from '../services/api';
import { Failure } from '../types';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface FailuresViewProps {
  projectId?: string;
}

export const FailuresView: React.FC<FailuresViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [failures, setFailures] = useState<Failure[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFailures = (id: string) => {
    setLoading(true);
    setError(null);
    ApiClient.getFailures(id)
      .then((data) => {
        const list = Array.isArray(data) ? data : (data ? [data] : []);
        setFailures(list);
      })
      .catch((err) => setError(err.message || 'Failed to fetch defect failures'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!effectiveProjectId) {
      setFailures([]);
      return;
    }
    fetchFailures(effectiveProjectId);
  }, [effectiveProjectId]);

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Defect Failures & Root Cause Analysis" />;
  }

  return (
    <div data-testid="failures-view" className="space-y-6">
      <div className="border-b border-slate-800 pb-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Defect Failures & Root Cause Analysis</h2>
          <p className="text-sm text-slate-400 mt-0.5">Correlated defect triage with grounded root-cause explanations.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => effectiveProjectId && fetchFailures(effectiveProjectId)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-mono"
          >
            ↻ Refresh
          </button>
          <span className="text-xs font-mono text-slate-400">Total Failures: {failures.length}</span>
        </div>
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading defect failures...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          Error: {error}
        </div>
      )}

      {!loading && failures.length === 0 && !error && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
          <div className="text-3xl text-emerald-400">✓</div>
          <h3 className="text-sm font-bold text-white">Zero Defect Failures Detected</h3>
          <p className="text-xs text-slate-400">
            All executed test suites in isolated sandboxes completed cleanly without assertions or crashes.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {failures.map((f) => (
          <div key={f.id} className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-950 text-rose-400 border border-rose-800">
                  {f.severity}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {f.category}
                </span>
                <span className="text-xs text-blue-400 font-mono">
                  {f.status}
                </span>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white">{f.title}</h3>
              <p className="text-xs text-rose-300/90 font-mono mt-1 bg-slate-950 p-2 rounded">
                {f.error_message}
              </p>
            </div>

            {f.stack_trace && (
              <details className="text-xs font-mono bg-slate-950/80 rounded border border-slate-800 p-3">
                <summary className="text-slate-400 cursor-pointer hover:text-white">
                  Stack Trace Analysis
                </summary>
                <pre className="mt-2 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {f.stack_trace}
                </pre>
              </details>
            )}

            {f.root_cause && (
              <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-900/40 text-xs font-mono text-blue-300 space-y-1">
                <div className="font-bold text-blue-400">Grounded Root Cause:</div>
                <div>{f.root_cause.summary}</div>
                {f.root_cause.recommended_fix_diff && (
                  <div className="text-emerald-400 pt-1">Fix Diff: {f.root_cause.recommended_fix_diff}</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
