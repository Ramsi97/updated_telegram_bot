# app/instances.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout

from services.processing_service import ProcessingService

# Set patient timeouts for slow processing/downloads
# Extreme patience for slow downloads (especially for the AI model and batch PDFs)
# connect=90s, sock_read=300s (5 min per chunk), total=1200s (20 min)
timeout = ClientTimeout(total=1200, connect=90, sock_read=300)
session = AiohttpSession(timeout=timeout)

bot = Bot(token=settings.TELEGRAM_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

# Singleton processor to ensure the lock is shared globally
processor = ProcessingService(bot=bot)