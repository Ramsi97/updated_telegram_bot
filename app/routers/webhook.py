from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from services.telegram_service import TelegramService
from services.processing_service import ProcessingService
from app.dependencies import get_telegram_service, get_processing_service
from app.config import settings
router = APIRouter(tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    telegram: TelegramService = Depends(get_telegram_service),
    processor: ProcessingService = Depends(get_processing_service)
):
    try:
        update = await request.json()
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")

        
        if not chat_id:
            return {"status": "error", "message": "No chat ID found"}

        authorized_ids = [
            int(uid.strip()) for uid in settings.AUTHORIZED_USER_IDS.split(",") if uid.strip()
        ]

        if user_id not in authorized_ids:
            print(f"🚫 Unauthorized user: {user_id}")
            await telegram.send_message(
                chat_id,
                "❌ Sorry, this bot is for paid users only.\n"
                "Please contact support to get access."
            )
            return {"status": "unauthorized"}
            
        # Handle PDF document
        if "document" in message:
            document = message["document"]
            if document.get("mime_type") == "application/pdf":
                file_id = document["file_id"]
                
                # Process in background
                background_tasks.add_task(
                    processor.process_pdf_from_telegram,
                    file_id=file_id,
                    chat_id=chat_id
                )
                return {"status": "processing"}
            else:
                await telegram.send_message(chat_id, "Please send a PDF file.")
        
        # Handle text commands
        elif "text" in message:
            text = message["text"]
            if text.startswith("/start"):
                await telegram.send_message(
                    chat_id, 
                    """Welcome to the National ID Fayda Printable Converter Service! 🎉

🪪 To get your printable ID card:
1. Visit the official Fayda website:
resident.fayda.et/PrintableCredential (https://resident.fayda.et/)
2. Enter your FCN/FAN and verify using the SMS OTP you receive.
3. Tap Download Printable Credential and download your PDF file.
4. Send the downloaded PDF file here to this bot.

🤖 The bot will automatically convert your PDF into a print-ready National ID card.
━━━━━━━━━━━━━━━━━━━━━━━

እንኳን ወደ ብሔራዊ መታወቂያ ፋይዳ ካርድ ሊታተም የሚችል መቀየሪያ አገልግሎት በደህና መጡ! 🎉

🪪 ሊታተም የሚችል መታወቂያ ካርድዎን ለማግኘት፡-
1. በመጀመሪያ የፋይዳ ድረ-ገጽ ይጎብኙ፡-
resident.fayda.et/PrintableCredential (https://resident.fayda.et/)

2. የእርስዎን FCN/FAN ያስገቡ እና የሚቀበሉትን SMS OTP በመጠቀም ያረጋግጡ።

3. Download Printable Credential የሚለውን ይጫኑ እና የፒዲኤፍ ፋይልዎን ያውርዱ።

4. የወረደውን ፒዲኤፍ ፋይል ቀጥታ ወደዚህ ቦት ይላኩ።

🤖 ቦቱ በራሱ ፒዲኤፍዎን ለህትመት ዝግጁ ወደሆነ ብሄራዊ መታወቂያ ካርድ ለውጦ ይልክልዎታል።"""
                )
            else:
                await telegram.send_message(
                    chat_id,
                    "I only process PDF files. Please send a PDF document."
                )
        
        return {"status": "handled"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/set-webhook")
async def set_webhook(telegram: TelegramService = Depends(get_telegram_service)):
    """Call this once to set up the webhook with Telegram"""
    success = await telegram.set_webhook()
    return {"status": "webhook set" if success else "webhook setup failed"}