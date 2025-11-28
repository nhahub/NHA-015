FROM python:3.11-slim

# 1. Install System Dependencies & Chromium
# We install 'chromium' and 'chromium-driver' directly from apt.

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Set Environment Variables
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 3. Python Setup
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY youm7.py .

# 5. Run
CMD ["python", "youm7.py"]