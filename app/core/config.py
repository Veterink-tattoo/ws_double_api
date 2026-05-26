import os
from pydantic_settings import BaseSettings
from app.core.meta import get_secret

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    BLAZE_WS_URL: str = os.getenv(
        "BLAZE_WS_URL", 
        "wss://api-gaming.blaze.bet.br/replication/?EIO=3&transport=websocket"
    )

    # Core Security Keys (Loaded via Docker Secrets, Zero .env)
    SECRET_KEY: str = get_secret("SECRET_KEY", "super-secret-key-change-it-in-production")
    ADMIN_TOKEN: str = get_secret("ADMIN_TOKEN", "admin_double_secret_key_8e72ba63f10d48f98a28")
    INTERNAL_KEY: str = get_secret("INTERNAL_KEY", "vettipster_internal_double_key_5d2b1f8c9e0a4f3a")

    # Dynamic Database URL Construction
    @property
    def DATABASE_URL(self) -> str:
        db_user = os.getenv("DB_U")
        db_name = os.getenv("DB_N")
        db_host = os.getenv("DB_H")
        db_password = get_secret("POSTGRES_PASSWORD")

        if db_user and db_name and db_host and db_password:
            # PostgreSQL URL using asyncpg
            return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}"
        
        # Default SQLite URL using aiosqlite (fully self-contained)
        return "sqlite+aiosqlite:////app/data/db.sqlite3"

settings = Settings()
