# app/dependencies.py
from app.instances import processor

def get_processing_service():
    # Return the singleton processor shared across all requests
    return processor