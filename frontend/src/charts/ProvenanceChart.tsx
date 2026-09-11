import React from 'react';

export const ProvenanceChart: React.FC = () => {
  const categories = [
    { label: 'REQUIREMENT_VERIFIED', pct: 45, color: 'bg-emerald-500', desc: 'Directly linked to spec' },
    { label: 'SCHEMA_DERIVED', pct: 30, color: 'bg-blue-500', desc: 'Generated from OpenAPI/AST' },
    { label: 'COVERAGE_ONLY', pct: 15, color: 'bg-amber-500', desc: 'Synthesized for branch coverage' },
    { label: 'AI_INFERRED', pct: 10, color: 'bg-purple-500', desc: 'Edge cases & anomaly models' },
  ];

  return (
    <div className="p-5 rounded-xl bg-sentinel-card border border-sentinel-border space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Test Provenance Distribution</h3>
        <span className="text-xs text-slate-400 font-mono">Enforced Contract</span>
      </div>

      <div className="flex h-3 w-full rounded-full overflow-hidden gap-0.5">
        {categories.map((c) => (
          <div key={c.label} style={{ width: `${c.pct}%` }} className={`${c.color} transition-all`} />
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        {categories.map((c) => (
          <div key={c.label} className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800 text-xs">
            <div className="flex items-center justify-between font-mono">
              <span className="text-slate-300 font-semibold">{c.label}</span>
              <span className="text-white font-bold">{c.pct}%</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">{c.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
