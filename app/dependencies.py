from services.telegram_service import TelegramService
from services.processing_service import ProcessingService
from app.config import settings

def get_telegram_service() -> TelegramService:
    return TelegramService(token=settings.BOT_TOKEN)

def get_processing_service() -> ProcessingService:
    telegram_service = get_telegram_service()
    return ProcessingService(telegram_service=telegram_service)