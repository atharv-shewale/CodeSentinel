import { Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { ProjectsList } from './pages/ProjectsList';
import { CreateProjectPage } from './pages/CreateProjectPage';
import { RequirementsView } from './pages/RequirementsView';
import { TestsView } from './pages/TestsView';
import { ExecutionsView } from './pages/ExecutionsView';
import { FailuresView } from './pages/FailuresView';
import { AuditsView } from './pages/AuditsView';
import { AnalyticsView } from './pages/AnalyticsView';
import { ReportsView } from './pages/ReportsView';
import { AIAssistantView } from './components/AIAssistantView';
import { ContractsExplorer } from './pages/ContractsExplorer';
import { ProjectProvider } from './context/ProjectContext';

export function App() {
  return (
    <ProjectProvider>
      <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 font-sans">
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto w-full">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/projects" element={<ProjectsList />} />
              <Route path="/projects/new" element={<CreateProjectPage />} />
              <Route path="/requirements" element={<RequirementsView />} />
              <Route path="/tests" element={<TestsView />} />
              <Route path="/executions" element={<ExecutionsView />} />
              <Route path="/failures" element={<FailuresView />} />
              <Route path="/audits" element={<AuditsView />} />
              <Route path="/analytics" element={<AnalyticsView />} />
              <Route path="/reports" element={<ReportsView />} />
              <Route path="/assistant" element={<AIAssistantView />} />
              <Route path="/contracts" element={<ContractsExplorer />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </ProjectProvider>
  );
}

export default App;
