import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { TestCase } from '../types';
import { ProvenanceBadge } from '../components/ProvenanceBadge';
import { NoProjectSelected } from '../components/NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface TestsViewProps {
  projectId?: string;
}

export const TestsView: React.FC<TestsViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [tests, setTests] = useState<TestCase[]>([]);
  const [selectedTier, setSelectedTier] = useState<string>('ALL');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTests = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getTests(id);
      setTests(data || []);
    } catch (err: any) {
      console.error('Failed to load tests:', err);
      setError(err.message || 'Failed to load test cases.');
      setTests([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveProjectId) {
      fetchTests(effectiveProjectId);
    } else {
      setTests([]);
      setError(null);
    }
  }, [effectiveProjectId, fetchTests]);

  const handleGenerate = async () => {
    if (!effectiveProjectId) return;
    setGenerating(true);
    setError(null);
    try {
      await ApiClient.generateTests(effectiveProjectId);
      await fetchTests(effectiveProjectId);
    } catch (err: any) {
      setError(`Test generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Test Cases & Provenance Lineage" />;
  }

  const filteredTests = selectedTier === 'ALL'
    ? tests
    : tests.filter((t) => t.provenance === selectedTier);

  return (
    <div data-testid="tests-view" className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Test Cases & Provenance Lineage</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Every test case displays an immutable provenance trust badge.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={async () => {
              if (!effectiveProjectId) return;
              setGenerating(true);
              setError(null);
              try {
                await ApiClient.runMutationRun(effectiveProjectId, true);
                await fetchTests(effectiveProjectId);
              } catch (err: any) {
                setError(`Mutation testing failed: ${err.message}`);
              } finally {
                setGenerating(false);
              }
            }}
            disabled={generating}
            className="px-4 py-2 rounded-lg bg-fuchsia-700 hover:bg-fuchsia-600 text-white text-xs font-semibold font-mono transition shadow-lg shadow-fuchsia-700/20 disabled:opacity-50"
          >
            {generating ? 'Running...' : '⚡ Run Mutation Suite'}
          </button>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition shadow-lg shadow-blue-500/20 disabled:opacity-50"
          >
            {generating ? 'Generating Tiered Tests...' : '+ Generate Tiered Tests'}
          </button>
        </div>
      </div>

      {/* Tier filter */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {['ALL', 'REQUIREMENT_VERIFIED', 'SCHEMA_DERIVED', 'COVERAGE_ONLY', 'AI_INFERRED', 'MUTATION_TARGETED'].map((tier) => (
          <button
            key={tier}
            onClick={() => setSelectedTier(tier)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition shrink-0 ${
              selectedTier === tier
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            {tier === 'ALL' ? 'All Tiers' : tier.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {loading && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading test cases from backend...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-xs font-mono">
          Error: {error}
        </div>
      )}

      {!loading && tests.length === 0 && !error && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
          <div className="text-3xl">🧪</div>
          <h3 className="text-sm font-bold text-white">No Test Cases Generated Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Run the automated tiered test generator to synthesize tests for verified requirements, schemas, and source code.
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition shadow-lg shadow-blue-500/20"
          >
            {generating ? 'Synthesizing...' : 'Synthesize Tiered Tests Now'}
          </button>
        </div>
      )}

      {/* Tests list */}
      <div className="space-y-3">
        {filteredTests.map((tc) => (
          <div
            key={tc.id}
            data-testid="test-case-row"
            className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-mono text-sm font-semibold text-white truncate">
                  {tc.name}
                </span>
                {/* CRITICAL TRUST BADGE: Rendered prominently next to test name */}
                <ProvenanceBadge provenance={tc.provenance} />
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                  {tc.test_type}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-950 text-slate-400 font-mono">
                  Status: {tc.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-1">{tc.description}</p>
              <div className="text-[11px] font-mono text-slate-500">{tc.file_path}</div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-slate-400 sm:border-l sm:border-slate-800 sm:pl-4">
              <div>Runs: <span className="text-white">{tc.execution_count}</span></div>
              <div>Pass: <span className="text-emerald-400">{tc.pass_count}</span></div>
              <div>Fail: <span className="text-rose-400">{tc.fail_count}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
