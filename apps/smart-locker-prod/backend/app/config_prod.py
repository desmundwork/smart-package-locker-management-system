"""Production configuration overlay.

Extends the POC Settings with auth-related settings. This module REPLACES the
POC's app/config.py in the production image (the build script copies it over
app/config.py). Keeping it separate in source makes the production-only
additions obvious in review.
"""
import os


def _require(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Required environment variable {name} is not set")
    return val


class Settings:
    def __init__(self) -> None:
        # ---- POC settings (unchanged) ----
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./locker.db")
        self.storage_unit_rate: float = float(os.getenv("STORAGE_UNIT_RATE", "1"))
        self.port: int = int(os.getenv("PORT", "8000"))
        self.hold_timeout_seconds: int = int(os.getenv("HOLD_TIMEOUT_SECONDS", "120"))

        # ---- Production auth settings ----
        # JWT signing secret. MUST be provided in production; no insecure default.
        self.jwt_secret: str = _require("JWT_SECRET")
        self.access_token_ttl_minutes: int = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60"))

        # Bootstrap users seeded on first startup (idempotent). Passwords are
        # hashed before storage. Supply strong values via the environment.
        self.seed_admin_username: str = os.getenv("SEED_ADMIN_USERNAME", "admin")
        self.seed_admin_password: str = os.getenv("SEED_ADMIN_PASSWORD", "")
        self.seed_agent_username: str = os.getenv("SEED_AGENT_USERNAME", "agent")
        self.seed_agent_password: str = os.getenv("SEED_AGENT_PASSWORD", "")
        self.seed_customer_username: str = os.getenv("SEED_CUSTOMER_USERNAME", "customer")
        self.seed_customer_password: str = os.getenv("SEED_CUSTOMER_PASSWORD", "")

        # Which view this container instance serves. The gateway sets this per
        # subdomain. One of: landing, admin, agent, customer.
        self.view: str = os.getenv("VIEW", "landing")


settings = Settings()
