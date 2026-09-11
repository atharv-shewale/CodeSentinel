import React from 'react';

interface Props {
  score: number;
}

export const HealthScoreGauge: React.FC<Props> = ({ score }) => {
  return (
    <div className="p-5 rounded-xl bg-sentinel-card border border-sentinel-border flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-slate-400 uppercase">Architecture Health</span>
        <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">Grade A</span>
      </div>
      <div className="my-4 flex items-baseline gap-2">
        <span className="text-4xl font-bold tracking-tight text-white">{score}</span>
        <span className="text-slate-500 font-mono text-sm">/ 100</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-emerald-500 to-blue-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${score}%` }}
        ></div>
      </div>
    </div>
  );
};
