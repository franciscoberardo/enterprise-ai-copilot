from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", extra="ignore"
    )

    business_api_url: HttpUrl = "http://127.0.0.1:3001"
    api_timeout_seconds: float = Field(default=10, gt=0, le=120)
    mcp_server_url: HttpUrl = "http://127.0.0.1:8001/mcp"
    mcp_timeout_seconds: float = Field(default=15, gt=0, le=120)

    cors_origins: list[str] = ["http://localhost:5173"]

    context_token_limit: int = Field(default=6000, ge=1000)
    context_recent_turns: int = Field(default=6, ge=1)


settings = AgentSettings()
