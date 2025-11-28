FROM python:3.11-slim

# 1. Install System Dependencies & Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Environment Variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 3. Python Setup
WORKDIR /app

# Upgrade pip first
RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# 4. Copy Code 
COPY ahram.py .

# 5. Run 
CMD ["python", "ahram.py"]