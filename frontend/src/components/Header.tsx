import React from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';

export const Header: React.FC = () => {
  const { projects, selectedProjectId, setSelectedProjectId } = useProject();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-6">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-emerald-400 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20 group-hover:scale-105 transition">
            CS
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-tight">CodeSentinel</h1>
            <p className="text-[11px] text-slate-400 font-mono">Software Engineering Intelligence</p>
          </div>
        </Link>

        {/* Global Project Switcher */}
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-slate-800">
          <span className="text-xs font-mono text-slate-500">Project:</span>
          <select
            value={selectedProjectId || ''}
            onChange={(e) => setSelectedProjectId(e.target.value || null)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-xs font-mono rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500 max-w-[220px] truncate"
          >
            <option value="">-- No Project Selected --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.default_branch})
              </option>
            ))}
          </select>
          <Link
            to="/projects/new"
            className="text-xs font-mono text-blue-400 hover:text-blue-300 font-bold px-2 py-1 rounded bg-blue-500/10 border border-blue-500/30"
          >
            + New
          </Link>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          SERVICES HEALTHY
        </div>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-sm font-mono"
        >
          API /docs
        </a>
      </div>
    </header>
  );
};
