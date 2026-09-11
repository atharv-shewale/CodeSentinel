"""
CodeSentinel Backend: Core Configuration.

Loads environment variables and application settings using Pydantic Settings.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General
    ENVIRONMENT: str = Field(default="development", description="Environment mode: development, testing, production.")
    DEBUG: bool = Field(default=True, description="Debug mode flag.")
    PROJECT_NAME: str = Field(default="CodeSentinel", description="Application name.")
    API_V1_PREFIX: str = Field(default="/api/v1", description="Prefix for v1 REST endpoints.")
    SECRET_KEY: str = Field(default="codesentinel-insecure-dev-secret-key-change-in-production-123456", description="Cryptographic secret key.")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origin domains."
    )

    # PostgreSQL
    POSTGRES_SERVER: str = Field(default="localhost", description="PostgreSQL host.")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port.")
    POSTGRES_USER: str = Field(default="codesentinel", description="PostgreSQL username.")
    POSTGRES_PASSWORD: str = Field(default="codesentinel_secret", description="PostgreSQL password.")
    POSTGRES_DB: str = Field(default="codesentinel_db", description="PostgreSQL database name.")

    @property
    def DATABASE_URL(self) -> str:
        """Construct PostgreSQL SQLAlchemy database URL."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Neo4j (Knowledge Graph)
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j bolt connection URI.")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username.")
    NEO4J_PASSWORD: str = Field(default="codesentinel_graph_secret", description="Neo4j password.")

    # Qdrant (Vector Database)
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant host.")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant HTTP port.")
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant API key if secured.")
    QDRANT_COLLECTION: str = Field(default="codesentinel_embeddings", description="Default Qdrant collection.")

    # Redis (Job Queue & Cache)
    REDIS_HOST: str = Field(default="localhost", description="Redis host.")
    REDIS_PORT: int = Field(default=6379, description="Redis port.")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password.")
    REDIS_DB: int = Field(default=0, description="Redis database index.")
    REDIS_JOB_QUEUE: str = Field(default="codesentinel:jobs:queue", description="Redis list key for queued jobs.")
    REDIS_JOB_PREFIX: str = Field(default="codesentinel:job:", description="Redis key prefix for job status hashes.")

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis connection URL."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Sandbox Execution (Phase 4 placeholder configuration)
    SANDBOX_DOCKER_NETWORK: str = Field(default="codesentinel_sandbox_net", description="Isolated Docker network for test sandbox.")
    SANDBOX_TIMEOUT_SECONDS: int = Field(default=300, description="Max execution timeout in seconds.")

    # LLM Inference
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key for high-speed LLM inference.")


settings = Settings()
