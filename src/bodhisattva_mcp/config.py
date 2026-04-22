"""Runtime settings for the Bodhisattva MCP server.

Settings come from environment variables (with optional ``.env`` loading
handled externally). The LLM provider is the only hard requirement on the
free tier.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["anthropic", "openai"]


def _default_journal_path() -> Path:
    return Path.home() / ".bodhisattva" / "journal.sqlite"


class Settings(BaseSettings):
    """Typed runtime settings for the MCP server."""

    model_config = SettingsConfigDict(
        env_prefix="BODHISATTVA_",
        env_file=None,
        extra="ignore",
    )

    llm_provider: Provider = "anthropic"
    llm_model: str = "claude-haiku-4-5-20251001"
    web_port: int = 8473
    journal_path: Path = Path()  # Placeholder; resolved in model_post_init.
    domain: Literal["general", "coaching", "mental_health"] = "general"

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        env_path = os.environ.get("BODHISATTVA_JOURNAL_PATH")
        if env_path:
            object.__setattr__(self, "journal_path", Path(env_path))
        elif self.journal_path == Path():
            object.__setattr__(self, "journal_path", _default_journal_path())

    def build_model(self) -> BaseChatModel:
        """Build the LangChain chat model from provider settings."""
        if self.llm_provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required when BODHISATTVA_LLM_PROVIDER=anthropic"
                )
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=self.llm_model, api_key=api_key)

        if self.llm_provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required when BODHISATTVA_LLM_PROVIDER=openai")
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=self.llm_model, api_key=api_key)

        raise ValueError(f"Unsupported provider: {self.llm_provider}")
