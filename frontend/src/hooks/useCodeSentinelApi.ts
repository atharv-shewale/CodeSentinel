import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Project, TestCase, Requirement } from '../types';

export function useCodeSentinelData() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tests, setTests] = useState<TestCase[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [projRes, testRes, reqRes] = await Promise.all([
          apiService.getProjects(),
          apiService.getTests(),
          apiService.getRequirements(),
        ]);

        if (projRes.success && projRes.data) setProjects(projRes.data);
        if (testRes.success && testRes.data) setTests(testRes.data);
        if (reqRes.success && reqRes.data) setRequirements(reqRes.data);
      } catch (err: any) {
        setError(err.message || 'Failed to load platform data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return { projects, tests, requirements, loading, error };
}
