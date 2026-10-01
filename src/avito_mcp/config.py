"""Settings read from environment variables, with defaults for macOS."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


@dataclass(frozen=True)
class Config:
    home: Path
    profile_dir: Path
    chrome_binary: Path
    cdp_port: int
    min_nav_interval: float
    shots_dir: Path
    chrome_args: tuple[str, ...]
    before_start_cmd: str
    after_idle_cmd: str
    idle_seconds: int
    transport: str
    http_host: str
    http_port: int

    @property
    def cdp_url(self) -> str:
        return f"http://127.0.0.1:{self.cdp_port}"


def load_config() -> Config:
    home = _env_path("AVITO_MCP_HOME", Path.home() / ".avito-mcp")
    return Config(
        home=home,
        profile_dir=_env_path("AVITO_MCP_PROFILE", home / "chrome-profile"),
        chrome_binary=_env_path(
            "AVITO_MCP_CHROME",
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ),
        cdp_port=int(os.environ.get("AVITO_MCP_PORT", "9333")),
        min_nav_interval=float(os.environ.get("AVITO_MCP_MIN_INTERVAL", "2.5")),
        shots_dir=home / "screenshots",
        # extra Chrome flags, e.g. "--disable-dev-shm-usage --disable-gpu" on a headless Linux server
        chrome_args=tuple(os.environ.get("AVITO_MCP_CHROME_ARGS", "").split()),
        # shell hooks: run before Chrome is launched / after it was closed for inactivity
        before_start_cmd=os.environ.get("AVITO_MCP_BEFORE_START", ""),
        after_idle_cmd=os.environ.get("AVITO_MCP_AFTER_IDLE", ""),
        idle_seconds=int(os.environ.get("AVITO_MCP_IDLE_SECONDS", "0")),
        transport=os.environ.get("AVITO_MCP_TRANSPORT", "stdio"),
        http_host=os.environ.get("AVITO_MCP_HTTP_HOST", "127.0.0.1"),
        http_port=int(os.environ.get("AVITO_MCP_HTTP_PORT", "8793")),
    )
