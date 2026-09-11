import React from 'react';
import { TestProvenance } from '../types';

interface ProvenanceBadgeProps {
  provenance: TestProvenance | 'NONE';
  className?: string;
}

export const PROVENANCE_CONFIG = {
  REQUIREMENT_VERIFIED: {
    label: 'REQUIREMENT VERIFIED',
    shortLabel: 'REQ VERIFIED',
    badgeClass: 'badge-requirement-verified',
    colorClass: 'bg-emerald-950/80 text-emerald-400 border-emerald-500/60 shadow-emerald-950/30',
    dotClass: 'bg-emerald-400',
    description: 'Directly derived 1:1 from acceptance criteria',
  },
  SCHEMA_DERIVED: {
    label: 'SCHEMA DERIVED',
    shortLabel: 'SCHEMA',
    badgeClass: 'badge-schema-derived',
    colorClass: 'bg-sky-950/80 text-sky-400 border-sky-500/60 shadow-sky-950/30',
    dotClass: 'bg-sky-400',
    description: 'Deterministically synthesized from API & DB schemas (0 LLM)',
  },
  COVERAGE_ONLY: {
    label: 'COVERAGE ONLY',
    shortLabel: 'PATH ONLY',
    badgeClass: 'badge-coverage-only',
    colorClass: 'bg-amber-950/80 text-amber-400 border-amber-500/60 shadow-amber-950/30',
    dotClass: 'bg-amber-400',
    description: 'Path execution only; asserts no business correctness claims',
  },
  AI_INFERRED: {
    label: 'AI INFERRED',
    shortLabel: 'AI INFERRED',
    badgeClass: 'badge-ai-inferred',
    colorClass: 'bg-purple-950/80 text-purple-400 border-purple-500/60 shadow-purple-950/30',
    dotClass: 'bg-purple-400',
    description: 'Synthesized via QA agent; flagged for human review',
  },
  MUTATION_TARGETED: {
    label: 'MUTATION TARGETED',
    shortLabel: 'MUTANT KILLER',
    badgeClass: 'badge-mutation-targeted',
    colorClass: 'bg-fuchsia-950/80 text-fuchsia-300 border-fuchsia-500/60 shadow-fuchsia-950/30',
    dotClass: 'bg-fuchsia-400',
    description: 'Synthesized to kill survived code mutants',
  },
  NONE: {
    label: 'UNTESTED GAP',
    shortLabel: 'GAP',
    badgeClass: 'badge-untested-gap',
    colorClass: 'bg-rose-950/80 text-rose-400 border-rose-500/60 shadow-rose-950/30',
    dotClass: 'bg-rose-400',
    description: 'No test case linked to this requirement',
  },
};

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({ provenance, className = '' }) => {
  const config = PROVENANCE_CONFIG[provenance] || PROVENANCE_CONFIG.AI_INFERRED;

  return (
    <span
      data-testid="provenance-badge"
      data-provenance={provenance}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-semibold border shadow-sm transition ${config.badgeClass} ${config.colorClass} ${className}`}
      title={config.description}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
      <span>{config.label}</span>
    </span>
  );
};
