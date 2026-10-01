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
    )
