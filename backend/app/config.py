"""Application configuration, loaded from environment variables.

Defaults let the app run with zero setup for the POC (design §9).
"""
import os


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./locker.db")
        self.storage_unit_rate: float = float(os.getenv("STORAGE_UNIT_RATE", "1"))
        self.port: int = int(os.getenv("PORT", "8000"))
        # A held locker that isn't confirmed within this many seconds is released.
        self.hold_timeout_seconds: int = int(os.getenv("HOLD_TIMEOUT_SECONDS", "120"))


settings = Settings()
