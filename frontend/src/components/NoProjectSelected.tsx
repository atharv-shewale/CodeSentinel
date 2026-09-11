import React from 'react';
import { Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';

interface NoProjectSelectedProps {
  viewName?: string;
}

export const NoProjectSelected: React.FC<NoProjectSelectedProps> = ({ viewName = 'this view' }) => {
  const { projects, selectProject } = useProject();

  return (
    <div
      data-testid="no-project-selected"
      className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center max-w-2xl mx-auto my-12 space-y-6 shadow-xl"
    >
      <div className="w-16 h-16 mx-auto rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-3xl">
        📁
      </div>

      <div className="space-y-2">
        <h2 className="text-xl font-bold text-white tracking-tight">No Project Selected</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          To view <span className="text-blue-400 font-medium">{viewName}</span>, choose an active codebase under
          CodeSentinel monitoring or onboard a new repository.
        </p>
      </div>

      {projects.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 max-w-md mx-auto text-left space-y-2">
          <label className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Select Existing Project:
          </label>
          <div className="space-y-1.5">
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => selectProject(p)}
                className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 hover:border-blue-500/50 border border-slate-800 text-left transition group"
              >
                <div>
                  <div className="text-xs font-bold text-white group-hover:text-blue-400 transition font-mono">
                    {p.name}
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    {p.total_files} files • {p.total_lines_of_code} LOC
                  </div>
                </div>
                <span className="text-xs text-blue-400 font-mono group-hover:translate-x-1 transition">
                  Select →
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        <Link
          to="/projects"
          className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold font-mono border border-slate-700 transition"
        >
          View All Projects
        </Link>
        <Link
          to="/projects/new"
          className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition shadow-lg shadow-blue-500/20"
        >
          + Onboard New Repository
        </Link>
      </div>
    </div>
  );
};
