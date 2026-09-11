import React from 'react';
import { HealthScoreData } from '../types';

interface HealthScoreCardProps {
  health: HealthScoreData;
}

export const HealthScoreCard: React.FC<HealthScoreCardProps> = ({ health }) => {
  const { health_score, grade, formula, components } = health;

  const getGradeBadge = (g: string) => {
    switch (g) {
      case 'A':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'B':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'C':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
      default:
        return 'bg-rose-500/20 text-rose-400 border-rose-500/50';
    }
  };

  return (
    <div
      data-testid="health-score-card"
      className="p-6 rounded-xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-6"
    >
      {/* Header: Score and Grade */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 font-mono">
            System Health Index
          </h2>
          <p className="text-xs text-slate-500 mt-0.5 font-mono">
            Formula: <span data-testid="health-formula" className="text-slate-400">{formula}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div
            data-testid="health-grade"
            className={`px-3 py-1 rounded-lg text-lg font-bold font-mono border ${getGradeBadge(grade)}`}
          >
            GRADE {grade}
          </div>
          <div
            data-testid="health-score-value"
            className="text-3xl font-extrabold font-mono text-white tracking-tight"
          >
            {health_score}
            <span className="text-sm text-slate-500 font-normal">/100</span>
          </div>
        </div>
      </div>

      {/* Component Breakdown: Guaranteed to display every sub-component */}
      <div data-testid="health-breakdown" className="space-y-3 pt-2 border-t border-slate-800">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
          Score Component Breakdown
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {/* 1. Requirement Coverage */}
          <div data-testid="component-requirement-coverage" className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
              <span>Req Coverage</span>
              <span className="font-mono text-emerald-400 font-semibold">35%</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {components.requirement_coverage.score}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full"
                style={{ width: `${components.requirement_coverage.score}%` }}
              />
            </div>
          </div>

          {/* 2. Requirement Pass Rate */}
          <div data-testid="component-requirement-pass-rate" className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
              <span>Req Pass Rate</span>
              <span className="font-mono text-blue-400 font-semibold">25%</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {components.requirement_pass_rate.score}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-blue-500 h-full rounded-full"
                style={{ width: `${components.requirement_pass_rate.score}%` }}
              />
            </div>
          </div>

          {/* 3. Code Quality */}
          <div data-testid="component-code-quality" className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
              <span>Code Quality</span>
              <span className="font-mono text-indigo-400 font-semibold">15%</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {components.code_quality.score}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full"
                style={{ width: `${components.code_quality.score}%` }}
              />
            </div>
          </div>

          {/* 4. Security Posture */}
          <div data-testid="component-security" className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
              <span>Security</span>
              <span className="font-mono text-purple-400 font-semibold">15%</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {components.security.score}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-purple-500 h-full rounded-full"
                style={{ width: `${components.security.score}%` }}
              />
            </div>
          </div>

          {/* 5. Architecture Health */}
          <div data-testid="component-architecture" className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
              <span>Architecture</span>
              <span className="font-mono text-cyan-400 font-semibold">10%</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {components.architecture.score}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-cyan-500 h-full rounded-full"
                style={{ width: `${components.architecture.score}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
