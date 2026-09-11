import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { AuditFinding } from '../types';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface AuditsViewProps {
  projectId?: string;
}

export const AuditsView: React.FC<AuditsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [findings, setFindings] = useState<AuditFinding[]>([]);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(false);
  const [runningAudit, setRunningAudit] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFindings = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getFindings(id);
      setFindings(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch audit findings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchFindings(effectiveProjectId);
    } else {
      setFindings([]);
      setError(null);
    }
  }, [effectiveProjectId, fetchFindings]);

  const handleRunAudit = async () => {
    if (!effectiveProjectId) return;
    setRunningAudit(true);
    setError(null);
    try {
      const results = await ApiClient.runAudit(effectiveProjectId);
      setFindings(results || []);
    } catch (err: any) {
      setError(`Audit execution failed: ${err.message}`);
    } finally {
      setRunningAudit(false);
    }
  };

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Code Quality & Security Audits" />;
  }

  const filtered = selectedSeverity === 'ALL'
    ? findings
    : findings.filter((f) => f.severity === selectedSeverity);

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-950/80 text-rose-400 border-rose-600/60';
      case 'HIGH':
        return 'bg-amber-950/80 text-amber-400 border-amber-600/60';
      case 'MEDIUM':
        return 'bg-yellow-950/80 text-yellow-400 border-yellow-600/60';
      default:
        return 'bg-blue-950/80 text-blue-400 border-blue-600/60';
    }
  };

  return (
    <div data-testid="audits-view" className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Code Quality & Security Audits</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Deterministic AST rules, secrets scanner, dependency advisories, and architecture drift checks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAudit}
            disabled={runningAudit}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono disabled:opacity-50 transition shadow-lg shadow-blue-500/20"
          >
            {runningAudit ? 'Scanning AST Rules...' : '+ Run Comprehensive Audit'}
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
          <button
            key={sev}
            onClick={() => setSelectedSeverity(sev)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition shrink-0 ${
              selectedSeverity === sev
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading audit findings...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          {error}
        </div>
      )}

      {!loading && findings.length === 0 && !error && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
          <div className="text-3xl">🛡️</div>
          <h3 className="text-sm font-bold text-white">No Audit Findings Detected</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Click "+ Run Comprehensive Audit" to perform static AST analysis for planted secrets, cyclomatic complexity, and CVEs.
          </p>
          <button
            onClick={handleRunAudit}
            disabled={runningAudit}
            className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition shadow-lg shadow-blue-500/20"
          >
            {runningAudit ? 'Scanning...' : 'Execute Audit Scan Now'}
          </button>
        </div>
      )}

      <div className="space-y-4">
        {filtered.map((f) => (
          <div key={f.id} className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold border ${getSeverityBadge(f.severity)}`}>
                  {f.severity}
                </span>
                <span className="font-mono text-xs text-blue-400 font-bold">{f.rule_id}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {f.category}
                </span>
              </div>
              <span className="text-xs text-slate-500 font-mono">{f.standard}</span>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-white">{f.title}</h3>
              <p className="text-xs text-slate-400 mt-1">{f.description}</p>
            </div>

            <div className="p-2.5 rounded bg-slate-950 font-mono text-xs text-slate-300 flex items-center justify-between">
              <span className="text-slate-400">
                Location: <span className="text-white">{f.location.file_path}</span> (Lines {f.location.start_line}-{f.location.end_line})
              </span>
              <span className="text-emerald-400">Deterministic Rule</span>
            </div>

            {f.remediation_suggestion && (
              <div className="text-xs font-mono text-slate-300 bg-emerald-950/20 border border-emerald-900/30 p-2.5 rounded">
                <span className="text-emerald-400 font-bold">Remediation: </span>
                {f.remediation_suggestion}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
