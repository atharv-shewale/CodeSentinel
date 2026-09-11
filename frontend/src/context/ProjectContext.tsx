import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { ApiClient } from '../services/api';
import { Project } from '../types';

interface ProjectContextType {
  selectedProjectId: string | null;
  selectedProject: Project | null;
  projects: Project[];
  loading: boolean;
  error: string | null;
  setSelectedProjectId: (id: string | null) => void;
  selectProject: (project: Project | null) => void;
  refreshProjects: () => Promise<Project[]>;
}

const STORAGE_KEY = 'codesentinel_selected_project_id';

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedProjectId, setSelectedProjectIdState] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY) || null;
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshProjects = useCallback(async (): Promise<Project[]> => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getProjects();
      setProjects(data || []);

      // If we currently have a selectedProjectId, check if it's still in the list
      setSelectedProjectIdState((current) => {
        if (current && data?.some((p) => p.id === current)) {
          return current;
        }
        // If current is invalid or null, but we have projects in the DB, default to first or keep null
        if (data && data.length > 0) {
          const firstId = data[0].id;
          localStorage.setItem(STORAGE_KEY, firstId);
          return firstId;
        }
        localStorage.removeItem(STORAGE_KEY);
        return null;
      });

      return data || [];
    } catch (err: any) {
      console.error('Failed to load projects:', err);
      setError(err.message || 'Failed to connect to backend.');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  const setSelectedProjectId = (id: string | null) => {
    setSelectedProjectIdState(id);
    if (id) {
      localStorage.setItem(STORAGE_KEY, id);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const selectProject = (project: Project | null) => {
    if (project) {
      setSelectedProjectId(project.id);
    } else {
      setSelectedProjectId(null);
    }
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId) || null;

  return (
    <ProjectContext.Provider
      value={{
        selectedProjectId,
        selectedProject,
        projects,
        loading,
        error,
        setSelectedProjectId,
        selectProject,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = (): ProjectContextType => {
  const context = useContext(ProjectContext);
  if (!context) {
    return {
      selectedProjectId: null,
      selectedProject: null,
      projects: [],
      loading: false,
      error: null,
      setSelectedProjectId: () => {},
      selectProject: () => {},
      refreshProjects: async () => [],
    };
  }
  return context;
};
