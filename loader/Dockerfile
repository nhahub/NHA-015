FROM python:3.11-slim

# Install compilers for AI math
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#DOWNLOAD THE MULTILINGUAL MODEL FOR EMBEDDINGS
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY etl_loader.py .

CMD ["python", "etl_loader.py"]