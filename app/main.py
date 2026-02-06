# app/main.py
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.instances import bot, dp, scheduler  # Import from instances, NOT main
from app.routers import webhook
from app.routers.bot_handlers import router as bot_router
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    scheduler.start()
    dp.include_router(bot_router)
    
    webhook_url = f"{settings.WEBHOOK_URL}/webhook"
    await bot.set_webhook(url=webhook_url, drop_pending_updates=False)
    
    # Store in state for easy access if needed
    app.state.bot = bot
    app.state.dp = dp
    app.state.scheduler = scheduler
    
    print(f"🚀 Bot started. Webhook: {webhook_url}")
    yield
    
    # SHUTDOWN
    scheduler.shutdown()
    await bot.session.close()

app = FastAPI(title="National ID Bot", lifespan=lifespan)
app.include_router(webhook.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)