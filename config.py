import os
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger("app.config")

def mask_key(key: str | None) -> str:
    """Mask sensitive API key strings for secure logging."""
    if not key or len(key) <= 8:
        return "********"
    return f"{key[:4]}****{key[-4:]}"

class Settings(BaseSettings):
    SELLVIA_API_KEY: str = os.getenv("SELLVIA_API_KEY", "")
    SELLVIA_OLD_API_KEY: str | None = os.getenv("SELLVIA_OLD_API_KEY", None)
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "default-change-me")
    SELLVIA_BASE_URL: str = os.getenv("SELLVIA_BASE_URL", "https://sellviaapp.com/api/v1")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

def log_key_status():
    logger.info(f"Active Sellvia Key Loaded: {mask_key(settings.SELLVIA_API_KEY)}")
    if settings.SELLVIA_OLD_API_KEY:
        logger.info(f"Fallback Sellvia Key Active: {mask_key(settings.SELLVIA_OLD_API_KEY)}")

log_key_status()
