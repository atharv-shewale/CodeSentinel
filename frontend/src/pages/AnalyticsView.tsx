import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { AnalyticsData, TraceabilityItem } from '../types';
import { HealthScoreCard } from '../components/HealthScoreCard';
import { ProvenanceBadge } from '../components/ProvenanceBadge';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface AnalyticsViewProps {
  projectId?: string;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [traceability, setTraceability] = useState<TraceabilityItem[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'traceability'>('overview');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsData, traceData] = await Promise.all([
        ApiClient.getAnalytics(id),
        ApiClient.getTraceability(id).catch(() => []),
      ]);
      setAnalytics(analyticsData);
      setTraceability(traceData || []);
    } catch (err: any) {
      console.error('Failed to load analytics data:', err);
      setError(err.message || 'Failed to load platform analytics.');
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchData(effectiveProjectId);
    } else {
      setAnalytics(null);
      setTraceability([]);
      setError(null);
    }
  }, [effectiveProjectId, fetchData]);

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Analytics & Traceability Matrix" />;
  }

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 font-mono text-sm">
        Loading platform analytics and traceability matrix...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-300 font-mono text-xs space-y-3">
        <div className="font-bold text-sm">Error Loading Analytics</div>
        <p>{error}</p>
        <button
          onClick={() => fetchData(effectiveProjectId)}
          className="px-4 py-2 rounded-lg bg-rose-900 hover:bg-rose-800 text-white font-mono text-xs transition"
        >
          ↻ Retry Request
        </button>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-sm">
        No analytics data available for this project.
      </div>
    );
  }

  return (
    <div data-testid="analytics-view" className="space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Engineering Intelligence & Traceability</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Transparent quality formulas, tiered pass rates, and end-to-end verification traceability.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
              activeTab === 'overview'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            Health & Pass Rates
          </button>
          <button
            onClick={() => setActiveTab('traceability')}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
              activeTab === 'traceability'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            Traceability Matrix ({traceability.length})
          </button>
        </div>
      </div>

      {activeTab === 'overview' ? (
        <div className="space-y-6">
          {/* Health Score Card with Component Breakdown */}
          <HealthScoreCard health={analytics.health} />

          {/* Tiered Pass Rates */}
          <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                Pass Rate Breakdown by Provenance Tier
              </h3>
              <span className="text-xs font-mono text-emerald-400 font-semibold">
                Overall: {analytics.pass_rates.overall_pass_rate_pct}%
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
                    <span>Passed: {stats.passed}/{stats.total_runs}</span>
                    <span>Failed: {stats.failed}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Traceability Matrix */
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-400">
            Bi-directional traceability: connects business requirements to verified test suites, coverage, and execution status.
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/80">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-4">Requirement ID</th>
                  <th className="p-4">Criteria</th>
                  <th className="p-4">Linked Test Cases</th>
                  <th className="p-4">Provenance</th>
                  <th className="p-4">Execution Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {traceability.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500">
                      No traceability linkages established yet. Ensure requirements have acceptance criteria.
                    </td>
                  </tr>
                ) : (
                  traceability.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/40 transition">
                      <td className="p-4 font-bold text-blue-400">{item.requirement_identifier}</td>
                      <td className="p-4 text-slate-300 max-w-xs truncate">{item.requirement_title || item.entity_name}</td>
                      <td className="p-4 text-white font-semibold">{item.test_name || 'Untested'}</td>
                      <td className="p-4">
                        {item.provenance ? (
                          <ProvenanceBadge provenance={item.provenance} />
                        ) : (
                          <span className="text-rose-400 font-mono">UNVERIFIED</span>
                        )}
                      </td>
                      <td className="p-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                            item.execution_status === 'PASSED'
                              ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                              : item.execution_status === 'FAILED'
                              ? 'bg-rose-950 text-rose-400 border-rose-800'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {item.execution_status || 'NOT RUN'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
