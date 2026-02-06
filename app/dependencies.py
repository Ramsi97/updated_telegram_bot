# app/dependencies.py
from app.instances import bot  
from services.processing_service import ProcessingService

def get_processing_service():
    # Pass the bot instance to the service
    return ProcessingService(bot=bot)