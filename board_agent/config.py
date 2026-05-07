from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    mode: str = "auto"
    host: str = "0.0.0.0"
    port: int = 8080
    static_dir: Path = Path("web")

    @property
    def mock_mode(self) -> bool:
        return self.mode.lower() == "mock"


def load_settings() -> Settings:
    return Settings(
        mode=os.getenv("RK_BOX_MODE", "auto"),
        host=os.getenv("RK_BOX_HOST", "0.0.0.0"),
        port=int(os.getenv("RK_BOX_PORT", "8080")),
        static_dir=Path(os.getenv("RK_BOX_STATIC_DIR", "web")),
    )
