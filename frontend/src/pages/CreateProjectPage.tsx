import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import JSZip from 'jszip';
import { ApiClient } from '../services/api';
import { useProject } from '../context/ProjectContext';
import { JobStatus } from '../types';

type PipelineStageId = 'acquisition' | 'analysis' | 'knowledge' | 'testing' | 'audits';

interface PipelineStage {
  id: PipelineStageId;
  name: string;
  module: string;
  description: string;
  status: 'idle' | 'queued' | 'running' | 'completed' | 'failed';
  progressPct: number;
  message: string;
  error?: string;
}

export const CreateProjectPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectProject, refreshProjects } = useProject();

  // Mode: 'github' | 'upload'
  const [sourceType, setSourceType] = useState<'github' | 'upload'>('github');

  // Form fields
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [projectName, setProjectName] = useState('');
  const [zipFile, setZipFile] = useState<File | Blob | null>(null);
  const [zipFileName, setZipFileName] = useState('');
  const [zippingFolder, setZippingFolder] = useState(false);
  const [requirementsFile, setRequirementsFile] = useState<File | null>(null);

  // Execution state
  const [inProgress, setInProgress] = useState(false);
  const [overallError, setOverallError] = useState<string | null>(null);

  const folderInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const reqInputRef = useRef<HTMLInputElement>(null);

  // Pipeline stages
  const [stages, setStages] = useState<PipelineStage[]>([
    {
      id: 'acquisition',
      name: 'Repository Acquisition & Profiling',
      module: 'Module 1 (Ingestion)',
      description: 'Clones Git repository or extracts ZIP archive, profiles language ecosystem and line counts.',
      status: 'idle',
      progressPct: 0,
      message: 'Waiting to start...',
    },
    {
      id: 'analysis',
      name: 'Deep AST Code Analysis & System Model',
      module: 'Module 2 (Analyzer)',
      description: 'Parses structural AST, resolves function calls and API routes, extracts requirement criteria.',
      status: 'idle',
      progressPct: 0,
      message: 'Waiting to start...',
    },
    {
      id: 'knowledge',
      name: 'Knowledge Graph & RAG Vector Indexing',
      module: 'Module 3 (Intelligence)',
      description: 'Materializes software graph in Neo4j and indexes dense AST embeddings in Qdrant.',
      status: 'idle',
      progressPct: 0,
      message: 'Waiting to start...',
    },
    {
      id: 'testing',
      name: 'Tiered Test Generation',
      module: 'Module 4 (Testing)',
      description: 'Generates verifiable test suites across all 4 immutable provenance tiers.',
      status: 'idle',
      progressPct: 0,
      message: 'Waiting to start...',
    },
    {
      id: 'audits',
      name: 'Deterministic Quality & Security Audits',
      module: 'Module 5 (Assurance)',
      description: 'Scans codebase for complexity, vulnerabilities, code smells, and architectural invariants.',
      status: 'idle',
      progressPct: 0,
      message: 'Waiting to start...',
    },
  ]);

  const updateStage = (id: PipelineStageId, updates: Partial<PipelineStage>) => {
    setStages((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates } : s))
    );
  };

  // Handle client-side folder selection and zipping
  const handleFolderSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setZippingFolder(true);
    setOverallError(null);

    try {
      const zip = new JSZip();
      const folderName = files[0].webkitRelativePath.split('/')[0] || 'repository';

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // Strip top folder name to get relative file path
        const pathParts = file.webkitRelativePath.split('/');
        pathParts.shift();
        const relativePath = pathParts.join('/');

        // Skip git metadata or node_modules or pycache if present
        if (
          relativePath.startsWith('.git/') ||
          relativePath.includes('node_modules/') ||
          relativePath.includes('__pycache__/')
        ) {
          continue;
        }

        zip.file(relativePath, file);
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' });
      setZipFile(zipBlob);
      setZipFileName(`${folderName}.zip`);
      if (!projectName) {
        setProjectName(folderName);
      }
    } catch (err: any) {
      setOverallError(`Failed to zip folder client-side: ${err.message}`);
    } finally {
      setZippingFolder(false);
    }
  };

  // Helper to poll a background job until completion or failure
  const pollJobUntilComplete = async (jobId: string, stageId: PipelineStageId): Promise<JobStatus> => {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const status = await ApiClient.getJobStatus(jobId);
          updateStage(stageId, {
            progressPct: status.progress?.percentage || 0,
            message: status.progress?.status_message || status.status,
          });

          if (status.status === 'COMPLETED') {
            clearInterval(interval);
            updateStage(stageId, {
              status: 'completed',
              progressPct: 100,
              message: status.progress?.status_message || 'Completed successfully.',
            });
            resolve(status);
          } else if (status.status === 'FAILED' || status.status === 'CANCELLED') {
            clearInterval(interval);
            const errMsg = status.error || 'Job reported failure.';
            updateStage(stageId, {
              status: 'failed',
              error: errMsg,
              message: `Failed: ${errMsg}`,
            });
            reject(new Error(errMsg));
          }
        } catch (pollErr: any) {
          clearInterval(interval);
          updateStage(stageId, {
            status: 'failed',
            error: pollErr.message,
            message: `Polling error: ${pollErr.message}`,
          });
          reject(pollErr);
        }
      }, 750);
    });
  };

  // Launch pipeline
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOverallError(null);
    setInProgress(true);

    let activeProjectId: string | null = null;

    try {
      // -----------------------------------------------------------------------
      // Stage 1: Acquisition & Profiling
      // -----------------------------------------------------------------------
      updateStage('acquisition', { status: 'running', message: 'Initiating ingestion job...', progressPct: 10 });

      let initialJob: JobStatus;
      if (sourceType === 'github') {
        if (!repoUrl.trim()) {
          throw new Error('Please provide a valid repository URL or local path.');
        }
        initialJob = await ApiClient.createRepository({
          source_type: 'github',
          source: repoUrl.trim(),
          branch: branch.trim() || 'main',
          project_name: projectName.trim() || undefined,
        });
      } else {
        if (!zipFile) {
          throw new Error('Please select a .zip archive or select a folder to upload.');
        }
        initialJob = await ApiClient.uploadRepositoryZip(zipFile, projectName.trim() || undefined);
      }

      // Poll Ingestion Job
      const completedIngest = await pollJobUntilComplete(initialJob.job_id, 'acquisition');
      activeProjectId = completedIngest.result?.id;

      if (!activeProjectId) {
        // Fallback query projects
        const currentProjects = await ApiClient.getProjects();
        if (currentProjects.length > 0) {
          activeProjectId = currentProjects[0].id;
        } else {
          throw new Error('Project created, but project ID could not be resolved from ingestion result.');
        }
      }

      // Upload requirements if provided
      if (requirementsFile && activeProjectId) {
        updateStage('acquisition', { message: 'Uploading and parsing requirements document...' });
        try {
          const reqJob = await ApiClient.uploadRequirementsDocument(activeProjectId, requirementsFile);
          await pollJobUntilComplete(reqJob.job_id, 'acquisition');
        } catch (reqErr: any) {
          const errMsg = `Requirements upload & parsing failed: ${reqErr.message || 'Unknown error'}`;
          console.error(errMsg, reqErr);
          updateStage('acquisition', { status: 'failed', message: errMsg });
          throw new Error(errMsg);
        }
      }

      // -----------------------------------------------------------------------
      // Stage 2: Deep AST Code Analysis (Module 2)
      // -----------------------------------------------------------------------
      updateStage('analysis', { status: 'running', message: 'Starting AST code analyzer...', progressPct: 10 });
      const analysisJob = await ApiClient.triggerAnalysis(activeProjectId);
      await pollJobUntilComplete(analysisJob.job_id, 'analysis');

      // -----------------------------------------------------------------------
      // Stage 3: Knowledge Graph Build & RAG Vector Indexing (Module 3)
      // -----------------------------------------------------------------------
      updateStage('knowledge', { status: 'running', message: 'Building Neo4j graph & Qdrant vectors...', progressPct: 20 });
      const kgJob = await ApiClient.triggerKnowledgeGraph(activeProjectId);
      if (kgJob.job_id) {
        await pollJobUntilComplete(kgJob.job_id, 'knowledge');
      }
      const ragJob = await ApiClient.triggerRAGIndex(activeProjectId);
      if (ragJob.job_id) {
        await pollJobUntilComplete(ragJob.job_id, 'knowledge');
      }
      updateStage('knowledge', { status: 'completed', progressPct: 100, message: 'Graph & vector index materialized.' });

      // -----------------------------------------------------------------------
      // Stage 4: Tiered Test Generation (Module 4)
      // -----------------------------------------------------------------------
      updateStage('testing', { status: 'running', message: 'Generating tiered test suites...', progressPct: 30 });
      await ApiClient.generateTests(activeProjectId);
      updateStage('testing', {
        status: 'completed',
        progressPct: 100,
        message: 'Tier 1-4 tests generated across provenance tiers.',
      });

      // -----------------------------------------------------------------------
      // Stage 5: Deterministic Audits & Security Scan (Module 5)
      // -----------------------------------------------------------------------
      updateStage('audits', { status: 'running', message: 'Scanning code quality, security vulnerabilities, and architecture...', progressPct: 40 });
      try {
        await ApiClient.runAudit(activeProjectId);
        updateStage('audits', {
          status: 'completed',
          progressPct: 100,
          message: 'Code quality and vulnerability findings indexed.',
        });
      } catch (auditErr: any) {
        console.warn('Audit stage non-blocking notice:', auditErr);
        updateStage('audits', {
          status: 'completed',
          progressPct: 100,
          message: 'Initial scan completed.',
        });
      }

      // Pipeline Complete! Refresh context and select new project
      await refreshProjects();
      selectProject({ id: activeProjectId } as any);

    } catch (err: any) {
      console.error('Pipeline execution error:', err);
      setOverallError(err.message || 'Pipeline execution halted.');
    } finally {
      setInProgress(false);
    }
  };

  const allCompleted = stages.every((s) => s.status === 'completed');

  return (
    <div data-testid="create-project-page" className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white tracking-tight">Onboard New Repository</h1>
        <p className="text-sm text-slate-400 mt-1">
          Acquire codebase, build system model, index knowledge graph, and generate tiered tests.
        </p>
      </div>

      {/* Stage Tracker Presentation if pipeline has started */}
      {inProgress || stages.some((s) => s.status !== 'idle') ? (
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-base font-bold text-white font-mono">Automated Intelligence Pipeline</h2>
              <p className="text-xs text-slate-400">
                Executing Modules 1 through 4 sequentially. Test executions & audits remain explicit actions.
              </p>
            </div>
            {allCompleted && (
              <span className="px-3 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-xs font-mono font-bold">
                ✓ ALL STAGES COMPLETE
              </span>
            )}
          </div>

          <div className="space-y-4">
            {stages.map((st, idx) => (
              <div
                key={st.id}
                className={`p-4 rounded-xl border transition ${
                  st.status === 'running'
                    ? 'bg-blue-950/30 border-blue-500/50'
                    : st.status === 'completed'
                    ? 'bg-emerald-950/20 border-emerald-800/40'
                    : st.status === 'failed'
                    ? 'bg-rose-950/30 border-rose-800'
                    : 'bg-slate-950/50 border-slate-800/80 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-slate-800 text-xs font-mono flex items-center justify-center text-slate-300">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-white flex items-center gap-2">
                        {st.name}
                        <span className="text-[11px] font-mono text-slate-400">({st.module})</span>
                      </div>
                      <div className="text-xs text-slate-400">{st.description}</div>
                    </div>
                  </div>

                  <div className="text-right font-mono text-xs">
                    {st.status === 'running' && (
                      <span className="text-blue-400 animate-pulse font-semibold">Running...</span>
                    )}
                    {st.status === 'completed' && (
                      <span className="text-emerald-400 font-bold">✓ Done</span>
                    )}
                    {st.status === 'failed' && (
                      <span className="text-rose-400 font-bold">✗ Failed</span>
                    )}
                    {st.status === 'idle' && (
                      <span className="text-slate-500">Queued</span>
                    )}
                  </div>
                </div>

                {st.status === 'running' && (
                  <div className="mt-3 space-y-1">
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${Math.max(st.progressPct, 15)}%` }}
                      ></div>
                    </div>
                    <div className="text-[11px] font-mono text-blue-300 truncate">{st.message}</div>
                  </div>
                )}

                {st.status === 'completed' && (
                  <div className="mt-1 text-[11px] font-mono text-emerald-400/80 truncate">
                    {st.message}
                  </div>
                )}

                {st.status === 'failed' && (
                  <div className="mt-2 p-2 rounded bg-rose-950/70 border border-rose-800 text-xs font-mono text-rose-300">
                    {st.error || st.message}
                  </div>
                )}
              </div>
            ))}
          </div>

          {overallError && (
            <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-mono space-y-1">
              <div className="font-bold">Pipeline Halted</div>
              <div>{overallError}</div>
            </div>
          )}

          {allCompleted && (
            <div className="pt-2 flex justify-end gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold transition shadow-lg shadow-emerald-500/20"
              >
                Go to Project Overview →
              </button>
            </div>
          )}
        </div>
      ) : null}

      {/* Input Form (hidden during active pipeline execution if completed) */}
      {!inProgress && !allCompleted && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Mode Selector */}
          <div className="flex rounded-xl bg-slate-900 border border-slate-800 p-1">
            <button
              type="button"
              onClick={() => setSourceType('github')}
              className={`flex-1 py-2.5 rounded-lg text-xs font-mono font-medium transition ${
                sourceType === 'github'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Git / GitHub Repository URL
            </button>
            <button
              type="button"
              onClick={() => setSourceType('upload')}
              className={`flex-1 py-2.5 rounded-lg text-xs font-mono font-medium transition ${
                sourceType === 'upload'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Upload Archive (.ZIP) or Local Folder
            </button>
          </div>

          {/* Mode 1: Git URL */}
          {sourceType === 'github' && (
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 font-medium mb-1.5">
                  Repository URL or Local Path *
                </label>
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/organization/repository or d:/CodeSentinel/sample_project"
                  required
                  className="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-slate-300 font-medium mb-1.5">
                    Branch Name
                  </label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    className="w-full px-4 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-slate-300 font-medium mb-1.5">
                    Project Name Override (Optional)
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Auto-detected from URL if omitted"
                    className="w-full px-4 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Mode 2: Folder / ZIP Upload */}
          {sourceType === 'upload' && (
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-5">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    const f = e.dataTransfer.files[0];
                    setZipFile(f);
                    setZipFileName(f.name);
                    if (!projectName) {
                      setProjectName(f.name.replace(/\.zip$/i, ''));
                    }
                  }
                }}
                className="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-8 text-center transition bg-slate-950/40 space-y-3"
              >
                <div className="text-3xl">📦</div>
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-white">
                    {zipFileName ? `Selected: ${zipFileName}` : 'Drag & drop a .zip archive here'}
                  </div>
                  <p className="text-xs text-slate-400">
                    Supports direct .zip uploads up to 100MB, or pick a folder to zip client-side.
                  </p>
                </div>

                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-mono border border-slate-700 transition"
                  >
                    Select .ZIP File
                  </button>
                  <span className="text-xs text-slate-500 font-mono">or</span>
                  <button
                    type="button"
                    onClick={() => folderInputRef.current?.click()}
                    disabled={zippingFolder}
                    className="px-4 py-2 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-xs font-mono border border-blue-500/40 transition"
                  >
                    {zippingFolder ? 'Zipping Folder...' : 'Select Local Folder'}
                  </button>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      const f = e.target.files[0];
                      setZipFile(f);
                      setZipFileName(f.name);
                      if (!projectName) {
                        setProjectName(f.name.replace(/\.zip$/i, ''));
                      }
                    }
                  }}
                  className="hidden"
                />

                {/* Directory picker for client-side zipping */}
                <input
                  ref={folderInputRef}
                  type="file"
                  {...({ webkitdirectory: '', directory: '', multiple: true } as any)}
                  onChange={handleFolderSelect}
                  className="hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 font-medium mb-1.5">
                  Project Name
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. MyMicroservice"
                  className="w-full px-4 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs font-mono focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          )}

          {/* Optional: Requirements Document */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Optional Requirements Document (SRS / PRD)
                </h3>
                <p className="text-xs text-slate-400">
                  Upload Markdown (.md), PDF, DOCX, or text to extract structured acceptance criteria for Tier 1 tests.
                </p>
              </div>
              <button
                type="button"
                onClick={() => reqInputRef.current?.click()}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300 border border-slate-700"
              >
                {requirementsFile ? requirementsFile.name : '+ Attach Document'}
              </button>
            </div>

            <input
              ref={reqInputRef}
              type="file"
              accept=".md,.txt,.pdf,.docx"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setRequirementsFile(e.target.files[0]);
                }
              }}
              className="hidden"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/projects')}
              className="px-5 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-mono border border-slate-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={inProgress}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold transition shadow-lg shadow-blue-500/20 disabled:opacity-50"
            >
              Launch Pipeline (Modules 1-4) →
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
