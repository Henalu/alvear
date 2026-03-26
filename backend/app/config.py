from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    current = Path(__file__).resolve()
    backend_dir = current.parents[1]
    repo_root = current.parents[2]

    for candidate in (repo_root / ".env", backend_dir / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


_load_env()


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    api_key: str
    base_url: str
    model_name: str


class Config:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    BACKEND_DIR = Path(__file__).resolve().parents[1]

    APP_NAME = "Alvear"
    APP_ENV = os.getenv("APP_ENV", "development")

    UPLOAD_FOLDER = str(BACKEND_DIR / "uploads")
    LOG_FOLDER = str(BACKEND_DIR / "logs")
    SCRIPTS_DIR = str(BACKEND_DIR / "scripts")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen2.5:14b")

    # Optional dedicated fast model for high-volume simulation runs.
    LLM_BOOST_MODEL_NAME = os.getenv("LLM_BOOST_MODEL_NAME", LLM_MODEL_NAME)
    LLM_REQUEST_TIMEOUT_SECONDS = int(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "0"))

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "alvear-local")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "1200"))
    DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "150"))
    DEFAULT_AGENT_CAP = int(os.getenv("DEFAULT_AGENT_CAP", "24"))
    DEFAULT_MAX_ROUNDS = int(os.getenv("DEFAULT_MAX_ROUNDS", "12"))
    DEFAULT_SIMULATION_HOURS = int(os.getenv("DEFAULT_SIMULATION_HOURS", "12"))
    GRAPH_SEARCH_LIMIT = int(os.getenv("GRAPH_SEARCH_LIMIT", "12"))

    ZEP_API_KEY: Optional[str] = os.getenv("ZEP_API_KEY")

    @classmethod
    def ensure_directories(cls) -> None:
        for path in (cls.UPLOAD_FOLDER, cls.LOG_FOLDER):
            os.makedirs(path, exist_ok=True)

    @classmethod
    def llm_provider_config(cls) -> LLMProviderConfig:
        return LLMProviderConfig(
            provider=cls.LLM_PROVIDER,
            api_key=cls.LLM_API_KEY,
            base_url=cls.LLM_BASE_URL,
            model_name=cls.LLM_MODEL_NAME,
        )
