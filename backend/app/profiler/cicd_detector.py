"""
CodeSentinel Profiler: Docker & CI/CD Pipeline Detector.

Discovers container configurations (Docker, Compose) and CI/CD pipelines
(GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure Pipelines, etc.).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List


class CicdDetector:
    """Detects containerization artifacts and continuous integration workflows."""

    @classmethod
    def detect_all(cls, root_dir: str) -> Dict[str, Any]:
        """
        Scan repository root and config paths for Docker and CI/CD files.
        """
        docker_present = False
        docker_files: List[str] = []

        ci_present = False
        ci_systems: List[str] = []
        ci_files: List[str] = []

        # 1. Docker Detection
        docker_candidates = [
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "compose.yml", "compose.yaml", "Containerfile"
        ]
        for name in os.listdir(root_dir):
            if name in docker_candidates or name.lower().startswith("dockerfile.") or name.lower().startswith("compose."):
                docker_present = True
                docker_files.append(name)

        # Check docker/ subfolder if present
        docker_subfolder = os.path.join(root_dir, "docker")
        if os.path.isdir(docker_subfolder):
            docker_present = True
            for f in os.listdir(docker_subfolder):
                docker_files.append(f"docker/{f}")

        # 2. CI/CD Detection
        # GitHub Actions
        gh_workflows = os.path.join(root_dir, ".github", "workflows")
        if os.path.isdir(gh_workflows):
            workflow_files = [
                f".github/workflows/{f}" for f in os.listdir(gh_workflows)
                if f.endswith((".yml", ".yaml"))
            ]
            if workflow_files:
                ci_present = True
                ci_systems.append("github_actions")
                ci_files.extend(workflow_files)

        # GitLab CI
        if os.path.isfile(os.path.join(root_dir, ".gitlab-ci.yml")):
            ci_present = True
            ci_systems.append("gitlab_ci")
            ci_files.append(".gitlab-ci.yml")

        # Jenkins
        if os.path.isfile(os.path.join(root_dir, "Jenkinsfile")):
            ci_present = True
            ci_systems.append("jenkins")
            ci_files.append("Jenkinsfile")

        # CircleCI
        circleci_config = os.path.join(root_dir, ".circleci", "config.yml")
        if os.path.isfile(circleci_config):
            ci_present = True
            ci_systems.append("circleci")
            ci_files.append(".circleci/config.yml")

        # Azure Pipelines
        for az_file in ("azure-pipelines.yml", "azure-pipelines.yaml"):
            if os.path.isfile(os.path.join(root_dir, az_file)):
                ci_present = True
                ci_systems.append("azure_devops")
                ci_files.append(az_file)

        # Bitbucket Pipelines
        if os.path.isfile(os.path.join(root_dir, "bitbucket-pipelines.yml")):
            ci_present = True
            ci_systems.append("bitbucket_pipelines")
            ci_files.append("bitbucket-pipelines.yml")

        return {
            "docker": {
                "detected": docker_present,
                "files": docker_files,
            },
            "ci_cd": {
                "detected": ci_present,
                "systems": sorted(list(set(ci_systems))),
                "files": ci_files,
            },
        }
