import React from 'react';
import { TestProvenance } from '../types';

interface Props {
  provenance: TestProvenance;
}

export const ContractBadge: React.FC<Props> = ({ provenance }) => {
  const styles: Record<TestProvenance, { bg: string; text: string; label: string }> = {
    REQUIREMENT_VERIFIED: {
      bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      text: 'Verified by Spec',
      label: 'REQUIREMENT_VERIFIED',
    },
    SCHEMA_DERIVED: {
      bg: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
      text: 'OpenAPI / Schema',
      label: 'SCHEMA_DERIVED',
    },
    COVERAGE_ONLY: {
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      text: 'Branch Coverage',
      label: 'COVERAGE_ONLY',
    },
    AI_INFERRED: {
      bg: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
      text: 'AI Inferred Heuristic',
      label: 'AI_INFERRED',
    },
    MUTATION_TARGETED: {
      bg: 'bg-fuchsia-500/10 border-fuchsia-500/30 text-fuchsia-400',
      text: 'Mutant Killer',
      label: 'MUTATION_TARGETED',
    },
  };

  const current = styles[provenance] || styles.AI_INFERRED;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${current.bg}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {current.label}
    </span>
  );
};
