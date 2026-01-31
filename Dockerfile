FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for all your packages
RUN apt-get update && apt-get install -y \
    libmagic1 \
    poppler-utils \
    ghostscript \
    tesseract-ocr \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxml2-dev \
    libxslt1-dev \
    default-jre-headless \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto \
    fonts-freefont-otf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]