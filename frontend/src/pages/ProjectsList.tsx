import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';
import { Project } from '../types';

export const ProjectsList: React.FC = () => {
  const navigate = useNavigate();
  const { projects, selectedProjectId, selectProject, loading, error, refreshProjects } = useProject();

  const handleSelect = (project: Project) => {
    selectProject(project);
    navigate('/dashboard');
  };

  return (
    <div data-testid="projects-list-page" className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Managed Projects & Repositories</h2>
          <p className="text-sm text-slate-400">Onboarded codebases under continuous intelligence monitoring.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshProjects()}
            className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-mono border border-slate-800 transition"
          >
            ↻ Refresh
          </button>
          <Link
            to="/projects/new"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition shadow-lg shadow-blue-500/20"
          >
            + Onboard New Repository
          </Link>
        </div>
      </div>

      {loading && projects.length === 0 && (
        <div className="p-12 text-center text-slate-500 font-mono text-sm">
          Loading onboarded repositories...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-mono">
          Error loading projects: {error}
        </div>
      )}

      {!loading && projects.length === 0 && !error && (
        <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4 max-w-lg mx-auto">
          <div className="text-3xl">📁</div>
          <h3 className="text-base font-bold text-white">No Projects Onboarded Yet</h3>
          <p className="text-xs text-slate-400">
            Get started by onboarding a GitHub repository or uploading a local code archive for automated intelligence analysis.
          </p>
          <Link
            to="/projects/new"
            className="inline-block px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold font-mono transition"
          >
            + Onboard Your First Repository
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {projects.map((p) => {
          const isSelected = p.id === selectedProjectId;
          return (
            <div
              key={p.id}
              className={`p-5 rounded-xl bg-slate-900/80 border transition space-y-3 ${
                isSelected
                  ? 'border-blue-500/70 ring-1 ring-blue-500/40 shadow-lg shadow-blue-500/10'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white font-mono">{p.name}</h3>
                    {isSelected && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/40 text-[10px] font-mono font-bold">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-1">{p.description || p.repository_url}</p>
                </div>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {p.status}
                </span>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-2 border-t border-slate-800/80">
                <div>LOC: <span className="text-white">{p.total_lines_of_code}</span></div>
                <div>Files: <span className="text-white">{p.total_files}</span></div>
                <div>Branch: <span className="text-blue-400">{p.default_branch}</span></div>
                <div>Provider: <span className="text-slate-300">{p.provider}</span></div>
              </div>

              <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-800/50">
                <button
                  onClick={() => handleSelect(p)}
                  className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/40 text-xs font-mono font-semibold transition"
                >
                  {isSelected ? 'Open Overview →' : 'Select & Open →'}
                </button>

                <div className="flex flex-wrap gap-1.5 text-xs font-mono">
                  <button
                    onClick={() => { selectProject(p); navigate('/requirements'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Requirements Matrix"
                  >
                    Reqs
                  </button>
                  <button
                    onClick={() => { selectProject(p); navigate('/tests'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Tests & Lineage"
                  >
                    Tests
                  </button>
                  <button
                    onClick={() => { selectProject(p); navigate('/executions'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Docker Executions"
                  >
                    Execs
                  </button>
                  <button
                    onClick={() => { selectProject(p); navigate('/failures'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Failures & RCA"
                  >
                    Fails
                  </button>
                  <button
                    onClick={() => { selectProject(p); navigate('/audits'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Quality & Security Audits"
                  >
                    Audits
                  </button>
                  <button
                    onClick={() => { selectProject(p); navigate('/analytics'); }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    title="Analytics & Traceability"
                  >
                    Analytics
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
