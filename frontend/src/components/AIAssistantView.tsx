import React, { useState } from 'react';
import { ApiClient } from '../services/api';
import { AIAssistantResponse } from '../types';
import { NoProjectSelected } from './NoProjectSelected';
import { useProject } from '../context/ProjectContext';

interface AIAssistantViewProps {
  projectId?: string;
}

export const AIAssistantView: React.FC<AIAssistantViewProps> = ({ projectId: propProjectId }) => {
  const { selectedProjectId: contextProjectId } = useProject();
  const effectiveProjectId = propProjectId || contextProjectId;

  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AIAssistantResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !effectiveProjectId) return;

    setLoading(true);
    try {
      const res = await ApiClient.askAssistant(effectiveProjectId, question);
      setResponse(res);
    } catch (err) {
      console.error('Failed to ask assistant:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!effectiveProjectId) {
    return <NoProjectSelected viewName="Grounded AI Assistant" />;
  }

  return (
    <div data-testid="ai-assistant-view" className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">CodeSentinel Engineering Assistant</h2>
        <p className="text-sm text-slate-400 mt-1">
          Grounded QA agent querying knowledge graph and AST index. Speculation without code citations is rejected.
        </p>
      </div>

      {/* Query input form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <input
            data-testid="ai-question-input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about architectural rules, verified requirements, or test coverage..."
            className="flex-1 px-4 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono text-sm"
          />
          <button
            data-testid="ai-submit-button"
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition disabled:opacity-50"
          >
            {loading ? 'Querying...' : 'Ask Assistant'}
          </button>
        </div>
      </form>

      {/* Assistant Response Presentation */}
      {response && (
        <div data-testid="ai-response-container" className="space-y-4">
          {/* Grounding Warning Banner: CRITICAL TRUST SIGNAL */}
          {!response.is_grounded ? (
            <div
              data-testid="ungrounded-warning-banner"
              className="p-4 rounded-xl bg-amber-950/70 border-2 border-amber-500/80 text-amber-200 space-y-2 shadow-lg animate-pulse"
            >
              <div className="flex items-center gap-2 font-bold text-amber-300 uppercase tracking-wide text-xs">
                <span>⚠️</span>
                <span>UNGROUNDED SPECULATION WARNING</span>
              </div>
              <p className="text-xs text-amber-200/90 leading-relaxed">
                This response could not be grounded in verified repository code entities or acceptance criteria.
                Treat as unverified conjecture; do not use for architectural decisions.
              </p>
            </div>
          ) : (
            <div
              data-testid="grounded-trust-badge"
              className="p-3 rounded-lg bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 flex items-center justify-between text-xs"
            >
              <div className="flex items-center gap-2 font-semibold">
                <span>🛡️</span>
                <span>VERIFIED & GROUNDED IN CODE EVIDENCE</span>
              </div>
              <span className="font-mono text-emerald-400">
                Confidence: {(response.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Answer Text */}
          <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
              {response.answer}
            </div>

            {/* Citations List */}
            {((response.citations && response.citations.length > 0) || (response.cited_evidence && response.cited_evidence.length > 0)) && (
              <div className="pt-4 border-t border-slate-800 space-y-2">
                <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                  Grounding Evidence Citations:
                </div>
                <div className="flex flex-wrap gap-2">
                  {(response.citations || response.cited_evidence?.map((c) => c.identifier) || []).map((cite: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300 font-mono text-xs"
                    >
                      📎 {cite}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
