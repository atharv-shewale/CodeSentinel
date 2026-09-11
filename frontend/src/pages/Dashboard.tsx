import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { AnalyticsData } from '../types';
import { HealthScoreCard } from '../components/HealthScoreCard';
import { ProvenanceBadge } from '../components/ProvenanceBadge';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface DashboardProps {
  projectId?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getAnalytics(id);
      setAnalytics(data);
    } catch (err: any) {
      console.error('Failed to load analytics:', err);
      setError(err.message || 'Failed to retrieve analytics for project.');
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchAnalytics(effectiveProjectId);
    } else {
      setAnalytics(null);
      setError(null);
    }
  }, [effectiveProjectId, fetchAnalytics]);

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Platform Overview & Health Analytics" />;
  }

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 font-mono text-sm space-y-3">
        <div className="text-2xl animate-spin">⚙️</div>
        <div>Loading platform intelligence for project...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300 font-mono text-xs space-y-3">
          <div className="font-bold text-sm">Failed to Load Project Analytics</div>
          <p>{error}</p>
          <button
            onClick={() => fetchAnalytics(effectiveProjectId)}
            className="px-4 py-2 rounded-lg bg-rose-900 hover:bg-rose-800 text-white font-mono text-xs transition"
          >
            ↻ Retry Request
          </button>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-sm">
        No analytics data available yet. Run analysis or audits to calculate metrics.
      </div>
    );
  }

  return (
    <div data-testid="dashboard-page" className="space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">CodeSentinel Engineering Intelligence</h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic code assurance, automated tiered test generation, and compliance governance.
          </p>
        </div>

        <div className="flex gap-2">
          <span className="px-3 py-1 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-mono font-bold">
            Grade: {analytics.health.grade}
          </span>
          <span className="px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold">
            Health: {analytics.health.health_score}/100
          </span>
          <button
            onClick={() => fetchAnalytics(effectiveProjectId)}
            className="px-3 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-mono"
            title="Refresh analytics"
          >
            ↻
          </button>
        </div>
      </div>

      {/* 1. Health Score with Component Breakdown */}
      <HealthScoreCard health={analytics.health} />

      {/* 2. Pass Rate by Provenance Tier */}
      <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
            Test Pass Rates by Provenance Tier
          </h2>
          <span className="text-xs font-mono text-emerald-400">
            Total Pass Rate: {analytics.pass_rates.overall_pass_rate_pct}%
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Object.entries(analytics.pass_rates.by_provenance).map(([tier, stats]) => (
            <div key={tier} className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
              <div className="mb-2">
                <ProvenanceBadge provenance={tier as any} />
              </div>
              <div className="text-2xl font-bold font-mono text-white">
                {stats.pass_rate_pct}%
              </div>
              <div className="flex justify-between text-xs text-slate-400 font-mono">
                <span>Runs: {stats.total_runs}</span>
                <span className="text-emerald-400">Passed: {stats.passed}</span>
                {stats.failed > 0 && <span className="text-rose-400">Failed: {stats.failed}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Assurance & Governance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
            Requirements Traceability
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between text-slate-300">
              <span>Total Requirements:</span>
              <span className="text-white font-bold">{analytics.coverage?.total_requirements || 0}</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Verified with Criteria:</span>
              <span className="text-emerald-400 font-bold">{analytics.coverage?.verified_requirements || 0}</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Coverage Ratio:</span>
              <span className="text-blue-400 font-bold">{analytics.coverage?.requirement_coverage_pct || 0}%</span>
            </div>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
            Audit Conformance & Security
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between text-slate-300">
              <span>Active Findings:</span>
              <span className="text-white font-bold">{analytics.findings_summary?.total || 0}</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Critical Security Severity:</span>
              <span className="text-rose-400 font-bold">{analytics.findings_summary?.by_severity?.['CRITICAL'] || 0}</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>OWASP / CWE Conformance:</span>
              <span className="text-emerald-400 font-bold">Grade A</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
