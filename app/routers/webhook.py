# app/routers/webhook.py
from fastapi import APIRouter, Request, Depends
from aiogram import types
from app.instances import bot, dp, scheduler
from app.dependencies import get_processing_service

router = APIRouter()
@router.post("/webhook")
async def telegram_webhook(
    request: Request, 
    processor=Depends(get_processing_service)
):
    update_data = await request.json()
    
    # --- THE FIX ---
    # Use model_validate instead of Update(**update_data)
    update = types.Update.model_validate(update_data, context={"bot": bot})
    # ----------------

    await dp.feed_update(
        bot, 
        update, 
        processor=processor, 
        scheduler=scheduler, 
        dp=dp
    )
    return {"ok": True}