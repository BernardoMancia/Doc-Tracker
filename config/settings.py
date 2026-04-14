from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "sqlite+aiosqlite:///./osint_dlp.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8443
    debug: bool = False

    search_delay_min: float = 2.0
    search_delay_max: float = 5.0
    max_results_per_dork: int = 25
    max_file_size_mb: int = 50
    download_timeout: int = 30

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    proxy_url: str = ""

    scan_schedule_hours: str = "8,14,22"
    server_mode: bool = True
    dashboard_url: str = "http://82.112.245.99:8443"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def schedule_hours(self) -> list[int]:
        return [int(h.strip()) for h in self.scan_schedule_hours.split(",")]


settings = Settings()
