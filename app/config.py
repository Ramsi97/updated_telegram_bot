from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Telegram Bot Settings
    TELEGRAM_TOKEN: str
    WEBHOOK_URL: str
    API_BASE_URL: str = "https://api.telegram.org"
    BOT_NAME: str = "National ID converter"
    
    AUTHORIZED_USER_IDS: str = ""

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "storage" / "outputs"

    # Pydantic V2 configuration style
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",           # Important: ignores extra fields in .env
        protected_namespaces=(),  # Stops the "model_" warning
        case_sensitive=True
    )
    
    @property
    def authorized_users(self) -> set[int]:
        """Return authorized user IDs as a set of integers."""
        try:
            if not self.AUTHORIZED_USER_IDS:
                return set()
            return {int(uid.strip()) for uid in self.AUTHORIZED_USER_IDS.split(",")}
        except Exception as e:
            print(f"⚠️ Error parsing AUTHORIZED_USER_IDS: {e}")
            return set()

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)