FROM python:3.11-slim

# 1. Install compilers
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Libs
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 3. DOWNLOAD BETTER MODEL (Qwen 2.5 - 3B - Quantized)
RUN wget -O /app/model.gguf "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"

# 4. Copy Script
COPY english_processor.py .

# 5. Run
CMD ["python", "english_processor.py"]