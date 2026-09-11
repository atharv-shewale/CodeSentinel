import React from 'react';
import { NavLink } from 'react-router-dom';
import { useProject } from '../context/ProjectContext';

export const Sidebar: React.FC = () => {
  const { selectedProject } = useProject();

  const navItems = [
    { id: 'dashboard', path: '/dashboard', label: 'Overview', icon: '📊' },
    { id: 'projects', path: '/projects', label: 'Projects', icon: '📁' },
    { id: 'requirements', path: '/requirements', label: 'Requirements', icon: '📋' },
    { id: 'tests', path: '/tests', label: 'Tests & Lineage', icon: '🧪' },
    { id: 'executions', path: '/executions', label: 'Executions', icon: '⚡' },
    { id: 'failures', path: '/failures', label: 'Failures & RCA', icon: '🐞' },
    { id: 'audits', path: '/audits', label: 'Audits & Quality', icon: '🛡️' },
    { id: 'analytics', path: '/analytics', label: 'Analytics & Matrix', icon: '📈' },
    { id: 'reports', path: '/reports', label: 'Assurance Reports', icon: '📑' },
    { id: 'assistant', path: '/assistant', label: 'AI Assistant', icon: '🤖' },
    { id: 'contracts', path: '/contracts', label: 'Frozen Schemas', icon: '📜' },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950 p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider font-mono flex items-center justify-between">
          <span>Navigation</span>
          <NavLink
            to="/projects/new"
            className="text-[10px] text-blue-400 hover:text-blue-300 font-mono font-bold bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/30"
          >
            + New
          </NavLink>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.id}
              to={item.path}
              data-testid={`nav-${item.id}`}
              className={({ isActive }) =>
                `w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium font-mono transition ${
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                }`
              }
            >
              <span className="text-sm">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="space-y-3">
        {selectedProject ? (
          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-mono space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Selected Project</div>
            <div className="font-bold text-white truncate">{selectedProject.name}</div>
            <div className="text-[11px] text-emerald-400">{selectedProject.default_branch} • {selectedProject.total_files} files</div>
          </div>
        ) : (
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/40 text-xs font-mono space-y-1 text-amber-300">
            <div className="font-bold">No Project Active</div>
            <div className="text-[11px] text-amber-400/80">Select or onboard a repository to enable project views.</div>
          </div>
        )}

        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-1 font-mono">
          <div className="font-semibold text-slate-200">Trust Invariants</div>
          <div>Provenance: <span className="text-emerald-400">Enforced</span></div>
          <div>Grounding: <span className="text-blue-400">Strict</span></div>
        </div>
      </div>
    </aside>
  );
};
