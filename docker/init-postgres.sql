-- CodeSentinel Database Initialization Script
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Projects Table for Project domain persistence
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    repository_url VARCHAR(512) NOT NULL,
    default_branch VARCHAR(64) NOT NULL DEFAULT 'main',
    provider VARCHAR(32) NOT NULL DEFAULT 'GITHUB',
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    total_files VARCHAR(32) DEFAULT '0',
    total_lines_of_code VARCHAR(32) DEFAULT '0',
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_id ON projects(id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- Code Analyses Table
CREATE TABLE IF NOT EXISTS code_analyses (
    project_id VARCHAR(36) PRIMARY KEY,
    total_entities INTEGER NOT NULL DEFAULT 0,
    total_classes INTEGER NOT NULL DEFAULT 0,
    total_functions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_code_analyses_project_id ON code_analyses(project_id);
CREATE INDEX IF NOT EXISTS idx_code_analyses_created_at ON code_analyses(created_at);

-- Requirements Table
CREATE TABLE IF NOT EXISTS requirements (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    identifier VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    req_type VARCHAR(32) DEFAULT 'FUNCTIONAL',
    priority VARCHAR(32) DEFAULT 'MEDIUM',
    status VARCHAR(32) DEFAULT 'DRAFT',
    acceptance_criteria_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requirements_id ON requirements(id);
CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_identifier ON requirements(identifier);

-- Software System Models Table
CREATE TABLE IF NOT EXISTS software_system_models (
    project_id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_software_system_models_project_id ON software_system_models(project_id);

-- Initialization confirmation
SELECT 'CodeSentinel PostgreSQL Database Initialized Successfully' AS status;
