import React, { useEffect, useState } from 'react';
import { ApiClient } from '../services/api';
import { Requirement } from '../types';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface RequirementsViewProps {
  projectId?: string;
}

export const RequirementsView: React.FC<RequirementsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!effectiveProjectId) {
      setRequirements([]);
      return;
    }
    setLoading(true);
    setError(null);
    ApiClient.getRequirements(effectiveProjectId)
      .then((data) => setRequirements(data || []))
      .catch((err) => setError(err.message || 'Failed to load requirements'))
      .finally(() => setLoading(false));
  }, [effectiveProjectId]);

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Structured Requirements & Criteria" />;
  }

  return (
    <div data-testid="requirements-view" className="space-y-6">
      <div className="border-b border-slate-800 pb-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Structured Requirements & Criteria</h2>
          <p className="text-sm text-slate-400 mt-0.5">Specifications driving 1:1 Tier 1 requirement-verified tests.</p>
        </div>
        <span className="text-xs font-mono text-slate-400">Total: {requirements.length}</span>
      </div>

      {loading && (
        <div className="p-8 text-center text-slate-500 font-mono text-sm">
          Loading requirements from backend...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          Error: {error}
        </div>
      )}

      {!loading && requirements.length === 0 && !error && (
        <div className="p-8 text-center text-slate-500 font-mono text-sm">
          No requirements found for this project. Upload an SRS or requirements markdown document.
        </div>
      )}

      <div className="space-y-4">
        {requirements.map((r) => (
          <div key={r.id} className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-sm font-bold text-blue-400">{r.identifier}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                  {r.req_type}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-rose-950 text-rose-400 font-mono">
                  {r.priority}
                </span>
              </div>
              <span className="text-xs text-emerald-400 font-mono">Status: {r.status}</span>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white">{r.title}</h3>
              <p className="text-xs text-slate-400 mt-1">{r.description}</p>
            </div>

            {r.acceptance_criteria && r.acceptance_criteria.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                  Acceptance Criteria ({r.acceptance_criteria.length}):
                </div>
                <ul className="space-y-1 text-xs text-slate-300 font-mono">
                  {r.acceptance_criteria.map((c, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
