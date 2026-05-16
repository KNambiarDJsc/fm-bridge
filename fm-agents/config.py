"""
FM Trading Agency - Agent Pipeline Config
"""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings

class AgentSettings(BaseSettings):
    # LLM Provider
    llm_provider: str = "gemini"

    # Gemini
    google_api_key: str = ""
    gemini_deep_model: str = "gemini-2.5-pro-preview-06-05"
    gemini_quick_model: str = "gemini-2.5-flash"
    gemini_lite_model: str = "gemini-2.5-flash-lite-preview-06-17"

    # Claude
    anthropic_api_key: str = ""
    claude_deep_model: str = "claude-sonnet-4-5"
    claude_quick_model: str = "claude-haiku-4-5-20251001"

    # OpenAI
    openai_api_key: str = ""

    # Bridge
    bridge_url: str = "http://localhost:8002"
    bridge_timeout: int = 10

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "fm-trading-agency"
    langsmith_tracing: str = "false"

    # Pipeline
    agent_timeout_s: int = 1000
    pipeline_timeout_s: int = 1000

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
