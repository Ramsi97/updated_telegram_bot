# app/instances.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout

# Set a long timeout (15 minutes) for slow processing/downloads
timeout = ClientTimeout(total=900)
session = AiohttpSession(timeout=timeout)

bot = Bot(token=settings.TELEGRAM_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()