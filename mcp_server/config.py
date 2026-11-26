from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"), extra="ignore"
    )

    business_api_url: HttpUrl = "http://127.0.0.1:3001"
    api_timeout_seconds: float = Field(default=10, gt=0, le=120)
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8001, gt=0, le=65535)
