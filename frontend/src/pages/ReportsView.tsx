import React, { useState, useEffect, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface ReportsViewProps {
  projectId?: string;
}

export const ReportsView: React.FC<ReportsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<{
    project_id: string;
    generated_at: string;
    grade: string;
    health_score: number;
    markdown_content: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getReport(id);
      setReport(data);
    } catch (err: any) {
      console.error('Failed to load report:', err);
      setError(err.message || 'Failed to fetch assurance report.');
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchReport(effectiveProjectId);
    } else {
      setReport(null);
      setError(null);
    }
  }, [effectiveProjectId, fetchReport]);

  const handleDownloadMarkdown = () => {
    if (!report?.markdown_content) return;
    const blob = new Blob([report.markdown_content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `CodeSentinel_Assurance_Report_${effectiveProjectId?.substring(0, 8)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Assurance Reports" />;
  }

  return (
    <div data-testid="reports-view" className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Project Health & Compliance Reports</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Export comprehensive assurance reports combining audits, analytics, and traceability.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchReport(effectiveProjectId)}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition disabled:opacity-50 shadow-lg shadow-blue-500/20"
          >
            {loading ? 'Compiling Report...' : '↻ Refresh Report'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm space-y-2">
          <div className="text-2xl animate-spin">📄</div>
          <div>Aggregating multi-module intelligence report...</div>
        </div>
      )}

      {error && (
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300 font-mono text-xs space-y-3">
          <div className="font-bold text-sm">Failed to Generate Report</div>
          <p>{error}</p>
          <button
            onClick={() => fetchReport(effectiveProjectId)}
            className="px-4 py-2 rounded-lg bg-rose-900 hover:bg-rose-800 text-white font-mono text-xs transition"
          >
            ↻ Retry Generation
          </button>
        </div>
      )}

      {!loading && report && (
        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-base font-bold text-white font-mono">
                  Executive Assurance Report
                </h3>
                <span className="px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/40 text-xs font-mono font-bold">
                  Grade: {report.grade}
                </span>
                <span className="px-2.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-xs font-mono font-bold">
                  Health: {report.health_score}/100
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Project: {report.project_id} • Generated: {new Date(report.generated_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={handleDownloadMarkdown}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition flex items-center gap-2"
            >
              <span>⬇</span> Download Markdown (.md)
            </button>
          </div>

          <div className="p-4 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 space-y-2 border border-slate-800/80 max-h-[500px] overflow-y-auto whitespace-pre-wrap">
            {report.markdown_content}
          </div>
        </div>
      )}
    </div>
  );
};
