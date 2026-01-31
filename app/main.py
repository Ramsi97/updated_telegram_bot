from fastapi import FastAPI
from app.routers import webhook
from app.config import settings

app = FastAPI(
    title="Telegram PDF Bot",
    description="Convert PDF files to images via Telegram",
    version="1.0.0"
)

# Include routes
app.include_router(webhook.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "ok", "service": "Telegram PDF Bot"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)